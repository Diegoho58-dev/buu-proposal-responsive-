from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'jenny-diego-secret'

db = SQLAlchemy(app)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(80), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def home():
    latest_messages = Message.query.order_by(Message.created_at.desc()).limit(5).all()
    return render_template('home.html', latest_messages=latest_messages)

@app.route('/wall', methods=['GET', 'POST'])
def wall():
    if request.method == 'POST':
        author = request.form.get('author', '').strip()
        content = request.form.get('content', '').strip()
        if author and content:
            new_message = Message(author=author, content=content)
            db.session.add(new_message)
            db.session.commit()
        return redirect(url_for('wall'))

    messages = Message.query.order_by(Message.created_at.desc()).all()
    return render_template('wall.html', messages=messages)

@app.route('/note')
def note():
    return render_template('note.html')

@app.route('/delete/<int:message_id>', methods=['POST'])
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)
    db.session.delete(message)
    db.session.commit()
    return redirect(url_for('wall'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
