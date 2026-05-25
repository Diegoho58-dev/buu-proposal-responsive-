from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import os
import requests

app = Flask(__name__)

# ================= CONFIG =================
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave_super_segura")

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL no configurada")

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

ADMIN_USER_ID = 2

# ================= MODELOS =================

class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    sessions = db.relationship("UserSession", backref="user", lazy=True)


class UserSession(db.Model):
    __tablename__ = "user_session"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    login_at = db.Column(db.DateTime, default=datetime.utcnow)
    logout_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    ip_address = db.Column(db.String(80))
    user_agent = db.Column(db.String(500))
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)


class Message(db.Model):
    __tablename__ = "message"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"))


class Activity(db.Model):
    __tablename__ = "activity"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    costs = db.relationship("ActivityCost", backref="activity", cascade="all, delete")
    sales = db.relationship("ActivitySale", backref="activity", cascade="all, delete")


class ActivityCost(db.Model):
    __tablename__ = "activity_cost"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    activity_id = db.Column(db.Integer, db.ForeignKey("activity.id"))


class ActivitySale(db.Model):
    __tablename__ = "activity_sale"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    activity_id = db.Column(db.Integer, db.ForeignKey("activity.id"))

# ================= LOGIN =================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ================= UTILIDADES =================

def get_location_from_ip(ip_address):
    try:
        response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=5)

        if response.status_code == 200:
            data = response.json()
            return {
                "country": data.get("country_name", "Desconocido"),
                "city": data.get("city", "Desconocido"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
            }
    except Exception as e:
        print("Error ubicación:", e)

    return {
        "country": "Desconocido",
        "city": "Desconocido",
        "latitude": None,
        "longitude": None,
    }

# ✅ CORREGIDO (SIN ERROR)
def start_user_session(user):
    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)

    if ip_address:
        ip_address = ip_address.split(",")[0].strip()

    user_agent = request.headers.get("User-Agent", "Desconocido")

    location = get_location_from_ip(ip_address)

    new_session = UserSession(
        user_id=user.id,
        login_at=datetime.utcnow(),
        ip_address=ip_address,
        user_agent=user_agent,
        country=location["country"],
        city=location["city"],
        latitude=location["latitude"],
        longitude=location["longitude"],
    )

    db.session.add(new_session)
    db.session.commit()

    session["active_session_id"] = new_session.id


def end_user_session():
    session_id = session.get("active_session_id")

    if session_id:
        s = db.session.get(UserSession, session_id)

        if s and not s.logout_at:
            s.logout_at = datetime.utcnow()
            s.duration_seconds = int((s.logout_at - s.login_at).total_seconds())
            db.session.commit()

    session.pop("active_session_id", None)

# ✅ CREA SESIÓN AUTOMÁTICA
@app.before_request
def ensure_session():
    if current_user.is_authenticated and "active_session_id" not in session:
        start_user_session(current_user)

# ================= RUTAS =================

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/note")
def note():
    return render_template("note.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            flash("Usuario ya existe")
            return redirect("/register")

        user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )

        db.session.add(user)
        db.session.commit()

        login_user(user)
        start_user_session(user)

        return redirect("/")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()

        if user and check_password_hash(user.password_hash, request.form["password"]):
            login_user(user)
            start_user_session(user)
            return redirect("/")

        flash("Credenciales incorrectas")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    end_user_session()
    logout_user()
    return redirect("/")

# ================= ADMIN =================

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user.id != ADMIN_USER_ID or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():

    active_sessions = UserSession.query.filter(UserSession.logout_at.is_(None)).all()

    active_sessions_data = []

    for sess in active_sessions:
        user = db.session.get(User, sess.user_id)

        duration = int((datetime.utcnow() - sess.login_at).total_seconds())

        active_sessions_data.append({
            "user": user.username if user else "Desconocido",
            "ip": sess.ip_address,
            "country": sess.country,
            "city": sess.city,
            "login_at": sess.login_at.isoformat() if sess.login_at else None,
            "duration_seconds": duration,
            "user_agent": sess.user_agent
        })

    dashboard = {
        "kpis": {
            "total_users": User.query.count(),
            "total_sessions": UserSession.query.count(),
            "active_sessions": len(active_sessions_data)
        },
        "active_sessions": active_sessions_data
    }

    return render_template(
        "admin.html",
        dashboard=dashboard,
        dashboard_json=json.dumps(dashboard, default=str)
    )

# ================= INIT =================

with app.app_context():
    db.create_all()

    admin = db.session.get(User, ADMIN_USER_ID)
    if admin:
        admin.is_admin = True
        db.session.commit()

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
