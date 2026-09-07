# RentFlow — Rental Property Management (Windows Desktop App)

A comprehensive property management system with **automated invoice generation**,
**payment tracking**, **smart due/overdue detection** and **legal document storage**
— packaged as a native **Windows desktop application** (Django + pywebview + PyInstaller).

Design language: restrained European editorial style — deep navy, white, soft gray
and controlled orange accents; Arial typography; thin borders; soft shadows;
subtle glass surfaces; no dark mode; charts hand-built in SVG (works fully offline).

---

## Features

- **Dashboard** — summary cards, payment-status donut, 6-month collections bar
  chart, occupancy gauge, overdue alerts with days-late counters, recent activity,
  upcoming dues and new occupants.
- **Rental overview** — grid/list toggle, filter by building / status / type,
  search, colour-coded payment state (paid / due soon / overdue / vacant).
- **Flat / shop / cottage detail** — occupant, lease, 12-month payment history,
  occupancy timeline, documents, start/end occupancy.
- **Client (occupant) profiles** — personal & emergency info, document library
  (NID, agreement, legal), full payment history, tenancy timeline.
- **Payment portal** — building → flat auto-population, AJAX auto-fetch of
  occupant / rent / contact, smart multi-month due detection, cash / bank / bKash
  details (incl. screenshot upload), auto-check validation, invoice PDF generation
  and optional email, print/download.
- **Payment history** — rich filters (date range, building, status, method, search),
  analytics cards, slide-over detail panel with invoice download, resend,
  status edit and delete.
- **Automated invoices** — `INV-YYYY-MM-XXXX` numbering, branded ReportLab PDFs
  stored in `media/invoices/`, professional HTML email with PDF attachment.
- **Documents** — upload/validate/download NID, agreements and legal scans.
- **Auth** — login, sessions, staff/admin roles, Django admin.

## Quick start (development)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo          # demo buildings, occupants, payments
python manage.py runserver          # http://127.0.0.1:8000/  (admin / admin1234)
```

## Run as a desktop window

```bash
python run_desktop.py               # opens a native window (pywebview)
```

## Build the Windows .exe

See **[WINDOWS_SETUP.md](WINDOWS_SETUP.md)** for the full guide, or just run
`scripts\build_windows.bat` on Windows. Output lands in `dist\RentFlow\RentFlow.exe`.

## Configuration

Company / bank details and the rent due-day live in `config/settings.py → RENTFLOW`.
Email uses environment variables (`RENTFLOW_EMAIL_USER`, `RENTFLOW_EMAIL_PASSWORD`);
without them the app runs with a console email backend so invoices still generate.

## Tests

```bash
python manage.py test apps.payments
```

## Tech stack

Django 5 · SQLite · ReportLab · pywebview (Edge WebView2) · PyInstaller ·
vanilla JS + hand-rolled SVG charts (no external CDN — fully offline).
