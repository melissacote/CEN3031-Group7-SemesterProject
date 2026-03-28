# Runs app
import sys
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication, QMainWindow
from database.db_connection import create_tables

# initializing the application window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MedRec")
        self.setFixedSize(QSize(600, 400))

if __name__ == "__main__":
    create_tables() # connect and initialize SQLite database
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())






