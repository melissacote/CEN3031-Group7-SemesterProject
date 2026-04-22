from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QComboBox, QFormLayout, QLineEdit, QHeaderView, QHBoxLayout,
    QCheckBox, QSpinBox, QDateEdit, QDialog
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QFont

from ui.scanner_window import OCRScannerDialog
from services.medication import (
    add_medication,
    get_medications_for_management,
    update_medication,
    check_duplicate_medication,
    deactivate_medication,
)

# NOTE: strength = dosage, directions = route, timing buckets = scheduled_time (csv text).

# Maps OCR-returned frequency strings to (interval_days, doses_per_day)
_OCR_FREQ_TO_SCHEDULE = {
    "Once daily":         (1,  1),
    "Twice daily":        (1,  2),
    "Three times daily":  (1,  3),
    "Four times daily":   (1,  4),
    "Every other day":    (2,  1),
    "Weekly":             (7,  1),
    "Once weekly":        (7,  1),
    "Every other day":    (2,  1),
}


def _days_to_ui(days: int) -> tuple[int, str]:
    """Convert a DB interval (always in days) to (n, unit) for the UI spinbox/dropdown."""
    if days >= 7 and days % 7 == 0:
        return days // 7, "week(s)"
    return days, "day(s)"


def _build_frequency_label(interval_days: int, doses_per_day: int) -> str:
    """Build a human-readable frequency string to store in the DB `frequency` column."""
    dose_word = {1: "Once", 2: "Twice", 3: "Three times", 4: "Four times"}.get(
        doses_per_day, f"{doses_per_day}x"
    )
    if interval_days == 1:
        return f"{dose_word} daily"
    elif interval_days == 2:
        return f"{dose_word} every other day"
    elif interval_days % 7 == 0:
        weeks = interval_days // 7
        period = "weekly" if weeks == 1 else f"every {weeks} weeks"
        return f"{dose_word} {period}"
    else:
        return f"{dose_word} every {interval_days} days"


class ManageMedicationScreen(QWidget):
    """
    Screen for adding and editing medications.

    Replaces the old fixed-dropdown frequency model with a flexible
    interval + duration system so patients can accurately represent
    schedules like "every 5 days for 10 months" or "twice daily for 10 days".
    """

    def __init__(self, user_id: int, go_back_callback=None):
        super().__init__()
        self.user_id = user_id
        self.go_back_callback = go_back_callback
        self.editing_medication_id = None
        self.meds = []

        self.timing_options = ["Morning", "Midday", "Afternoon", "Evening", "Bedtime"]

        self.layout = QVBoxLayout(self)

        # Back button
        self.back_btn = QPushButton("← Back to Dashboard")
        self.back_btn.setMinimumHeight(40)
        self.back_btn.setStyleSheet(
            "background-color: #7f8c8d; color: white; border-radius: 5px;"
            " font-weight: bold; padding: 10px 18px;"
        )
        self.back_btn.clicked.connect(self.handle_back)
        self.layout.addWidget(self.back_btn)

        self.title_label = QLabel("Manage Medications")
        self.title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.layout.addWidget(self.title_label)

        self.form_title = QLabel("Add New Medication")
        self.form_title.setStyleSheet("font-weight: bold; color: #384e63;")
        self.layout.addWidget(self.form_title)

        self.warning_label = QLabel(
            "⚠️ Please verify all scanned instructions against the physical bottle."
        )
        self.warning_label.setStyleSheet(
            "color: #d35400; font-weight: bold; font-size: 12px;"
        )
        self.layout.addWidget(self.warning_label)

        # ── Form fields ──────────────────────────────────────────────────────
        self.form = QFormLayout()

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("e.g. Prednisone")

        self.input_strength = QLineEdit()
        self.input_strength.setPlaceholderText("e.g. 50mg, 5mg/5ml")

        self.input_directions = QLineEdit()
        self.input_directions.setPlaceholderText("e.g. Take 1 tablet daily at bedtime")

        self.input_notes = QLineEdit()
        self.input_notes.setPlaceholderText("e.g. Take with food, avoid grapefruit")

        self.form.addRow("Medication name:", self.input_name)
        self.form.addRow("Strength:", self.input_strength)
        self.form.addRow("Directions:", self.input_directions)
        self.form.addRow("Notes:", self.input_notes)

        # ── Frequency row: "Every [N] [day(s)/week(s)], [N] time(s) per dose day" ──
        freq_row = QHBoxLayout()
        freq_row.setSpacing(6)

        freq_row.addWidget(QLabel("Every"))

        self.input_interval = QSpinBox()
        self.input_interval.setRange(1, 365)
        self.input_interval.setValue(1)
        self.input_interval.setFixedWidth(60)
        freq_row.addWidget(self.input_interval)

        self.input_unit = QComboBox()
        self.input_unit.addItems(["day(s)", "week(s)"])
        self.input_unit.setFixedWidth(90)
        freq_row.addWidget(self.input_unit)

        freq_row.addWidget(QLabel(","))

        self.input_doses_per_day = QSpinBox()
        self.input_doses_per_day.setRange(1, 10)
        self.input_doses_per_day.setValue(1)
        self.input_doses_per_day.setFixedWidth(55)
        freq_row.addWidget(self.input_doses_per_day)

        freq_row.addWidget(QLabel("time(s) per dose day"))
        freq_row.addStretch()

        self.form.addRow("Frequency:", freq_row)

        # ── Duration row: start date + optional end date ──────────────────────
        duration_row = QHBoxLayout()
        duration_row.setSpacing(8)

        duration_row.addWidget(QLabel("Start:"))
        self.input_start_date = QDateEdit(QDate.currentDate())
        self.input_start_date.setCalendarPopup(True)
        self.input_start_date.setDisplayFormat("yyyy-MM-dd")
        duration_row.addWidget(self.input_start_date)

        duration_row.addWidget(QLabel("  End:"))
        self.input_end_date = QDateEdit(QDate.currentDate().addDays(30))
        self.input_end_date.setCalendarPopup(True)
        self.input_end_date.setDisplayFormat("yyyy-MM-dd")
        self.input_end_date.setEnabled(False)  # disabled while "Ongoing" is checked
        duration_row.addWidget(self.input_end_date)

        self.cb_ongoing = QCheckBox("Ongoing (no end date)")
        self.cb_ongoing.setChecked(True)
        self.cb_ongoing.toggled.connect(self._toggle_end_date)
        duration_row.addWidget(self.cb_ongoing)

        duration_row.addStretch()
        self.form.addRow("Duration:", duration_row)

        self.layout.addLayout(self.form)

        # ── Timing checkboxes ─────────────────────────────────────────────────
        timing_row = QHBoxLayout()
        timing_row.addWidget(QLabel("Timing:"))
        self.timing_checkboxes = {}
        for option in self.timing_options:
            cb = QCheckBox(option)
            self.timing_checkboxes[option] = cb
            timing_row.addWidget(cb)
        timing_row.addStretch()
        self.layout.addLayout(timing_row)

        # ── Action buttons ────────────────────────────────────────────────────
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(10)

        self.scan_btn = QPushButton("📸 Auto-fill with Webcam")
        self.scan_btn.setMinimumHeight(40)
        self.scan_btn.setStyleSheet(
            "background-color: #f39c12; color: white; border-radius: 5px;"
            " font-weight: bold; padding: 10px 18px;"
        )
        self.scan_btn.clicked.connect(self.open_scanner)
        self.button_layout.addWidget(self.scan_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setStyleSheet(
            "background-color: #27ab5f; color: white; border-radius: 5px;"
            " font-weight: bold; padding: 10px 18px;"
        )
        self.save_btn.clicked.connect(self.on_save)
        self.button_layout.addWidget(self.save_btn)

        self.cancel_edit_btn = QPushButton("Cancel Edit")
        self.cancel_edit_btn.setMinimumHeight(40)
        self.cancel_edit_btn.setStyleSheet(
            "background-color: #828c8c; color: white; border-radius: 5px;"
            " font-weight: bold; padding: 10px 18px;"
        )
        self.cancel_edit_btn.clicked.connect(self.cancel_edit)
        self.cancel_edit_btn.hide()
        self.button_layout.addWidget(self.cancel_edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setMinimumHeight(40)
        self.delete_btn.setStyleSheet(
            "background-color: #e74c3c; color: white; border-radius: 5px;"
            " font-weight: bold; padding: 10px 18px;"
        )
        self.delete_btn.clicked.connect(self.on_delete)
        self.delete_btn.hide()
        self.button_layout.addWidget(self.delete_btn)

        self.button_layout.addStretch()
        self.layout.addLayout(self.button_layout)

        # ── Saved medications table (7 columns) ───────────────────────────────
        self.table_label = QLabel("Saved Medications")
        self.table_label.setStyleSheet("font-weight: bold; color: #384e63;")
        self.layout.addWidget(self.table_label)

        self.edit_instructions_label = QLabel(
            'To edit: select a medication below, then press "Edit Selected"'
        )
        self.edit_instructions_label.setWordWrap(True)
        self.layout.addWidget(self.edit_instructions_label)

        self.med_table = QTableWidget(0, 7)
        self.med_table.setHorizontalHeaderLabels(
            ["Name", "Strength", "Directions", "Frequency", "Timing", "Notes", "Duration"]
        )
        self.med_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.med_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.med_table.setAlternatingRowColors(True)
        self.med_table.setWordWrap(True)
        header = self.med_table.horizontalHeader()
        for col in range(7):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        self.layout.addWidget(self.med_table)

        edit_row = QHBoxLayout()
        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.setMinimumHeight(50)
        self.edit_btn.setStyleSheet(
            "background-color: #3097db; color: white; border-radius: 5px; padding: 10px 18px;"
        )
        self.edit_btn.clicked.connect(self.on_edit)
        edit_row.addWidget(self.edit_btn)
        edit_row.addStretch()
        self.layout.addLayout(edit_row)

        self.reload_list()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _toggle_end_date(self, ongoing: bool) -> None:
        """Enable or disable the end-date picker based on the Ongoing checkbox."""
        self.input_end_date.setEnabled(not ongoing)

    def _read_interval_days(self) -> int:
        """Convert the interval spinbox + unit dropdown to a day count."""
        n = self.input_interval.value()
        return n * 7 if self.input_unit.currentText() == "week(s)" else n

    # ── Scanner ───────────────────────────────────────────────────────────────

    def open_scanner(self):
        dlg = OCRScannerDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.autofill_form(dlg.scanned_data)

    def autofill_form(self, scanned_data: dict) -> None:
        """Populate form fields from OCR-parsed label data."""
        self.clear_form()

        if "medication_name" in scanned_data:
            self.input_name.setText(scanned_data["medication_name"])

        if "dosage" in scanned_data:
            self.input_strength.setText(scanned_data["dosage"])

        if "special_instructions" in scanned_data:
            self.input_directions.setText(scanned_data["special_instructions"])
        elif "route" in scanned_data:
            self.input_directions.setText(scanned_data["route"])

        # Map OCR frequency string to interval + doses_per_day
        if "frequency" in scanned_data:
            interval_days, doses = _OCR_FREQ_TO_SCHEDULE.get(
                scanned_data["frequency"], (1, 1)
            )
            n, unit = _days_to_ui(interval_days)
            self.input_interval.setValue(n)
            self.input_unit.setCurrentIndex(self.input_unit.findText(unit))
            self.input_doses_per_day.setValue(doses)

        if "scheduled_time" in scanned_data:
            time_val = scanned_data["scheduled_time"]
            for option, cb in self.timing_checkboxes.items():
                if option.lower() in time_val.lower():
                    cb.setChecked(True)

    # ── CRUD operations ───────────────────────────────────────────────────────

    def on_save(self) -> None:
        """Validate fields and persist a new or updated medication record."""
        medication_name = self.input_name.text().strip()
        strength       = self.input_strength.text().strip()
        directions     = self.input_directions.text().strip()
        notes          = self.input_notes.text().strip()

        time_selected = [t for t in self.timing_options if self.timing_checkboxes[t].isChecked()]
        timing = ",".join(time_selected)

        if not medication_name or not strength or not directions:
            QMessageBox.warning(self, "⚠️ Missing info",
                                "Enter medication name, strength, and directions.")
            return

        interval_days  = self._read_interval_days()
        doses_per_day  = self.input_doses_per_day.value()
        frequency_label = _build_frequency_label(interval_days, doses_per_day)
        start_date     = self.input_start_date.date().toString("yyyy-MM-dd")
        end_date       = (
            None if self.cb_ongoing.isChecked()
            else self.input_end_date.date().toString("yyyy-MM-dd")
        )

        if self.editing_medication_id is None:
            if check_duplicate_medication(self.user_id, medication_name):
                reply = QMessageBox.warning(
                    self,
                    "Duplicate Medication",
                    f"A medication named '{medication_name}' is already active. "
                    "Add it anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            add_medication(
                self.user_id, medication_name, strength, directions,
                frequency_label, timing,
                special_instructions=notes,
                start_date=start_date,
                end_date=end_date,
                frequency_interval=interval_days,
                doses_per_day=doses_per_day,
            )

        else:
            update_medication(
                self.editing_medication_id,
                medication_name, strength, directions,
                frequency_label, timing, notes,
                start_date=start_date,
                end_date=end_date,
                frequency_interval=interval_days,
                doses_per_day=doses_per_day,
            )
            self.editing_medication_id = None
            self.form_title.setText("Add New Medication")
            self.save_btn.setText("Save")
            self.cancel_edit_btn.hide()
            self.delete_btn.hide()

        self.clear_form()
        self.reload_list()

    def on_edit(self) -> None:
        """Load the selected table row into the form for editing."""
        row = self.med_table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "⚠️ No Selection",
                                "Please click a medication row first.")
            return

        med = self.meds[row]
        self.editing_medication_id = med["medication_id"]
        self.input_name.setText(med["name"])
        self.input_strength.setText(med.get("dosage", ""))
        self.input_directions.setText(med.get("route", ""))
        self.input_notes.setText(med.get("special_instructions", ""))

        # Restore frequency controls from stored interval + doses_per_day
        interval_days = med.get("frequency_interval") or 1
        doses_per_day = med.get("doses_per_day") or 1
        n, unit = _days_to_ui(interval_days)
        self.input_interval.setValue(n)
        idx = self.input_unit.findText(unit)
        self.input_unit.setCurrentIndex(idx if idx >= 0 else 0)
        self.input_doses_per_day.setValue(doses_per_day)

        # Restore duration controls
        start_str = med.get("start_date")
        if start_str:
            self.input_start_date.setDate(QDate.fromString(start_str, "yyyy-MM-dd"))
        else:
            self.input_start_date.setDate(QDate.currentDate())

        end_str = med.get("end_date")
        if end_str:
            self.cb_ongoing.setChecked(False)
            self.input_end_date.setDate(QDate.fromString(end_str, "yyyy-MM-dd"))
        else:
            self.cb_ongoing.setChecked(True)

        # Restore timing checkboxes
        timing_str = med.get("scheduled_time", "") or ""
        selected_times = {t.strip() for t in timing_str.split(",")}
        for option, cb in self.timing_checkboxes.items():
            cb.setChecked(option in selected_times)

        self.form_title.setText("Edit Medication")
        self.save_btn.setText("Update")
        self.cancel_edit_btn.show()
        self.delete_btn.show()

    def on_delete(self) -> None:
        """Soft-delete the medication being edited."""
        if self.editing_medication_id is None:
            return

        reply = QMessageBox.warning(
            self,
            "Confirm Delete",
            f"Delete '{self.input_name.text()}'?\n\n"
            "It will be removed from your active list and daily tracker "
            "but preserved in historical reports.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            deactivate_medication(self.editing_medication_id)
            self.editing_medication_id = None
            self.form_title.setText("Add New Medication")
            self.save_btn.setText("Save")
            self.cancel_edit_btn.hide()
            self.delete_btn.hide()
            self.clear_form()
            self.reload_list()
            QMessageBox.information(self, "Deleted",
                                    "Medication successfully removed.")

    def cancel_edit(self) -> None:
        """Exit edit mode without saving."""
        self.editing_medication_id = None
        self.form_title.setText("Add New Medication")
        self.save_btn.setText("Save")
        self.cancel_edit_btn.hide()
        self.delete_btn.hide()
        self.clear_form()

    # ── Table ─────────────────────────────────────────────────────────────────

    def reload_list(self) -> None:
        """Refresh the table from the database."""
        self.med_table.setRowCount(0)
        self.meds = get_medications_for_management(self.user_id)
        self.med_table.setRowCount(len(self.meds))

        for row, med in enumerate(self.meds):
            raw_timing = med.get("scheduled_time") or ""
            ui_timing = ", ".join(p.strip() for p in raw_timing.split(",") if p.strip())

            start = med.get("start_date") or "—"
            end   = med.get("end_date") or "Ongoing"
            duration_str = f"{start} → {end}"

            self.med_table.setItem(row, 0, QTableWidgetItem(med["name"]))
            self.med_table.setItem(row, 1, QTableWidgetItem(med.get("dosage", "")))
            self.med_table.setItem(row, 2, QTableWidgetItem(med.get("route", "")))
            self.med_table.setItem(row, 3, QTableWidgetItem(med.get("frequency", "")))
            self.med_table.setItem(row, 4, QTableWidgetItem(ui_timing))
            self.med_table.setItem(row, 5, QTableWidgetItem(med.get("special_instructions", "")))
            self.med_table.setItem(row, 6, QTableWidgetItem(duration_str))

        for row in range(len(self.meds)):
            self.med_table.resizeRowToContents(row)

    def clear_form(self) -> None:
        """Reset all form inputs to their default state."""
        self.input_name.clear()
        self.input_strength.clear()
        self.input_directions.clear()
        self.input_notes.clear()
        self.input_interval.setValue(1)
        self.input_unit.setCurrentIndex(0)
        self.input_doses_per_day.setValue(1)
        self.input_start_date.setDate(QDate.currentDate())
        self.input_end_date.setDate(QDate.currentDate().addDays(30))
        self.cb_ongoing.setChecked(True)
        for cb in self.timing_checkboxes.values():
            cb.setChecked(False)

    def handle_back(self) -> None:
        if self.go_back_callback:
            self.go_back_callback()
