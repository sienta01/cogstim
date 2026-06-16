"""
Cognitive Stimulation Application
Version: 3.1.1
Release Date: June 17, 2026
Author: Timothy Subroto
Description: Professional cognitive assessment platform with Go/No-Go, Color Stroop, and Emoji Matching tests
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os
import re
import datetime
import time

# Set Timezone to UTC+8 (Indonesia/Jakarta)
os.environ["TZ"] = "Asia/Makassar"
try:
    time.tzset()
except AttributeError:
    pass  # time.tzset() is Unix-only, this allows local Windows development to continue working

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load version dynamically from VERSION file
def load_version():
    version_file = os.path.join(BASE_DIR, 'VERSION')
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return "3.1.0"
        
__version__ = load_version()

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

# Emoji Matching Test Configuration — loaded from emoji_names.js (single source of truth)
def load_emoji_set():
    """Load emoji data from static/emoji_names.js so it remains the single source of truth."""
    js_path = os.path.join(BASE_DIR, 'static', 'emoji_names.js')
    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    pairs = re.findall(r"'([^']+)':\s*'([^']+)'", content)
    return [{"emoji": emoji, "description": name} for emoji, name in pairs]

EMOJI_SET = load_emoji_set()

# Use absolute path for PythonAnywhere compatibility
# On PythonAnywhere, use home directory to avoid I/O issues
DB_PATH = os.path.expanduser('~/cogstim_data/database.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)  # e.g. +6281234567890
    is_admin = db.Column(db.Boolean, default=False)
    last_reminder_sent = db.Column(db.DateTime, nullable=True)

    # Relationship to Score
    scores = db.relationship('Score', backref='user', lazy=True)

# Score Model
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    test_type = db.Column(db.String(50), default="emoji")  # 'emoji', 'go_no_go', 'stroop'
    reaction_time = db.Column(db.Float, nullable=True)  # in milliseconds
    accuracy = db.Column(db.Float, nullable=True)  # percentage
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Dashboard route
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    user_scores = Score.query.filter_by(user_id=user.id).order_by(Score.timestamp.desc()).limit(10).all() if user else []
    now = datetime.datetime.now()
    username = user.username if user else ""
    is_admin = session.get("is_admin", False)
    return render_template("dashboard.html", scores=user_scores, now=now, username=username, is_admin=is_admin)

@app.route("/reference")
def reference():
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
    # Initialize test sequence — user plays as themselves
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
    session["total_reaction_time"] = 0
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
    session["total_reaction_time"] = 0
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
            flash("Pengguna tidak ditemukan, silakan daftar.")
        elif check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["is_admin"] = user.is_admin
            return redirect(url_for("dashboard"))
        else:
            flash("Username atau password salah.")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        phone_number = request.form.get("phone_number", "").strip()
        # Normalize phone number: ensure +62 prefix
        if phone_number:
            phone_number = phone_number.lstrip('0').lstrip('+').lstrip('62')
            phone_number = '+62' + phone_number
        if User.query.filter_by(username=username).first():
            flash("Username sudah digunakan.")
            return render_template("register.html")
        password_hash = generate_password_hash(password)
        new_user = User(username=username, password_hash=password_hash, phone_number=phone_number if phone_number else None)
        db.session.add(new_user)
        db.session.commit()
        # Auto sign-in after registration
        session["user_id"] = new_user.id
        session["is_admin"] = new_user.is_admin
        return redirect(url_for("dashboard"))
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
    if "user_id" not in session:
        return redirect(url_for("login"))

    data = request.get_json()
    test_type = session.get("test_type")
    trial_index = session.get("trial_index", 0)
    is_practice = session.get("is_practice", False)
    latency = data.get("latency", 0)
    session["total_reaction_time"] = session.get("total_reaction_time", 0) + latency
    
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
            session["score"] += 10
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
            session["score"] += 10
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
            session["score"] += 10
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
            avg_latency = session.get("total_reaction_time", 0) / session["total_count"] if session["total_count"] > 0 else 0
            test_scores = session.get("test_scores", {})
            test_scores[test_type] = {
                "score": session["score"],
                "correct_count": session["correct_count"],
                "total_count": session["total_count"],
                "avg_latency": round(avg_latency)
            }
            session["test_scores"] = test_scores
            
            # Save score to database
            accuracy = (session["correct_count"] / session["total_count"] * 100) if session["total_count"] > 0 else 0
            new_score = Score(
                score=session["score"],
                test_type=test_type,
                accuracy=accuracy,
                reaction_time=avg_latency,
                user_id=session["user_id"]
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
                    "is_correct": is_correct,
                    "message": result_message,
                    "next_test": "stroop",
                    "redirect_url": "/test_instructions/stroop"
                })
            elif test_type == 'stroop' and 'emoji' not in completed_tests:
                # Stroop finished, proceed to Emoji matching
                return jsonify({
                    "finished": True,
                    "is_correct": is_correct,
                    "message": result_message,
                    "next_test": "emoji",
                    "redirect_url": "/test_instructions/emoji"
                })
            else:
                # All tests finished, show final results
                return jsonify({
                    "finished": True,
                    "is_correct": is_correct,
                    "message": result_message,
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

    is_admin = session.get("is_admin", False)
    if is_admin:
        # Admin can see all scores from all users
        user_scores = Score.query.order_by(Score.timestamp.desc()).limit(200).all()
    else:
        # Normal user sees only their own scores
        user_scores = Score.query.filter_by(user_id=session["user_id"]).order_by(Score.timestamp.desc()).limit(100).all()
    return render_template("scores.html", scores=user_scores, is_admin=is_admin)


# ── Admin Panel (Web) ──────────────────────────────────────────────

@app.route("/admin")
def admin_panel():
    """Web admin panel – shows all users and their info"""
    if 'user_id' not in session or not session.get('is_admin', False):
        flash("Akses ditolak. Hanya admin.")
        return redirect(url_for('login'))
    return render_template('admin.html')


@app.route("/admin/api/users")
def admin_api_users():
    """JSON endpoint – user table data (consumed by both web admin & desktop app)"""
    # Allow access from desktop app via API key OR admin session
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    is_admin_session = 'user_id' in session and session.get('is_admin', False)
    if not is_admin_session and api_key != app.config.get('ADMIN_API_KEY', 'cogstim-admin-secret-key-2026'):
        return jsonify({"error": "Unauthorized"}), 401

    users = User.query.filter_by(is_admin=False).all()
    result = []
    for u in users:
        # Latest scores per test type
        latest_scores = {}
        for tt in ['go_no_go', 'stroop', 'emoji']:
            s = Score.query.filter_by(user_id=u.id, test_type=tt).order_by(Score.timestamp.desc()).first()
            latest_scores[tt] = s.score if s else None

        # Last execution = most recent score timestamp
        last_score = Score.query.filter_by(user_id=u.id).order_by(Score.timestamp.desc()).first()
        last_exec = last_score.timestamp.strftime('%Y-%m-%d %H:%M') if last_score and last_score.timestamp else None

        # Off time = days since last execution
        if last_score and last_score.timestamp:
            delta = datetime.datetime.utcnow() - last_score.timestamp
            off_time = f"{delta.days}d {delta.seconds // 3600}h"
        else:
            off_time = "Never"

        result.append({
            'id': u.id,
            'username': u.username,
            'phone_number': u.phone_number or '',
            'last_exec': last_exec,
            'off_time': off_time,
            'score_go_nogo': latest_scores['go_no_go'],
            'score_stroop': latest_scores['stroop'],
            'score_emoji': latest_scores['emoji'],
            'last_reminder_sent': u.last_reminder_sent.strftime('%Y-%m-%d %H:%M') if u.last_reminder_sent else None
        })
    return jsonify(result)


@app.route("/admin/api/user/<int:user_id>")
def admin_api_user_detail(user_id):
    """JSON endpoint – detailed user data including score history for graphs"""
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    is_admin_session = 'user_id' in session and session.get('is_admin', False)
    if not is_admin_session and api_key != app.config.get('ADMIN_API_KEY', 'cogstim-admin-secret-key-2026'):
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get_or_404(user_id)
    scores = Score.query.filter_by(user_id=user.id).order_by(Score.timestamp.asc()).all()

    score_history = {}
    for tt in ['go_no_go', 'stroop', 'emoji']:
        entries = [s for s in scores if s.test_type == tt]
        score_history[tt] = {
            'labels': [s.timestamp.strftime('%d/%m %H:%M') if s.timestamp else '' for s in entries],
            'scores': [s.score for s in entries],
            'accuracy': [round(s.accuracy, 1) if s.accuracy else 0 for s in entries],
            'reaction_time': [round(s.reaction_time) if s.reaction_time else 0 for s in entries]
        }

    last_score = Score.query.filter_by(user_id=user.id).order_by(Score.timestamp.desc()).first()

    return jsonify({
        'id': user.id,
        'username': user.username,
        'phone_number': user.phone_number or '',
        'last_exec': last_score.timestamp.strftime('%Y-%m-%d %H:%M') if last_score and last_score.timestamp else None,
        'last_reminder_sent': user.last_reminder_sent.strftime('%Y-%m-%d %H:%M') if user.last_reminder_sent else None,
        'score_history': score_history
    })


@app.route("/admin/api/send_reminder/<int:user_id>", methods=["POST"])
def admin_send_reminder(user_id):
    """Record that a reminder was sent (actual WhatsApp sending is done by desktop app)"""
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    is_admin_session = 'user_id' in session and session.get('is_admin', False)
    if not is_admin_session and api_key != app.config.get('ADMIN_API_KEY', 'cogstim-admin-secret-key-2026'):
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get_or_404(user_id)
    user.last_reminder_sent = datetime.datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "message": f"Reminder recorded for {user.username}"})


@app.route("/admin/api/check_pending")
def admin_api_check_pending():
    """Return users who haven't done any test today (for auto-reminder at 1pm)"""
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    if api_key != app.config.get('ADMIN_API_KEY', 'cogstim-admin-secret-key-2026'):
        return jsonify({"error": "Unauthorized"}), 401

    today = datetime.datetime.utcnow().date()
    users = User.query.filter_by(is_admin=False).all()
    pending = []
    for u in users:
        if not u.phone_number:
            continue
        last_score = Score.query.filter_by(user_id=u.id).order_by(Score.timestamp.desc()).first()
        did_today = False
        if last_score and last_score.timestamp:
            did_today = last_score.timestamp.date() == today
        if not did_today:
            pending.append({
                'id': u.id,
                'username': u.username,
                'phone_number': u.phone_number
            })
    return jsonify(pending)


@app.route("/admin/api/users/create", methods=["POST"])
def admin_api_create_user():
    """Create a new user account from admin panel"""
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    is_admin_session = 'user_id' in session and session.get('is_admin', False)
    if not is_admin_session and api_key != app.config.get('ADMIN_API_KEY', 'cogstim-admin-secret-key-2026'):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    phone_number = (data.get('phone_number') or '').strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    # Normalize phone number
    if phone_number:
        phone_number = phone_number.lstrip('0').lstrip('+').lstrip('62')
        phone_number = '+62' + phone_number

    new_user = User(
        username=username,
        password_hash=generate_password_hash(password),
        phone_number=phone_number if phone_number else None
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"success": True, "message": f"User '{username}' created", "id": new_user.id}), 201


@app.route("/admin/api/users/<int:user_id>/edit", methods=["PUT"])
def admin_api_edit_user(user_id):
    """Edit an existing user account"""
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    is_admin_session = 'user_id' in session and session.get('is_admin', False)
    if not is_admin_session and api_key != app.config.get('ADMIN_API_KEY', 'cogstim-admin-secret-key-2026'):
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get_or_404(user_id)
    data = request.get_json()

    new_username = (data.get('username') or '').strip()
    new_phone = (data.get('phone_number') or '').strip()
    new_password = (data.get('password') or '').strip()

    if new_username and new_username != user.username:
        if User.query.filter_by(username=new_username).first():
            return jsonify({"error": "Username already exists"}), 409
        user.username = new_username

    if new_phone:
        new_phone = new_phone.lstrip('0').lstrip('+').lstrip('62')
        new_phone = '+62' + new_phone
    user.phone_number = new_phone if new_phone else None

    if new_password:
        user.password_hash = generate_password_hash(new_password)

    db.session.commit()
    return jsonify({"success": True, "message": f"User '{user.username}' updated"})


@app.route("/admin/api/users/<int:user_id>/delete", methods=["DELETE"])
def admin_api_delete_user(user_id):
    """Delete a user account and all associated scores"""
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    is_admin_session = 'user_id' in session and session.get('is_admin', False)
    if not is_admin_session and api_key != app.config.get('ADMIN_API_KEY', 'cogstim-admin-secret-key-2026'):
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get_or_404(user_id)
    if user.is_admin:
        return jsonify({"error": "Cannot delete admin accounts"}), 403

    username = user.username
    Score.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({"success": True, "message": f"User '{username}' deleted"})


with app.app_context():
    db.create_all()  # Create database tables if they don't exist
    # Add new columns if they don't exist (migration for existing databases)
    import sqlalchemy
    inspector = sqlalchemy.inspect(db.engine)
    existing_columns = [col['name'] for col in inspector.get_columns('user')]
    if 'phone_number' not in existing_columns:
        with db.engine.connect() as conn:
            conn.execute(sqlalchemy.text('ALTER TABLE user ADD COLUMN phone_number VARCHAR(20)'))
            conn.commit()
    if 'last_reminder_sent' not in existing_columns:
        with db.engine.connect() as conn:
            conn.execute(sqlalchemy.text('ALTER TABLE user ADD COLUMN last_reminder_sent DATETIME'))
            conn.commit()

# Run the application for development
if __name__ == "__main__":
    app.run(debug=True)