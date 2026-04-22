# services/reports.py
from datetime import datetime, timedelta

def get_report_date_range(start_date=None, end_date=None):
    """Calculates the default 30-day window if no dates are provided."""
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        # Default to exactly 30 days ago
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    return start_date, end_date

def get_medication_history(user_id, start_date=None, end_date=None, conn=None):
    """Fetches medication logs between two specific dates."""
    start_date, end_date = get_report_date_range(start_date, end_date)
    
    if conn is None:
        from database.db_connection import get_connection
        conn = get_connection()
        
    with conn:
        cursor = conn.cursor()
        # Read admin log so report reflects med info taken at time of each dose
        cursor.execute('''
            SELECT medication_name, dosage, date_taken, time_taken, status, special_instructions
            FROM administration_log
            WHERE user_id = ? AND date_taken BETWEEN ? AND ?
            ORDER BY date_taken DESC, time_taken DESC
        ''', (user_id, start_date, end_date))
        
        # Package rows into dicts for templating
        keys = ["medication_name", "dosage", "date_taken", "time_taken", "status", "notes"]
        log_data = [dict(zip(keys, row)) for row in cursor.fetchall()]
        
        return log_data, start_date, end_date

def get_patient_dob(user_id, conn=None):
    """Fetch the patient's date of birth for report header."""
    if conn is None:
        from database.db_connection import get_connection
        conn = get_connection()

    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT date_of_birth FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()[0]