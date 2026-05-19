from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json

app = Flask(__name__)

# =========================
# CONFIG
# =========================
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev_key")

database_url = os.getenv("DATABASE_URL")

# ✅ NO rompe tu base actual
if not database_url:
    database_url = "sqlite:///database.db"

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================
# LOGIN CONFIG
# =========================
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

COLOMBIA_TZ = ZoneInfo("America/Bogota")
UTC_TZ = ZoneInfo("UTC")

# =========================
# MODELOS (compatibles con tu BD)
# =========================
class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Message(db.Model):
    __tablename__ = "message"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])
    user = db.relationship("User", foreign_keys=[user_id])

# =========================
# LOGIN LOADER
# =========================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================
# FILTROS
# =========================
@app.template_filter("colombia_time")
def colombia_time(dt):
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(COLOMBIA_TZ)

@app.template_filter("datetime_format")
def datetime_format(dt, fmt="%d/%m %H:%M"):
    return dt.strftime(fmt) if dt else ""

# =========================
# CHAT
# =========================
def get_chat_partner():
    # 🔁 tu lógica original
    if current_user.id == 2:
        return User.query.get(3)
    elif current_user.id == 3:
        return User.query.get(2)
    return None

# =========================
# RUTAS PRINCIPALES
# =========================
@app.route("/")
def home():
    latest_messages = Message.query.order_by(Message.created_at.desc()).limit(6).all()
    return render_template("home.html", latest_messages=latest_messages)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("wall"))

        flash("Usuario o contraseña incorrectos")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            flash("Completa los campos")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("Usuario ya existe")
            return redirect(url_for("register"))

        user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )

        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("wall"))

    return render_template("register.html")

# =========================
# WALL (chat clásico)
# =========================
@app.route("/wall")
@login_required
def wall():
    partner = get_chat_partner()
    return render_template("wall.html", partner=partner)

# =========================
# ✅ API CHAT SIN REFRESH
# =========================
@app.route("/api/messages")
@login_required
def api_messages():
    partner = get_chat_partner()

    if not partner:
        return jsonify([])

    messages = Message.query.filter(
        or_(
            (Message.sender_id == current_user.id) & (Message.receiver_id == partner.id),
            (Message.sender_id == partner.id) & (Message.receiver_id == current_user.id)
        )
    ).order_by(Message.created_at.asc()).all()

    return jsonify([
        {
            "id": m.id,
            "content": m.content,
            "sender": m.sender.username if m.sender else "Usuario",
            "sender_id": m.sender_id,
            "created_at": m.created_at.strftime("%H:%M")
        }
        for m in messages
    ])

@app.route("/api/send", methods=["POST"])
@login_required
def api_send():
    data = request.get_json(silent=True) or {}

    content = data.get("content", "").strip()
    partner = get_chat_partner()

    if content and partner:
        msg = Message(
            content=content,
            user_id=current_user.id,
            sender_id=current_user.id,
            receiver_id=partner.id
        )

        db.session.add(msg)
        db.session.commit()

        return jsonify({"ok": True})

    return jsonify({"ok": False})

# =========================
# ADMIN SEGURO
# =========================
@app.route("/admin")
@login_required
def admin():
    if not current_user.is_admin:
        abort(403)
    return render_template("admin.html")

# =========================
# INIT
# =========================
with app.app_context():
    db.create_all()

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
