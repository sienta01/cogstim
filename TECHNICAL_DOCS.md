# Technical Documentation - Cognitive Stimulation App

**Version**: 3.4.0 | **Last Updated**: June 22, 2026

## Architecture Overview

### Technology Stack
- **Backend**: Flask (Python web framework)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **UI Framework**: Materialize CSS (user-facing), Custom dark theme (admin panel)
- **Charting**: Chart.js 4.x
- **Security**: Werkzeug (password hashing)
- **Admin Desktop App**: PyQt6 (optional companion)

---

## Database Models

### User Model
```python
class User(db.Model):
    id: Integer (Primary Key)
    username: String(50) (Unique, Required)
    password_hash: String(255) (Required)
    phone_number: String(20) (Optional)  # e.g. +6281234567890
    is_admin: Boolean (Default: False)
    last_reminder_sent: DateTime (Optional)
    scores: Relationship → Score (one-to-many)
```

### Score Model
```python
class Score(db.Model):
    id: Integer (Primary Key)
    score: Integer (Required)
    test_type: String(50) (Default: 'emoji')  # 'go_no_go', 'stroop', 'emoji'
    reaction_time: Float (Optional, average latency in milliseconds)
    accuracy: Float (Optional, percentage 0-100)
    timestamp: DateTime (Auto-set to current time)
    user_id: Integer (Foreign Key → User)
```

---

## API Routes

### Authentication Routes

#### POST `/register`
- **Parameters**: username, password, phone_number (optional)
- **Action**: Creates user, normalizes phone to +62 prefix, auto-signs in
- **Redirects to**: /dashboard on success
- **Flash message**: "Username sudah digunakan" if duplicate

#### POST `/login`
- **Parameters**: username, password
- **Redirects to**: /dashboard on success
- **Flash message**: "Username atau password salah" on failure

#### GET `/logout`
- **Action**: Clears session
- **Redirects to**: /login

### Test Routes

#### GET `/select_test`
- **Requires**: user_id in session
- **Action**: Initializes test sequence (clears `completed_tests` and `test_scores`) and redirects to `/test_instructions/go_no_go`

#### GET `/test_instructions/<test_type>`
- **Parameters**: test_type ('go_no_go', 'stroop', or 'emoji')
- **Returns**: test_instructions.html with instructions for the specified test

#### GET `/practice/<test_type>`
- **Action**: Initializes a practice session (3 trials) for the given test type
- **Returns**: game.html in practice mode

#### GET `/ready/<test_type>`
- **Action**: Shows a ready/confirmation page after practice
- **Returns**: ready.html

#### GET `/game/<test_type>`
- **Parameters**: test_type ('go_no_go', 'stroop', or 'emoji')
- **Requires**: user_id in session
- **Action**: Initializes actual test (10 trials) and sets session state
- **Session vars set**: test_type, score, correct_count, total_count, trial_index, total_reaction_time, is_practice

#### GET `/next`
- **Returns**: JSON with next trial data or finish summary
- **Response formats**:
  - **Go/No-Go**: `{ "shape": str, "is_go": bool, "finished": bool }`
  - **Stroop**: `{ "word": str, "display_color": hex, "correct_answer": str, "finished": bool }`
  - **Emoji**: `{ "emoji": str, "description": str, "finished": bool }`
  - **Finished**: `{ "finished": true, "score": int, "correct": int, "total": int, "avg_latency": int }`

#### POST `/submit`
- **Body**: JSON with user response + latency
  - **Go/No-Go**: `{ "action": "go" | "nogo" | "nogo_timeout", "latency": int }`
  - **Stroop**: `{ "answer": "red" | ... | "timeout", "latency": int }`
  - **Emoji**: `{ "user_choice": bool, "latency": int }`
- **Returns**:
  - During test: `{ "message": str, "is_correct": bool }`
  - Test finished with next test: `{ "finished": true, "next_test": str, "redirect_url": str }`
  - All tests finished: `{ "finished": true, "final_results": true, "all_scores": {...} }`
- **Side effects**: Saves Score (with accuracy and avg reaction_time) to database on test completion

#### GET `/test_results`
- **Returns**: test_results.html — final results page showing all three test scores with latency

### Dashboard Route

#### GET `/dashboard`
- **Requires**: user_id in session
- **Returns**: dashboard.html
- **Context**:
  - `scores`: List of dicts per date with keys: `date`, `go_no_go`, `stroop`, `emoji`, `go_no_go_latency`, `stroop_latency`, `emoji_latency`
  - `chart_data`: Object with `labels`, score arrays (`go_no_go`, `stroop`, `emoji`), and latency arrays (`go_no_go_latency`, `stroop_latency`, `emoji_latency`)
  - `now`, `username`, `is_admin`

### Navigation Routes

#### GET `/`
- **Redirects to**: /dashboard

#### GET `/reference`
- **Returns**: reference.html

### Admin Routes (Web)

#### GET `/admin`
- **Requires**: admin session
- **Returns**: admin.html — full admin panel with user table and detail modals

#### GET `/admin/api/users`
- **Auth**: Admin session or `X-API-Key` header
- **Returns**: JSON array of user objects with fields:
  - `id`, `username`, `phone_number`, `last_exec`, `off_time`
  - `score_go_nogo`, `score_stroop`, `score_emoji` (latest scores)
  - `latency_go_nogo`, `latency_stroop`, `latency_emoji` (latest reaction times in ms)
  - `last_reminder_sent`

#### GET `/admin/api/user/<user_id>`
- **Auth**: Admin session or API key
- **Returns**: Detailed user data with `score_history` per test type containing `labels`, `scores`, `accuracy`, `reaction_time` arrays

#### POST `/admin/api/users/create`
- **Body**: `{ "username": str, "password": str, "phone_number": str }`
- **Returns**: `{ "success": true, "id": int }`

#### PUT `/admin/api/users/<user_id>/edit`
- **Body**: `{ "username": str, "password": str, "phone_number": str }` (all optional)
- **Returns**: `{ "success": true }`

#### POST `/admin/api/send_reminder/<user_id>`
- **Action**: Records reminder timestamp for user

#### GET `/admin/api/check_pending`
- **Returns**: Users who haven't done any test today (for auto-reminders)

---

## Test Generation Logic

### Go/No-Go Trial Generation
```python
def generate_go_no_go_trials(num_trials):
    # Returns array of {shape, is_go} objects
    # GO_SHAPES = ["⭕", "🔷", "🔶"]
    # NO_GO_SHAPES = ["🔺", "✋"]
  # Randomly selects shape type (approximate 50% go, 50% no-go)
  # Ensures no more than N identical stimulus types in succession (default max 5)
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

### Emoji Trial Generation
```python
def generate_emoji_trials(num_trials):
  # Returns array of {emoji, description, is_match} objects
  # EMOJI_SET = list of (emoji, correct_description)
  # For each trial, randomly choose whether to present a matching or mismatched description
  # Ensure trials are balanced and randomized
```

---

## Session Management

### Session Variables During Test

| Variable | Type | Purpose |
|----------|------|---------|
| user_id | int | Current logged-in user |
| is_admin | bool | Whether user has admin privileges |
| test_type | str | 'go_no_go', 'stroop', or 'emoji' |
| score | int | Current accumulated score |
| correct_count | int | Number of correct responses |
| total_count | int | Total trials attempted |
| trial_index | int | Current trial number (0-indexed) |
| total_reaction_time | float | Sum of all reaction times (ms) |
| is_practice | bool | Whether this run is a practice session |
| go_no_go_trials | list | Array of GO/NO-GO trial objects |
| stroop_trials | list | Array of Stroop trial objects |
| emoji_trials | list | Array of Emoji trial objects |
| completed_tests | list | Tests finished in current sequence |
| test_scores | dict | Accumulated scores per test type |

---

## Scoring System

### Go/No-Go Scoring
- **Points per trial**: 10 points
- **Correct response**: GO action for "JALAN" stimulus, NO action for "DIAM" stimulus
- **Maximum score**: 100 (10 trials × 10 points)

### Stroop Scoring
- **Points per trial**: 10 points
- **Correct response**: Color button matches display color (not word meaning)
- **Maximum score**: 100 (10 trials × 10 points)

### Emoji Matching Scoring
- **Points per trial**: 10 points
- **Correct response**: Correctly identifies whether emoji matches description
- **Maximum score**: 100 (10 trials × 10 points)

### Accuracy Calculation
```
accuracy = (correct_count / total_count) * 100
```
- Stored in `Score.accuracy` field
- Displayed as percentage on results screen

### Latency (Reaction Time) Tracking
```
avg_latency = total_reaction_time / total_count
```
- Each trial's response time (ms) is sent via the `latency` field in `/submit`
- Accumulated in `session['total_reaction_time']` across all trials
- Average stored in `Score.reaction_time` field (ms)
- Displayed in:
  - Dashboard score table (below each score)
  - Dashboard latency chart ("Grafik Waktu Reaksi")
  - Admin panel user table (below each score pill)
  - Admin user detail modal (dual-axis chart with score + latency)
  - Test results page (per-test summary)

---

## Frontend Components

### dashboard.html
- **Purpose**: Main user dashboard
- **Elements**:
  - Greeting with time-of-day awareness
  - "Mulai Latihan" button to start test sequence
  - Admin panel link (admin users only)
  - Score history table with latency sub-text per cell
  - Score trend chart (Chart.js line chart)
  - Latency trend chart ("Grafik Waktu Reaksi", dashed lines)

### test_instructions.html
- **Purpose**: Pre-test instructions page per test type
- **Elements**: Instructions, practice button, start button

### game.html
- **Purpose**: Unified test interface for all three test types
- **Conditional rendering**:
  - Go/No-Go mode: "JALAN"/"DIAM" button display
  - Stroop mode: Colored word + 5 color buttons
  - Emoji mode: Emoji + description + match/no-match buttons
- **Dynamic elements**:
  - Progress bar (updates with trial_index)
  - Result feedback (✅/❌) after each submission
  - Auto-advance to next test on completion

### test_results.html
- **Purpose**: Final results page after all three tests
- **Elements**: Score, accuracy, and average latency per test type

### admin.html
- **Purpose**: Admin panel with dark theme
- **Elements**:
  - Stats row (total users, active today, inactive, no phone)
  - Searchable/sortable user table with scores + latency
  - User detail modal with dual-axis charts (score + reaction time)
  - Toast notifications

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
- **Performance tracking**: Query scores by date range
- **Data export**: Add CSV/PDF export functionality

### Implemented Features (v3.4.0)
- ✅ **Reaction time tracking**: Latency captured per trial, averaged per test
- ✅ **Performance graphs**: Score and latency trend charts on dashboard
- ✅ **Admin analytics**: Dual-axis charts in admin detail modal (score + latency)

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
├── app.py                 # Main application (routes, models, logic)
├── VERSION                # Semantic version file
├── CHANGELOG.md           # Release history
├── TECHNICAL_DOCS.md      # This file
├── USER_GUIDE.md          # End-user guide
├── README.md              # Project overview
├── requirements.txt       # Python dependencies
├── database.db            # SQLite database (generated)
├── static/
│   └── emoji_names.js     # Single source of truth for emoji data
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html     # Score table + score/latency charts
│   ├── test_instructions.html
│   ├── ready.html
│   ├── game.html          # Unified test interface
│   ├── test_results.html  # Final results with latency
│   ├── admin.html         # Admin panel (dark theme)
│   └── reference.html
├── admin_app/             # Desktop admin companion (PyQt6)
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
- [ ] Emoji matching test with correct/incorrect pairings
- [ ] Score accuracy calculation
- [ ] Latency (reaction time) recording and display
- [ ] Dashboard score table shows latency below scores
- [ ] Dashboard latency chart renders correctly
- [ ] Admin table shows latency below score pills
- [ ] Admin detail modal shows dual-axis charts (score + latency)
- [ ] Practice mode (3 trials) followed by actual test (10 trials)
- [ ] Test sequence flow: Go/No-Go → Stroop → Emoji → Results
- [ ] Session timeout behavior
- [ ] Mobile responsiveness
