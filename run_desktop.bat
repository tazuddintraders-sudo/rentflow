@echo off
REM ============================================================
REM  RentFlow desktop app - run from source (native window)
REM ============================================================
setlocal
if not exist .venv (
  echo First run: setting up environment...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  python manage.py migrate
  python manage.py seed_demo
) else (
  call .venv\Scripts\activate.bat
)
echo.
echo Starting RentFlow desktop app...
echo (If no window appears, open http://127.0.0.1:8000/ in your browser)
echo Login: admin / admin1234
echo.
python run_desktop.py
pause
