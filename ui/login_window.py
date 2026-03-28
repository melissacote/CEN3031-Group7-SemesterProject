# login_window.py
"""
Login and Registration module for the PyQt6 Dashboard Application.

Contains LoginWindow and RegisterDialog classes with comprehensive input validation.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QDialog, QFormLayout, QComboBox,
    QDateEdit
)
from PyQt6.QtCore import Qt, QDate, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from ui.main_window import MainWindow
from database.db_connection import verify_user, create_new_user
import re


class LoginWindow(QWidget):
    """
    Main login window displayed when the application starts.

    Provides username/password fields and a button to open the registration dialog.
    """

    def __init__(self):
        """Initialize the login window UI and connect signals."""
        super().__init__()
        self.setWindowTitle("Login - PyQt6 Dashboard")
        self.setFixedSize(440, 340)

        self.setStyleSheet("""
            QWidget { background-color: #2c3e50; color: white; }
            QLineEdit, QComboBox, QDateEdit {
                padding: 10px; font-size: 15px; border-radius: 6px;
                background-color: #34495e; color: white;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(25)
        layout.setContentsMargins(50, 50, 50, 50)

        # Title
        title = QLabel("🔑 Welcome")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Input fields
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        login_btn = QPushButton("Login")
        login_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; padding: 14px; 
                          font-size: 16px; border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        login_btn.clicked.connect(self.handle_login)

        create_btn = QPushButton("Create New Account")
        create_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; padding: 14px; 
                          font-size: 16px; border-radius: 8px; }
            QPushButton:hover { background-color: #5dade2; }
        """)
        create_btn.clicked.connect(self.show_register_dialog)

        btn_layout.addWidget(login_btn)
        btn_layout.addWidget(create_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def handle_login(self) -> None:
        """
        Handle login button click.
        Validates credentials and opens the main dashboard if successful.
        """
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if verify_user(username, password):
            self.main_window = MainWindow(username)
            self.main_window.show()
            self.close()
        else:
            QMessageBox.critical(
                self, "Login Failed",
                "Invalid username or password.\n\n"
                "Default demo account:\nUsername: admin\nPassword: password"
            )

    def show_register_dialog(self) -> None:
        """Open the registration dialog and show success message if registration completes."""
        dialog = RegisterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(
                self, "Registration Successful",
                "Your account has been created successfully!\nYou can now log in."
            )


class RegisterDialog(QDialog):
    """
    Registration dialog with comprehensive input validation for new users.

    Validates:
    - First/Last names contain only letters and spaces
    - Age between 18 and 110
    - SSN last 4 digits are numeric and exactly 4 characters
    - Basic email format
    """

    def __init__(self, parent=None):
        """Initialize the registration form with validators."""
        super().__init__(parent)
        self.setWindowTitle("Create New Account")
        self.setFixedSize(540, 680)

        layout = QFormLayout()
        layout.setSpacing(14)
        layout.setContentsMargins(45, 35, 45, 35)

        # Form fields
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        self.first_name = QLineEdit()
        self.last_name = QLineEdit()

        # Name validator: letters and spaces only
        name_regex = QRegularExpression(r"^[A-Za-z\s]+$")
        name_validator = QRegularExpressionValidator(name_regex)
        self.first_name.setValidator(name_validator)
        self.last_name.setValidator(name_validator)

        self.dob = QDateEdit()
        self.dob.setCalendarPopup(True)
        self.dob.setDate(QDate.currentDate().addYears(-30))

        self.ssn_last4 = QLineEdit()
        self.ssn_last4.setMaxLength(4)
        self.ssn_last4.setPlaceholderText("1234")
        # Numbers only for SSN
        ssn_regex = QRegularExpression(r"^\d{0,4}$")
        self.ssn_last4.setValidator(QRegularExpressionValidator(ssn_regex))

        self.gender = QComboBox()
        self.gender.addItems(["", "Male", "Female"])

        self.address = QLineEdit()
        self.email = QLineEdit()
        self.phone = QLineEdit()

        # Add fields to form
        layout.addRow("Username *:", self.username)
        layout.addRow("Password *:", self.password)
        layout.addRow("First Name *:", self.first_name)
        layout.addRow("Last Name *:", self.last_name)
        layout.addRow("Date of Birth *:", self.dob)
        layout.addRow("SSN Last 4 Digits:", self.ssn_last4)
        layout.addRow("Gender:", self.gender)
        layout.addRow("Address:", self.address)
        layout.addRow("Email:", self.email)
        layout.addRow("Phone Number:", self.phone)

        # Action buttons
        btn_layout = QHBoxLayout()
        register_btn = QPushButton("Create Account")
        register_btn.clicked.connect(self.validate_and_register)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(register_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        self.setLayout(layout)

    def validate_and_register(self) -> None:
        """
        Validate all input fields and create new user if validation passes.
        Shows appropriate error messages for invalid inputs.
        """
        # Check required fields
        if not self.username.text().strip() or not self.password.text().strip():
            QMessageBox.warning(self, "Missing Fields", "Username and Password are required.")
            return

        if not self.first_name.text().strip() or not self.last_name.text().strip():
            QMessageBox.warning(self, "Missing Fields", "First Name and Last Name are required.")
            return

        # Age validation (18 to 110 years old)
        today = QDate.currentDate()
        birth_date = self.dob.date()
        age = birth_date.daysTo(today) // 365

        if age < 18:
            QMessageBox.warning(self, "Invalid Age", "You must be at least 18 years old to register.")
            return
        if age > 110:
            QMessageBox.warning(self, "Invalid Age", "Please enter a realistic date of birth (maximum age 110).")
            return

        # SSN validation
        ssn = self.ssn_last4.text().strip()
        if ssn and len(ssn) != 4:
            QMessageBox.warning(self, "Invalid SSN", "Last 4 digits of SSN must be exactly 4 numbers.")
            return

        # Basic email validation
        email = self.email.text().strip()
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            QMessageBox.warning(self, "Invalid Email", "Please enter a valid email address.")
            return

        # Prepare data for database
        user_data = {
            'username': self.username.text().strip(),
            'password': self.password.text().strip(),
            'first_name': self.first_name.text().strip(),
            'last_name': self.last_name.text().strip(),
            'date_of_birth': birth_date.toString("yyyy-MM-dd"),
            'ssn_last4': ssn,
            'gender': self.gender.currentText(),
            'address': self.address.text().strip(),
            'email': email,
            'phone': self.phone.text().strip()
        }

        if create_new_user(user_data):
            self.accept()
        else:
            QMessageBox.warning(self, "Registration Failed",
                                "Username already exists. Please choose a different username.")