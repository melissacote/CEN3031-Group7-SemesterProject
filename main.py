# main.py
"""
Main entry point for the PyQt6 Application.

This script initializes the database and launches the login window.
"""

import sys
from PyQt6.QtWidgets import QApplication
from database.db_connection import create_tables, get_connection
from scripts.seed_fda_data import is_database_seeded, seed_data

# HELPER: Grab the ID of the fake user from test_logic.py
def get_test_user_id():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE username='test_patient'")
        result = cursor.fetchone()
        return result[0] if result else None

# HELPER: Run startup checks to ensure database is seeded and ready    
def run_startup_checks():
    """
    Ensures the local environment is ready. 
    If product.txt has been updated or DB is empty, it re-seeds.
    """
    print("[SYSTEM] Running startup diagnostic...")
    
    # Ensure tables exist (users, medications, and fda_medications)
    create_tables() 
    
    if not is_database_seeded():
        print("[SYSTEM] FDA Database missing or outdated. Initializing local seed...")
        seed_data()
        print("[SYSTEM] Seed complete.")
    else:
        print("[SYSTEM] Local FDA Knowledge Base: READY.")

if __name__ == "__main__":
    """
    Main entry point for the program.
    """

    create_tables() # connect and initialize SQLite database

    # Validate if the test user exists in the DB
    test_user_id = get_test_user_id()

    # For testing only, change as needed. Keep False for production to prevent crashes
    test_mode = False
    if test_mode and test_user_id is None:
        print("Warning: Test user not found. Booting normally instead of exiting.")

    # Instantiate application using the given arguments
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Tray mode: only logout button fully quits
    
    # Initialize SQLite database and seed FDA data FIRST
    run_startup_checks()

    # Now that the environment is ready, safely import UI
    from ui.login_window import LoginWindow

    app.setStyle("Fusion") # Modern application-wide style

    # Comment/uncomment either one for debugging, but ultimately LoginWindow() is the correct one.
    login_window = LoginWindow()
    #login_window = MainWindow(test_user_id)

    # Display the UI window
    login_window.show()

    # Quit code execution upon exit.
    sys.exit(app.exec())