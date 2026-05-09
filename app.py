from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)

app.config["SECRET_KEY"] = "supersecretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# =========================
# MODELOS
# =========================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    content = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    is_seen = db.Column(db.Boolean, default=False)


# =========================
# LOGIN
# =========================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =========================
# HELPERS
# =========================

def get_chat_partner():
    if not current_user.is_authenticated:
        return None

    return User.query.filter(User.id != current_user.id).first()


@app.template_filter("datetime_format")
def datetime_format(value, format="%I:%M %p"):
    if value:
        return value.strftime(format)
    return ""


# =========================
# RUTAS
# =========================

@app.route("/")
@login_required
def home():
    return redirect(url_for("wall"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Usuario ya existe")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        user = User(
            username=username,
            password=hashed_password
        )

        db.session.add(user)
        db.session.commit()

        flash("Usuario creado correctamente")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("wall"))

        flash("Credenciales inválidas")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/wall", methods=["GET", "POST"])
@login_required
def wall():
    partner = get_chat_partner()

    if not partner:
        return render_template(
            "wall.html",
            partner=None,
            messages=[]
        )

    if request.method == "POST":
        content = request.form.get("content")

        if content:
            new_message = Message(
                sender_id=current_user.id,
                receiver_id=partner.id,
                content=content
            )
            db.session.add(new_message)
            db.session.commit()

        return redirect(url_for("wall"))

    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) &
         (Message.receiver_id == partner.id)) |
        ((Message.sender_id == partner.id) &
         (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()

    # marcar mensajes recibidos como vistos
    unseen = Message.query.filter_by(
        sender_id=partner.id,
        receiver_id=current_user.id,
        is_seen=False
    ).all()

    for msg in unseen:
        msg.is_seen = True

    db.session.commit()

    return render_template(
        "wall.html",
        partner=partner,
        messages=messages
    )


# =========================
# INIT DB
# =========================

with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
