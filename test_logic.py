# This is a simple test script to verify that the medication addition and sorting logic works correctly. It will create a test user, add some medications with different times, and then fetch and print the sorted list of today's medications for that user.
from database.db_connection import create_tables, get_connection
from services.medication import add_medication, get_todays_medications_sorted
from utils.password import hash_password

# 1. Initialize the database
create_tables()

# 2. Create a fake user directly using SQL for testing
with get_connection() as conn:
    cursor = conn.cursor()
    try:
        # Hash the test password before saving it to the database
        hashed_pw = hash_password('pass1234567890')

        # Use parameterized queries (?, ?) to safely insert the data
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('test_patient', hashed_pw))
        conn.commit()
    except:
        pass # User already exists from a previous test run
    
    # Get the user_id of our fake user
    cursor.execute("SELECT user_id FROM users WHERE username='test_patient'")
    test_user_id = cursor.fetchone()[0]

# 3. Test add_medication function
print("Adding test medications...")
add_medication(test_user_id, "Lisinopril", "10 mg", "Oral", "Daily", "09:00 AM")
add_medication(test_user_id, "Aspirin", "81 mg", "Oral", "Daily", "08:00 AM") # Earlier time to test sorting

# 4. Test sorting query
print("\nFetching today's medications (Should be sorted chronologically):")
results = get_todays_medications_sorted(test_user_id)

for med in results:
    med_id, name, dosage, time, is_taken, special_instructions, time_taken = med
    if is_taken == 1:
        print(f"Time: {time} | Medication: {name} ({dosage}) ✅")
    else:
        print(f"Time: {time} | Medication: {name} ({dosage})")