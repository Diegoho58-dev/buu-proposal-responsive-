from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# 🔥 CONFIGURACIÓN BASE DE DATOS (SUPABASE)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 🧠 MODELO (tabla messages)
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    message = db.Column(db.Text)

# 🏠 RUTA PRINCIPAL
@app.route('/')
def home():
    return render_template('index.html')

# 📩 GUARDAR MENSAJE
@app.route('/send', methods=['POST'])
def send():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    new_message = Message(name=name, email=email, message=message)
    db.session.add(new_message)
    db.session.commit()

    return redirect(url_for('home'))

# 🔥 CREAR TABLAS AUTOMÁTICAMENTE
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
