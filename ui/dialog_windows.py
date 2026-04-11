# dialog_windows.py

"""
All popup dialogs used by the MainWindow.
Each class is self-contained and well-documented.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QComboBox, QFormLayout, QGroupBox, QLineEdit, QListWidget, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
import pandas as pd
import csv
import os
from ui.date_panel import DateSelectionPanel
from services.reports import get_medication_history
from utils.pdf_generator import generate_pdf_report
from services.medication import add_medication, get_medications_for_management


class AddMedicationDialog(QDialog):
    """Add medication dialog for the management screen."""
    medication_saved = pyqtSignal()

    def __init__(self, user_id: int, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Add medication")
        self.resize(460, 460)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("New medication"))

        # Form fields the user fills before pressing save
        form = QFormLayout()
        self.input_name = QLineEdit()
        self.input_dosage = QLineEdit()
        self.input_route = QLineEdit()
        self.input_frequency = QLineEdit()
        self.input_scheduled_time = QLineEdit()
        self.input_prescriber = QLineEdit()
        self.input_special_instructions = QLineEdit()
        self.input_name.setPlaceholderText("required")
        self.input_dosage.setPlaceholderText("required")
        self.input_route.setPlaceholderText("required")
        self.input_frequency.setPlaceholderText("required")
        self.input_scheduled_time.setPlaceholderText("required")
        self.input_prescriber.setPlaceholderText("optional")
        self.input_special_instructions.setPlaceholderText("optional")
        form.addRow("Medication name:", self.input_name)
        form.addRow("Dosage:", self.input_dosage)
        form.addRow("Route:", self.input_route)
        form.addRow("Frequency:", self.input_frequency)
        form.addRow("Scheduled time:", self.input_scheduled_time)
        form.addRow("Prescriber:", self.input_prescriber)
        form.addRow("Special instructions:", self.input_special_instructions)
        layout.addLayout(form)

        # Save button to add the medication record to the database
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.on_save)
        layout.addWidget(save_btn)

        # List of medications already saved for this user
        layout.addWidget(QLabel("Saved medications"))
        self.med_list = QListWidget()
        self.med_list.setMinimumHeight(150)
        layout.addWidget(self.med_list)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.reload_list()

    def reload_list(self):
        # Called when dialog opens and after each successful save
        # Pulling the latest rows from the DB so the list stays in sync
        self.med_list.clear()
        meds = get_medications_for_management(self.user_id)
        for med in meds:
            self.med_list.addItem(f"{med['name']} | {med['dosage']} | {med['scheduled_time']}")

    def on_save(self):
        # Validating the required fields before saving the medication record
        medication_name = self.input_name.text().strip()
        dosage = self.input_dosage.text().strip()
        route = self.input_route.text().strip()
        frequency = self.input_frequency.text().strip()
        scheduled_time = self.input_scheduled_time.text().strip()
        if not medication_name or not dosage or not route or not frequency or not scheduled_time:
            QMessageBox.warning(self, "Missing info", "Enter medication name, dosage, route, frequency, and scheduled time.")
            return

        # Inserting the medication record into the database
        add_medication(
            self.user_id,
            medication_name,
            dosage,
            route,
            frequency,
            scheduled_time,
            self.input_prescriber.text().strip(),
            self.input_special_instructions.text().strip(),
        )

        # Clearing the form fields and refreshing the list to show the new medication record
        self.input_name.clear()
        self.input_dosage.clear()
        self.input_route.clear()
        self.input_frequency.clear()
        self.input_scheduled_time.clear()
        self.input_prescriber.clear()
        self.input_special_instructions.clear()
        self.reload_list()
        self.medication_saved.emit()

class ProfileWindow(QDialog):
    """Displays the logged-in user's full profile information."""

    def __init__(self, profile: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Patient Profile")
        self.setFixedSize(520, 480)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h2>👤 {profile['first_name']} {profile['last_name']}</h2>"))

        info = [
            ("Username", profile['username']),
            ("Date of Birth", profile['date_of_birth'] or "—")
        ]

        for label, value in info:
            layout.addWidget(QLabel(f"<b>{label}:</b> {value}"))
        layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class AnalyticsWindow(QDialog):
    """Medication analytics summary with dosages, interactions, start dates, missed days."""

    def __init__(self, medications: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Medication Analytics")
        self.resize(720, 560)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>📊 Medication Summary</h2>"))

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Medication", "Dosage", "Frequency", "Started", "Missed Days", "Notes"])
        table.setRowCount(len(medications))

        # Hard-coded demo interactions and missed days.
        # TODO: implement interactions based on list of user's medications.
        interaction_map = {
            "Med1": "May interact with potassium supplements",
            "Med2": "No major interactions noted",
            "Med3": "Avoid grapefruit juice"
        }

        for row, med in enumerate(medications):
            table.setItem(row, 0, QTableWidgetItem(med["name"]))
            table.setItem(row, 1, QTableWidgetItem(med["dosage"]))
            table.setItem(row, 2, QTableWidgetItem(med["frequency"]))
            table.setItem(row, 3, QTableWidgetItem(med["start_date"]))
            table.setItem(row, 4, QTableWidgetItem(str(row + 2)))
            table.setItem(row, 5, QTableWidgetItem(med.get("notes", "")))

        layout.addWidget(table)

        # Simple interaction warning box
        warning = QLabel(f"<b>Potential Interactions:</b><br>{'<br>'.join([f'• {k}: {v}' for k, v in interaction_map.items()])}")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class ExportDialog(QDialog):
    """Export own user data + medications to CSV."""

    def __init__(self, username: str, profile: dict, medications: list[dict], parent=None):
        super().__init__(parent)
        self.username = username
        self.profile = profile
        self.medications = medications
        self.setWindowTitle("Export Your Data")
        self.setFixedSize(460, 280)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h3>Export data for <b>{username}</b></h3>"))
        layout.addWidget(QLabel("This will only export <i>your own</i> profile and medication records."))

        export_btn = QPushButton("Export to CSV")
        export_btn.clicked.connect(self.export_to_csv)
        layout.addWidget(export_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def export_to_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save CSV", f"{self.username}_data.csv", "CSV Files (*.csv)")
        if not filename:
            return

        try:
            # Build separate dfs for profile data and medication data
            df_profile = pd.DataFrame([
                {"first_name": self.profile.get("first_name"),
                 "last_name": self.profile.get("last_name"),
                 "date_of_birth": self.profile.get("date_of_birth")
                 }])
            df_meds = pd.DataFrame(self.medications)

            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["PROFILE"])
                df_profile.to_csv(f, index=False)
                f.write("\nMEDICATIONS\n")
                df_meds.to_csv(f, index=False)

            QMessageBox.information(self, "Success", f"Data exported to {os.path.basename(filename)}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))


class MedicationReportDialog(QDialog):
    """Dialog to select dates and generate a PDF report of medication intake."""
    def __init__(self, user_id, username, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.username = username
        self.setWindowTitle("Generate PDF Medication Report")
        self.resize(350, 250)

        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"<h3>📄 Medication Intake Report for {username}</h3>"))
        layout.addWidget(QLabel("This will create a professional PDF summary of your current medications."))
        layout.addWidget(QLabel("Select the date range for the medical report:"))

        # Use date selection panel to allow users to pick custom start/end dates for the report (defaults to last 30 days)  
        self.date_panel = DateSelectionPanel()
        layout.addWidget(self.date_panel)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        # The action button inside the popup
        self.generate_btn = QPushButton("💾 Save PDF")
        self.generate_btn.setStyleSheet("padding: 10px; font-weight: bold;")
        self.generate_btn.clicked.connect(self.generate_pdf)
        layout.addWidget(self.generate_btn)

    def generate_pdf(self):
        """Handles the generation process when the button is clicked."""
        # Grab custom dates from the UI panel
        start_date, end_date = self.date_panel.get_selected_dates()

        # Open a "Save As" file dialog
        default_filename = f"{self.username}_Adherence_Report.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Patient Report", 
            os.path.join(os.path.expanduser("~"), "Desktop", default_filename),
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return # User canceled the save dialog

        self.generate_btn.setText("Generating...")
        self.generate_btn.setEnabled(False)

        # Call the backend PDF generator
        success = generate_pdf_report(
            user_id=self.user_id,
            patient_name=self.username,
            start_date=start_date,
            end_date=end_date,
            output_path=file_path
        )

        # Handle Success/Failure
        if success:
            QMessageBox.information(self, "Success", f"Report successfully saved to:\n\n{file_path}")
            self.accept() # Close the popup window
        else:
            QMessageBox.critical(self, "Error", "Failed to generate the PDF report. Please check the logs.")
            self.generate_btn.setText("💾 Save PDF")
            self.generate_btn.setEnabled(True)


class SettingsWindow(QDialog):
    """Webcam configuration UI (no hardware interface implemented yet)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings – Webcam Configuration")
        self.setFixedSize(520, 380)

        layout = QVBoxLayout(self)

        group = QGroupBox("Available Webcams")
        form = QFormLayout(group)

        self.cam_combo = QComboBox()
        self.cam_combo.addItems(["Webcam 1 (Integrated)", "Webcam 2 (USB)", "Virtual Camera"])
        form.addRow("Select Webcam:", self.cam_combo)

        self.resolution = QLineEdit("1920x1080")
        form.addRow("Resolution:", self.resolution)

        self.fps = QLineEdit("30")
        form.addRow("Frames per second:", self.fps)

        layout.addWidget(group)

        apply_btn = QPushButton("Apply Settings")
        apply_btn.clicked.connect(self.apply_settings)
        layout.addWidget(apply_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def apply_settings(self):
        QMessageBox.information(
            self,
            "Settings Saved",
            f"Webcam configured:\n"
            f"Device: {self.cam_combo.currentText()}\n"
            f"Resolution: {self.resolution.text()}\n"
            f"FPS: {self.fps.text()}\n\n"
            "Hardware interface will be implemented in a future update."
        )

class MedicationHistoryDialog(QDialog):
    """An interactive UI to view past medication administration logs."""
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Medication History Log")
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        # Use date selection panel to allow users to pick custom start/end dates
        self.date_panel = DateSelectionPanel()
        layout.addWidget(self.date_panel)

        # Search/Filter Button
        self.search_btn = QPushButton("🔍 Load History")
        self.search_btn.setStyleSheet("padding: 10px; font-weight: bold; background-color: #2c3e50; color: white;")
        self.search_btn.clicked.connect(self.load_history)
        layout.addWidget(self.search_btn)

        # The table to display the results
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Date", "Time", "Medication", "Dosage"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        # Stretch columns to fit the window
        header = self.table.horizontalHeader()
        for col in range(4):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
            
        layout.addWidget(self.table)
        
        # Load the default 30-day view immediately when the window opens
        self.load_history()

    def load_history(self):
        # Ask the panel for the dates
        start, end = self.date_panel.get_selected_dates()
        
        # Fetch the data
        logs, _, _ = get_medication_history(self.user_id, start, end)
        
        # Clear existing table data
        self.table.setRowCount(0)
        
        if not logs:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("No records found for this period."))
            self.table.setSpan(0, 0, 1, 4)
            return

        # Populate the table with the fetched logs
        self.table.setRowCount(len(logs))
        for row_idx, row_data in enumerate(logs):
            # row_data from get_medication_history is (med_name, dosage, date, time)
            # Rearrange it slightly to match the table headers (Date, Time, Med, Dosage)
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(row_data[2]))) # Date
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(row_data[3]))) # Time
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(row_data[0]))) # Medication Name
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(row_data[1]))) # Dosage