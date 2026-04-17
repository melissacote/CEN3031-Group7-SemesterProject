# Medication database operations
import sqlite3
from datetime import datetime
from database.db_connection import get_connection
from services.user import get_user_id


# ADDED BY NC: Implement adding medications in database
def add_medication(user_id, medication_name, dosage, route, frequency, scheduled_time, prescriber="", special_instructions="", conn: sqlite3.Connection | None = None):
    if conn is None:
        conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO medications (user_id, medication_name, dosage, route, frequency, scheduled_time, prescriber, special_instructions) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, medication_name, dosage, route, frequency, scheduled_time, prescriber, special_instructions))
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

# ADDED BY NC: Implement query for medications to be administered on current date & chronological sorting
def get_todays_medications_sorted(user_id, conn: sqlite3.Connection | None = None):
    date_today = datetime.now().strftime("%Y-%m-%d")

    if conn is None:
        conn = get_connection()
    with conn:
        cursor = conn.cursor()
        
        # LEFT JOIN the administration_log to see if a record exists for TODAY
        cursor.execute('''
            SELECT m.medication_id, m.medication_name, m.dosage, m.scheduled_time,
                   CASE WHEN a.log_id IS NOT NULL THEN 1 ELSE 0 END as is_taken,
                   m.special_instructions,
                   a.time_taken
            FROM medications m
            LEFT JOIN administration_log a 
                ON m.medication_id = a.medication_id 
                AND a.user_id = m.user_id 
                AND a.date_taken = ?
                AND a.status = 1
            WHERE m.user_id = ? AND m.is_active = 1
            ORDER BY m.scheduled_time ASC
        ''', (date_today, user_id))
        
        return cursor.fetchall()

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

# Returns list of medication dictionaries for the user for the management screen.
def get_medications_for_management(user_id, conn: sqlite3.Connection | None = None):
    if conn is None:
        conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT medication_id, medication_name, dosage, route, frequency, scheduled_time, prescriber, special_instructions
            FROM medications
            WHERE user_id = ? AND is_active = 1
            ORDER BY LOWER(medication_name) ASC
        ''', (user_id,))
        rows = cursor.fetchall()
        return [dict(zip(["medication_id", "name", "dosage", "route", "frequency", "scheduled_time", "prescriber", "special_instructions"], row)) for row in rows]

def update_medication(medication_id, medication_name, dosage, route, frequency, scheduled_time, conn: sqlite3.Connection | None = None):
    """
    Update an exisitng medication record.

    NOTE: dosage and route are current DB column names (UI uses strength / directions).
    """
    if conn is None:
        conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE medications
            SET medication_name=?, dosage=?, route=?, frequency=?, scheduled_time=?
            WHERE medication_id=?
        ''', (medication_name, dosage, route, frequency, scheduled_time, medication_id))
        conn.commit()