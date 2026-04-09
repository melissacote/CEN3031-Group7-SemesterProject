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
        # Join the logs with the medications table to get names and dosages
        cursor.execute('''
            SELECT m.medication_name, m.dosage, a.date_taken, a.time_taken
            FROM administration_log a
            JOIN medications m ON a.medication_id = m.medication_id
            WHERE a.user_id = ? AND a.date_taken BETWEEN ? AND ?
            ORDER BY a.date_taken DESC, a.time_taken DESC
        ''', (user_id, start_date, end_date))
        
        return cursor.fetchall(), start_date, end_date