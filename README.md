# Cognitive Stimulation Assessment Platform

![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)
![Release Date](https://img.shields.io/badge/release-2026--06--14-brightgreen.svg)
![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.0+-red.svg)

> A professional cognitive assessment platform featuring scientifically-validated cognitive tests for measuring response inhibition, executive function, and selective attention.

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Features](#features)
- [Test Types](#test-types)
- [Installation](#installation)
- [Usage](#usage)
- [Documentation](#documentation)
- [System Requirements](#system-requirements)
- [Version History](#version-history)
- [License](#license)

---

## 🚀 Quick Start

### Run the Application
```bash
cd "c:\Users\user\OneDrive\Documents\IT Stuffs\GitHub\cogstim"
python app.py
```

Then open your browser to: `http://localhost:5000`

### Default Access
1. **Register** a new account or login
2. **Add a patient** to track
3. **Run tests**: by default tests run in sequence (Go/No-Go → Stroop → Emoji Matching). You can run practice rounds first.
4. **Complete the test sequence** and view consolidated results

---

## ✨ Features

### Core Features
✅ **Professional Cognitive Tests** - Two scientifically-validated assessment tools
✅ **User Authentication** - Secure login and registration system
✅ **Patient Management** - Add, edit, and track multiple patients
✅ **Score History** - Complete tracking of test results with timestamps
✅ **Real-Time Feedback** - Immediate correctness feedback during tests
✅ **Accuracy Tracking** - Percentage accuracy and reaction time measurements
✅ **Responsive Design** - Works seamlessly on desktop, tablet, and mobile devices
✅ **Progress Visualization** - Visual progress bars during testing

### Test Features
- Variable trials per test (see Test Types)
- Practice rounds available (3 practice trials per test)
- Timed responses with reaction time tracking
- Brief blank inter-trial interval to reduce carry-over effects
- Accurate scoring and percentage accuracy reporting
- Test-specific feedback and consolidated results across tests

---

## 🎯 Test Types

### 1️⃣ Go/No-Go Test
**Purpose**: Measures response inhibition and impulse control

- **GO Stimuli**: ⭕ 🔷 🔶 (User must click the button)
- **NO-GO Stimuli**: 🔺 ✋ (User must NOT click)
-- **Duration**: ~30-60 seconds
-- **Trials**: 10
-- **Max Score**: 100 points
-- **Scoring**: 10 points per correct response
-- **Notes**: Stimulus generator limits consecutive identical stimuli (max 5 in succession)

**Clinical Application**: 
- Assesses executive function
- Evaluates impulse control
- Measures response inhibition
- Used in ADHD and impulse disorder assessment

---

### 2️⃣ Color Stroop Test
**Purpose**: Measures executive function and selective attention

- **Task**: Color words displayed in different colors (e.g., word "MERAH" in BLUE color)
- **Requirement**: Click the button matching the TEXT COLOR (not word meaning)
-- **Duration**: ~60-150 seconds
-- **Trials**: 20
-- **Max Score**: 200 points
-- **Scoring**: 10 points per correct response

---

### 3️⃣ Emoji Matching Test
**Purpose**: Quick associative matching test using emoji and short labels

- **Task**: A target emoji is shown with a textual description. Choose whether the description matches the emoji (True / False).
- **Trials**: 10
- **Max Score**: 100 points
- **Scoring**: 10 points per correct response
- **Notes**: Practice rounds available; included as the final test in the default sequence

**Color Codes (Indonesian)**:
- 🔴 MERAH (Red)
- 🔵 BIRU (Blue)
- 🟢 HIJAU (Green)
- 🟡 KUNING (Yellow)
- 🟣 UNGU (Purple)

**Clinical Application**:
- Tests selective attention
- Measures cognitive flexibility
- Evaluates executive function
- Used in dementia and cognitive decline screening

---

## 📦 Installation

### Prerequisites
- Python 3.7 or higher
- Flask 2.0 or higher
- SQLAlchemy
- SQLite3

### Setup Instructions

1. **Clone the repository**
```bash
cd "c:\Users\user\OneDrive\Documents\IT Stuffs\GitHub\cogstim"
```

2. **Create virtual environment** (Optional but recommended)
```bash
python -m venv .venv
.venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
python app.py
```

5. **Access the application**
Open browser to: `http://localhost:5000`

---

## 📖 Usage

### For Clinicians/Testers

1. **Register Account**
   - Go to Registration page
   - Create username and password
   - Click "Register"

2. **Add Patient**
   - Go to Dashboard
   - Enter patient name, age, and notes
   - Click "Add Patient"

3. **Run Test**
   - Select patient from list
   - Choose test type (Go/No-Go or Stroop)
   - Follow on-screen instructions
   - Complete all trials
   - View results

4. **View History**
   - Click "View Scores" on Dashboard
   - See all test results for patient
   - Compare test types and accuracy

### For Administrators

- User management and patient oversight
- Score history review
- Performance tracking and reporting
- System monitoring

---

## 📚 Documentation

### For Users
| Document | Purpose | Time |
|----------|---------|------|
| [USER_GUIDE.md](./USER_GUIDE.md) | Step-by-step usage instructions | 10 min |
| [README_CHANGES.md](./README_CHANGES.md) | Quick overview of changes | 5 min |

### For Developers
| Document | Purpose | Time |
|----------|---------|------|
| [TECHNICAL_DOCS.md](./TECHNICAL_DOCS.md) | Complete technical reference | 30 min |
| [REFACTOR_SUMMARY.md](./REFACTOR_SUMMARY.md) | Detailed implementation changes | 15 min |
| [FLOW_DIAGRAM.md](./FLOW_DIAGRAM.md) | Visual flowcharts and diagrams | 10-20 min |

### For Project Overview
| Document | Purpose | Time |
|----------|---------|------|
| [BEFORE_AFTER_COMPARISON.md](./BEFORE_AFTER_COMPARISON.md) | Impact and improvements | 15 min |
| [DOCUMENTATION_INDEX.md](./DOCUMENTATION_INDEX.md) | Navigation guide | 5 min |
| [PROJECT_COMPLETION.md](./PROJECT_COMPLETION.md) | Completion status | 5 min |
| [CHANGELOG.md](./CHANGELOG.md) | Version history and changes | 10 min |

---

## 💻 System Requirements

### Minimum Requirements
- **OS**: Windows, macOS, or Linux
- **Python**: 3.7+
- **RAM**: 512 MB
- **Disk**: 500 MB
- **Browser**: Modern browser (Chrome, Firefox, Safari, Edge)

### Recommended Requirements
- **OS**: Windows 10/11 or Ubuntu 20.04+
- **Python**: 3.9+
- **RAM**: 2 GB
- **Disk**: 1 GB
- **Browser**: Chrome/Firefox (latest versions)

---

## 📊 Database Schema

### User Model
```
- id (Primary Key)
- username (Unique)
- password_hash
- patients (Relationship)
```

### Patient Model
```
- id (Primary Key)
- name
- age
- notes
- user_id (Foreign Key → User)
- scores (Relationship)
```

### Score Model
```
- id (Primary Key)
- score (0-200)
- test_type (go_no_go, stroop)
- reaction_time (milliseconds)
- accuracy (percentage)
- timestamp
- patient_id (Foreign Key → Patient)
```

---

## 🔧 Configuration

### Application Settings (app.py)
```python
SECRET_KEY = 'your_secret_key'
SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False
```

### Test Configurations

**Go/No-Go Test**
- GO_SHAPES: ["TEKAN"]
- NO_GO_SHAPES: ["JANGAN TEKAN"]
- Trials: 20
- Points per trial: 10

**Color Stroop Test**
- COLORS: ["red", "blue", "green", "yellow", "purple"]
- Trials: 20
- Points per trial: 10

---

## 📈 Test Scoring

### Scoring Method
- **Correct Response**: +10 points
- **Incorrect Response**: 0 points
- **No Response (Timeout)**: 0 points
- **False Positive (No-Go)**: 0 points (no points deducted)

### Accuracy Calculation
```
Accuracy % = (Correct Responses / Total Trials) × 100
```

### Performance Interpretation
- **90-100%**: Excellent (180-200 points)
- **80-89%**: Good (160-179 points)
- **70-79%**: Fair (140-159 points)
- **60-69%**: Below Average (120-139 points)
- **< 60%**: Poor (< 120 points)

---

## 🐛 Troubleshooting

### Application Won't Start
```
Error: Address already in use
Solution: Change port in app.py or kill process on port 5000
```

### Database Errors
```
Error: Database locked
Solution: Close all connections and restart application
```

### Test Not Responding
```
Solution: 
1. Refresh page
2. Clear browser cache
3. Restart application
```

### Scores Not Saving
```
Solution:
1. Check database.db file exists
2. Verify write permissions
3. Check browser console for errors
```

---

## 📝 Version Information

### Current Version: 2.3.0
- **Release Date**: March 11, 2026
- **Status**: Stable
- **Last Updated**: 2026-03-11

### Version History
See [CHANGELOG.md](./CHANGELOG.md) for complete version history and release notes.

### Major Changes in v2.3.0
- **Dashboard Redesign**: Simplified dashboard to focus on user scores instead of patient management
- **Geriatric UI**: Designed a geriatric-friendly login and interface with high contrast and larger fonts
- **Role-Based Access**: Implemented admin vs normal user roles for score visibility
- **Code Optimization**: Cleaned up the codebase, removing unused files and optimizing code

### Major Changes in v2.2.1
- Documentation consolidation and cleanup
- Removed redundant temporary files
- Streamlined version tracking system

### Major Changes in v2.2.0
- **New Test**: Emoji Matching test integrated
- **Practice Mode**: 3 practice trials for each test
- **Ready Page**: Confirmation page after practice
- **Improved Flow**: Go/No-Go → Stroop → Emoji Matching → Results

### Major Changes in v2.1.0
- Added version tracking infrastructure
- VERSION file for easy access
- CHANGELOG.md for complete history

---

## 📞 Support

### Getting Help
1. **Read Documentation**: Start with [USER_GUIDE.md](./USER_GUIDE.md)
2. **Check Troubleshooting**: See section above
3. **Review Technical Docs**: [TECHNICAL_DOCS.md](./TECHNICAL_DOCS.md)
4. **Check Changelog**: [CHANGELOG.md](./CHANGELOG.md)

### Common Tasks
- **How to use the app**: [USER_GUIDE.md](./USER_GUIDE.md)
- **What changed**: [README_CHANGES.md](./README_CHANGES.md) or [CHANGELOG.md](./CHANGELOG.md)
- **Technical details**: [TECHNICAL_DOCS.md](./TECHNICAL_DOCS.md)
- **Navigation guide**: [DOCUMENTATION_INDEX.md](./DOCUMENTATION_INDEX.md)

---

## 📄 License

This project is provided as-is for clinical and educational use.
For commercial use, contact the development team.

---

## 🎓 Clinical References

### Go/No-Go Test
- **Measure**: Response Inhibition, Executive Function
- **Population**: ADHD, Impulse Disorders, Executive Dysfunction
- **Duration**: 20-40 seconds
- **Reliability**: Validated cognitive assessment tool

### Color Stroop Test
- **Measure**: Executive Function, Selective Attention, Cognitive Flexibility
- **Population**: Dementia, Cognitive Decline, Executive Disorders
- **Duration**: 40-100 seconds
- **Reliability**: Widely used in cognitive assessment batteries

---

## 👥 Development Team

**Cognitive Stimulation Assessment Platform**
- Version: 2.3.0
- Framework: Flask + SQLAlchemy + SQLite
- Python: 3.7+
- Last Updated: March 11, 2026

---

## 📌 Quick Links

- [Quick Start Guide](#quick-start)
- [Installation Instructions](#installation)
- [User Guide](./USER_GUIDE.md)
- [Technical Documentation](./TECHNICAL_DOCS.md)
- [Change Log](./CHANGELOG.md)
- [Documentation Index](./DOCUMENTATION_INDEX.md)

---

## 🔗 File Structure

```
cogstim/
├── app.py                          # Main application
├── auth.py                         # Authentication module (empty)
├── game.py                         # Game logic module (empty)
├── models.py                       # Database models (empty)
├── requirements.txt                # Python dependencies
├── VERSION                         # Current version number
├── database.db                     # SQLite database
├── README.md                       # This file
├── CHANGELOG.md                    # Version history
├── templates/
│   ├── dashboard.html             # Main dashboard
│   ├── login.html                 # Login page
│   ├── register.html              # Registration page
│   ├── game.html                  # Test interface
│   ├── select_test.html           # Test selection
│   ├── scores.html                # Score history
│   ├── edit_patient.html          # Patient editor
│   ├── test_instructions.html     # Test instructions
│   ├── test_results.html          # Results display
│   └── reference.html             # Reference page
└── docs/
    ├── USER_GUIDE.md              # User instructions
    ├── TECHNICAL_DOCS.md          # Technical reference
    ├── README_CHANGES.md          # Change summary
    ├── REFACTOR_SUMMARY.md        # Implementation details
    ├── FLOW_DIAGRAM.md            # Process diagrams
    ├── BEFORE_AFTER_COMPARISON.md # Improvements
    ├── DOCUMENTATION_INDEX.md     # Navigation guide
    └── PROJECT_COMPLETION.md      # Project status
```

---

**Last Updated**: March 11, 2026  
**Version**: 2.3.0  
**Status**: Production Ready ✅

