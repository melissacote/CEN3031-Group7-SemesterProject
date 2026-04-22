# UI screen for tracking today's dosages

from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QMessageBox
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from services.medication import get_todays_medications_sorted
from services.administration_log import log_medication_taken, undo_medication_taken


class DosageTrackingScreen(QWidget):
    """
    Daily dosage tracker.

    Displays only the medications due on today's date, respecting each
    medication's frequency interval (daily, every N days, weekly, etc.)
    and course duration (start / end dates).

    Multi-dose medications (e.g. twice daily) show a "X/Y doses" counter
    and allow the patient to log each individual dose separately.
    """

    def __init__(self, user_id, go_back_callback=None):
        super().__init__()

        self.user_id = user_id
        self.go_back_callback = go_back_callback
        self.timing_buckets = ("Morning", "Midday", "Afternoon", "Evening", "Bedtime")
        self.large_font = QFont("Arial", 16)
        self.setFont(self.large_font)

        self.layout = QVBoxLayout()

        self.back_btn = QPushButton("← Back to Dashboard")
        self.back_btn.setMinimumHeight(40)
        self.back_btn.setStyleSheet(
            "background-color: #7f8c8d; color: white; border-radius: 5px; font-weight: bold;"
        )
        self.back_btn.clicked.connect(self.handle_back)
        self.layout.addWidget(self.back_btn)

        today_str = datetime.now().strftime("%A, %B %d, %Y")
        self.title_label = QLabel(f"Today's Dosage Tracker — {today_str}")
        self.title_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.layout.addWidget(self.title_label)

        self.tracking_list = QListWidget()

        self.mark_taken_btn = QPushButton("Mark Selected as Taken")
        self.mark_taken_btn.setMinimumHeight(50)
        self.mark_taken_btn.setStyleSheet(
            "background-color: #005A9C; color: white; border-radius: 5px;"
        )
        self.mark_taken_btn.clicked.connect(self.mark_as_taken)

        self.undo_btn = QPushButton("Undo (Mark as Untaken)")
        self.undo_btn.setMinimumHeight(50)
        self.undo_btn.setStyleSheet(
            "background-color: #FF9800; color: white; border-radius: 5px;"
        )
        self.undo_btn.clicked.connect(self.undo_taken)

        self.layout.addWidget(self.tracking_list)
        self.layout.addWidget(self.mark_taken_btn)
        self.layout.addWidget(self.undo_btn)

        self.setLayout(self.layout)
        self.load_medications()

    def handle_back(self):
        if self.go_back_callback:
            self.go_back_callback()

    def split_meds_by_timing_bucket(self, meds):
        """Splits today's meds into timing buckets for display"""
        # Each bucket name and list of meds under that heading (excluding unstandardized entries)
        buckets = {name: [] for name in self.timing_buckets}
        unscheduled = []

        # Put each med into every timing bucket it's assigned to
        for med in meds:
            med_id, name, dosage, scheduled_time, doses_per_day, times_taken, notes = med

            has_standard_time = False
            for time in scheduled_time.split(","):
                if time in buckets:
                    buckets[time].append(med)
                    has_standard_time = True

            # No time selected / old med / test entry
            if not has_standard_time:
                unscheduled.append(med)

        return buckets, unscheduled


    def load_medications(self):
        self.tracking_list.clear()

        meds = get_todays_medications_sorted(self.user_id)

        if not meds:
            self.tracking_list.addItem("No medications scheduled for today.")
            return

        buckets, unscheduled = self.split_meds_by_timing_bucket(meds)

        # Build the headings by time bucket 
        time_headings = []
        for time_bucket in self.timing_buckets:
            if buckets[time_bucket]:
                time_headings.append((time_bucket, buckets[time_bucket]))

        # For meds without a standardized time entry
        if unscheduled:
            time_headings.append(("Unscheduled", unscheduled))

        # Create the heading items for each time bucket
        for time_header, meds_in_heading in time_headings:
            time_heading_item = QListWidgetItem(time_header)
            time_heading_item.setFlags(Qt.ItemFlag.NoItemFlags)
            time_heading_item.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            self.tracking_list.addItem(time_heading_item)
    
            for med in meds_in_heading:
                med_id, name, dosage, scheduled_time, doses_per_day, times_taken, notes = med

                notes_display = f" | {notes}" if notes else ""
                all_taken = times_taken >= doses_per_day
                dose_counter = f" [{times_taken}/{doses_per_day} doses]" if doses_per_day > 1 else ""

                if all_taken:
                    display_text = (
                        f"{name} ({dosage}){notes_display}{dose_counter} ✅"
                    )
                else:
                    display_text = (
                        f"{name} ({dosage}){notes_display}{dose_counter}"
                    )

                self.tracking_list.addItem(display_text)

                # Store scheduling data so the action buttons know what to act on
                self.tracking_list.item(self.tracking_list.count() - 1).setData(
                    32,
                    {
                        "med_id":        med_id,
                        "doses_per_day": doses_per_day,
                        "times_taken":   times_taken,
                    },
                )

            # Spacer between headings
            spacer = QListWidgetItem()
            spacer.setFlags(Qt.ItemFlag.NoItemFlags)
            self.tracking_list.addItem(spacer)

    def mark_as_taken(self):
        selected_item = self.tracking_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Selection Error",
                                "Please click a medication first.")
            return

        data = selected_item.data(32)
        if data["times_taken"] >= data["doses_per_day"]:
            label = "dose" if data["doses_per_day"] == 1 else "all doses"
            QMessageBox.information(self, "Already Taken",
                                    f"You have already logged {label} for today.")
            return

        log_medication_taken(self.user_id, data["med_id"])
        self.load_medications()
        QMessageBox.information(self, "Success", "Dose logged successfully.")

    def undo_taken(self):
        selected_item = self.tracking_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Selection Error",
                                "Please click a medication first.")
            return

        data = selected_item.data(32)
        success = undo_medication_taken(self.user_id, data["med_id"])

        if success:
            self.load_medications()
            QMessageBox.information(self, "Undo Success", "Last dose entry removed.")
        else:
            QMessageBox.warning(self, "Undo Failed",
                                "No dose record found to undo for today.")