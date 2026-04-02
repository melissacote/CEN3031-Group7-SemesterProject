# database.py
"""
Database module for the PyQt6 Dashboard Application.

Handles SQLite database initialization, user creation, and authentication.
"""

import sqlite3

DB_NAME = 'medrec.db'

def get_connection():
    return sqlite3.connect(DB_NAME)

def create_tables():
    with get_connection() as conn:
        cursor = conn.cursor()

        # Create users table with all required personal information fields
        create_users = '''
            CREATE TABLE IF NOT EXISTS users
            (
                user_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                date_of_birth TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''
        cursor.execute(create_users)

        # Create medications table with all required medication information fields
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
        cursor.execute(create_medications)

        # Create administration log table with all metadata information fields
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
        cursor.execute(create_administration_log)

        #FIXME: Currently there is an error here where the first_name column is not detected.

        # Create default admin account if it doesn't exist
        # cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        # if cursor.fetchone()[0] == 0:
        #     cursor.execute('''
        #             INSERT INTO users (username, password, first_name, last_name, email)
        #             VALUES (?, ?, ?, ?, ?)
        #         ''', ("admin", "password", "Admin", "User", "admin@example.com"))

        conn.commit()

def get_user_id(username: str) -> int | None:
    """Return user ID for a given username."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def get_user_profile(username: str) -> dict | None:
    """Return full user profile as dictionary."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            conn.close()
            return dict(zip(columns, row))
        conn.close()
        return None
    except Exception:
        return None


def get_user_medications(username: str) -> list[dict]:
    """Return list of medication dictionaries for the user."""
    user_id = get_user_id(username)
    if not user_id:
        return []
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT medication_name, dosage, frequency, start_date, notes
            FROM medications
            WHERE user_id = ?
            ORDER BY start_date DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(["name", "dosage", "frequency", "start_date", "notes"], row)) for row in rows]
    except Exception:
        return []

def verify_user(username: str, password: str) -> bool:
    """
    Verify if the provided username and password match a record in the database.

    Args:
        username: The username to check
        password: The password to verify

    Returns:
        True if credentials are valid, False otherwise
    """
    if not username or not password:
        return False
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        return result and result[0] == password
    except Exception:
        return False


def create_new_user(user_data: dict) -> bool:
    """
    Create a new user record in the database with all registration fields.

    Args:
        user_data: Dictionary containing user registration information

    Returns:
        True if user was created successfully, False if username already exists or error occurred
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO users (
                username, password, first_name, last_name, date_of_birth
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            user_data['username'],
            user_data['password'],
            user_data.get('first_name'),
            user_data.get('last_name'),
            user_data.get('date_of_birth')
        ))

        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Username already exists
        return False
    except Exception as e:
        print(f"Database error during user creation: {e}")
        return False

# For temp testing purposes only, remove when testing complete and move function call to main
if __name__ == '__main__':
    create_tables()
