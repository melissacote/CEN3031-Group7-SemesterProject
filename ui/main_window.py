# main_window.py
"""
Main dashboard window for the PyQt6 application.

Displays menu bar, toolbar, quick action buttons, and interactive matplotlib charts.
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame, QLabel,
    QToolBar, QMenuBar, QMenu, QMessageBox, QPushButton, QApplication,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QScrollArea
)
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtCore import Qt, QSize
from services.medication import get_user_medications, get_medications_for_management
from services.user import get_user_id, get_user_profile
from ui.dialog_windows import ( ProfileWindow, AnalyticsWindow, ExportDialog, MedicationReportDialog, SettingsWindow, 
    MedicationHistoryDialog 
)
from ui.tracking_screen import DosageTrackingScreen
from ui.manage_medication import ManageMedicationScreen


class MainWindow(QMainWindow):
    """
    Main application window shown after successful login.

    Features:
    - Menu bar with File, Options, and Tools
    - Toolbar with quick actions
    - Dashboard with charts and quick action panel
    """

    def __init__(self, username: str = "User"):
        """
        Initialize the main dashboard window.

        Args:
            username: Username of the currently logged-in user
        """
        super().__init__()
        self.tracking_widget = None
        self.date_panel_btn = None
        self.current_user = username
        self.current_user_id = get_user_id(username)
        self.is_large_print = False
        self.setWindowTitle(f"MedRec 1.0.0 Dashboard - {username}")
        self.resize(1350, 850)

        # self.setup_menu_bar()
        self.setup_toolbar()
        self.setup_central_widget()

    def setup_menu_bar(self) -> None:
        """Menu bar with File / Options / Tools (unchanged)."""
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        file_menu.addAction(QAction("New Project...", self))
        file_menu.addAction(QAction("Open...", self))
        file_menu.addAction(QAction("Save", self))
        file_menu.addSeparator()
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        options_menu = menubar.addMenu("&Options")
        options_menu.addAction(QAction("Preferences...", self))

        tools_menu = menubar.addMenu("&Tools")
        tools_menu.addAction(QAction("Data Analyzer", self))
        tools_menu.addAction(QAction("Export Report", self))

    def setup_toolbar(self) -> None:
        """Toolbar with accessibility toggle."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(26, 26))
        self.addToolBar(toolbar)

        # Accesbility Toggle
        self.access_act = QAction("👓 Large Print", self)
        self.access_act.setCheckable(True)  # Makes it act like an on/off switch
        self.access_act.triggered.connect(self.toggle_accessibility_font)
        toolbar.addAction(self.access_act)

    def launch_dosage_tracker(self, user_id):
        # Pass the setup_central_widget function so the tracking screen can return to the dashboard
        self.tracking_widget = DosageTrackingScreen(user_id, go_back_callback=self.setup_central_widget)
        self.setCentralWidget(self.tracking_widget)

    def launch_manage_medication(self):
        """Opens Manage Medication Screen"""
        self.manage_medication_widget = ManageMedicationScreen(self.current_user_id, go_back_callback=self.setup_central_widget)
        # Scroll area when the window isn't maximized (no bottom cutoff)
        scroll = QScrollArea()
        scroll.setWidget(self.manage_medication_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.setCentralWidget(scroll)
        self._load_medications_into_table()

    def setup_central_widget(self) -> None:
        """Central area with charts and quick actions."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Quick Actions
        left = self.create_left_panel()
        splitter.addWidget(left)

        # Center: Charts
        center = self.create_charts_panel()
        splitter.addWidget(center)

        splitter.setSizes([300, 1000])
        main_layout.addWidget(splitter)

        self.statusBar().showMessage(f"✅ Logged in as {self.current_user} | Dashboard ready")

    def create_left_panel(self) -> QFrame:
        """Quick action buttons with requested functionality."""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.addWidget(QLabel("<h3>🚀 Quick Actions</h3>"))

        # Medication management button
        manage_med_btn = QPushButton("➕ Add/Manage Medication")
        manage_med_btn.setStyleSheet("padding: 14px; text-align: left;")
        manage_med_btn.clicked.connect(self.launch_manage_medication)
        layout.addWidget(manage_med_btn)

        # Dosage Tracker
        track_btn = QPushButton("💊 Daily Dosage Tracker")
        track_btn.setStyleSheet("padding: 14px; text-align: left;")
        track_btn.clicked.connect(lambda: self.launch_dosage_tracker(self.current_user_id))
        layout.addWidget(track_btn)

        # Generate Report
        report_btn = QPushButton("📄 Generate Report")
        report_btn.clicked.connect(self.generate_medication_report)
        report_btn.setStyleSheet("padding: 14px; text-align: left;")
        layout.addWidget(report_btn)

        # View Analytics – placeholder
        # analytics_btn = QPushButton("📈 View Analytics")
        # analytics_btn.setStyleSheet("padding: 14px; text-align: left;")
        # layout.addWidget(analytics_btn)

        # View History Log
        history_btn = QPushButton("🔍 View History Log")
        history_btn.clicked.connect(self.show_history)
        history_btn.setStyleSheet("padding: 14px; text-align: left;")
        layout.addWidget(history_btn)

        # Settings
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.clicked.connect(self.show_settings)
        settings_btn.setStyleSheet("padding: 14px; text-align: left;")
        layout.addWidget(settings_btn)
        
        layout.addStretch()
        return frame

    def create_charts_panel(self) -> QWidget:
        """Create the center panel showing the user's current medication list."""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header row: title
        header_row = QHBoxLayout()
        title = QLabel("<h2>Current Medications</h2>")
        header_row.addWidget(title)
        layout.addLayout(header_row)

        # Table
        self.med_table = QTableWidget()
        self.med_table.setColumnCount(6)
        self.med_table.setHorizontalHeaderLabels(
            ["Medication Name", "Dosage", "Route", "Frequency", "Scheduled Time", "Prescriber"]
        )
        self.med_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.med_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.med_table.setAlternatingRowColors(True)
        header = self.med_table.horizontalHeader()
        for col in range(6):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.med_table)

        self._load_medications_into_table()

        return frame

    def _load_medications_into_table(self) -> None:
        """Fetch medications from DB and populate self.med_table."""
        meds = get_medications_for_management(self.current_user_id)
        self.med_table.setRowCount(0)

        if not meds:
            self.med_table.setRowCount(1)
            placeholder = QTableWidgetItem("No medications found.")
            placeholder.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.med_table.setItem(0, 0, placeholder)
            self.med_table.setSpan(0, 0, 1, 6)
            self.statusBar().showMessage("No medications on record.")
            return

        self.med_table.setRowCount(len(meds))
        columns = ["name", "dosage", "route", "frequency", "scheduled_time", "prescriber"]
        for row, med in enumerate(meds):
            for col, key in enumerate(columns):
                value = med.get(key) or ""
                self.med_table.setItem(row, col, QTableWidgetItem(str(value)))

        self.statusBar().showMessage(
            f"✅ {len(meds)} medication(s) loaded for {self.current_user}"
        )

    # ==================== FUNCTIONAL BUTTONS ====================

    def refresh_data(self):
        """Refresh user data from SQLite."""
        profile = get_user_profile(self.current_user)
        meds = get_user_medications(self.current_user)
        self.statusBar().showMessage(f"✅ Refreshed – {len(meds)} medications loaded for {self.current_user}")
        QMessageBox.information(self, "Refresh Complete",
                                "User profile and medication data have been reloaded from the database.")

    def show_profile(self):
        """Open Profile window."""
        profile = get_user_profile(self.current_user)
        if profile:
            win = ProfileWindow(profile, self)
            win.exec()
        else:
            QMessageBox.warning(self, "Error", "Could not load profile.")

    def show_analytics(self):
        """Open Analytics window."""
        meds = get_user_medications(self.current_user)
        win = AnalyticsWindow(meds, self)
        win.exec()

    def toggle_accessibility_font(self):
        """Toggles global application font for accessibility."""
        app = QApplication.instance()

        if self.is_large_print:
            # Revert to standard font
            app.setFont(QFont("Segoe UI", 10))

            # Clear the global stylesheet override
            app.setStyleSheet("")

            self.is_large_print = False
            self.access_act.setChecked(False)  # Unpress the toolbar button
            self.statusBar().showMessage("Accessibility: Standard Print Enabled")
        else:
            # Apply accessible large print
            app.setFont(QFont("Arial", 18))

            # FORCE override all hardcoded widget font-sizes with a global wildcard
            app.setStyleSheet("* { font-size: 18pt; }")

            self.is_large_print = True
            self.access_act.setChecked(True)  # Press the toolbar button in
            self.statusBar().showMessage("Accessibility: Large Print Enabled")

        # Janky fix: QTableWidget can lag behind global font/stylesheet on fast Large Print toggles
        # so reload the manage meds table forces rows to match current app style
        central = self.centralWidget()
        inner = central.widget() if central is not None and isinstance(central, QScrollArea) else None
        if inner is not None and hasattr(inner, "reload_list"):
            inner.reload_list()

    def show_export(self):
        """Open Export dialog."""
        profile = get_user_profile(self.current_user)
        meds = get_user_medications(self.current_user)
        if profile:
            dlg = ExportDialog(self.current_user, profile, meds, self)
            dlg.exec()
        else:
            QMessageBox.warning(self, "Error", "Could not load data for export.")

    def generate_medication_report(self):
        """Open Generate Report dialog (PDF)."""
        
        # Check if they have medications first
        meds = get_medications_for_management(self.current_user_id)
        if not meds:
            QMessageBox.information(
                self, 
                "No Medications", 
                "No medication records found for this user. Nothing to report!"
            )
            return
        
        dlg = MedicationReportDialog(self.current_user_id, self.current_user, self)
        dlg.exec()

    def show_settings(self):
        """Open Webcam Settings window."""
        win = SettingsWindow(self)
        win.exec()
    
    def show_history(self):
        """Open the interactive History Viewer."""
        dlg = MedicationHistoryDialog(self.current_user_id, self)
        dlg.exec()