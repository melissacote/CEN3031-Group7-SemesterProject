# main.py
"""
Main entry point for the PyQt6 Application.

This script initializes the database and launches the login window.
"""

import sys
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QMenuBar
from database.db_connection import create_tables, get_connection
from ui.login_window import LoginWindow
from ui.main_window import MainWindow

# HELPER: Grab the ID of the fake user from test_logic.py
def get_test_user_id():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE username='test_patient'")
        result = cursor.fetchone()
        return result[0] if result else None

if __name__ == "__main__":
    """
    Main entry point for the program.
    """

    create_tables() # connect and initialize SQLite database

    # Validate if the test user exists in the DB
    test_user_id = get_test_user_id()

    # For testing only, change as needed
    test_mode = True
    if test_mode is True and test_user_id is None:
        print("Error: Run 'python test_logic.py' first to generate the test data!")
        sys.exit(1)
    elif test_user_id is None:
        print("Error: User does not exist.")
        # TODO: replace sys.exit(1) with a loop to prompt for a new user id.
        sys.exit(1)

    # Instantiate application using the given arguments
    app = QApplication(sys.argv)

    app.setStyle("Fusion") # Modern application-wide style

    # Comment/uncomment either one for debugging, but ultimately LoginWindow() is the correct one.
    login_window = LoginWindow()
    #login_window = MainWindow(test_user_id)

    # Display the UI window
    login_window.show()

    # Quit code execution upon exit.
    sys.exit(app.exec())
