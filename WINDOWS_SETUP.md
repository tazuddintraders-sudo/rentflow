# RentFlow — Windows Desktop Installation & Build Guide

RentFlow is a rental property management system (Django) that runs as a **native
Windows desktop application** — not in a web browser. It uses a local SQLite
database, generates PDF invoices with ReportLab, and opens in a native window
powered by the Microsoft Edge WebView2 runtime (already present on Windows 10/11).

---

## What you need to download (one-time setup)

| # | Software | Why | Download |
|---|----------|-----|----------|
| 1 | **Python 3.11 or 3.12** (64-bit) | Runs the whole app | https://www.python.org/downloads/ |
| 2 | (Included) Edge WebView2 Runtime | Native app window — already on Windows 10/11 | https://developer.microsoft.com/microsoft-edge/webview2/ |

> **Important during Python install:** tick **“Add python.exe to PATH”** on the
> first installer screen, then click *Install Now*.

Everything else (Django, ReportLab, pywebview, PyInstaller) installs automatically
from `requirements.txt` — you do not download them manually.

---

## Option A — Run directly (fastest, for development / daily use)

Double-click **`run_desktop.bat`** the first time (it creates the environment and
installs everything), then it launches the native window. Or use PowerShell:

```powershell
# Open PowerShell in the project folder, then:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo          # optional: loads demo buildings & data
python run_desktop.py               # launches the native app window
```

The app opens in its own window. Login with **admin / admin1234** (demo data).

To run in your default browser instead (no native window):

```powershell
python manage.py runserver 127.0.0.1:8000
# then open http://127.0.0.1:8000/
```

---

## Option B — Build a standalone Windows program (.exe)

This produces a **`RentFlow.exe`** you can double-click on any Windows PC (no
Python needed on that machine).

Double-click **`scripts\build_windows.bat`**, or run these steps in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py collectstatic --noinput
pyinstaller RentFlow.spec --noconfirm --clean
```

When it finishes you will find:

```
dist\
 └─ RentFlow\
     ├─ RentFlow.exe          ← double-click to launch
     └─ (...support files...)
```

Copy the entire **`dist\RentFlow`** folder to the target computer. On first run
it creates a **`RentFlow_Data`** folder next to the `.exe` containing:

- `rentflow.db` — your database (back this up)
- `media\invoices\` — generated invoice PDFs
- `media\documents\` — uploaded NID / agreements / legal scans
- `media\profiles\`, `media\buildings\` — photos

> To create a single distributable installer, wrap `dist\RentFlow` with
> **Inno Setup** (free): https://jrsoftware.org/isdl.php

---

## Enabling real email (Gmail SMTP) for invoice sending

By default the app runs with no email configured — invoices are generated, saved
and can be downloaded/printed, and emails are written to the console/log. To
actually email invoices from Gmail:

1. Enable **2-Step Verification** on the Google account.
2. Create an **App Password**: Google Account → Security → App passwords.
3. Set these environment variables before launching (PowerShell):

```powershell
$env:RENTFLOW_EMAIL_USER = "youraddress@gmail.com"
$env:RENTFLOW_EMAIL_PASSWORD = "xxxxxxxxxxxxxxxx"   # the 16-char app password
python run_desktop.py
```

(Or set them permanently via *System Properties → Environment Variables*.)

---

## Backups

Copy the **`RentFlow_Data`** folder (next to the exe) or the project’s
`rentflow.db` + `media\` folder. That is your entire business data.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `python` not recognised | Re-run Python installer with “Add to PATH” ticked |
| Window never opens | Ensure WebView2 runtime is installed (link above); the app still works at `http://127.0.0.1:8000/` via `runserver` |
| PowerShell blocks scripts | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Port already in use | The launcher automatically picks the next free port |
| Forgot admin password | `python manage.py createsuperuser` to make a new admin |
| Want fresh demo data | `python manage.py seed_demo --flush` |

---

## Project layout

```
config/            Django settings, URLs (data dir, email, company info)
apps/
  accounts/        login, users, roles
  properties/      buildings, levels, flats, occupants, occupancies, documents
  payments/        payments, invoices (PDF), email, smart due-month logic
  dashboard/       overview, stats, charts data
templates/         all HTML (base + per-app pages)
static/            CSS design system, vanilla JS, images, vendor assets
run_desktop.py     native-window launcher (pywebview)
RentFlow.spec      PyInstaller packaging recipe
scripts/           Windows .bat helpers (run + build)
```
