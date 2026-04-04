# User database operations
import sqlite3

from database.db_connection import get_connection
from utils.password import verify_password, hash_password


def get_user_id(username: str, conn: sqlite3.Connection | None = None) -> int | None:
    """Return user ID for a given username."""
    if conn is None:
        conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception:
        return None


def get_user_profile(username: str, conn: sqlite3.Connection | None = None) -> dict | None:
    """Return full user profile as dictionary."""
    if conn is None:
        conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
    except Exception:
        return None


def verify_user(username: str, password: str, conn: sqlite3.Connection | None = None) -> bool:
    """
    Verify if the provided username and password match a record in the database.

    Args:
        username: The username to check
        password: The password to verify
        conn: Optional database connection. If not provided, get_connection() will be used by default.

    Returns:
        True if credentials are valid, False otherwise
    """
    if not username or not password:
        return False
    if conn is None:
        conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            return result and verify_password(result[0], password)
    except Exception:
        return False


def create_new_user(user_data: dict, conn: sqlite3.Connection | None = None) -> bool:
    """
    Create a new user record in the database with all registration fields.

    Args:
        user_data: Dictionary containing user registration information
        conn: Optional database connection. If not provided, get_connection() will be used by default.

    Returns:
        True if user was created successfully, False if username already exists or error occurred
    """
    if conn is None:
        conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            hashed_password = hash_password(user_data['password'])

            cursor.execute('''
                INSERT INTO users (
                    username, password, first_name, last_name, date_of_birth
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                user_data['username'],
                hashed_password,
                user_data.get('first_name'),
                user_data.get('last_name'),
                user_data.get('date_of_birth')
            ))

            conn.commit()
            return True
    except sqlite3.IntegrityError:
        # Username already exists
        return False
    except Exception as e:
        print(f"Database error during user creation: {e}")
        return False
