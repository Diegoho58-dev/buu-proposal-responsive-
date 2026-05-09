from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import os

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


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
ADMIN_USER_ID = 2


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


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    sent_messages = db.relationship(
        "Message",
        foreign_keys="Message.sender_id",
        backref="sender",
        lazy=True,
        cascade="all, delete-orphan",
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
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    login_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    logout_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    ip_address = db.Column(db.String(80), nullable=True)


class Message(db.Model):
    __tablename__ = "message"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    is_read = db.Column(db.Boolean, nullable=False, default=False)
    read_at = db.Column(db.DateTime, nullable=True)


class Activity(db.Model):
    __tablename__ = "activity"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

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
    return db.session.get(User, int(user_id))


def get_chat_partner():
    if not current_user.is_authenticated:
        return None

    if current_user.id == 2:
        return db.session.get(User, 3)
    if current_user.id == 3:
        return db.session.get(User, 2)

    return None


def ensure_user_table_columns():
    try:
        with db.engine.connect() as connection:
            connection.exec_driver_sql(
                'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE'
            )
            connection.commit()
    except Exception as e:
        print("ERROR AGREGANDO is_admin:", e)


def ensure_message_table_columns():
    try:
        with db.engine.connect() as connection:
            connection.exec_driver_sql(
                'ALTER TABLE "message" ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE'
            )
            connection.exec_driver_sql(
                'ALTER TABLE "message" ADD COLUMN IF NOT EXISTS read_at TIMESTAMP NULL'
            )
            connection.commit()
    except Exception as e:
        print("ERROR AGREGANDO COLUMNAS DE MENSAJE:", e)


def assign_admin_by_id():
    try:
        admin_user = db.session.get(User, ADMIN_USER_ID)
        if admin_user and not admin_user.is_admin:
            admin_user.is_admin = True
            db.session.commit()
            print(f"Usuario ID {ADMIN_USER_ID} marcado como administrador.")
    except Exception as e:
        db.session.rollback()
        print("ERROR ASIGNANDO ADMIN POR ID:", e)


def start_user_session(user):
    new_session = UserSession(
        user_id=user.id,
        login_at=datetime.utcnow(),
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
    )
    db.session.add(new_session)
    db.session.commit()
    session["active_session_id"] = new_session.id


def end_user_session():
    active_session_id = session.get("active_session_id")
    if not active_session_id:
        return

    current_session = db.session.get(UserSession, active_session_id)
    if current_session and current_session.logout_at is None:
        current_session.logout_at = datetime.utcnow()
        current_session.duration_seconds = int(
            (current_session.logout_at - current_session.login_at).total_seconds()
        )
        db.session.commit()

    session.pop("active_session_id", None)


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
        new_user = User(username=username, password_hash=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        start_user_session(new_user)
        return redirect(url_for("wall"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("wall"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            start_user_session(user)
            return redirect(url_for("wall"))

        flash("Usuario o contraseña incorrectos.")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    end_user_session()
    logout_user()
    return redirect(url_for("home"))


@app.route("/wall", methods=["GET", "POST"])
@login_required
def wall():
    partner = get_chat_partner()

    if not partner:
        flash("Este usuario no está habilitado para el chat principal.")
        return render_template("wall.html", messages=[], partner=None)

    if request.method == "POST":
        content = request.form.get("content", "").strip()

        if content:
            message = Message(
                content=content,
                sender_id=current_user.id,
                receiver_id=partner.id,
                is_read=False,
            )
            db.session.add(message)
            db.session.commit()

        return redirect(url_for("wall"))

    messages = (
        Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == partner.id))
            | ((Message.sender_id == partner.id) & (Message.receiver_id == current_user.id))
        )
        .order_by(Message.created_at.asc())
        .all()
    )

    updated = False
    for message in messages:
        if message.receiver_id == current_user.id and not message.is_read:
            message.is_read = True
            message.read_at = datetime.utcnow()
            updated = True

    if updated:
        db.session.commit()

    return render_template("wall.html", messages=messages, partner=partner)


@app.route("/delete/<int:message_id>", methods=["POST"])
@login_required
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)

    if message.sender_id != current_user.id:
        flash("No puedes borrar este mensaje.")
        return redirect(url_for("wall"))

    db.session.delete(message)
    db.session.commit()
    flash("Mensaje eliminado.")
    return redirect(url_for("wall"))


@app.route("/activities", methods=["GET", "POST"])
@login_required
def activities():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        if not title:
            flash("El nombre de la actividad es obligatorio.")
            return redirect(url_for("activities"))

        activity = Activity(title=title, description=description)
        db.session.add(activity)
        db.session.commit()

        flash("Actividad creada correctamente.")
        return redirect(url_for("activity_detail", activity_id=activity.id))

    all_activities = Activity.query.order_by(Activity.created_at.desc()).all()
    return render_template("activities.html", activities=all_activities)


@app.route("/activities/<int:activity_id>", methods=["GET"])
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


@app.route("/activities/<int:activity_id>/add-payer", methods=["POST"])
@login_required
def add_payer(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    name = request.form.get("name", "").strip()

    if not name:
        flash("Debes escribir el nombre de la persona.")
        return redirect(url_for("activity_detail", activity_id=activity.id))

    payer = ActivityPayer(name=name, activity_id=activity.id)
    db.session.add(payer)
    db.session.commit()

    flash("Persona agregada.")
    return redirect(url_for("activity_detail", activity_id=activity.id))


@app.route("/activities/<int:activity_id>/add-cost", methods=["POST"])
@login_required
def add_cost(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    description = request.form.get("description", "").strip()
    amount_raw = request.form.get("amount", "").strip()

    if not description or not amount_raw:
        flash("Completa la descripción y el valor del costo.")
        return redirect(url_for("activity_detail", activity_id=activity.id))

    try:
        amount = float(amount_raw)
    except ValueError:
        flash("El valor del costo debe ser numérico.")
        return redirect(url_for("activity_detail", activity_id=activity.id))

    cost = ActivityCost(description=description, amount=amount, activity_id=activity.id)
    db.session.add(cost)
    db.session.commit()

    flash("Costo agregado.")
    return redirect(url_for("activity_detail", activity_id=activity.id))


@app.route("/activities/<int:activity_id>/add-sale", methods=["POST"])
@login_required
def add_sale(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    description = request.form.get("description", "").strip()
    amount_raw = request.form.get("amount", "").strip()

    if not description or not amount_raw:
        flash("Completa la descripción y el valor de la venta.")
        return redirect(url_for("activity_detail", activity_id=activity.id))

    try:
        amount = float(amount_raw)
    except ValueError:
        flash("El valor de la venta debe ser numérico.")
        return redirect(url_for("activity_detail", activity_id=activity.id))

    sale = ActivitySale(description=description, amount=amount, activity_id=activity.id)
    db.session.add(sale)
    db.session.commit()

    flash("Venta agregada.")
    return redirect(url_for("activity_detail", activity_id=activity.id))


@app.route("/admin")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("No tienes permisos para entrar al panel administrativo.")
        return redirect(url_for("home"))

    total_users = User.query.count()
    total_activities = Activity.query.count()
    total_sessions = UserSession.query.count()

    completed_sessions = UserSession.query.filter(
        UserSession.duration_seconds.isnot(None)
    ).all()

    total_connection_seconds = sum(
        s.duration_seconds for s in completed_sessions if s.duration_seconds
    )
    avg_connection_seconds = (
        int(total_connection_seconds / len(completed_sessions))
        if completed_sessions
        else 0
    )

    now = datetime.utcnow()
    start_range = now - timedelta(days=6)
    sessions_last_7 = UserSession.query.filter(UserSession.login_at >= start_range).all()

    sessions_by_day = {}
    minutes_by_day = {}

    for i in range(7):
        day = (start_range + timedelta(days=i)).date()
        key = day.strftime("%d/%m")
        sessions_by_day[key] = 0
        minutes_by_day[key] = 0

    for s in sessions_last_7:
        day_key = s.login_at.date().strftime("%d/%m")
        if day_key in sessions_by_day:
            sessions_by_day[day_key] += 1
        if s.duration_seconds:
            minutes_by_day[day_key] += round(s.duration_seconds / 60, 2)

    dashboard = {
        "kpis": {
            "total_users": total_users,
            "total_activities": total_activities,
            "total_sessions": total_sessions,
            "total_connection_hours": round(total_connection_seconds / 3600, 2),
            "avg_connection_minutes": round(avg_connection_seconds / 60, 2),
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
    }

    return render_template(
        "admin.html",
        dashboard=dashboard,
        dashboard_json=json.dumps(dashboard),
    )


with app.app_context():
    db.create_all()
    ensure_user_table_columns()
    ensure_message_table_columns()
    assign_admin_by_id()


if __name__ == "__main__":
    app.run(debug=True)
