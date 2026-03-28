# Runs app
import sys
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication, QMainWindow
from database.db_connection import create_tables, get_connection
from ui.tracking_screen import DosageTrackingScreen

# HELPER: Grab the ID of the fake user from test_logic.py
def get_test_user_id():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE username='test_patient'")
        result = cursor.fetchone()
        return result[0] if result else None

# initializing the application window
class MainWindow(QMainWindow):
    def __init__(self, user_id):
        super().__init__()
        self.setWindowTitle("MedRec")
        self.setFixedSize(QSize(600, 500))

        # Pass the ID to the UI so it queries the right data
        self.tracking_widget = DosageTrackingScreen(user_id)
        self.setCentralWidget(self.tracking_widget)

if __name__ == "__main__":
    create_tables() # connect and initialize SQLite database
    # Check if the test user exists in the DB
    test_user_id = get_test_user_id()   
    if test_user_id is None:
        print("Error: Run 'python test_logic.py' first to generate the test data!")
        sys.exit(1)
    app = QApplication(sys.argv)
    window = MainWindow(test_user_id)
    window.show()
    sys.exit(app.exec())