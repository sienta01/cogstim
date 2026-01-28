# Technical Documentation - Cognitive Stimulation App

## Architecture Overview

### Technology Stack
- **Backend**: Flask (Python web framework)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **UI Framework**: Materialize CSS
- **Security**: Werkzeug (password hashing)

---

## Database Models

### User Model
```python
class User(db.Model):
    id: Integer (Primary Key)
    username: String (Unique, Required)
    password_hash: String (Required)
    patients: Relationship → Patient (one-to-many)
```

### Patient Model
```python
class Patient(db.Model):
    id: Integer (Primary Key)
    name: String (Required)
    age: Integer (Optional)
    notes: Text (Optional)
    user_id: Integer (Foreign Key → User)
    scores: Relationship → Score (one-to-many)
```

### Score Model
```python
class Score(db.Model):
    id: Integer (Primary Key)
    score: Integer (Required)
    test_type: String (Default: "emoji") # 'go_no_go', 'stroop'
    reaction_time: Float (Optional, milliseconds)
    accuracy: Float (Optional, percentage)
    timestamp: DateTime (Auto-set to current time)
    patient_id: Integer (Foreign Key → Patient)
```

---

## API Routes

### Authentication Routes

#### POST `/register`
- **Parameters**: username, password
- **Redirects to**: /login on success
- **Flash message**: "Username sudah digunakan" if duplicate

#### POST `/login`
- **Parameters**: username, password
- **Redirects to**: /dashboard on success
- **Flash message**: "Username atau password salah" on failure

#### GET `/logout`
- **Action**: Clears session
- **Redirects to**: /login

### Patient Management Routes

#### POST `/add_patient`
- **Parameters**: name, age, notes
- **Requires**: user_id in session
- **Action**: Creates new patient linked to current user
- **Redirects to**: /dashboard

#### GET `/edit_patient/<patient_id>`
- **Requires**: user_id in session, patient owned by user
- **Returns**: edit_patient.html template

#### POST `/edit_patient/<patient_id>`
- **Parameters**: name, age, notes
- **Action**: Updates patient record
- **Redirects to**: /dashboard

#### GET `/delete_patient/<patient_id>`
- **Requires**: user_id in session, patient owned by user
- **Action**: Deletes patient and associated scores
- **Redirects to**: /dashboard

#### GET `/select_patient/<patient_id>`
- **Action**: Sets patient in session, redirects to test selection
- **Session vars**: selected_patient_id, selected_patient_name

### Test Routes

#### GET `/select_test`
- **Requires**: user_id in session
- **Returns**: select_test.html (test selection interface)

#### GET `/game/<test_type>`
- **Parameters**: test_type ('go_no_go' or 'stroop')
- **Requires**: user_id, selected_patient_id in session
- **Action**: Initializes test by generating trials
- **Session vars set**:
  - test_type
  - score (0)
  - correct_count (0)
  - total_count (0)
  - trial_index (0)
  - go_no_go_trials OR stroop_trials (array)

#### GET `/next`
- **Returns**: JSON with next trial data
- **Response formats**:
  - **Go/No-Go**: `{ "shape": str, "is_go_trial": bool, "finished": bool }`
  - **Stroop**: `{ "word": str, "display_color": hex, "correct_answer": str, "finished": bool }`

#### POST `/submit`
- **Body**: JSON with user response
- **Go/No-Go**: `{ "action": "go" | "no_go" }`
- **Stroop**: `{ "answer": "red" | "blue" | "green" | "yellow" | "purple" }`
- **Returns**: 
  - During test: `{ "message": str, "is_correct": bool }`
  - On completion: `{ "finished": true, "score": int, "correct": int, "total": int }`
- **Side effects**: Saves Score to database when test completes

### Score/History Routes

#### GET `/scores`
- **Returns**: scores.html with paginated scores
- **Shows**: Last 100 scores for user's patients

#### GET `/view_patient_scores/<patient_id>`
- **Returns**: scores.html filtered to specific patient
- **Shows**: All scores for that patient in descending timestamp order

### Navigation Routes

#### GET `/`
- **Redirects to**: /dashboard

#### GET `/dashboard`
- **Requires**: user_id in session
- **Returns**: dashboard.html with patient list
- **Context**: patients list, current time, username

#### GET `/reference`
- **Returns**: reference.html
- **Purpose**: Legacy route (kept for compatibility)

---

## Test Generation Logic

### Go/No-Go Trial Generation
```python
def generate_go_no_go_trials(num_trials):
    # Returns array of {shape, is_go} objects
    # GO_SHAPES = ["⭕", "🔷", "🔶"]
    # NO_GO_SHAPES = ["🔺", "✋"]
    # Randomly selects shape type (50% go, 50% no-go)
```

### Stroop Trial Generation
```python
def generate_stroop_trials(num_trials):
    # Returns array of {word, display_color, correct_answer} objects
    # word = COLOR_DISPLAY_NAMES[meaning] (Indonesian: MERAH, BIRU, etc.)
    # display_color = COLOR_HEX[color] (RGB hex value)
    # correct_answer = color (the displayed color, not word meaning)
    # Ensures word color ≠ word meaning (always mismatch)
```

---

## Session Management

### Session Variables During Test

| Variable | Type | Purpose |
|----------|------|---------|
| user_id | int | Current logged-in user |
| selected_patient_id | int | Patient for score recording |
| selected_patient_name | str | Patient display name |
| test_type | str | 'go_no_go' or 'stroop' |
| score | int | Current accumulated score |
| correct_count | int | Number of correct responses |
| total_count | int | Total trials attempted |
| trial_index | int | Current trial number (0-19) |
| go_no_go_trials | list | Array of GO/NO-GO trials |
| stroop_trials | list | Array of Stroop trials |

---

## Scoring System

### Go/No-Go Scoring
- **Points per trial**: 10 points
- **Correct response**: Matches trial type (GO action for GO shapes, NO action for NO-GO)
- **Maximum score**: 200 (20 trials × 10 points)

### Stroop Scoring
- **Points per trial**: 10 points
- **Correct response**: Color button matches display color (not word meaning)
- **Maximum score**: 200 (20 trials × 10 points)

### Accuracy Calculation
```
accuracy = (correct_count / total_count) * 100
```
- Stored in Score.accuracy field
- Displayed as percentage on results screen

---

## Frontend Components

### select_test.html
- **Purpose**: Test type selection
- **Elements**:
  - Test description cards
  - Links to start each test
  - Back button to dashboard
- **Styling**: Gradient background, card-based layout

### game.html
- **Purpose**: Unified test interface
- **Conditional rendering**:
  - Go/No-Go mode: Shape display + button
  - Stroop mode: Word display + 5 color buttons
- **Dynamic elements**:
  - Progress bar (updates with trial_index)
  - Result message (updates after submission)
  - Final results screen (on completion)
- **Styling**: Materialize CSS, animations, responsive

### scores.html
- **Purpose**: Score history display
- **Features**:
  - Sortable columns (click header to sort)
  - Test type indicators (emojis)
  - Accuracy percentage display
  - Formatted timestamps

---

## JavaScript Flow

### Test Execution Flow (game.html)

```
loadNextTrial()
    ↓
displayGoNoGoTrial() OR displayStroopTrial()
    ↓
submitGoNoGo() OR submitStroop() [on user action]
    ↓
handleResponse()
    ↓
if finished:
    showFinalResults()
else:
    loadNextTrial() [after 1.5s delay]
```

### Response Handling
- Prevents multiple submissions (responseGiven flag)
- Provides immediate feedback (✅/❌)
- Delays next trial by 1500ms for user to see feedback
- Handles completion by displaying results screen

---

## Security Considerations

### Implemented
- ✅ Password hashing with Werkzeug (PBKDF2)
- ✅ Session-based authentication
- ✅ User-patient relationship validation
- ✅ CSRF protection via Flask defaults

### Recommendations for Production
- [ ] Implement HTTPS/SSL
- [ ] Add rate limiting for API endpoints
- [ ] Implement CSRF tokens in forms
- [ ] Add input validation and sanitization
- [ ] Implement audit logging for data changes
- [ ] Use environment variables for config
- [ ] Implement session expiration
- [ ] Add email verification for registration

---

## Performance Considerations

### Database Queries
- Patient queries filtered by user_id (prevents data leakage)
- Score queries use pagination (limit 100)
- Indexes recommended on: user_id, patient_id, test_type

### Frontend Optimization
- Minimal external dependencies (only Materialize)
- Async fetch for API calls (no page reload)
- CSS animations for visual feedback
- Immediate UI response (no loading spinners needed)

### Session Management
- Trials stored in session (not database)
- Score saved only on test completion
- Session cleared on logout

---

## Error Handling

### Backend Error Handling
- Missing session variables → Redirect to login
- Invalid patient ID → Flash message, redirect
- Invalid test type → Flash message, redirect to test selection
- Database errors → Implicit 500 error (should add handler)

### Frontend Error Handling
- Network errors → No explicit handling (should add)
- Missing DOM elements → Silent fail (should add error display)

### Recommended Improvements
- Add try-catch blocks in JavaScript
- Implement error modal for network failures
- Add server-side error logging
- Implement 404 and 500 error pages

---

## Extension Points

### Adding New Tests
1. Add test configuration to app.py
2. Create trial generation function
3. Add test type to game/<test_type> route
4. Create test UI in game.html
5. Add submission logic in /submit route
6. Update scores.html to display new test type

### Adding Features
- **Difficulty levels**: Add difficulty parameter to trial generation
- **Reaction time**: Add timestamp to frontend, calculate in submit
- **Performance tracking**: Query scores by date range
- **Data export**: Add CSV/PDF export functionality
- **Statistics**: Add dashboard with performance graphs

---

## Deployment Checklist

- [ ] Set SECRET_KEY to random value
- [ ] Change SQLALCHEMY_DATABASE_URI for production DB
- [ ] Enable HTTPS
- [ ] Set Flask debug=False
- [ ] Configure proper logging
- [ ] Set up database backups
- [ ] Test error pages
- [ ] Configure CORS if needed
- [ ] Set up monitoring/alerting
- [ ] Implement rate limiting

---

## File Structure

```
cogstim/
├── app.py                 # Main application file
├── models.py              # Empty (could move models here)
├── game.py                # Empty (could add game logic)
├── auth.py                # Empty (could move auth here)
├── requirements.txt       # Python dependencies
├── database.db            # SQLite database (generated)
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── edit_patient.html
│   ├── select_test.html   # NEW
│   ├── game.html          # UPDATED
│   ├── scores.html        # UPDATED
│   └── reference.html
└── __pycache__/
```

---

## Testing Recommendations

### Unit Tests to Add
- Password hashing/verification
- Trial generation logic
- Score calculation
- Session management

### Integration Tests to Add
- Complete user flow (register → add patient → run test → view scores)
- Invalid patient access prevention
- Multiple concurrent users
- Database persistence

### Manual Testing Checklist
- [ ] Go/No-Go test with correct and incorrect responses
- [ ] Stroop test with color matching
- [ ] Score accuracy calculation
- [ ] Multi-patient score separation
- [ ] Session timeout behavior
- [ ] Mobile responsiveness
