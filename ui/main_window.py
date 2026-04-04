# main_window.py
"""
Main dashboard window for the PyQt6 application.

Displays menu bar, toolbar, quick action buttons, and interactive matplotlib charts.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QFrame, QLabel,
    QToolBar, QMenuBar, QMenu, QMessageBox, QPushButton, QApplication
)
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtCore import Qt, QSize
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import numpy as np

from services.medication import get_user_medications
from services.user import get_user_id, get_user_profile
from ui.dialog_windows import ProfileWindow, AnalyticsWindow, ExportDialog, MedicationReportDialog, SettingsWindow, AddMedicationDialog
from ui.tracking_screen import DosageTrackingScreen


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
        self.access_act.setCheckable(True) # Makes it act like an on/off switch
        self.access_act.triggered.connect(self.toggle_accessibility_font)
        toolbar.addAction(self.access_act)

    def launch_dosage_tracker(self, user_id):
        # Pass the setup_central_widget function so the tracking screen can return to the dashboard
        self.tracking_widget = DosageTrackingScreen(user_id, go_back_callback=self.setup_central_widget)
        self.setCentralWidget(self.tracking_widget)

    def open_add_medication_dialog(self):
        # Opens the add medication dialog from the dashboard button interaction
        dialog = AddMedicationDialog(self.current_user_id, self)
        dialog.exec()

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
        add_med_btn = QPushButton("➕ Add Medication")
        add_med_btn.setStyleSheet("padding: 14px; text-align: left;")
        add_med_btn.clicked.connect(self.open_add_medication_dialog)
        layout.addWidget(add_med_btn)

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

        # Settings
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.clicked.connect(self.show_settings)
        settings_btn.setStyleSheet("padding: 14px; text-align: left;")
        layout.addWidget(settings_btn)

        layout.addStretch()
        return frame

    def create_charts_panel(self) -> QWidget:
        """Create the center panel containing matplotlib charts."""

        # NOTE: THIS FUNCTION CAN BE IMPROVED/MODIFIED TO SUIT OUR NEEDS, IT IS JUST AN EXAMPLE OF WHAT WE CAN DO.
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Line Chart - Default tracker
        fig1 = plt.Figure(figsize=(10, 5), dpi=100)
        canvas1 = FigureCanvas(fig1)
        ax1 = fig1.add_subplot(111)
        x = np.linspace(0, 12, 100)

        # TODO: This is hard-coded for now, we need to implement smart logic to data requirements
        ax1.plot(x, np.sin(x), label="Medcation 1", color="#27ae60", linewidth=3)
        ax1.plot(x, np.cos(x), label="Medication 2", color="#e74c3c", linewidth=3)
        ax1.set_title("1 Year Medication Intake Tracker", fontsize=14, fontweight="bold")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        layout.addWidget(canvas1)

        # Bar Chart - Missed medication tracker
        fig2 = plt.Figure(figsize=(10, 5), dpi=100)
        canvas2 = FigureCanvas(fig2)
        ax2 = fig2.add_subplot(111)

        #TODO: This is hard-coded for now, we need to implement smart logic to handle each medication the user is taking
        quarters = ["Med1", "Med2", "Med3", "Med4"]
        values = [23, 10, 57, 16]
        ax2.bar(quarters, values, color=["#3498db", "#2ecc71", "#f1c40f", "#e67e22"])
        ax2.set_title("Number of Missed Days", fontsize=14, fontweight="bold")
        ax2.set_ylim(0, 110)
        ax2.grid(True, alpha=0.3)
        layout.addWidget(canvas2)

        return widget

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
            self.access_act.setChecked(False) # Unpress the toolbar button
            self.statusBar().showMessage("Accessibility: Standard Print Enabled")
        else:
            # Apply accessible large print
            app.setFont(QFont("Arial", 18))
            
            # FORCE override all hardcoded widget font-sizes with a global wildcard
            app.setStyleSheet("* { font-size: 18pt; }") 
            
            self.is_large_print = True
            self.access_act.setChecked(True) # Press the toolbar button in
            self.statusBar().showMessage("Accessibility: Large Print Enabled")

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
        meds = get_user_medications(self.current_user)
        if meds:
            dlg = MedicationReportDialog(self.current_user, meds, self)
            dlg.exec()
        else:
            QMessageBox.information(self, "No Medications", "No medication records found for this user.")

    def show_settings(self):
        """Open Webcam Settings window."""
        win = SettingsWindow(self)
        win.exec()