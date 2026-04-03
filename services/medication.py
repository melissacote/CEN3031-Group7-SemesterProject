# Medication database operations
import sqlite3
from datetime import datetime
from database.db_connection import get_connection, DB_NAME
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

# ADDED BY NC: Implement query for medications to be administered on current date & chronological sorting
def get_todays_medications_sorted(user_id, conn: sqlite3.Connection | None = None):
    if conn is None:
        conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT medication_id, medication_name, dosage, scheduled_time 
            FROM medications 
            WHERE user_id=? 
            ORDER BY scheduled_time ASC
        ''', (user_id,))
        return cursor.fetchall()
    
# ADDED BY NC: Log when a medication is taken
def log_medication_taken(user_id, med_id, conn: sqlite3.Connection | None = None):
    # Get current date and time
    date_taken = datetime.now().strftime("%Y-%m-%d")
    time_taken = datetime.now().strftime("%H:%M:%S")

    if conn is None:
        conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO administration_log (user_id, medication_id, date_taken, time_taken, status, notes) 
            VALUES (?, ?, ?, ?, 1, '')
        ''', (user_id, med_id, date_taken, time_taken))
        conn.commit()

# ADDED BY NC: Undo marking a medication as taken
def undo_medication_taken(user_id, med_id, conn: sqlite3.Connection | None = None):
    date_today = datetime.now().strftime("%Y-%m-%d")

    if conn is None:
        conn = get_connection()
    with conn:
        cursor = conn.cursor()
        
        # Find the single most recent log entry for this medication today
        cursor.execute('''
            SELECT log_id FROM administration_log 
            WHERE user_id=? AND medication_id=? AND date_taken=?
            ORDER BY time_taken DESC LIMIT 1
        ''', (user_id, med_id, date_today))
        
        result = cursor.fetchone()
        if result:
            log_id = result[0]
            # Delete that specific timestamp log
            cursor.execute("DELETE FROM administration_log WHERE log_id=?", (log_id,))
            conn.commit()
            return True # Successfully undone
        return False # Nothing to undo


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
            WHERE user_id = ?
            ORDER BY start_date DESC
        """, (user_id,))
        rows = cursor.fetchall()
        return [dict(zip(["name", "dosage", "frequency", "start_date", "notes"], row)) for row in rows]
    except Exception:
        return []
    finally:
        if owned_conn:
            conn.close()
