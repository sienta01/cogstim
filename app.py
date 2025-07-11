from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# Emoji-Description Pairs
emoji_set = [
    {"emoji": "😀", "description": "Wajah"},
    {"emoji": "🚗", "description": "Mobil"},
    {"emoji": "🍎", "description": "Apel"},
    {"emoji": "🐶", "description": "Anjing"},
    {"emoji": "⚽", "description": "Bola"},
    {"emoji": "🌞", "description": "Matahari"},
    {"emoji": "📚", "description": "Buku"},
    {"emoji": "🎸", "description": "Gitar"},
    {"emoji": "✈️", "description": "Pesawat"},
    {"emoji": "🎂", "description": "Kue"}
]

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # Relationship to Score (Optional)
    scores = db.relationship('Score', backref='user', lazy=True)

# Score Model
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

with app.app_context():
    db.create_all()

@app.route("/game")
def game():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    session["emoji_queue"] = random.sample(emoji_set, 10)
    session["emoji_index"] = 0
    session["score"] = 0
    return render_template('game.html')
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            return redirect(url_for("game"))
        else:
            flash("Username atau password salah.")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            flash("Username sudah digunakan.")
            return render_template("register.html")
        password_hash = generate_password_hash(password)
        new_user = User(username=username, password_hash=password_hash)
        db.session.add(new_user)
        db.session.commit()
        session["user_id"] = new_user.id
        return redirect(url_for("game"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/next")
def next_pair():
    # Pastikan sesi sudah memiliki emoji_queue
    if "emoji_queue" not in session:
        session["emoji_queue"] = random.sample(emoji_set, 10)  # Acak 10 pasangan emoji-deskripsi
        session["emoji_index"] = 0
        session["score"] = 0  # Reset skor setiap permainan baru

    if session["emoji_index"] >= len(session["emoji_queue"]):
        return jsonify({"finished": True, "score": session["score"]})

    # Ambil pasangan emoji yang sedang dimainkan
    current_pair = session["emoji_queue"][session["emoji_index"]]

    # Tentukan apakah kombinasi ini benar atau salah
    is_correct = random.choice([True, False])
    session["current_correct"] = is_correct

    if is_correct:
        description = current_pair["description"]  # Gunakan deskripsi yang benar
    else:
        # Pilih deskripsi yang salah
        wrong_pair = random.choice([e for e in emoji_set if e["emoji"] != current_pair["emoji"]])
        description = wrong_pair["description"]

    return jsonify({
        "finished": False,
        "emoji": current_pair["emoji"],
        "description": description
    })

@app.route("/submit", methods=["POST"])
def submit():
    if "user_id" not in session:
        return redirect(url_for("login"))

    data = request.get_json()
    user_choice = data["user_choice"]  # Jawaban dari user (True atau False)
    correct_answer = session.get("current_correct", False)  # Ambil jawaban benar dari session

    if user_choice == correct_answer:
        session["score"] += 10  # Tambah skor jika jawaban benar
        result_message = "✅ Benar!"
    else:
        result_message = "❌ Salah!"

    session["emoji_index"] += 1  # Pindah ke pertanyaan berikutnya

    if session["emoji_index"] >= 10:
        # Simpan skor ke database
        new_score = Score(user_id=session["user_id"], score=session["score"])
        db.session.add(new_score)
        db.session.commit()
        
        return jsonify({"finished": True, "score": session["score"]})

    return jsonify({"message": result_message, "correct_answer": correct_answer})

@app.route("/")
def reference():
    return render_template("reference.html", emoji_set=emoji_set)

@app.route("/scores")
def scores():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_scores = Score.query.filter_by(user_id=session["user_id"]).order_by(Score.timestamp.desc()).limit(100).all()
    return render_template("scores.html", scores=user_scores)

if __name__ == "__main__":
    app.run(debug=True)
