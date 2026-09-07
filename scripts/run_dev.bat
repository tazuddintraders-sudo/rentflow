@echo off
REM Run RentFlow from source in your default browser (no packaging).
setlocal
if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
  python manage.py migrate
  python manage.py seed_demo
) else (
  call .venv\Scripts\activate.bat
)
echo.
echo Starting RentFlow at http://127.0.0.1:8000/
echo Login: admin / admin1234   (Ctrl+C to stop)
echo.
start "" http://127.0.0.1:8000/
python manage.py runserver 127.0.0.1:8000
pause
