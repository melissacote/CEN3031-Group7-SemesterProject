# Medication database operations
from database.db_connection import get_connection

# ADDED BY NC: Implement adding medications in database
def add_medication(user_id, medication_name, dosage, route, frequency, scheduled_time, prescriber="", special_instructions=""):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO medications (user_id, medication_name, dosage, route, frequency, scheduled_time, prescriber, special_instructions) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, medication_name, dosage, route, frequency, scheduled_time, prescriber, special_instructions))
        conn.commit()

# ADDED BY NC: Implement query for medications to be administered on current date & chronological sorting
def get_todays_medications_sorted(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT medication_id, medication_name, dosage, scheduled_time 
            FROM medications 
            WHERE user_id=? 
            ORDER BY scheduled_time ASC
        ''', (user_id,))
        return cursor.fetchall()