from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# Go/No-Go Test Configuration
GO_SHAPES = ["⭕", "🔷", "🔶"]  # Shapes to press "GO" on
NO_GO_SHAPES = ["🔺", "✋"]  # Shapes to NOT press

# Color Stroop Test Configuration
COLORS = ["red", "blue", "green", "yellow", "purple"]
COLOR_DISPLAY_NAMES = {
    "red": "MERAH",
    "blue": "BIRU", 
    "green": "HIJAU",
    "yellow": "KUNING",
    "purple": "UNGU"
}
COLOR_HEX = {
    "red": "#FF0000",
    "blue": "#0000FF",
    "green": "#00AA00",
    "yellow": "#FFFF00",
    "purple": "#AA00AA"
}

import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
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
    test_type = db.Column(db.String(50), default="emoji")  # 'emoji', 'go_no_go', 'stroop'
    reaction_time = db.Column(db.Float, nullable=True)  # in milliseconds
    accuracy = db.Column(db.Float, nullable=True)  # percentage
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)

# Dashboard route
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    patients = Patient.query.filter_by(user_id=user.id).all() if user else []
    import datetime
    now = datetime.datetime.now()
    username = user.username if user else ""
    return render_template("dashboard.html", patients=patients, now=now, username=username)

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

@app.route("/reference")
def reference():
    session["reference_shown"] = True
    return render_template("reference.html")

@app.route("/select_test")
def select_test():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("select_test.html")

@app.route("/game/<test_type>")
def game(test_type):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if test_type not in ['go_no_go', 'stroop']:
        flash("Invalid test type")
        return redirect(url_for('select_test'))
    
    session["test_type"] = test_type
    session["score"] = 0
    session["correct_count"] = 0
    session["total_count"] = 0
    session["trial_index"] = 0
    
    if test_type == 'go_no_go':
        session["go_no_go_trials"] = generate_go_no_go_trials(20)  # 20 trials
    elif test_type == 'stroop':
        session["stroop_trials"] = generate_stroop_trials(20)  # 20 trials
    
    return render_template('game.html', test_type=test_type)

def generate_go_no_go_trials(num_trials):
    """Generate random Go/No-Go trials"""
    trials = []
    for _ in range(num_trials):
        is_go = random.choice([True, False])
        if is_go:
            shape = random.choice(GO_SHAPES)
        else:
            shape = random.choice(NO_GO_SHAPES)
        trials.append({
            "shape": shape,
            "is_go": is_go
        })
    return trials

def generate_stroop_trials(num_trials):
    """Generate Stroop color word trials - word color doesn't match word meaning"""
    trials = []
    for _ in range(num_trials):
        word_color = random.choice(COLORS)  # What color the word is displayed in
        word_meaning = random.choice([c for c in COLORS if c != word_color])  # The word itself (mismatched)
        trials.append({
            "word": COLOR_DISPLAY_NAMES[word_meaning],
            "display_color": COLOR_HEX[word_color],
            "correct_answer": word_color  # User should respond to color, not word meaning
        })
    return trials

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("No user found, please register.")
        elif check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))
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
        # After registration, redirect to login page
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/next")
def next_trial():
    """Get next trial for the current test"""
    test_type = session.get("test_type")
    trial_index = session.get("trial_index", 0)
    
    if test_type == 'go_no_go':
        trials = session.get("go_no_go_trials", [])
        if trial_index >= len(trials):
            return jsonify({"finished": True, "score": session["score"], "correct": session["correct_count"], "total": session["total_count"]})
        
        trial = trials[trial_index]
        return jsonify({
            "finished": False,
            "shape": trial["shape"],
            "is_go_trial": trial["is_go"]
        })
    
    elif test_type == 'stroop':
        trials = session.get("stroop_trials", [])
        if trial_index >= len(trials):
            return jsonify({"finished": True, "score": session["score"], "correct": session["correct_count"], "total": session["total_count"]})
        
        trial = trials[trial_index]
        return jsonify({
            "finished": False,
            "word": trial["word"],
            "display_color": trial["display_color"],
            "correct_answer": trial["correct_answer"]
        })
    
    return jsonify({"finished": True, "error": "Invalid test type"})

@app.route("/submit", methods=["POST"])
def submit():
    if "user_id" not in session or "selected_patient_id" not in session:
        return redirect(url_for("login"))

    data = request.get_json()
    test_type = session.get("test_type")
    trial_index = session.get("trial_index", 0)
    
    if test_type == 'go_no_go':
        trials = session.get("go_no_go_trials", [])
        if trial_index >= len(trials):
            return jsonify({"finished": True})
        
        trial = trials[trial_index]
        user_action = data.get("action")  # "go", "nogo", or "nogo_timeout"
        expected_action = "go" if trial["is_go"] else "nogo"
        
        # Handle timeout (no response = nogo)
        if user_action == "nogo_timeout":
            user_action = "nogo"
        
        is_correct = user_action == expected_action
        session["total_count"] += 1
        if is_correct:
            session["correct_count"] += 1
            session["score"] += 10
            result_message = "✅ Benar!"
        else:
            result_message = "❌ Salah!"
    
    elif test_type == 'stroop':
        trials = session.get("stroop_trials", [])
        if trial_index >= len(trials):
            return jsonify({"finished": True})
        
        trial = trials[trial_index]
        user_answer = data.get("answer")  # The color user selected
        correct_answer = trial["correct_answer"]
        
        is_correct = user_answer == correct_answer
        session["total_count"] += 1
        if is_correct:
            session["correct_count"] += 1
            session["score"] += 10
            result_message = "✅ Benar!"
        else:
            result_message = "❌ Salah!"
    
    else:
        return jsonify({"error": "Invalid test type"})
    
    session["trial_index"] += 1
    
    # Check if finished
    if session["trial_index"] >= (len(trials) if test_type == 'go_no_go' else len(session.get("stroop_trials", []))):
        # Save score to database
        selected_patient_id = session.get("selected_patient_id")
        if selected_patient_id:
            accuracy = (session["correct_count"] / session["total_count"] * 100) if session["total_count"] > 0 else 0
            new_score = Score(
                score=session["score"],
                test_type=test_type,
                accuracy=accuracy,
                patient_id=selected_patient_id
            )
            db.session.add(new_score)
            db.session.commit()
        
        return jsonify({
            "finished": True,
            "score": session["score"],
            "correct": session["correct_count"],
            "total": session["total_count"]
        })
    
    return jsonify({
        "message": result_message,
        "is_correct": is_correct
    })

@app.route("/")
def index():
    return redirect(url_for("dashboard"))

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
    return redirect(url_for("select_test"))

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

# Edit Patient route
@app.route("/edit_patient/<int:patient_id>", methods=["GET", "POST"])
def edit_patient(patient_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    patient = Patient.query.filter_by(id=patient_id, user_id=session["user_id"]).first()
    if not patient:
        flash("Patient not found.")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        patient.name = request.form.get("name")
        patient.age = request.form.get("age")
        patient.notes = request.form.get("notes")
        db.session.commit()
        flash("Patient updated successfully.")
        return redirect(url_for("dashboard"))
    return render_template("edit_patient.html", patient=patient)

# Delete Patient route
@app.route("/delete_patient/<int:patient_id>")
def delete_patient(patient_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    patient = Patient.query.filter_by(id=patient_id, user_id=session["user_id"]).first()
    if not patient:
        flash("Patient not found.")
        return redirect(url_for("dashboard"))
    db.session.delete(patient)
    db.session.commit()
    flash("Patient deleted successfully.")
    return redirect(url_for("dashboard"))

with app.app_context():
    db.create_all()  # Create database tables if they don't exist

# Run the application for development
if __name__ == "__main__":
    app.run(debug=True)