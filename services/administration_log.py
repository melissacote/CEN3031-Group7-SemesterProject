# Administration log database operations
import sqlite3
from datetime import datetime

from database.db_connection import get_connection

# ADDED BY NC: Log when a medication is taken
def log_medication_taken(user_id, med_id, conn: sqlite3.Connection | None = None):
    # Get current date and time
    date_taken = datetime.now().strftime("%Y-%m-%d")
    time_taken = datetime.now().strftime("%H:%M:%S")

    if conn is None:
        conn = get_connection()
    with conn:
        cursor = conn.cursor()
        # Get the current med fields so we can preserve them on the administration log table for reporting
        medication_name, dosage, route, frequency, special_instructions = cursor.execute('''
            SELECT medication_name, dosage, route, frequency, special_instructions
            FROM medications
            WHERE medication_id = ?
            ''', (med_id,)).fetchone()

        cursor.execute('''
            INSERT INTO administration_log (user_id, medication_id, medication_name, dosage, route, frequency, special_instructions, date_taken, time_taken, status, notes) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, '')
        ''', (user_id, med_id, medication_name, dosage, route, frequency, special_instructions, date_taken, time_taken))
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
