# ui/dialog_windows.py

"""
All popup dialogs used by the MainWindow.
Each class is self-contained and well-documented.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QComboBox, QFormLayout, QGroupBox, QLineEdit, QListWidget, QHeaderView, QCheckBox
)
from PyQt6.QtCore import QStandardPaths
from PyQt6.QtGui import QColor
import pandas as pd
import csv
import os
from ui.date_panel import DateSelectionPanel
from services.reports import get_medication_history
from utils.pdf_generator import generate_pdf_report
from utils.camera import find_available_cameras, save_camera_preference, load_full_camera_config

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
    """Dialog to select dates, report type, and generate a PDF report of medication intake."""
    def __init__(self, user_id, username, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.username = username
        self.setWindowTitle("Generate PDF Medication Report")
        self.resize(350, 320)

        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"<h3>📄 Medication Intake Report for {username}</h3>"))
        layout.addWidget(QLabel("This will create a professional PDF summary of your medications."))
        
        # Create report query UI toggle
        layout.addWidget(QLabel("<b>Report Type:</b>"))
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            "Both (Medication List & Admin Record)", 
            "Medication List Only", 
            "Administration Record Only"
        ])
        layout.addWidget(self.report_type_combo)

        layout.addWidget(QLabel("<b>Select Date Range:</b>"))
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
        report_type = self.report_type_combo.currentText() # Pass to backend

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
            output_path=file_path,
            report_type=report_type
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
        
        # Load the user's full configuration to pre-fill the form
        current_config = load_full_camera_config()
        
        if not self.available_cams:
            self.cam_combo.addItem("No cameras detected")
            self.cam_combo.setEnabled(False)
        else:
            for cam in self.available_cams:
                self.cam_combo.addItem(f"Camera {cam}")
            
            saved_cam = current_config.get("preferred_camera_index", 0)
            if saved_cam in self.available_cams:
                dropdown_index = self.available_cams.index(saved_cam)
                self.cam_combo.setCurrentIndex(dropdown_index)

        form.addRow("Select Webcam:", self.cam_combo)

        # Convert Resolution to Dropdown
        self.resolution = QComboBox()
        self.resolution.addItems(["1920x1080", "1280x720", "800x600", "640x480"])
        saved_res = f"{current_config.get('width', 1920)}x{current_config.get('height', 1080)}"
        
        res_idx = self.resolution.findText(saved_res)
        if res_idx != -1:
            self.resolution.setCurrentIndex(res_idx)
            
        form.addRow("Resolution:", self.resolution)

        # Convert FPS to Dropdown
        self.fps = QComboBox()
        self.fps.addItems(["30", "60"])
        saved_fps = str(current_config.get('fps', 30))
        
        fps_idx = self.fps.findText(saved_fps)
        if fps_idx != -1:
            self.fps.setCurrentIndex(fps_idx)
            
        form.addRow("Frames per second:", self.fps)

        # Auto-Focus Checkbox
        self.autofocus_cb = QCheckBox("Enable Hardware Auto-Focus")
        current_af_setting = current_config.get("autofocus", False)
        self.autofocus_cb.setChecked(current_af_setting)
        self.autofocus_cb.setToolTip("Uncheck to lock focus manually if your camera is pulsing/blurring.")
        form.addRow("Auto-Focus:", self.autofocus_cb)

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
            
            # Read directly from the dropdowns safely
            try:
                res_text = self.resolution.currentText().lower().split('x')
                w = int(res_text[0].strip())
                h = int(res_text[1].strip())
                fps = int(self.fps.currentText().strip())
                af_status = self.autofocus_cb.isChecked()

            except Exception:
                QMessageBox.warning(self, "Invalid Input", "Settings parsing failed.")
                return

            save_camera_preference(
                camera_index=selected_hardware_index, 
                width=w, 
                height=h, 
                fps=fps, 
                autofocus=af_status
            )
            
        QMessageBox.information(self, "Settings Saved", "Hardware preferences have been updated.")
        self.accept()


class MedicationHistoryDialog(QDialog):
    """An interactive UI to view past medication administration logs."""
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Medication History Log")
        self.resize(750, 500)

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
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Date", "Time", "Medication", "Dosage", "Notes", "Status"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        # Stretch columns to fit the window
        header = self.table.horizontalHeader()
        for col in range(6):
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
            self.table.setSpan(0, 0, 1, 6)
            return

        # Populate the table with the fetched logs
        self.table.setRowCount(len(logs))
        for row_idx, row_data in enumerate(logs):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(row_data["date_taken"])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(row_data["time_taken"])))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(row_data["medication_name"])))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(row_data["dosage"])))
            
            # Extract notes safely
            notes_str = str(row_data["notes"]) if row_data.get("notes") else ""
            self.table.setItem(row_idx, 4, QTableWidgetItem(notes_str))
            
            # Highlight/flag missed doses in the history UI
            status_val = row_data["status"]
            status_text = "Taken" if status_val == 1 else "Missed"
            item = QTableWidgetItem(status_text)
            
            if status_val == 0:
                item.setForeground(QColor("#c0392b"))
                
            self.table.setItem(row_idx, 5, item)