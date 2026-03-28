import sqlite3

DB_NAME = 'medrec.db'

def get_connection():
    return sqlite3.connect(DB_NAME)

def create_tables():
    with get_connection() as conn:
        cursor = conn.cursor()

        create_users = '''
            CREATE TABLE IF NOT EXISTS users
            (
                user_id INTEGER NOT NULL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        '''

        create_medications = '''
            CREATE TABLE IF NOT EXISTS medications
            (
                medication_id INTEGER NOT NULL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(user_id),
                medication_name TEXT NOT NULL,
                dosage TEXT NOT NULL,
                route TEXT NOT NULL,
                frequency TEXT NOT NULL,
                scheduled_time TEXT,
                prescriber TEXT,
                special_instructions TEXT
            )
        '''

        create_administration_log = '''
            CREATE TABLE IF NOT EXISTS administration_log
            (
                log_id INTEGER NOT NULL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(user_id),
                medication_id INTEGER NOT NULL REFERENCES medications(medication_id),
                date_taken TEXT NOT NULL,
                time_taken TEXT NOT NULL,
                status INTEGER NOT NULL,
                notes TEXT
            )
        '''

        cursor.execute(create_users)
        cursor.execute(create_medications)
        cursor.execute(create_administration_log)
        conn.commit()

# For temp testing purposes only, remove when testing complete and move function call to main
if __name__ == '__main__':
    create_tables()
