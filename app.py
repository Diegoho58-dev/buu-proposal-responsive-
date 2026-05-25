# Reemplazo profesional de `app.py`

Reemplaza COMPLETAMENTE tu archivo `app.py` por este código.

```python
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
from zoneinfo import ZoneInfo

import json
import os
import requests


# =========================================================
# CONFIGURACIÓN PRINCIPAL
# =========================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "clave_super_segura_cambiar_en_produccion",
)

# Base de datos local y producción
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1,
    )

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db = SQLAlchemy(app)


# =========================================================
# LOGIN MANAGER
# =========================================================

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Debes iniciar sesión"
login_manager.init_app(app)


# =========================================================
# ZONAS HORARIAS
# =========================================================

COLOMBIA_TZ = ZoneInfo("America/Bogota")
UTC_TZ = ZoneInfo("UTC")


# =========================================================
# HELPERS GLOBALES
# =========================================================

@app.context_processor
def inject_globals():
    return {
        "now": datetime.now(),
        "timedelta": timedelta,
    }


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


# =========================================================
# MODELOS
# =========================================================

class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    is_admin = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    messages = db.relationship(
        "Message",
        foreign_keys="Message.user_id",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    sent_messages = db.relationship(
        "Message",
        foreign_keys="Message.sender_id",
        backref="sender",
        lazy=True,
    )

    received_messages = db.relationship(
        "Message",
        foreign_keys="Message.receiver_id",
        backref="receiver",
        lazy=True,
    )

    sessions = db.relationship(
        "UserSession",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )


class UserSession(db.Model):
    __tablename__ = "user_session"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
    )

    login_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

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

    content = db.Column(
        db.Text,
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
    )

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
    )

    receiver_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
    )


class Activity(db.Model):
    __tablename__ = "activity"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(
        db.String(150),
        nullable=False,
    )

    description = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    payers = db.relationship(
        "ActivityPayer",
        backref="activity",
        lazy=True,
        cascade="all, delete-orphan",
    )

    costs = db.relationship(
        "ActivityCost",
        backref="activity",
        lazy=True,
        cascade="all, delete-orphan",
    )

    sales = db.relationship(
        "ActivitySale",
        backref="activity",
        lazy=True,
        cascade="all, delete-orphan",
    )


class ActivityPayer(db.Model):
    __tablename__ = "activity_payer"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(120),
        nullable=False,
    )

    activity_id = db.Column(
        db.Integer,
        db.ForeignKey("activity.id"),
        nullable=False,
    )


class ActivityCost(db.Model):
    __tablename__ = "activity_cost"

    id = db.Column(db.Integer, primary_key=True)

    description = db.Column(
        db.String(200),
        nullable=False,
    )

    amount = db.Column(
        db.Float,
        nullable=False,
    )

    activity_id = db.Column(
        db.Integer,
        db.ForeignKey("activity.id"),
        nullable=False,
    )


class ActivitySale(db.Model):
    __tablename__ = "activity_sale"

    id = db.Column(db.Integer, primary_key=True)

    description = db.Column(
        db.String(200),
        nullable=False,
    )

    amount = db.Column(
        db.Float,
        nullable=False,
    )

    activity_id = db.Column(
        db.Integer,
        db.ForeignKey("activity.id"),
        nullable=False,
    )


# =========================================================
# LOGIN
# =========================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =========================================================
# UTILIDADES
# =========================================================


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))

        if not current_user.is_admin:
            abort(403)

        return f(*args, **kwargs)

    return decorated_function



def get_chat_partner():
    users = User.query.filter(User.id != current_user.id).all()

    if users:
        return users[0]

    return None



def get_location_from_ip(ip_address):
    try:
        response = requests.get(
            f"https://ipapi.co/{ip_address}/json/",
            timeout=3,
        )

        if response.status_code == 200:
            data = response.json()

            return {
                "country": data.get("country_name", "Desconocido"),
                "city": data.get("city", "Desconocido"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
            }

    except Exception as error:
        print("ERROR UBICACIÓN:", error)

    return {
        "country": "Desconocido",
        "city": "Desconocido",
        "latitude": None,
        "longitude": None,
    }



def start_user_session(user):
    ip_address = request.headers.get(
        "X-Forwarded-For",
        request.remote_addr,
    )

    user_agent = request.headers.get(
        "User-Agent",
        "Desconocido",
    )

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
    active_session_id = session.get("active_session_id")

    if not active_session_id:
        return

    current_session = UserSession.query.get(active_session_id)

    if current_session and current_session.logout_at is None:
        current_session.logout_at = datetime.utcnow()

        current_session.duration_seconds = int(
            (
                current_session.logout_at
                - current_session.login_at
            ).total_seconds()
        )

        db.session.commit()

    session.pop("active_session_id", None)


# =========================================================
# RUTAS PRINCIPALES
# =========================================================

@app.route("/")
def home():
    latest_messages = Message.query.order_by(
        Message.created_at.desc()
    ).limit(6).all()

    return render_template(
        "home.html",
        latest_messages=latest_messages,
    )


@app.route("/note")
def note():
    return render_template("note.html")


# =========================================================
# REGISTRO
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("wall"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Completa todos los campos")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:
            flash("Ese usuario ya existe")
            return redirect(url_for("register"))

        # El PRIMER usuario será administrador automáticamente
        is_first_user = User.query.count() == 0

        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            password_hash=hashed_password,
            is_admin=is_first_user,
        )

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        start_user_session(new_user)

        if is_first_user:
            flash("Administrador creado correctamente")
        else:
            flash("Cuenta creada correctamente")

        return redirect(url_for("wall"))

    return render_template("register.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("wall"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(
            user.password_hash,
            password,
        ):
            login_user(user)
            start_user_session(user)

            flash("Bienvenido")

            return redirect(url_for("wall"))

        flash("Usuario o contraseña incorrectos")

        return redirect(url_for("login"))

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
@login_required
def logout():
    end_user_session()
    logout_user()

    flash("Sesión cerrada")

    return redirect(url_for("home"))


# =========================================================
# CHAT
# =========================================================

@app.route("/wall", methods=["GET", "POST"])
@login_required
def wall():
    partner = get_chat_partner()

    if not partner:
        return render_template(
            "wall.html",
            messages=[],
            partner=None,
            total_messages=0,
        )

    if request.method == "POST":
        content = request.form.get("content", "").strip()

        if content:
            message = Message(
                content=content,
                user_id=current_user.id,
                sender_id=current_user.id,
                receiver_id=partner.id,
            )

            db.session.add(message)
            db.session.commit()

        return redirect(url_for("wall"))

    offset = request.args.get("offset", 0, type=int)
    messages_per_page = 20

    messages_query = Message.query.filter(
        (
            (Message.sender_id == current_user.id)
            & (Message.receiver_id == partner.id)
        )
        |
        (
            (Message.sender_id == partner.id)
            & (Message.receiver_id == current_user.id)
        )
    )

    total_messages = messages_query.count()

    messages = (
        messages_query
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(messages_per_page)
        .all()
    )

    messages = list(reversed(messages))

    has_more = (
        offset + messages_per_page
    ) < total_messages

    next_offset = offset + messages_per_page

    return render_template(
        "wall.html",
        messages=messages,
        partner=partner,
        total_messages=total_messages,
        current_offset=offset,
        next_offset=next_offset,
        has_more=has_more,
    )


# =========================================================
# BORRAR MENSAJES
# =========================================================

@app.route("/delete/<int:message_id>", methods=["POST"])
@login_required

def delete_message(message_id):
    message = Message.query.get_or_404(message_id)

    if message.sender_id != current_user.id:
        flash("No puedes borrar este mensaje")
        return redirect(url_for("wall"))

    db.session.delete(message)
    db.session.commit()

    flash("Mensaje eliminado")

    return redirect(url_for("wall"))


# =========================================================
# ACTIVIDADES
# =========================================================

@app.route("/activities", methods=["GET", "POST"])
@login_required

def activities():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get(
            "description",
            "",
        ).strip()

        if not title:
            flash("El nombre de la actividad es obligatorio")
            return redirect(url_for("activities"))

        activity = Activity(
            title=title,
            description=description,
        )

        db.session.add(activity)
        db.session.commit()

        flash("Actividad creada correctamente")

        return redirect(
            url_for(
                "activity_detail",
                activity_id=activity.id,
            )
        )

    all_activities = Activity.query.order_by(
        Activity.created_at.desc()
    ).all()

    return render_template(
        "activities.html",
        activities=all_activities,
    )


@app.route("/activities/<int:activity_id>")
@login_required

def activity_detail(activity_id):
    activity = Activity.query.get_or_404(activity_id)

    total_costs = sum(cost.amount for cost in activity.costs)
    total_sales = sum(sale.amount for sale in activity.sales)
    balance = total_sales - total_costs

    return render_template(
        "activity_detail.html",
        activity=activity,
        total_costs=total_costs,
        total_sales=total_sales,
        balance=balance,
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
@login_required
@admin_required

def admin_dashboard():
    total_users = User.query.count()
    total_activities = Activity.query.count()
    total_sessions = UserSession.query.count()

    active_sessions = UserSession.query.filter(
        UserSession.logout_at.is_(None)
    ).all()

    completed_sessions = UserSession.query.filter(
        UserSession.duration_seconds.isnot(None)
    ).all()

    total_connection_seconds = sum(
        s.duration_seconds
        for s in completed_sessions
        if s.duration_seconds
    )

    avg_connection_seconds = 0

    if completed_sessions:
        avg_connection_seconds = int(
            total_connection_seconds
            / len(completed_sessions)
        )

    now = datetime.utcnow()
    start_range = now - timedelta(days=6)

    sessions_last_7 = UserSession.query.filter(
        UserSession.login_at >= start_range
    ).all()

    sessions_by_day = {}
    minutes_by_day = {}

    for i in range(7):
        day = (
            start_range + timedelta(days=i)
        ).date()

        key = day.strftime("%d/%m")

        sessions_by_day[key] = 0
        minutes_by_day[key] = 0

    for sess in sessions_last_7:
        day_key = sess.login_at.date().strftime("%d/%m")

        if day_key in sessions_by_day:
            sessions_by_day[day_key] += 1

        if sess.duration_seconds:
            minutes_by_day[day_key] += round(
                sess.duration_seconds / 60,
                2,
            )

    active_sessions_data = []

    for sess in active_sessions:
        user = User.query.get(sess.user_id)

        duration = int(
            (
                datetime.utcnow()
                - sess.login_at
            ).total_seconds()
        )

        active_sessions_data.append(
            {
                "user": user.username if user else "Desconocido",
                "ip": sess.ip_address,
                "country": sess.country,
                "city": sess.city,
                "latitude": sess.latitude,
                "longitude": sess.longitude,
                "login_at": sess.login_at,
                "duration_seconds": duration,
                "user_agent": sess.user_agent,
            }
        )

    dashboard = {
        "kpis": {
            "total_users": total_users,
            "total_activities": total_activities,
            "total_sessions": total_sessions,
            "active_sessions": len(active_sessions),
            "total_connection_hours": round(
                total_connection_seconds / 3600,
                2,
            ),
            "avg_connection_minutes": round(
                avg_connection_seconds / 60,
                2,
            ),
        },
        "charts": {
            "sessions_by_day": {
                "labels": list(sessions_by_day.keys()),
                "values": list(sessions_by_day.values()),
            },
            "minutes_by_day": {
                "labels": list(minutes_by_day.keys()),
                "values": list(minutes_by_day.values()),
            },
        },
        "admin_data": {
            "nombre": current_user.username,
            "usuario": current_user.username,
            "rol": "Administrador",
            "id_usuario": current_user.id,
        },
        "active_sessions": active_sessions_data,
    }

    return render_template(
        "admin.html",
        dashboard=dashboard,
        dashboard_json=json.dumps(dashboard),
    )


# =========================================================
# INICIALIZACIÓN
# =========================================================

with app.app_context():
    db.create_all()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)

```
