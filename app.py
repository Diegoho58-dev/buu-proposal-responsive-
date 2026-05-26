from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
from sqlalchemy.exc import SQLAlchemyError
import os
import requests

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave_super_segura")

database_url = os.getenv("DATABASE_URL")
if not database_url:
    # Fallback para desarrollo local si no hay DATABASE_URL
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///local.db"
else:
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

# El ID del administrador se mantiene como referencia, pero se priorizará el flag is_admin
ADMIN_USER_ID = 2

@app.context_processor
def inject_globals():
    return {
        'now': datetime.now(),
        'timedelta': timedelta
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

class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    messages = db.relationship("Message", foreign_keys="Message.user_id", backref="user", lazy=True, cascade="all, delete-orphan")
    sent_messages = db.relationship("Message", foreign_keys="Message.sender_id", backref="sender", lazy=True)
    received_messages = db.relationship("Message", foreign_keys="Message.receiver_id", backref="receiver", lazy=True)
    sessions = db.relationship("UserSession", backref="user", lazy=True, cascade="all, delete-orphan")

class UserSession(db.Model):
    __tablename__ = "user_session"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    login_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    logout_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    ip_address = db.Column(db.String(80), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

class Message(db.Model):
    __tablename__ = "message"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Text()
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
    # Lógica simple para alternar entre los dos usuarios principales
    if current_user.id == 2:
        return User.query.get(3)
    elif current_user.id == 3:
        return User.query.get(2)
    return None

def get_location_from_ip(ip_address):
    """Obtiene ubicación aproximada basada en la IP"""
    if not ip_address or ip_address == "127.0.0.1":
        return {"country": "Local", "city": "Local", "latitude": None, "longitude": None, "isp": "Local"}
    try:
        response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "country": data.get("country_name", "Desconocido"),
                "city": data.get("city", "Desconocido"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "isp": data.get("org", "Desconocido")
            }
    except Exception as e:
        print(f"Error obteniendo ubicación: {e}")
    return {
        "country": "Desconocido",
        "city": "Desconocido",
        "latitude": None,
        "longitude": None,
        "isp": "Desconocido"
    }

def ensure_admin_column():
    try:
        with db.engine.connect() as connection:
            # PostgreSQL syntax
            connection.exec_driver_sql('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE')
            connection.commit()
    except Exception as e:
        print("INFO: Columna is_admin ya existe o error controlado:", e)

def ensure_session_columns():
    """Asegura que las columnas de ubicación existan"""
    try:
        with db.engine.connect() as connection:
            columns = [
                ('user_agent', 'VARCHAR(500)'),
                ('country', 'VARCHAR(100)'),
                ('city', 'VARCHAR(100)'),
                ('latitude', 'FLOAT'),
                ('longitude', 'FLOAT')
            ]
            for col_name, col_type in columns:
                try:
                    connection.exec_driver_sql(f'ALTER TABLE "user_session" ADD COLUMN IF NOT EXISTS {col_name} {col_type}')
                except:
                    pass
            connection.commit()
    except Exception as e:
        print("INFO: Columnas de sesión ya existen o error controlado:", e)

def assign_admin_by_id():
    try:
        # Aseguramos que al menos el usuario con ID 2 sea admin
        admin_user = User.query.get(ADMIN_USER_ID)
        if admin_user and not admin_user.is_admin:
            admin_user.is_admin = True
            db.session.commit()
        
        # Si no existe el ID 2, hacemos admin al primer usuario que encontremos (para recuperación)
        if not admin_user:
            first_user = User.query.first()
            if first_user and not first_user.is_admin:
                first_user.is_admin = True
                db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("ERROR ASIGNANDO ADMIN:", e)

def start_user_session(user):
    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
    if "," in ip_address: ip_address = ip_address.split(",")[0].strip()
    
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
        longitude=location["longitude"]
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
        current_session.duration_seconds = int((current_session.logout_at - current_session.login_at).total_seconds())
        db.session.commit()
    session.pop("active_session_id", None)

def admin_required(f):
    """Decorador para verificar que el usuario es administrador"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_admin:
            flash("No tienes permisos para acceder a esta sección.")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def home():
    try:
        latest_messages = Message.query.order_by(Message.created_at.desc()).limit(6).all()
    except Exception as e:
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
        return render_template("wall.html", messages=[], partner=None, total_messages=0)

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if content:
            message = Message(content=content, user_id=current_user.id, sender_id=current_user.id, receiver_id=partner.id)
            db.session.add(message)
            db.session.commit()
        return redirect(url_for("wall"))

    offset = request.args.get("offset", 0, type=int)
    messages_per_page = 20

    total_messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == partner.id)) |
        ((Message.sender_id == partner.id) & (Message.receiver_id == current_user.id))
    ).count()

    messages_query = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == partner.id)) |
        ((Message.sender_id == partner.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.desc()).offset(offset).limit(messages_per_page).all()

    messages = list(reversed(messages_query))
    has_more = (offset + messages_per_page) < total_messages
    next_offset = offset + messages_per_page

    return render_template("wall.html", messages=messages, partner=partner, total_messages=total_messages, current_offset=offset, next_offset=next_offset, has_more=has_more)

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
    return render_template("activity_detail.html", activity=activity, total_costs=total_costs, total_sales=total_sales, balance=balance)

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
@admin_required
def admin_dashboard():
    # Definir zona horaria local
    local_tz = pytz.timezone("America/Bogota")

    def to_local(dt):
        if dt is None:
            return None
        return dt.astimezone(local_tz)

    total_users = User.query.count()
    total_activities = Activity.query.count()
    total_sessions = UserSession.query.count()
    
    # Sesiones activas (sin logout_at)
    active_sessions = UserSession.query.filter(UserSession.logout_at.is_(None)).order_by(UserSession.login_at.desc()).all()
    
    # Historial de sesiones (últimas 20 terminadas)
    session_history = UserSession.query.filter(UserSession.logout_at.isnot(None)).order_by(UserSession.logout_at.desc()).limit(20).all()
    
    # Sesiones completadas para estadísticas
    completed_sessions = UserSession.query.filter(UserSession.duration_seconds.isnot(None)).all()
    total_connection_seconds = sum(s.duration_seconds for s in completed_sessions if s.duration_seconds)
    avg_connection_seconds = int(total_connection_seconds / len(completed_sessions)) if completed_sessions else 0
    
    # Datos de gráficos (últimos 7 días)
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
    
    # Preparar datos de sesiones activas
    active_sessions_data = []
    for sess in active_sessions:
        user = User.query.get(sess.user_id)
        duration = int((datetime.utcnow() - sess.login_at).total_seconds())
        active_sessions_data.append({
            "user": user.username if user else "Desconocido",
            "ip": sess.ip_address,
            "country": sess.country,
            "city": sess.city,
            "login_at": to_local(sess.login_at),   # convertido a hora local
            "duration_seconds": duration,
            "user_agent": sess.user_agent
        })

    # Preparar historial de sesiones
    history_data = []
    for sess in session_history:
        user = User.query.get(sess.user_id)
        history_data.append({
            "user": user.username if user else "Desconocido",
            "ip": sess.ip_address,
            "country": sess.country,
            "city": sess.city,
            "login_at": to_local(sess.login_at),   # convertido a hora local
            "logout_at": to_local(sess.logout_at), # convertido a hora local
            "duration_seconds": sess.duration_seconds
        })
    
    dashboard = {
        "kpis": {
            "total_users": total_users,
            "total_activities": total_activities,
            "total_sessions": total_sessions,
            "active_sessions": len(active_sessions),
            "total_connection_hours": round(total_connection_seconds / 3600, 2),
            "avg_connection_minutes": round(avg_connection_seconds / 60, 2)
        },
        "charts": {
            "sessions_by_day": {"labels": list(sessions_by_day.keys()), "values": list(sessions_by_day.values())},
            "minutes_by_day": {"labels": list(minutes_by_day.keys()), "values": list(minutes_by_day.values())}
        },
        "admin_data": {
            "nombre": current_user.username,
            "usuario": current_user.username,
            "rol": "Administrador",
            "id_usuario": current_user.id
        },
        "active_sessions": active_sessions_data,
        "history": history_data
    }

    # Serializador para datetime
    def custom_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError("Type not serializable")

    return render_template(
        "admin.html",
        dashboard=dashboard,
        dashboard_json=json.dumps(dashboard, default=custom_serializer)
    )

with app.app_context():
    db.create_all()
    ensure_admin_column()
    ensure_session_columns()
    assign_admin_by_id()

if __name__ == "__main__":
    app.run(debug=True)
