# dialog_windows.py

"""
All popup dialogs used by the MainWindow.
Each class is self-contained and well-documented.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QComboBox, QFormLayout, QGroupBox, QLineEdit
)
from PyQt6.QtCore import Qt
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import csv
import os
from datetime import datetime


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
    """Generate PDF report of medication intake."""

    def __init__(self, username: str, medications: list[dict], parent=None):
        super().__init__(parent)
        self.username = username
        self.medications = medications
        self.setWindowTitle("Generate Medication Report")
        self.setFixedSize(480, 300)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h3>📄 Medication Intake Report for {username}</h3>"))
        layout.addWidget(QLabel("This will create a professional PDF summary of your current medications."))

        generate_btn = QPushButton("Generate & Save PDF")
        generate_btn.clicked.connect(self.generate_pdf)
        layout.addWidget(generate_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def generate_pdf(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save PDF", f"{self.username}_medication_report.pdf", "PDF Files (*.pdf)")
        if not filename:
            return

        try:
            c = canvas.Canvas(filename, pagesize=letter)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, 750, f"Medication Report – {self.username}")
            c.setFont("Helvetica", 12)
            c.drawString(50, 720, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}")

            y = 680
            for med in self.medications:
                c.drawString(50, y, f"• {med['name']}  |  {med['dosage']}  |  {med['frequency']}")
                y -= 20
                if y < 100:
                    c.showPage()
                    y = 750

            c.save()
            QMessageBox.information(self, "Success", f"PDF saved as {os.path.basename(filename)}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "PDF Generation Failed", str(e))


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