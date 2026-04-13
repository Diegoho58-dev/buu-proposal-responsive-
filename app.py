from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # 🔐 necesario para sesiones

# 🔥 CONEXIÓN A BASE DE DATOS (SUPABASE)
database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise ValueError("❌ DATABASE_URL no está configurada en Render")

# 🔧 Arreglo típico de Render + PostgreSQL
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 🔐 LOGIN MANAGER
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

# 🧑‍💻 MODELOS
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", backref="messages")

# 🔄 CARGAR USUARIO
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 🏠 HOME
@app.route("/")
def home():
    latest_messages = Message.query.order_by(Message.created_at.desc()).limit(6).all()
    return render_template("home.html", latest_messages=latest_messages)

# 📝 REGISTRO
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

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Ese usuario ya existe.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        user = User(username=username, password_hash=hashed_password)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("wall"))

    return render_template("register.html")

# 🔐 LOGIN
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

# 🚪 LOGOUT
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

# 💬 MURO
@app.route("/wall", methods=["GET", "POST"])
@login_required
def wall():
    if request.method == "POST":
        content = request.form.get("content", "").strip()

        if content:
            new_message = Message(content=content, user_id=current_user.id)
            db.session.add(new_message)
            db.session.commit()

        return redirect(url_for("wall"))

    messages = Message.query.order_by(Message.created_at.desc()).all()
    return render_template("wall.html", messages=messages)

# 📝 NOTA
@app.route("/note")
@login_required
def note():
    return render_template("note.html")

# 🗑️ ELIMINAR MENSAJE
@app.route("/delete/<int:message_id>", methods=["POST"])
@login_required
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)

    if message.user_id != current_user.id:
        flash("No puedes borrar un mensaje que no es tuyo.")
        return redirect(url_for("wall"))

    db.session.delete(message)
    db.session.commit()
    return redirect(url_for("wall"))

# 🔥 CREAR TABLAS (solo si no existen)
with app.app_context():
    db.create_all()

# ▶️ EJECUCIÓN LOCAL
if __name__ == "__main__":
    app.run(debug=True)
