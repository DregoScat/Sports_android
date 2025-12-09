# Original Files

This folder contains the original source files before project reorganization.

## Contents

| File | Description |
|------|-------------|
| `app.py` | Original Flask application (monolithic) |
| `squats.py` | Original squat analyzer module |
| `jump.py` | Original jump analyzer module |
| `requirements.txt` | Original Python dependencies |
| `test_frame_cam1.jpg` | Test image for debugging |

## Note

These files are kept for reference purposes. The active codebase has been reorganized into the `server/` folder with a modular architecture.

### Migration Mapping

| Original | New Location |
|----------|--------------|
| `app.py` | `server/src/api/routes.py` + `server/run.py` |
| `squats.py` | `server/src/analyzers/squat_analyzer.py` |
| `jump.py` | `server/src/analyzers/jump_analyzer.py` |
| `requirements.txt` | `server/requirements.txt` |

## Safe to Delete

Once you've verified the new structure works correctly, this folder can be safely deleted.
