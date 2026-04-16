# database.py
"""
Database module for the PyQt6 Dashboard Application.

Handles SQLite database initialization, user creation, and authentication.
"""

import sqlite3
import os

# Safely anchor to the MedRec root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_NAME = os.path.join(BASE_DIR, 'medrec.db')

def get_connection():
    return sqlite3.connect(DB_NAME)


def create_tables(conn: sqlite3.Connection | None = None) -> None:
    """
    Create all required database tables if they do not already exist.

    Args:
        conn: Optional database connection. If not provided, get_connection() will be used by default.
    """
    if conn is None:
        conn = get_connection()
    with conn:
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
        conn.commit()