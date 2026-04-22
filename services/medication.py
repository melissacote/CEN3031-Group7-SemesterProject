# Medication database operations
import sqlite3
from datetime import datetime, date
from database.db_connection import get_connection
from services.user import get_user_id


def _is_due_today(start_date_str: str | None, end_date_str: str | None,
                  interval: int | None, today: date) -> bool:
    """Return True if a medication is scheduled to be taken on `today`."""
    # Legacy rows without a start date are always shown
    if not start_date_str:
        return True

    start = datetime.strptime(start_date_str, "%Y-%m-%d").date()

    if today < start:
        return False  # course hasn't started yet

    if end_date_str:
        end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        if today > end:
            return False  # course is finished

    effective_interval = interval if interval and interval > 1 else 1
    days_elapsed = (today - start).days
    return days_elapsed % effective_interval == 0


def add_medication(user_id, medication_name, dosage, route, frequency, scheduled_time,
                   prescriber="", special_instructions="",
                   start_date=None, end_date=None, frequency_interval=1, doses_per_day=1,
                   conn: sqlite3.Connection | None = None):
    if conn is None:
        conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO medications
                (user_id, medication_name, dosage, route, frequency, scheduled_time,
                 prescriber, special_instructions,
                 start_date, end_date, frequency_interval, doses_per_day)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, medication_name, dosage, route, frequency, scheduled_time,
              prescriber, special_instructions,
              start_date, end_date, frequency_interval, doses_per_day))
        conn.commit()


# ADDED: Issue #31 - Check for duplicate medication names
def check_duplicate_medication(user_id, medication_name, conn: sqlite3.Connection | None = None) -> bool:
    """Query database for matching active medication name to check for duplicates."""
    if conn is None:
        conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM medications
            WHERE user_id = ? AND LOWER(medication_name) = LOWER(?) AND is_active = 1
        ''', (user_id, medication_name.strip()))
        count = cursor.fetchone()[0]
        return count > 0


# ADDED: Helper to mark a medication inactive instead of permanently deleting
def deactivate_medication(medication_id, conn: sqlite3.Connection | None = None):
    """Mark a medication as inactive instead of deleting it."""
    if conn is None:
        conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE medications SET is_active = 0 WHERE medication_id = ?
        ''', (medication_id,))
        conn.commit()


def get_todays_medications_sorted(user_id, conn: sqlite3.Connection | None = None):
    """
    Return active medications that are due today, sorted by scheduled_time.

    Each row is a tuple:
        (medication_id, medication_name, dosage, scheduled_time,
         doses_per_day, times_taken_today, special_instructions)

    Only medications whose frequency schedule lands on today's date are included.
    """
    today = datetime.now().date()
    date_str = today.strftime("%Y-%m-%d")

    if conn is None:
        conn = get_connection()
    with conn:
        cursor = conn.cursor()

        # Fetch all active medications with a count of how many doses have been logged today
        cursor.execute('''
            SELECT m.medication_id, m.medication_name, m.dosage, m.scheduled_time,
                   m.doses_per_day, COUNT(a.log_id) AS times_taken_today,
                   m.special_instructions,
                   m.start_date, m.end_date, m.frequency_interval
            FROM medications m
            LEFT JOIN administration_log a
                ON m.medication_id = a.medication_id
                AND a.user_id = m.user_id
                AND a.date_taken = ?
                AND a.status = 1
            WHERE m.user_id = ? AND m.is_active = 1
            GROUP BY m.medication_id
            ORDER BY m.scheduled_time ASC
        ''', (date_str, user_id))

        rows = cursor.fetchall()

    # Filter in Python: only keep medications whose schedule falls on today
    result = []
    for row in rows:
        (med_id, name, dosage, scheduled_time, doses_per_day,
         times_taken, special_instructions, start_date, end_date, interval) = row

        if _is_due_today(start_date, end_date, interval, today):
            result.append((med_id, name, dosage, scheduled_time,
                           doses_per_day or 1, times_taken, special_instructions))

    return result


def get_user_medications(username: str, conn: sqlite3.Connection | None = None) -> list[dict]:
    """Return list of medication dictionaries for the user."""
    if conn is None:
        owned_conn = True
        conn = get_connection()
    else:
        owned_conn = False
    user_id = get_user_id(username, conn)
    if not user_id:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT medication_name, dosage, frequency, scheduled_time
            FROM medications
            WHERE user_id = ? AND is_active = 1
            ORDER BY scheduled_time DESC
        """, (user_id,))
        rows = cursor.fetchall()
        return [dict(zip(["name", "dosage", "frequency", "scheduled_time"], row)) for row in rows]
    except Exception:
        return []
    finally:
        if owned_conn:
            conn.close()


def get_medications_for_management(user_id, conn: sqlite3.Connection | None = None):
    """Return active medications with all fields needed by the management screen."""
    if conn is None:
        conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT medication_id, medication_name, dosage, route, frequency, scheduled_time,
                   prescriber, special_instructions,
                   start_date, end_date, frequency_interval, doses_per_day
            FROM medications
            WHERE user_id = ? AND is_active = 1
            ORDER BY LOWER(medication_name) ASC
        ''', (user_id,))
        rows = cursor.fetchall()
        keys = ["medication_id", "name", "dosage", "route", "frequency", "scheduled_time",
                "prescriber", "special_instructions",
                "start_date", "end_date", "frequency_interval", "doses_per_day"]
        return [dict(zip(keys, row)) for row in rows]

def update_medication(medication_id, medication_name, dosage, route, frequency, scheduled_time, special_instructions,
                      start_date=None, end_date=None, frequency_interval=1, doses_per_day=1,
                      conn: sqlite3.Connection | None = None):
    """Update an existing medication record."""
    if conn is None:
        conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE medications
            SET medication_name=?, dosage=?, route=?, frequency=?, scheduled_time=?, special_instructions=?,
                start_date=?, end_date=?, frequency_interval=?, doses_per_day=?
            WHERE medication_id=?
        ''', (medication_name, dosage, route, frequency, scheduled_time, special_instructions,
              start_date, end_date, frequency_interval, doses_per_day,
              medication_id))
        conn.commit()
