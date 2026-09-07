@echo off
REM ============================================================
REM  RentFlow - one-click Windows build script
REM  Run this on a Windows 10/11 machine (PowerShell or CMD).
REM ============================================================
setlocal

echo.
echo === [1/6] Checking Python ==================================
python --version
if errorlevel 1 (
  echo Python is not installed. Install Python 3.11+ from https://www.python.org/downloads/
  echo Make sure "Add python.exe to PATH" is ticked during install.
  pause
  exit /b 1
)

echo.
echo === [2/6] Creating virtual environment ====================
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat

echo.
echo === [3/6] Installing dependencies ==========================
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo === [4/6] Preparing static files ==========================
python manage.py collectstatic --noinput
python manage.py migrate

echo.
echo === [5/6] Building the Windows app with PyInstaller =======
pyinstaller RentFlow.spec --noconfirm --clean

echo.
echo === [6/6] Done =============================================
echo.
echo Your app is in:  dist\RentFlow\RentFlow.exe
echo A "RentFlow_Data" folder will be created next to the .exe on
echo first run - it holds the database, documents and invoices.
echo.
echo Default login:   username admin   password admin1234
echo.
pause
