# ACSP - Ai Crane Scheduler Program

A Python-based maintenance scheduling application for crane equipment.

## Features
- Dashboard with equipment status overview
- Sidebar with quick stats (Total, Overdue, Warning)
- Calendar view for maintenance history
- Add/Edit/Delete maintenance records from calendar
- Filter equipment by status

## Requirements
- Python 3.8+
- tkinter (included with Python)

## Run
```bash
python run.py
```

## Project Structure
```
ACSP/
  main.py           # Entry point (via module)
  database.py       # SQLite database handling
  ui/
    app.py          # Main application window
    calendar.py     # Calendar view components
    styles.py       # UI styling
  tools/
    import_legacy.py    # Import from legacy pms.db
    sync_equipment.py   # Sync equipment dates
run.py              # Simple entry point
```
