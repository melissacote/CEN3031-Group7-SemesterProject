from database.db_connection import get_connection

print("Checking the Administration Log Table...\n")

with get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM administration_log")
    logs = cursor.fetchall()
    
    if not logs:
        print("The table is empty. No medications have been taken yet.")
    else:
        for log in logs:
            log_id, user_id, med_id, date, time, status, notes = log
            print(f"Log ID: {log_id} | User: {user_id} | Med ID: {med_id} | Taken on: {date} at {time}")