# --- TODO TU IMPORT ORIGINAL SE MANTIENE ---
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

ADMIN_USER_ID = 2  # lo dejamos pero ya no depende de esto

# -------- MODELOS (NO SE TOCAN) --------
# TODO: TU CÓDIGO DE MODELOS ORIGINAL AQUÍ (NO CAMBIA)
# (User, Message, Activity, etc.)

# -------- LOGIN --------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------- 🔥 FIX ADMIN --------
def admin_required(f):
    """Verifica que el usuario sea administrador"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not current_user.is_authenticated:
            abort(403)

        # ✅ SOLO validamos is_admin
        if not current_user.is_admin:
            abort(403)

        return f(*args, **kwargs)

    return decorated_function

# -------- RUTAS (TODO IGUAL) --------
@app.route("/")
def home():
    return render_template("home.html")

# --- AQUÍ NO TOCAS NADA MÁS ---
# DEJA TODAS TUS RUTAS TAL CUAL

# -------- ADMIN --------
@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_activities = Activity.query.count()
    total_sessions = UserSession.query.count()

    return render_template(
        "admin.html",
        dashboard={
            "kpis": {
                "total_users": total_users,
                "total_activities": total_activities,
                "total_sessions": total_sessions
            }
        },
        dashboard_json=json.dumps({})
    )

# -------- INIT --------
def ensure_admin():
    try:
        admin_user = User.query.get(2)
        if admin_user:
            admin_user.is_admin = True
            db.session.commit()
            print("✅ ADMIN ASEGURADO")
    except Exception as e:
        db.session.rollback()
        print("❌ ERROR ADMIN:", e)

with app.app_context():
    db.create_all()
    ensure_admin()

if __name__ == "__main__":
