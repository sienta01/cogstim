# Changelog

All notable changes to the Cognitive Stimulation Application are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.2.0] - 2026-01-29

### Added
- Emoji Matching test (10 trials) integrated into default test sequence
- Practice mode for each test (3 practice trials)
- Ready/confirmation page after practice rounds

### Changed
- Go/No-Go default trials reduced to 10; consecutive identical stimuli limited to 5
- Default test flow changes: Go/No-Go → Stroop → Emoji Matching → Results

### Fixed
- Buttons staying disabled after first response (emoji & stroop fixes)
- Final results display now includes emoji matching scores
- Button re-enable logic and UI sizing issues resolved

### Documentation
- Updated README, USER_GUIDE, and technical documents to reflect new tests and workflow

---

## [2.1.0] - 2026-01-28

### Added
- Version tracking system with VERSION file
- Version information in app.py module docstring
- CHANGELOG.md for version history tracking
- Comprehensive README.md as main entry point
- VERSION constant in Python modules

### Changed
- Updated documentation structure for better organization
- Streamlined documentation index
- Enhanced user guide with clearer instructions

### Fixed
- Improved code documentation and comments
- Better version consistency across files

### Documentation
- 8 comprehensive documentation files for reference
- Complete user guide and technical documentation
- Flow diagrams and implementation summaries

---

## [2.0.0] - 2026-01-15

### Major Changes
**Application Refactored**: Complete rewrite from emoji-matching game to professional cognitive assessment platform

### Added
- **Go/No-Go Test**: Measures response inhibition and impulse control
  - 20 trials, max 200 points
  - GO shapes: ⭕ 🔷 🔶 (respond by clicking)
  - NO-GO shapes: 🔺 ✋ (respond by not clicking)
  - Real-time feedback and progress tracking

- **Color Stroop Test**: Measures executive function and selective attention
  - 20 trials, max 200 points
  - Mismatched color words in different colors
  - Users click correct color button (not word meaning)
  - Real-time feedback and progress tracking

- **Test Selection Interface**: Beautiful UI for selecting between tests
- **Enhanced Score Tracking**: Now tracks test type, accuracy, and reaction time
- **Improved Database Schema**: Updated Score model with new fields
- **Professional UI Design**: Responsive layout across all devices
- **Progress Tracking**: Visual progress bars during tests
- **Feedback System**: Real-time correctness feedback (✅/❌)

### Modified Files
- `app.py` (379 lines) - Complete backend rewrite with new test logic
- `templates/game.html` - Completely redesigned universal test interface
- `templates/scores.html` - Updated with test type and accuracy tracking
- Database schema updated

### New Files
- `templates/select_test.html` - Test selection interface
- 8 comprehensive documentation files

### Documentation
- USER_GUIDE.md - Step-by-step user instructions
- README_CHANGES.md - Quick overview of changes
- TECHNICAL_DOCS.md - Complete technical reference
- REFACTOR_SUMMARY.md - Detailed change documentation
- FLOW_DIAGRAM.md - Visual flowcharts and process diagrams
- BEFORE_AFTER_COMPARISON.md - Comparison of improvements
- DOCUMENTATION_INDEX.md - Navigation guide
- PROJECT_COMPLETION.md - Completion status report

### Test Specifications
- **Test Duration**: 
  - Go/No-Go: 20-40 seconds
  - Stroop: 40-100 seconds
- **Trials per Test**: 20
- **Maximum Score**: 200 per test
- **Scoring Method**: 10 points per correct response

---

## [1.0.0] - 2026-01-01

### Initial Release
- Basic emoji-matching memory game
- Single test type with 10 trials
- Simple score tracking
- User authentication system
- Patient management
- Basic UI and database

---

## Version Compatibility

### Current Version: 2.1.0
- Python 3.7+
- Flask 2.0+
- SQLAlchemy compatible
- Modern browser support

### Upgrade Path
- Version 1.0.0 → 2.0.0: Database migration required (automatic)
- Version 2.0.0 → 2.1.0: No migration required (backward compatible)

---

## Release Notes

### v2.1.0 Release Notes
- Focus on documentation and code organization
- Added version tracking infrastructure
- Improved codebase maintainability
- No breaking changes from v2.0.0

### v2.0.0 Release Notes
- Complete application redesign
- Professional cognitive assessment capabilities
- Multiple test types
- Enhanced data tracking
- **Breaking Change**: Database schema updated (migration auto-runs)

---

## Support

For issues or questions about specific versions, refer to:
- **Technical Details**: [TECHNICAL_DOCS.md](./TECHNICAL_DOCS.md)
- **User Guide**: [USER_GUIDE.md](./USER_GUIDE.md)
- **Implementation Details**: [REFACTOR_SUMMARY.md](./REFACTOR_SUMMARY.md)

---

## Versioning Policy

This project follows Semantic Versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Significant changes, potentially breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, minor improvements

