from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from zoneinfo import ZoneInfo
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


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    messages = db.relationship("Message", backref="user", lazy=True, cascade="all, delete-orphan")


class Message(db.Model):
    __tablename__ = "message"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


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


@app.route("/")
def home():
    return render_template("home.html")


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
            return redirect(url_for("wall"))

        flash("Usuario o contraseña incorrectos.")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/wall", methods=["GET", "POST"])
@login_required
def wall():
    if request.method == "POST":
        content = request.form.get("content", "").strip()

        if content:
            message = Message(content=content, user_id=current_user.id)
            db.session.add(message)
            db.session.commit()

        return redirect(url_for("wall"))

    messages = Message.query.order_by(Message.created_at.desc()).all()
    return render_template("wall.html", messages=messages)


@app.route("/delete/<int:message_id>", methods=["POST"])
@login_required
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)

    if message.user_id != current_user.id:
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
        balance=balance
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


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
