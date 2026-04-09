# UI screen for tracking today's dosages

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QMessageBox
from PyQt6.QtGui import QFont

from services.medication import get_todays_medications_sorted
from services.administration_log import log_medication_taken, undo_medication_taken


# Added by NC: This is the UI screen for tracking today's dosages. It will call the query to load the medications from
# the database and display them in a list. The "Mark as Taken" button is just a placeholder to show how you can interact
# with the selected medication item and its associated database ID.

class DosageTrackingScreen(QWidget):
    """
    Class object for the dosage tracking screen.

    Params
    ------
        QWidget (type): Qt widget

    Returns
    -------
        None
    """

    def __init__(self, user_id, go_back_callback=None):
        # Call init function of parent class
        super().__init__()

        self.user_id = user_id
        self.go_back_callback = go_back_callback
        self.large_font = QFont("Arial", 16)
        self.setFont(self.large_font)

        self.layout = QVBoxLayout()

        self.back_btn = QPushButton("← Back to Dashboard")
        self.back_btn.setMinimumHeight(40)
        self.back_btn.setStyleSheet("background-color: #7f8c8d; color: white; border-radius: 5px; font-weight: bold;")
        self.back_btn.clicked.connect(self.handle_back)
        self.layout.addWidget(self.back_btn)

        self.title_label = QLabel("Today's Dosage Tracker")
        self.title_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))

        self.tracking_list = QListWidget()

        self.mark_taken_btn = QPushButton("Mark Selected as Taken")
        self.mark_taken_btn.setMinimumHeight(50)
        self.mark_taken_btn.setStyleSheet("background-color: #005A9C; color: white; border-radius: 5px;")

        # Connect the button click to a test popup
        self.mark_taken_btn.clicked.connect(self.mark_as_taken)
        self.undo_btn = QPushButton("Undo (Mark as Untaken)")
        self.undo_btn.setMinimumHeight(50)
        self.undo_btn.setStyleSheet("background-color: #FF9800; color: white; border-radius: 5px;")
        self.undo_btn.clicked.connect(self.undo_taken)

        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.tracking_list)
        self.layout.addWidget(self.mark_taken_btn)
        self.layout.addWidget(self.undo_btn)

        self.setLayout(self.layout)

        self.load_medications()
    
    def handle_back(self):
        # Triggers the callback to return to the main dashboard.
        if self.go_back_callback:
            self.go_back_callback()

    def load_medications(self):
        self.tracking_list.clear()

        meds = get_todays_medications_sorted(self.user_id)

        if not meds:
            self.tracking_list.addItem("No medications scheduled for today.")
            return

        for med in meds:
            med_id, name, dosage, time, is_taken = med
            # The UI accurately reflects the database state!
            if is_taken == 1:
                display_text = f"{time} - {name} ({dosage}) ✅"
            else:
                display_text = f"{time} - {name} ({dosage})"

            # Add it to the visual UI list
            self.tracking_list.addItem(display_text)

            # Secretly store the database ID inside the UI item so the "Mark Taken" button knows which one is clicked
            self.tracking_list.item(self.tracking_list.count() - 1).setData(32, med_id)

    def mark_as_taken(self):
        selected_item = self.tracking_list.currentItem()
        if selected_item:
            if "✅" in selected_item.text():
                QMessageBox.information(self, "Already Taken", "This medication is already marked as taken.")
                return

            med_id = selected_item.data(32)
            log_medication_taken(self.user_id, med_id)

            # True Database Synchronization
            # Instead of manually hacking the text, force the UI to reload fresh from the database
            self.load_medications() 
            QMessageBox.information(self, "Success", "Medication logged successfully.")
        else:
            QMessageBox.warning(self, "Selection Error", "Please click a medication first.")

    def undo_taken(self):
        selected_item = self.tracking_list.currentItem()
        if selected_item:
            med_id = selected_item.data(32)
            success = undo_medication_taken(self.user_id, med_id)

            if success:
                # True Database Synchronization
                self.load_medications() # Refresh UI from database
                QMessageBox.information(self, "Undo Success", "Medication administration undone.")
            else:
                QMessageBox.warning(self, "Undo Failed", "No record found to undo for today.")
        else:
            QMessageBox.warning(self, "Selection Error", "Please click a medication first.")
