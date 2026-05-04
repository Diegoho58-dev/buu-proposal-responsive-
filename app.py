from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import func
import os

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave_super_segura")

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("❌ ERROR: DATABASE_URL no está configurada")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

COLOMBIA_TZ = ZoneInfo("America/Bogota")
UTC_TZ = ZoneInfo("UTC")


@app.template_filter("colombia_time")
def colombia_time(dt):
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(COLOMBIA_TZ)


@app.template_filter("datetime_format")
def datetime_format(dt, fmt="%d/%m/%Y %H:%M"):
    if not dt:
        return ""
    return dt.strftime(fmt)


def format_seconds(total_seconds):
    if total_seconds is None:
        return "0 min"

    total_seconds = int(total_seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours} h")
    if minutes > 0:
        parts.append(f"{minutes} min")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} s")

    return " ".join(parts)


@app.template_filter("duration_format")
def duration_format(total_seconds):
    return format_seconds(total_seconds)


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_online = db.Column(db.Boolean, default=False, nullable=False)
    connection_count = db.Column(db.Integer, default=0, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_logout_at = db.Column(db.DateTime, nullable=True)
    current_session_started_at = db.Column(db.DateTime, nullable=True)
    total_connected_seconds = db.Column(db.Integer, default=0, nullable=False)
    last_session_seconds = db.Column(db.Integer, default=0, nullable=False)

    messages = db.relationship(
        "Message",
        foreign_keys="Message.user_id",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    sent_messages = db.relationship(
        "Message",
        foreign_keys="Message.sender_id",
        backref="sender",
        lazy=True
    )

    received_messages = db.relationship(
        "Message",
        foreign_keys="Message.receiver_id",
        backref="receiver",
        lazy=True
    )


class Message(db.Model):
    __tablename__ = "message"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)


class Activity(db.Model):
    __tablename__ = "activity"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payers = db.relationship("ActivityPayer", backref="activity", lazy=True, cascade="all, delete-orphan")
    costs = db.relationship("ActivityCost", backref="activity", lazy=True, cascade="all, delete-orphan")
    sales = db.relationship("ActivitySale", backref="activity", lazy=True, cascade="all, delete-orphan")


class ActivityPayer(db.Model):
    __tablename__ = "activity_payer"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey("activity.id"), nullable=False)


class ActivityCost(db.Model):
    __tablename__ = "activity_cost"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey("activity.id"), nullable=False)


class ActivitySale(db.Model):
    __tablename__ = "activity_sale"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey("activity.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_chat_partner():
    if current_user.id == 2:
        return User.query.get(3)
    elif current_user.id == 3:
        return User.query.get(2)
    return None


def is_admin_user(user):
    if not user or not user.is_authenticated:
        return False
    return user.is_admin


def promote_admin_user():
    diego_user = User.query.filter(func.lower(User.username) == "diego").first()
    if diego_user and not diego_user.is_admin:
        diego_user.is_admin = True
        db.session.commit()


@app.route("/")
def home():
    try:
        latest_messages = Message.query.order_by(Message.created_at.desc()).limit(6).all()
    except Exception as e:
        print("ERROR BD:", e)
        latest_messages = []

    return render_template("home.html", latest_messages=latest_messages)


@app.route("/note")
def note():
    return render_template("note.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("wall"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Completa todos los campos.")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("Ese usuario ya existe.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            password_hash=hashed_password,
            is_admin=username.lower() == "diego"
        )

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        new_user.is_online = True
        new_user.connection_count += 1
        new_user.last_login_at = datetime.utcnow()
        new_user.current_session_started_at = datetime.utcnow()
        db.session.commit()

        return redirect(url_for("wall"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("wall"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user 
