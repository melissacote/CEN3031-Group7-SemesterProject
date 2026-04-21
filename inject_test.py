import sqlite3

# Connect to your local database
conn = sqlite3.connect('medrec.db')
cursor = conn.cursor()

try:
    # Use user_id as the column name, and 1 as the value for the test patient
    cursor.execute('''
        INSERT INTO administration_log 
        (user_id, medication_id, medication_name, dosage, route, frequency, special_instructions, date_taken, time_taken, status, notes) 
        VALUES (1, 1, 'Test Med', '100mg', 'oral', 'Once daily', '', '2026-04-16', 'Morning', 0, 'Missed dose test')
    ''')
    conn.commit()
    print("✅ Successfully injected missed dose into the database!")
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    conn.close()