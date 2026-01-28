# Quick Start Guide - Cognitive Stimulation App

## How to Use the App

### 1. User Registration & Login
- Go to the app and click **Register**
- Enter a username and password
- Login with your credentials

### 2. Patient Management (Dashboard)
- **Add Patient**: Enter name, age, and notes, then click "Add Patient"
- **View Patient**: All patients are listed in the table
- **Edit Patient**: Click "Edit" button to modify patient information
- **Delete Patient**: Click "Delete" button to remove patient (confirmation required)

### 3. Running a Cognitive Test

#### Step 1: Select Patient
- From the dashboard, click the **"Select"** button next to a patient
- This patient's data will be used to save test scores

#### Step 2: Choose Test Type
You'll see two test options:

##### 🎯 **Go/No-Go Test**
- **What it measures**: Response inhibition and impulse control
- **How to play**:
  - You'll see shapes appear on screen
  - For GO shapes (⭕ circle, 🔷 diamond, 🔶 orange): Click the **"TEKAN GO"** button
  - For NO-GO shapes (🔺 triangle, ✋ hand): **Don't click** - wait for next shape
  - Respond as quickly and accurately as possible
- **Duration**: 20 trials (approximately 1-2 minutes)
- **Scoring**: 10 points per correct response

##### 🎨 **Color Stroop Test**
- **What it measures**: Executive function and attention control
- **How to play**:
  - You'll see a color word displayed in a DIFFERENT color
  - Example: The word "MERAH" (red) appears in BLUE color
  - **Click the button that matches the TEXT COLOR, NOT the word meaning**
  - In the example above, you would click the BLUE button
- **Duration**: 20 trials (approximately 2-3 minutes)
- **Scoring**: 10 points per correct response

#### Step 3: Complete Test
- The progress bar at the top shows your progress
- After each response, you'll see feedback: ✅ Correct or ❌ Incorrect
- After all 20 trials complete, you'll see:
  - Final Score
  - Accuracy Percentage
  - Number of Correct Answers

#### Step 4: View Results
- Click **"Lihat Semua Skor"** (View All Scores) to see test history
- Click **"Kembali ke Dashboard"** to return and select another patient

### 4. Viewing Score History
- From dashboard: Click **"View Score"** next to a patient to see their scores only
- Or click the **Scores** menu to see all your patients' scores
- Scores show:
  - Patient name
  - Test type (Go/No-Go or Stroop)
  - Score achieved
  - Accuracy percentage
  - Date and time

---

## Test Tips

### For Go/No-Go Test:
- React quickly to GO shapes
- Remember: Only click for GO shapes (⭕🔷🔶)
- Don't click for NO-GO shapes (🔺✋)
- Focus and don't let yourself get distracted

### For Stroop Test:
- **Important**: Ignore the WORD MEANING, focus on the TEXT COLOR
- This test is challenging because your brain naturally wants to read the word
- Click the color button as quickly as possible
- The colors are: Red, Blue, Green, Yellow, Purple
- Indonesian names on buttons: MERAH, BIRU, HIJAU, KUNING, UNGU

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Patient not found" error | Make sure to select a patient from the dashboard first |
| Test page blank | Refresh the page or restart the test |
| Can't submit responses | Make sure you wait for the interface to fully load |
| Scores not saved | Check that a patient was selected before starting the test |

---

## Keyboard Shortcuts (Recommended)
- **Go/No-Go**: Use mouse or touchpad to click the button quickly
- **Stroop**: Use mouse to click color buttons as fast as possible

---

## Performance Notes

- Tests are timed - faster accurate responses = better performance
- Accuracy is calculated as: (Correct Answers / Total Trials) × 100
- Each patient's scores are saved separately
- Historical data is preserved for trend analysis

---

## Admin Notes
- Test data includes: score, test type, accuracy %, and timestamp
- Database automatically creates backup entries for each test
- All patient data is linked to user accounts
- Test types can be distinguished in score history
