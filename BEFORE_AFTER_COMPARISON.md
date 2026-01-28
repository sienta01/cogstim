# Before & After Comparison

## Test Type Comparison

### BEFORE: Emoji-Description Matching

```
Test Name: Emoji Matching Game
Purpose: Memory/pattern matching
Mechanism: 
  - Display emoji (e.g., 😀)
  - Display description (correct or incorrect)
  - User clicks "Benar" (True) or "Salah" (False)
  
Example Trial:
  Emoji: 😀
  Description: Wajah
  Expected Response: "Benar" (True)

Duration: ~1-2 minutes (10 trials)
Max Score: 100 (10 points × 10 trials)
Cognitive Domain: Recognition memory

Data Tracked:
  - Score only
  - No accuracy %
  - No test type differentiation
```

---

### AFTER: Multi-test Suite (Go/No-Go, Stroop, Emoji)

#### Test 1: Go/No-Go Test

```
Test Name: Go/No-Go Response Inhibition Test
Purpose: Measure response inhibition & impulse control
Mechanism:
  - Display random shape
  - For GO shapes (⭕ 🔷 🔶): User clicks "TEKAN GO" button
  - For NO-GO shapes (🔺 ✋): User waits (doesn't click)

Example Trial:
  Trial 1: Shape ⭕ appears → User clicks → ✅ Correct (GO trial)
  Trial 2: Shape 🔺 appears → User waits → ✅ Correct (NO-GO trial)
  Trial 3: Shape ⭕ appears → User waits → ❌ Wrong (should have clicked)

Duration: ~30-60 seconds (10 trials)
Max Score: 100 (10 points × 10 trials)
Practice: 3 trials available
Cognitive Domain: Response inhibition, executive control

Data Tracked:
  - Score (0-200)
  - Accuracy percentage
  - Correct/total responses
  - Test type identifier
  - Optional: Reaction time
```

#### Test 2: Color Stroop Test

```
Test Name: Color Stroop Selective Attention Test
Purpose: Measure executive function & cognitive flexibility
Mechanism:
  - Display a color word in a DIFFERENT color
  - User must click button matching TEXT COLOR (not word meaning)
  
Example Trial:
  Word displayed: "MERAH" (means "Red")
  Color displayed in: Blue (#0000FF)
  User should click: Blue button (text color)
  
  If user clicks Red (word meaning): ❌ Wrong
  If user clicks Blue (text color): ✅ Correct

Why hard? Brain automatically tries to read the word,
creating cognitive conflict between word meaning and color

Duration: ~40-100 seconds (20 trials)
Max Score: 200 (10 points × 20 trials)
Cognitive Domain: Executive function, selective attention, cognitive flexibility

Data Tracked:
  - Score (0-200)
  - Accuracy percentage
  - Correct/total responses
  - Test type identifier
  - Optional: Reaction time
```

---

## UI/UX Changes

### BEFORE: Single Game Interface

```
Screen: game.html

Layout:
┌─────────────────────────────────────────┐
│         Apakah kombinasi ini benar?     │
│                                         │
│                 😀                      │
│                                         │
│               Wajah                     │
│                                         │
│         [Benar ✅] [Salah ✖️]          │
│                                         │
│           ✅ Benar! / ❌ Salah!        │
│                                         │
│         [Lihat Skor] (at end)          │
└─────────────────────────────────────────┘

Navigation: Dashboard → Game → Results
```

### AFTER: Test Selection + Dynamic Dual Interface

```
Screen 1: select_test.html

Layout:
┌────────────────────────────────────────┐
│      Pilih Test Kognitif               │
├────────────────────────────────────────┤
│                                        │
│  ┌──────────────────────────────────┐  │
│  │ 🎯 Go/No-Go Test                 │  │
│  │ Measures: Response inhibition     │  │
│  │ Description: Click for GO shapes  │  │
│  │ Duration: ~30 seconds             │  │
│  │        [Mulai Test →]             │  │
│  └──────────────────────────────────┘  │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │ 🎨 Color Stroop Test             │  │
│  │ Measures: Executive function      │  │
│  │ Description: Match text color     │  │
│  │ Duration: ~60 seconds             │  │
│  │        [Mulai Test →]             │  │
│  └──────────────────────────────────┘  │
│                                        │
│  [← Kembali ke Dashboard]              │
└────────────────────────────────────────┘


Screen 2: game.html (Go/No-Go Mode)

Layout:
┌─────────────────────────────────────────┐
│    🎯 Go/No-Go Test                     │
│                                         │
│  Progress: [████░░░░░] 40%              │
│                                         │
│  Tekan jika adalah GO ✓ | Jangan Tekan  │
│  jika NO-GO ✗                           │
│                                         │
│                  ⭕                     │
│                                         │
│           [TEKAN GO ✓]                  │
│                                         │
│            ✅ Benar!                    │
│                                         │
└─────────────────────────────────────────┘


Screen 3: game.html (Stroop Mode)

Layout:
┌─────────────────────────────────────────┐
│    🎨 Color Stroop Test                 │
│                                         │
│  Progress: [███░░░░░░] 30%              │
│                                         │
│  Pilih warna TULISAN, bukan arti kata!  │
│                                         │
│     MERAH (displayed in BLUE)           │
│                                         │
│   [🔴]  [🔵]  [🟢]  [🟡]  [🟣]         │
│  MERAH BIRU HIJAU KUNING UNGU          │
│                                         │
│            ✅ Benar!                    │
│                                         │
└─────────────────────────────────────────┘


Screen 4: game.html (Results)

Layout:
┌─────────────────────────────────────────┐
│          🎉 Test Selesai!               │
│                                         │
│              150                        │
│                                         │
│   ✓ 15/20 | Akurasi: 75%                │
│                                         │
│    [Lihat Semua Skor →]                 │
│    [Kembali ke Dashboard]               │
│                                         │
└─────────────────────────────────────────┘

Navigation: Dashboard → Select Test → Test → Results
```

---

## Database Schema Changes

### BEFORE: Score Table

```sql
CREATE TABLE score (
    id INTEGER PRIMARY KEY,
    score INTEGER NOT NULL,
    timestamp DATETIME,
    patient_id INTEGER FOREIGN KEY
);

Columns: 3
Data tracked: Score only
```

### AFTER: Score Table

```sql
CREATE TABLE score (
    id INTEGER PRIMARY KEY,
    score INTEGER NOT NULL,           -- Points earned (0-200)
    test_type VARCHAR(50),            -- 'go_no_go' or 'stroop'
    reaction_time FLOAT,              -- Optional: milliseconds
    accuracy FLOAT,                   -- Percentage (0-100)
    timestamp DATETIME,               -- When test was taken
    patient_id INTEGER FOREIGN KEY    -- Which patient
);

Columns: 7 (4 new fields)
Data tracked: Score, Test type, Accuracy, Reaction time, Timestamp
```

### Migration Notes

```
Existing Score Records:
┌────────┬─────────┬────────────┬─────────────┬────────┐
│ id     │ score   │ test_type  │ accuracy    │ ...    │
├────────┼─────────┼────────────┼─────────────┼────────┤
│ 1      │ 80      │ NULL       │ NULL        │ ...    │ ← Old records
│ 2      │ 90      │ NULL       │ NULL        │ ...    │ ← No test type
│ 3      │ 150     │ 'stroop'   │ 75.0        │ ...    │ ← New format
│ 4      │ 180     │ 'go_no_go' │ 90.0        │ ...    │ ← New format
└────────┴─────────┴────────────┴─────────────┴────────┘

No data loss - all old records preserved
New fields are NULL for old records
```

---

## Route Changes

### BEFORE

```
POST /login → /dashboard
POST /register → /login
GET /dashboard → Patient list
GET /reference → Reference page (used in test)
GET /game → Start test immediately
GET /next → Get next emoji pair
POST /submit → Process answer
GET /logout → Logout
```

### AFTER

```
POST /login → /dashboard
POST /register → /login
GET /dashboard → Patient list
GET /select_patient/<id> → /select_test (NEW)
GET /select_test → Test selection page (NEW)
GET /game/<type> → Initialize test (UPDATED)
GET /next → Get next trial (UPDATED - more complex)
POST /submit → Process answer (UPDATED - more complex)
GET /logout → Logout
```

---

## Session Variable Changes

### BEFORE

```python
session = {
    "user_id": int,
    "selected_patient_id": int,
    "reference_shown": bool,
    "emoji_queue": list,           # Array of emoji pairs
    "emoji_index": int,             # Current position
    "score": int,                   # Points
    "current_correct": bool         # Expected answer for current
}
```

### AFTER

```python
session = {
    "user_id": int,
    "selected_patient_id": int,
    "selected_patient_name": str,   # NEW
    "test_type": str,               # NEW: 'go_no_go' or 'stroop'
    "score": int,
    "correct_count": int,           # NEW: Track accuracy
    "total_count": int,             # NEW: Track accuracy
    "trial_index": int,             # NEW: Current trial (0-19)
    "go_no_go_trials": list,        # NEW: OR
    "stroop_trials": list           # NEW: - depending on test type
}
```

---

## Scoring Logic Changes

### BEFORE: Binary Correct/Incorrect

```python
if user_choice == correct_answer:
    session["score"] += 10
    result = "✅ Benar!"
else:
    result = "❌ Salah!"
```

### AFTER: Accuracy Tracking

```python
session["total_count"] += 1

if user_response_correct:
    session["correct_count"] += 1
    session["score"] += 10
    result = "✅ Benar!"
else:
    result = "❌ Salah!"

# On completion:
accuracy = (session["correct_count"] / session["total_count"]) * 100
Score.create(
    score=session["score"],
    test_type=session["test_type"],
    accuracy=accuracy,
    patient_id=session["selected_patient_id"]
)
```

---

## Performance Metrics

### BEFORE

```
Data per test:
- Score value only
- No performance metrics
- No test differentiation

Scoreboard:
┌─────────────┬─────────┐
│ Patient     │ Score   │
├─────────────┼─────────┤
│ John (80)   │ 80      │
│ Jane (90)   │ 90      │
│ Bob (70)    │ 70      │
└─────────────┴─────────┘
Cannot determine performance quality
```

### AFTER

```
Data per test:
- Score value
- Test type
- Accuracy percentage
- Timestamp
- Optional reaction time

Scoreboard:
┌──────────┬────────────┬────────┬──────────┐
│ Patient  │ Test       │ Score  │ Accuracy │
├──────────┼────────────┼────────┼──────────┤
│ John     │ Go/No-Go   │ 180    │ 90%      │
│ John     │ Stroop     │ 140    │ 70%      │
│ Jane     │ Go/No-Go   │ 200    │ 100%     │
│ Jane     │ Stroop     │ 160    │ 80%      │
│ Bob      │ Go/No-Go   │ 150    │ 75%      │
│ Bob      │ Stroop     │ 120    │ 60%      │
└──────────┴────────────┴────────┴──────────┘
Can now analyze test-specific performance
Can track improvement over time
Can compare cognitive domains
```

---

## Summary: What Improved?

| Aspect | Before | After |
|--------|--------|-------|
| **Tests Available** | 1 (Memory) | 2 (Response Control + Executive Function) |
| **Test Types** | Recognition memory | Response inhibition + Selective attention |
| **Trials per Test** | 10 | 20 |
| **Max Score** | 100 | 200 |
| **Data Tracked** | Score | Score, Type, Accuracy, Timestamp, Reaction time |
| **Performance Visibility** | Basic score | Detailed metrics with accuracy % |
| **Test Duration** | 1-2 min | 20-100 seconds (varies by test) |
| **Difficulty** | Easy-Medium | Medium-Hard (Stroop especially challenging) |
| **Cognitive Domains** | 1 | 2+ |
| **UI/UX** | Single interface | Adaptive dual interface + selection |
| **Documentation** | Minimal | Comprehensive (4 docs) |

---

## Impact on Clinicians/Testers

### BEFORE
- Limited assessment capability
- Only memory testing
- Minimal data for analysis
- Single generic score

### AFTER
- Multi-domain cognitive assessment
- Can identify specific cognitive deficits
- Rich data for trend analysis
- Separate scores for different domains
- Better clinical insights
- More professional testing experience

