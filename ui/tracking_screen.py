# UI screen for tracking today's dosages
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QMessageBox
from PyQt6.QtGui import QFont

from services.medication import get_todays_medications_sorted, log_medication_taken, undo_medication_taken

# Added by NC: This is the UI screen for tracking today's dosages. It will call the query to load the medications from the database and display them in a list. The "Mark as Taken" button is just a placeholder to show how you can interact with the selected medication item and its associated database ID.
class DosageTrackingScreen(QWidget):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        
        self.large_font = QFont("Arial", 16)
        self.setFont(self.large_font)

        self.layout = QVBoxLayout()
        
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

    def load_medications(self):
        self.tracking_list.clear()
        
        # Execute the query you wrote in services/medication.py!
        meds = get_todays_medications_sorted(self.user_id)
        
        if not meds:
            self.tracking_list.addItem("No medications scheduled for today.")
            return

        for med in meds:
            med_id, name, dosage, time = med
            display_text = f"{time} - {name} ({dosage})"
            
            # Add it to the visual UI list
            self.tracking_list.addItem(display_text)
            
            # Secretly store the database ID inside the UI item so the "Mark Taken" button knows which one is clicked
            self.tracking_list.item(self.tracking_list.count()-1).setData(32, med_id)

    def mark_as_taken(self):
        selected_item = self.tracking_list.currentItem()
        if selected_item:
            # Prevent double-logging if it already has a checkmark
            if "test_checkmark" in selected_item.text():
                QMessageBox.information(self, "Already Taken", "This medication is already marked as taken.")
                return

            med_id = selected_item.data(32)
            log_medication_taken(self.user_id, med_id)
            
            # Add a visual checkmark instead of deleting the item
            selected_item.setText(selected_item.text() + " test_checkmark")
        else:
            QMessageBox.warning(self, "Selection Error", "Please click a medication first.")

    def undo_taken(self):
        selected_item = self.tracking_list.currentItem()
        if selected_item:
            med_id = selected_item.data(32)
            
            # Attempt to undo in the database
            success = undo_medication_taken(self.user_id, med_id)
            
            if success:
                # Remove the visual checkmark
                new_text = selected_item.text().replace(" test_checkmark", "")
                selected_item.setText(new_text)
                QMessageBox.information(self, "Undo Success", "Medication administration undone.")
            else:
                QMessageBox.warning(self, "Undo Failed", "No record found to undo for today.")
        else:
            QMessageBox.warning(self, "Selection Error", "Please click a medication first.")