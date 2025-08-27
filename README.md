# Home Budget (Python + Tkinter)

Desktop app for managing personal finances:
- User login (SHA-256 password hashes)
- Encrypted transactions (Fernet, binary file)
- Recurring transactions (auto-append overdue)
- Budget planning per category (limits)
- Charts: pie, bar, line (matplotlib)
- Calendar (tkcalendar)
- Theme switching (ttk themes)

## Requirements
- Python 3.10+
- Linux / Windows / macOS
- **Ubuntu**: `sudo apt install python3-tk` (Tkinter runtime)

## Setup
```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python budget_app.py

