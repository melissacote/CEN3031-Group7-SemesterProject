# MedRec

A desktop medication management application built with PyQt6. MedRec allows patients to track daily medication adherence, scan prescription bottle labels with a webcam using optical character recognition, and generate professional PDF reports for their healthcare providers.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Running Tests](#running-tests)
- [CI/CD](#cicd)
- [Dependencies](#dependencies)

---

## Features

| Feature | Description |
|---|---|
| **Secure Authentication** | User registration and login with Argon2id password hashing; Enter key submits the login form |
| **Medication Management** | Add, edit, and soft-delete medications with name, strength, directions, notes, and timing; duplicate detection warns before saving |
| **Custom Frequency & Duration** | Set any schedule — daily, every N days, every N weeks, or multiple doses per day — with an optional start and end date per medication course |
| **OCR Label Scanner** | Webcam-based prescription label scanning powered by PaddleOCR with live focus detection and automatic form population |
| **Smart Daily Dosage Tracker** | Displays only the medications due on the current date based on each medication's interval and course window; tracks individual dose counts for multi-dose schedules |
| **PDF Reports** | Generate professional medication adherence reports over custom date ranges |
| **History Log** | Browse past administration records filtered by date range |
| **System Tray** | Closing the window minimizes to the Windows system tray; the application keeps running in the background and can be restored by clicking the tray icon |
| **Logout** | The toolbar logout button is the only way to fully exit the application |
| **Accessibility** | One-click large print mode scales all UI text to 18pt |
| **Camera Settings** | Configure webcam resolution, frame rate, and autofocus preference |

---

## Architecture

MedRec follows a four-layer architecture that runs top-down in one direction: Presentation -> Application -> Business Logic -> Data Access.

```
┌─────────────────────────────────────┐
│         Presentation Layer          │  User Interface including PyQt6 windows and dialogs
├─────────────────────────────────────┤
│         Application Layer           │  Application services such as OCR engine, image processing, PDF generation, and password hashing
├─────────────────────────────────────┤
│        Business Logic Layer         │  Functions for services such as medication list, administration logging, and user information
├─────────────────────────────────────┤
│         Data Access Layer           │  Database communication and table creation (SQLite via db_connection.py)
└─────────────────────────────────────┘
```

**Key design rules:**
- UI files do not contain SQL queries — all data access goes through `services/`
- Services receive an optional `conn` parameter to support both production and test (in-memory) databases
- Passwords are never stored in plain text; Argon2id hashes are stored and verified via `utils/password.py`

---

## Project Structure

```
MedRec/
├── main.py                        # Entry point — DB init, FDA seed check, app launch
├── config.json                    # Webcam preferences (auto-generated on first settings save)
├── requirements.txt               # Python dependencies
├── test_logic.py                  # Manual logic check script for user setup and medication sorting/tracker behavior
├── verify_db.py                   # Manual logic check script to check administration_log rows
│
├── database/
│   └── db_connection.py           # SQLite connection, table creation
│
├── services/
│   ├── user.py                    # Registration, login, profile retrieval
│   ├── medication.py              # Medication CRUD and sorted queries
│   ├── administration_log.py      # Log and undo medication intake events
│   ├── ocr_engine.py              # PaddleOCR text extraction and label parsing
│   └── reports.py                 # Administration history aggregation
│
├── ui/
│   ├── login_window.py            # Login and registration dialogs
│   ├── main_window.py             # Dashboard, toolbar, system tray
│   ├── manage_medication.py       # Add / edit medications screen
│   ├── tracking_screen.py         # Daily dosage tracker
│   ├── scanner_window.py          # Webcam OCR scanner dialog
│   ├── dialog_windows.py          # Report, history, settings, export dialogs
│   └── date_panel.py              # Reusable date range picker component
│
├── utils/
│   ├── camera.py                  # Webcam init, config persistence, frame preprocessing
│   ├── password.py                # Argon2id hashing and verification
│   └── pdf_generator.py           # Jinja2 + xhtml2pdf report rendering
│
├── scripts/
│   └── seed_fda_data.py           # One-time seed of 100k+ FDA drug records
│
├── templates/
│   └── report_template.html       # Jinja2 HTML template for PDF reports
│
├── data/
│   └── product.txt                # FDA medication database (tab-delimited)
│
├── tests/
│   ├── conftest.py                # pytest fixtures (in-memory SQLite test DB)
│   ├── test_user.py               # User service tests
│   ├── test_medications.py        # Medication service tests
│   ├── test_administration_log.py # Administration log service tests
│   └── test_camera.py             # Camera utility tests
│
└── assets/                        # Application icons and images
```

---

## Database Schema

MedRec uses a local SQLite database (`medrec.db`) created automatically on first launch.

### `users`
| Column | Type | Notes |
|---|---|---|
| `user_id` | INTEGER PK | Auto-increment |
| `username` | TEXT UNIQUE | Required |
| `password` | TEXT | Argon2id hash |
| `first_name` | TEXT | |
| `last_name` | TEXT | |
| `date_of_birth` | TEXT | YYYY-MM-DD |
| `created_at` | TIMESTAMP | Default: current time |

### `medications`
| Column | Type | Notes |
|---|---|---|
| `medication_id` | INTEGER PK | ID assigned on insert |
| `user_id` | INTEGER FK | References `users.user_id` |
| `medication_name` | TEXT | Required |
| `dosage` | TEXT | e.g. `50mg` (displayed as "Strength" in UI) |
| `route` | TEXT | e.g. `Oral` (displayed as "Directions" in UI) |
| `frequency` | TEXT | Human-readable label e.g. `Twice every 5 days` (auto-generated from interval + doses) |
| `scheduled_time` | TEXT | Comma-separated timing buckets: `Morning,Evening` |
| `prescriber` | TEXT | Optional |
| `special_instructions` | TEXT | Optional (displayed as "Notes" in UI) |
| `is_active` | INTEGER | Soft-delete flag (`1` = active, `0` = inactive) |
| `start_date` | TEXT | YYYY-MM-DD; first day of the medication course |
| `end_date` | TEXT | YYYY-MM-DD; last day of the course, or `NULL` for ongoing |
| `frequency_interval` | INTEGER | Days between dose days (e.g. `1` = daily, `5` = every 5 days, `7` = weekly) |
| `doses_per_day` | INTEGER | How many times to take the medication on each dose day (e.g. `2` = twice daily) |

### `administration_log`
| Column | Type | Notes |
|---|---|---|
| `log_id` | INTEGER PK | ID assigned on insert |
| `user_id` | INTEGER FK | References `users.user_id` |
| `medication_id` | INTEGER FK | References `medications.medication_id` |
| `medication_name` | TEXT | Snapshot of the name at log time (preserves history if medication is later edited) |
| `dosage` | TEXT | Snapshot of dosage at log time |
| `route` | TEXT | Snapshot of route at log time |
| `frequency` | TEXT | Snapshot of frequency label at log time |
| `special_instructions` | TEXT | Snapshot of notes at log time |
| `date_taken` | TEXT | YYYY-MM-DD |
| `time_taken` | TEXT | HH:MM:SS |
| `status` | INTEGER | `1` = taken |
| `notes` | TEXT | Optional patient note added at log time |

### `fda_medications`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `ndc` | TEXT | National Drug Code (indexed) |
| `brand_name` | TEXT | |
| `generic_name` | TEXT | |

> The `fda_medications` table is seeded from `data/product.txt` on first launch and is used by the OCR engine for fuzzy drug name matching.

---

## Prerequisites

- **Python 3.12**
- **Windows 10 / 11** (system tray and webcam integration are Windows-targeted; the core app runs cross-platform)
- A webcam is optional — all features except OCR scanning work without one

---

## Installation

**1. Clone the repository**

```bash
git clone <repository-url>
cd MedRec
```

**2. Create and activate a virtual environment**

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

> On first install, PaddleOCR will download its language models (~100 MB) the first time the OCR scanner is opened.

**4. Install system libraries required for PDF generation** (if building on Linux/CI)

```bash
sudo apt-get install -y libcairo2-dev pkg-config python3-dev
```

---

## Configuration

Webcam settings are stored in `config.json` at the project root. This file is created automatically when you first apply settings from the Settings window. You can also create it manually:

```json
{
  "preferred_camera_index": 0,
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "autofocus": false
}
```

| Field | Description |
|---|---|
| `preferred_camera_index` | Index of the preferred webcam (0 = first detected) |
| `width` / `height` | Capture resolution |
| `fps` | Target frame rate (`30` or `60`) |
| `autofocus` | `true` enables hardware autofocus; `false` locks focus (recommended for scanning) |

---

## Running the Application

```bash
python main.py
```

On startup, MedRec will:

1. Create database tables if they do not exist
2. Check whether the FDA drug database has been seeded; if not, it seeds it automatically from `data/product.txt`
3. Launch the login window

---

## Running Tests

Tests use pytest with an in-memory SQLite database, so no test data is written to `medrec.db`.

```bash
pytest tests/ -v
```

The test suite covers:

| Test file | Coverage |
|---|---|
| `test_user.py` | Registration, login, user ID lookup |
| `test_medications.py` | Add, update, query, sort medications |
| `test_administration_log.py` | Log taken, undo taken |
| `test_camera.py` | Camera enumeration, config persistence, frame capture |

---

## CI/CD

MedRec uses **CircleCI** for continuous integration. On every push, the pipeline:

1. Spins up a `cimg/python:3.12` Docker container
2. Installs system dependencies for PDF generation (`libcairo2-dev`)
3. Installs Python dependencies via `pip install -r requirements.txt`
4. Runs the full test suite with `pytest tests/ -v`

Pipeline configuration: `.circleci/config.yml`

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `PyQt6` | 6.10.2 | Desktop UI framework |
| `paddleocr` | 2.7.3 | OCR engine for label scanning |
| `paddlepaddle` | 2.6.2 | PaddleOCR backend |
| `opencv-python-headless` | 4.9.0.80 | Webcam capture and image preprocessing |
| `thefuzz` | 0.22.1 | Fuzzy string matching for drug name lookup |
| `python-Levenshtein` | 0.25.1 | Edit distance acceleration for thefuzz |
| `argon2-cffi` | latest | Argon2id password hashing |
| `xhtml2pdf` | latest | HTML-to-PDF report rendering |
| `jinja2` | latest | PDF report templating |
| `pandas` | latest | CSV data export |
| `numpy` | 1.26.4 | Numerical operations (PaddleOCR dependency) |
| `pytest` | latest | Test framework |
