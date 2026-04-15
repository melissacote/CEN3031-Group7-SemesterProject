# dialog_windows.py

"""
All popup dialogs used by the MainWindow.
Each class is self-contained and well-documented.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QComboBox, QFormLayout, QGroupBox, QLineEdit, QListWidget, QHeaderView
)
from PyQt6.QtCore import pyqtSignal, QStandardPaths
import pandas as pd
import csv
import os
from ui.date_panel import DateSelectionPanel
from services.reports import get_medication_history
from ui.scanner_window import OCRScannerDialog
from utils.pdf_generator import generate_pdf_report
from services.medication import add_medication, get_medications_for_management
from utils.camera import find_available_cameras, load_camera_preference, save_camera_preference

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

        # Open a "Save As" file dialog using secure QStandardPaths
        desktop_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        default_filename = f"{self.username}_Adherence_Report.pdf"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Patient Report", 
            os.path.join(desktop_path, default_filename),
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
    """Webcam configuration UI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings – Webcam Configuration")
        self.setFixedSize(520, 380)

        layout = QVBoxLayout(self)

        group = QGroupBox("Available Webcams")
        form = QFormLayout(group)

        self.cam_combo = QComboBox()
        self.available_cams = find_available_cameras()
        
        if not self.available_cams:
            self.cam_combo.addItem("No cameras detected")
            self.cam_combo.setEnabled(False)
        else:
            for cam in self.available_cams:
                self.cam_combo.addItem(f"Camera {cam}")
            
            saved_cam = load_camera_preference()
            if saved_cam in self.available_cams:
                dropdown_index = self.available_cams.index(saved_cam)
                self.cam_combo.setCurrentIndex(dropdown_index)

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
        if self.available_cams:
            selected_hardware_index = self.available_cams[self.cam_combo.currentIndex()]
            save_camera_preference(selected_hardware_index)
            
        QMessageBox.information(self, "Settings Saved", "Hardware preferences have been updated.")
        self.accept()

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