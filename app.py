"""
Cognitive Stimulation Application
Version: 2.2.0
Release Date: February 3, 2026
Author: Development Team
Description: Professional cognitive assessment platform with Go/No-Go, Color Stroop, and Emoji Matching tests
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random

# Application Version
__version__ = "2.2.0"
__release_date__ = "2026-02-03"
__app_name__ = "Cognitive Stimulation Assessment"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# Go/No-Go Test Configuration
GO_SHAPES = ["JALAN"]  # Text button for GO action
NO_GO_SHAPES = ["DIAM"]  # Text button for NO-GO action

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

# Emoji Matching Test Configuration
EMOJI_SET = [
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

import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Use absolute path for PythonAnywhere compatibility
# On PythonAnywhere, use home directory to avoid I/O issues
DB_PATH = os.path.expanduser('~/cogstim_data/database.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
# old config
# app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
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

@app.route("/test_instructions/<test_type>")
def test_instructions(test_type):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if test_type not in ['go_no_go', 'stroop', 'emoji']:
        flash("Invalid test type")
        return redirect(url_for('dashboard'))
    return render_template('test_instructions.html', test_type=test_type)

@app.route("/select_test")
def select_test():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Initialize test sequence
    session["completed_tests"] = []
    session["test_scores"] = {}
    return redirect(url_for("test_instructions", test_type="go_no_go"))

@app.route("/game/<test_type>")
def game(test_type):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if test_type not in ['go_no_go', 'stroop', 'emoji']:
        flash("Invalid test type")
        return redirect(url_for('dashboard'))
    
    session["test_type"] = test_type
    session["score"] = 0
    session["correct_count"] = 0
    session["total_count"] = 0
    session["trial_index"] = 0
    session["is_practice"] = False
    
    if test_type == 'go_no_go':
        total_trials = 10
        session["go_no_go_trials"] = generate_go_no_go_trials(total_trials)  # go/no-go number of trials
    elif test_type == 'stroop':
        total_trials = 10
        session["stroop_trials"] = generate_stroop_trials(total_trials)  # stroop number of trials
    elif test_type == 'emoji':
        total_trials = 10
        session["emoji_trials"] = generate_emoji_trials(total_trials)  # emoji matching number of trials
    
    return render_template('game.html', test_type=test_type, total_trials=total_trials)

@app.route("/practice/<test_type>")
def practice(test_type):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if test_type not in ['go_no_go', 'stroop', 'emoji']:
        flash("Invalid test type")
        return redirect(url_for('dashboard'))
    
    session["test_type"] = test_type
    session["score"] = 0
    session["correct_count"] = 0
    session["total_count"] = 0
    session["trial_index"] = 0
    session["is_practice"] = True
    
    if test_type == 'go_no_go':
        practice_trials = 3
        session["go_no_go_practice_trials"] = generate_go_no_go_trials(practice_trials)  # practice trials
        total_trials = practice_trials
    elif test_type == 'stroop':
        practice_trials = 3
        session["stroop_practice_trials"] = generate_stroop_trials(practice_trials)  # practice trials
        total_trials = practice_trials
    elif test_type == 'emoji':
        practice_trials = 3
        session["emoji_practice_trials"] = generate_emoji_trials(practice_trials)  # practice trials
        total_trials = practice_trials
    
    return render_template('game.html', test_type=test_type, total_trials=total_trials)

@app.route("/ready/<test_type>")
def ready(test_type):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if test_type not in ['go_no_go', 'stroop', 'emoji']:
        flash("Invalid test type")
        return redirect(url_for('dashboard'))
    
    return render_template('ready.html', test_type=test_type)

def generate_go_no_go_trials(num_trials):
    """Generate random Go/No-Go trials with max 5 consecutive same type"""
    trials = []
    max_consecutive = 5
    consecutive_count = 0
    last_was_go = None
    
    for _ in range(num_trials):
        # If we've hit the max consecutive, force the opposite
        if consecutive_count >= max_consecutive:
            is_go = not last_was_go
            consecutive_count = 1
        else:
            is_go = random.choice([True, False])
            # Check if it's the same as the last one
            if is_go == last_was_go:
                consecutive_count += 1
            else:
                consecutive_count = 1
        
        last_was_go = is_go
        
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

def generate_emoji_trials(num_trials):
    """Generate Emoji matching trials"""
    trials = []
    for _ in range(num_trials):
        # Select a random emoji
        correct_emoji = random.choice(EMOJI_SET)
        
        # Decide if the pairing is correct or incorrect
        is_correct = random.choice([True, False])
        
        if is_correct:
            description = correct_emoji["description"]
        else:
            # Choose a wrong description from a different emoji
            wrong_emoji = random.choice([e for e in EMOJI_SET if e["emoji"] != correct_emoji["emoji"]])
            description = wrong_emoji["description"]
        
        trials.append({
            "emoji": correct_emoji["emoji"],
            "description": description,
            "is_correct": is_correct
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
    is_practice = session.get("is_practice", False)
    
    if test_type == 'go_no_go':
        if is_practice:
            trials = session.get("go_no_go_practice_trials", [])
        else:
            trials = session.get("go_no_go_trials", [])
        
        if trial_index >= len(trials):
            return jsonify({"finished": True, "score": session["score"], "correct": session["correct_count"], "total": session["total_count"]})
        
        trial = trials[trial_index]
        return jsonify({
            "finished": False,
            "shape": trial["shape"],
            "is_go": trial["is_go"]
        })
    
    elif test_type == 'stroop':
        if is_practice:
            trials = session.get("stroop_practice_trials", [])
        else:
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
    
    elif test_type == 'emoji':
        is_practice = session.get("is_practice", False)
        if is_practice:
            trials = session.get("emoji_practice_trials", [])
        else:
            trials = session.get("emoji_trials", [])
        
        if trial_index >= len(trials):
            return jsonify({"finished": True, "score": session["score"], "correct": session["correct_count"], "total": session["total_count"]})
        
        trial = trials[trial_index]
        return jsonify({
            "finished": False,
            "emoji": trial["emoji"],
            "description": trial["description"]
        })
    
    return jsonify({"finished": True, "error": "Invalid test type"})

@app.route("/submit", methods=["POST"])
def submit():
    if "user_id" not in session or "selected_patient_id" not in session:
        return redirect(url_for("login"))

    data = request.get_json()
    test_type = session.get("test_type")
    trial_index = session.get("trial_index", 0)
    is_practice = session.get("is_practice", False)
    
    if test_type == 'go_no_go':
        if is_practice:
            trials = session.get("go_no_go_practice_trials", [])
        else:
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
            session["score"] += 5
            result_message = "✅ Benar!"
        else:
            result_message = "❌ Salah!"
    
    elif test_type == 'stroop':
        if is_practice:
            trials = session.get("stroop_practice_trials", [])
        else:
            trials = session.get("stroop_trials", [])
            
        if trial_index >= len(trials):
            return jsonify({"finished": True})
        
        trial = trials[trial_index]
        user_answer = data.get("answer")  # The color user selected
        correct_answer = trial["correct_answer"]
        
        # Handle timeout (no response)
        if user_answer == "timeout":
            is_correct = False
        else:
            is_correct = user_answer == correct_answer
        
        session["total_count"] += 1
        if is_correct:
            session["correct_count"] += 1
            session["score"] += 5
            result_message = "✅ Benar!"
        else:
            result_message = "❌ Salah!"
    
    elif test_type == 'emoji':
        if is_practice:
            trials = session.get("emoji_practice_trials", [])
        else:
            trials = session.get("emoji_trials", [])
            
        if trial_index >= len(trials):
            return jsonify({"finished": True})
        
        trial = trials[trial_index]
        user_choice = data.get("user_choice")  # True or False from user
        correct_answer = trial["is_correct"]
        
        is_correct = user_choice == correct_answer
        session["total_count"] += 1
        if is_correct:
            session["correct_count"] += 1
            session["score"] += 5
            result_message = "✅ Benar!"
        else:
            result_message = "❌ Salah!"
    
    else:
        return jsonify({"error": "Invalid test type"})
    
    session["trial_index"] += 1
    
    # Check if finished
    if session["trial_index"] >= len(trials):
        if is_practice:
            # Practice test finished, will show message on next /next call
            return jsonify({
                "practice_finished": True,
                "message": "Praktik selesai!"
            })
        else:
            # Actual test finished, save scores
            test_scores = session.get("test_scores", {})
            test_scores[test_type] = {
                "score": session["score"],
                "correct_count": session["correct_count"],
                "total_count": session["total_count"]
            }
            session["test_scores"] = test_scores
            
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
            
            # Check what test comes next
            completed_tests = session.get("completed_tests", [])
            completed_tests.append(test_type)
            session["completed_tests"] = completed_tests
            
            if test_type == 'go_no_go' and 'stroop' not in completed_tests:
                # Go/No-Go finished, proceed to Stroop
                return jsonify({
                    "finished": True,
                    "next_test": "stroop",
                    "redirect_url": "/test_instructions/stroop"
                })
            elif test_type == 'stroop' and 'emoji' not in completed_tests:
                # Stroop finished, proceed to Emoji matching
                return jsonify({
                    "finished": True,
                    "next_test": "emoji",
                    "redirect_url": "/test_instructions/emoji"
                })
            else:
                # All tests finished, show final results
                return jsonify({
                    "finished": True,
                    "final_results": True,
                    "all_scores": test_scores
                })
    
    # For Stroop test, include user answer and correct answer in feedback
    if test_type == 'stroop':
        # For timeout, don't include user_answer in response
        if user_answer == "timeout":
            return jsonify({
                "message": result_message,
                "is_correct": is_correct,
                "correct_answer": correct_answer
            })
        else:
            return jsonify({
                "message": result_message,
                "is_correct": is_correct,
                "user_answer": user_answer,
                "correct_answer": correct_answer
            })
    
    return jsonify({
        "message": result_message,
        "is_correct": is_correct
    })

@app.route("/test_results")
def test_results():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('test_results.html')

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