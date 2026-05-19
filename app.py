from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import os

app = Flask(__name__)

# 🔐 CONFIG
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave_segura_dev")
database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise ValueError("DATABASE_URL no configurada")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# 🔐 LOGIN
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

COLOMBIA_TZ = ZoneInfo("America/Bogota")
UTC_TZ = ZoneInfo("UTC")

ADMIN_USER_ID = 2

# ----------------------------
# 📦 MODELOS
# ----------------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])

class UserSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    login_at = db.Column(db.DateTime, default=datetime.utcnow)
    logout_at = db.Column(db.DateTime)
    duration = db.Column(db.Integer)

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    costs = db.relationship("ActivityCost", backref="activity", cascade="all, delete-orphan")
    sales = db.relationship("ActivitySale", backref="activity", cascade="all, delete-orphan")
    payers = db.relationship("ActivityPayer", backref="activity", cascade="all, delete-orphan")

class ActivityCost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    activity_id = db.Column(db.Integer, db.ForeignKey("activity.id"))

class ActivitySale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    activity_id = db.Column(db.Integer, db.ForeignKey("activity.id"))

class ActivityPayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    activity_id = db.Column(db.Integer, db.ForeignKey("activity.id"))

# ----------------------------
# 🔐 LOGIN
# ----------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------------------
# 🧠 CHAT
# ----------------------------

def get_chat_partner():
    if current_user.id == 2:
        return User.query.get(3)
    elif current_user.id == 3:
        return User.query.get(2)
    return None

# ----------------------------
# 🌐 RUTAS
# ----------------------------

@app.route("/")
def home():
    messages = Message.query.order_by(Message.created_at.desc()).limit(6).all()
    return render_template("home.html", latest_messages=messages)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

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

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()

        if user and check_password_hash(user.password_hash, request.form["password"]):
            login_user(user)
            return redirect(url_for("wall"))

        flash("Credenciales incorrectas")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

@app.route("/wall")
@login_required
def wall():
    partner = get_chat_partner()
    return render_template("wall.html", partner=partner)

# ----------------------------
# ⚡ API CHAT (SIN REFRESH)
# ----------------------------

@app.route("/api/messages")
@login_required
def api_messages():
    partner = get_chat_partner()
    if not partner:
        return jsonify([])

    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == partner.id)) |
        ((Message.sender_id == partner.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()

    return jsonify([{
        "id": m.id,
        "content": m.content,
        "sender": m.sender.username,
        "sender_id": m.sender_id,
        "created_at": m.created_at.strftime("%H:%M")
    } for m in messages])

@app.route("/api/send", methods=["POST"])
@login_required
def api_send():
    data = request.get_json()
    content = data.get("content", "").strip()
    partner = get_chat_partner()

    if content and partner:
        msg = Message(
            content=content,
            sender_id=current_user.id,
            receiver_id=partner.id
        )
        db.session.add(msg)
        db.session.commit()

        return jsonify({"ok": True})

    return jsonify({"ok": False})

# ----------------------------
# 💰 ACTIVIDADES
# ----------------------------

@app.route("/activities", methods=["GET", "POST"])
@login_required
def activities():
    if request.method == "POST":
        act = Activity(
            title=request.form["title"],
            description=request.form.get("description")
        )
        db.session.add(act)
        db.session.commit()
        return redirect(url_for("activity_detail", activity_id=act.id))

    return render_template("activities.html", activities=Activity.query.all())

@app.route("/activities/<int:activity_id>")
@login_required
def activity_detail(activity_id):
    act = Activity.query.get_or_404(activity_id)

    total_costs = sum(c.amount for c in act.costs)
    total_sales = sum(s.amount for s in act.sales)

    return render_template(
        "activity_detail.html",
        activity=act,
        total_costs=total_costs,
        total_sales=total_sales,
        balance=total_sales - total_costs
    )

# ----------------------------
# 👮 ADMIN
# ----------------------------

@app.route("/admin")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)

    return render_template("admin.html", dashboard={})

# ----------------------------
# 🚀 INIT
# ----------------------------

with app.app_context():
    db.create_all()

    # asignar admin automático
    admin = User.query.get(ADMIN_USER_ID)
    if admin:
        admin.is_admin = True
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
