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

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave_super_segura")

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("ERROR: DATABASE_URL no está configurada")

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

# -------- MODELOS -------- #

class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

class UserSession(db.Model):
    __tablename__ = "user_session"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    login_at = db.Column(db.DateTime, default=datetime.utcnow)
    logout_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)

class Message(db.Model):
    __tablename__ = "message"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------- DECORADOR ADMIN -------- #

def admin_required(f):
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)

        if not current_user.is_admin:
            abort(403)

        return f(*args, **kwargs)

    return decorated_function

# -------- RUTAS -------- #

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        user = User(username=username, password_hash=password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("home"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()

        if user and check_password_hash(user.password_hash, request.form["password"]):
            login_user(user)
            return redirect(url_for("home"))

        flash("Credenciales incorrectas")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

# -------- ADMIN -------- #

@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    users = User.query.count()
    return render_template("admin.html", total_users=users)

# -------- INIT -------- #

def ensure_admin():
    try:
        user = User.query.filter_by(username="diego").first()
        if user:
            user.is_admin = True
            db.session.commit()
            print("✅ Admin asignado correctamente")
    except:
        db.session.rollback()

with app.app_context():
    db.create_all()
    ensure_admin()

if __name__ == "__main__":
    app.run(debug=True)
