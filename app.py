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

    # Relationship to Patient
    patients = db.relationship('Patient', backref='user', lazy=True)

# Patient Model
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationship to Score
    scores = db.relationship('Score', backref='patient', lazy=True)

# Score Model
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)

# Dashboard route
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    patients = Patient.query.filter_by(user_id=user.id).all() if user else []
    return render_template("dashboard.html", patients=patients)

# Add Patient route
@app.route("/add_patient", methods=["POST"])
def add_patient():
    if "user_id" not in session:
        return redirect(url_for("login"))
    name = request.form.get("name")
    age = request.form.get("age")
    notes = request.form.get("notes")
    if not name:
        flash("Patient name is required.")
        return redirect(url_for("dashboard"))
    patient = Patient(name=name, age=age, notes=notes, user_id=session["user_id"])
    db.session.add(patient)
    db.session.commit()
    flash("Patient added successfully.")
    return redirect(url_for("dashboard"))

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
    if "user_id" not in session or "selected_patient_id" not in session:
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
        new_score = Score(score=session["score"], patient_id=session["selected_patient_id"])
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

    # Show scores for all patients of this user
    patients = Patient.query.filter_by(user_id=session["user_id"]).all()
    patient_ids = [p.id for p in patients]
    user_scores = Score.query.filter(Score.patient_id.in_(patient_ids)).order_by(Score.timestamp.desc()).limit(100).all()
    return render_template("scores.html", scores=user_scores)

# Select Patient route
@app.route("/select_patient/<int:patient_id>")
def select_patient(patient_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    patient = Patient.query.filter_by(id=patient_id, user_id=session["user_id"]).first()
    if not patient:
        flash("Patient not found.")
        return redirect(url_for("dashboard"))
    session["selected_patient_id"] = patient.id
    session["selected_patient_name"] = patient.name
    return redirect(url_for("game"))

# View Patient Scores route
@app.route("/view_patient_scores/<int:patient_id>")
def view_patient_scores(patient_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    patient = Patient.query.filter_by(id=patient_id, user_id=session["user_id"]).first()
    if not patient:
        flash("Patient not found.")
        return redirect(url_for("dashboard"))
    scores = Score.query.filter_by(patient_id=patient.id).order_by(Score.timestamp.desc()).all()
    return render_template("scores.html", scores=scores, patient=patient)

if __name__ == "__main__":
    app.run(debug=True)
