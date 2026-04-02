# User database operations
import sqlite3

from database.db_connection import DB_NAME


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
