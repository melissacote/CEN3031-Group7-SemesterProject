from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QComboBox, QFormLayout, QLineEdit, QHeaderView, QHBoxLayout, QCheckBox
)
from PyQt6.QtGui import QFont

from services.medication import add_medication, get_medications_for_management, update_medication

# NOTE: For now strength = dosage, directions = route, timing buckets = scheduled_time (csv text).
# Update this once schema refactor happens 

class ManageMedicationScreen(QWidget):
    """
    Class object for the medication management screen. 
    
    This screen allows user to add/edit medications and review saved medications in a table.
    
    Params
    ------
        QWidget (type): Qt widget
    
    Returns
    ------
        None
    """

    def __init__(self, user_id: int, go_back_callback=None):
        """
        Params
        ------
            user_id (int): Logged-in user's ID
            go_back_callback (callable | None): Callback to return to the dashboard
        """
        super().__init__()
        self.user_id = user_id
        self.go_back_callback = go_back_callback
        # None = add mode. Set to selected medication_id user chooses to edit
        self.editing_medication_id = None
        self.meds = []

        # Frequency and timing labels stored here. Update this list if options change
        self.frequency_options = ['Once daily', 'Twice daily', 'Three times daily', 'Four times daily', 'As needed', 'Every other day', 'Weekly']
        self.timing_options = ['Morning', 'Midday', 'Afternoon', 'Evening', 'Bedtime']

        # Main vertical layout for all widgets on this screen
        self.layout = QVBoxLayout(self)

        # Back button to exit screen (button design from tracking screen)
        self.back_btn = QPushButton("← Back to Dashboard")
        self.back_btn.setMinimumHeight(40)
        self.back_btn.setStyleSheet("background-color: #7f8c8d; color: white; border-radius: 5px; font-weight: bold; padding: 10px 18px;")
        self.back_btn.clicked.connect(self.handle_back)
        self.layout.addWidget(self.back_btn)

        # Title styling
        self.title_label = QLabel("Manage Medications")
        self.title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.layout.addWidget(self.title_label)

        # Form title styling
        self.form_title = QLabel("Add New Medication")
        self.form_title.setStyleSheet("font-weight: bold; color: #384e63;")
        self.layout.addWidget(self.form_title)

        # Form fields the user fills before pressing save
        self.form = QFormLayout()

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("e.g. Prednisone")

        self.input_strength = QLineEdit()
        self.input_strength.setPlaceholderText("e.g. 50mg, 5mg/5ml")

        self.input_directions = QLineEdit()
        self.input_directions.setPlaceholderText("e.g. Take 1 tablet daily at bedtime")

        self.input_frequency = QComboBox()
        self.input_frequency.addItems(self.frequency_options)

        self.form.addRow("Medication name:", self.input_name)
        self.form.addRow("Strength:", self.input_strength)
        self.form.addRow("Directions:", self.input_directions)
        self.form.addRow("Frequency:", self.input_frequency)

        self.layout.addLayout(self.form) # form field with text options

        # Timing checkboxes
        self.timing_layout = QHBoxLayout()
        self.timing_layout.addWidget(QLabel("Timing: "))
        self.timing_checkboxes = {}
        
        # Creates checkboxes from timing class var options 
        for option in self.timing_options:
            checkbox = QCheckBox(option)
            self.timing_checkboxes[option] = checkbox
            self.timing_layout.addWidget(checkbox)

        self.timing_layout.addStretch()
        self.layout.addLayout(self.timing_layout) # checkboxes added to form

        # Layout area for save and cancel edit buttons
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(10)

        # Save button to add the medication record to the database
        self.save_btn = QPushButton("Save")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setStyleSheet("background-color: #27ab5f; color: white; border-radius: 5px; font-weight: bold; padding: 10px 18px;")
        self.save_btn.clicked.connect(self.on_save)
        self.button_layout.addWidget(self.save_btn)

        # Cancel edit button that appears once user starts edit seleciton
        self.cancel_edit_btn = QPushButton("Cancel Edit")
        self.cancel_edit_btn.setMinimumHeight(40)
        self.cancel_edit_btn.setStyleSheet("background-color: #828c8c; color: white; border-radius: 5px; font-weight: bold; padding: 10px 18px;")
        self.cancel_edit_btn.clicked.connect(self.cancel_edit)
        self.cancel_edit_btn.hide()
        self.button_layout.addWidget(self.cancel_edit_btn)

        self.button_layout.addStretch()
        self.layout.addLayout(self.button_layout) # adding buttons to layout

        # Layout area for medications table with 5 columns
        self.med_table = QTableWidget(0, 5)

        # Heading for table
        self.table_label = QLabel("Saved Medications")
        self.table_label.setStyleSheet("font-weight: bold; color: #384e63;")
        self.layout.addWidget(self.table_label)

        # Help message to instruct users on how to edit their medication details
        self.edit_instructions_label = QLabel('To edit: select a medication below, then press "Edit Selected"')
        self.edit_instructions_label.setWordWrap(True)
        self.layout.addWidget(self.edit_instructions_label)

        # Table for display medications to edit (table design from main window)
        self.med_table.setHorizontalHeaderLabels(["Name", "Strength", "Directions", "Frequency", "Timing"])
        self.med_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.med_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.med_table.setAlternatingRowColors(True)
        self.med_table.setWordWrap(True)
        self.header = self.med_table.horizontalHeader()

        # Makes all columns resize to fill the table width
        for col in range(5):
            self.header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
    
        self.layout.addWidget(self.med_table) # adding table to layout

        # Horizontal row so "Edit Selected" stays button sized on the left. Without this, adding the
        # button straight to the vertical layout stretches it to the full window width.
        self.edit_row = QHBoxLayout()

        # Edit button for table
        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.setMinimumHeight(50)
        self.edit_btn.setStyleSheet("background-color: #3097db; color: white; border-radius: 5px; padding: 10px 18px;")
        self.edit_btn.clicked.connect(self.on_edit)

        self.edit_row.addWidget(self.edit_btn)
        self.edit_row.addStretch()
        self.layout.addLayout(self.edit_row)

        self.reload_list()

    def on_save(self):
        """Validates required fields before saving a new or existing medication record."""
        medication_name = self.input_name.text().strip()
        strength = self.input_strength.text().strip()
        directions = self.input_directions.text().strip()
        frequency = self.input_frequency.currentText()
        
        # NOTE: scheduled_time is stored as comma separated timing buckets for now (e.g. Morning,Evening)
        time_selected = [time for time in self.timing_options if self.timing_checkboxes[time].isChecked()]
        timing = ','.join(time_selected)

        # If missing required info prompt user with warning
        if not medication_name or not strength or not directions:
            QMessageBox.warning(self, "⚠️ Missing info", "Enter medication name, strength, and directions.")
            return

        # NOTE: add_medication/update_medication still take (dosage, route, scheduled_time) args
        # so strength/directions/timing vars are passed in those positions for now
        if self.editing_medication_id is None:
            add_medication(
                self.user_id,
                medication_name,
                strength,
                directions,
                frequency,
                timing
            )

        # If in editing mode update the selected medication
        else:
            update_medication(
                self.editing_medication_id,
                medication_name,
                strength,
                directions,
                frequency,
                timing
            )
        
            self.editing_medication_id = None
            self.form_title.setText("Add New Medication")
            self.save_btn.setText("Save")
            self.cancel_edit_btn.hide()

        # reset the screen and load db changes
        self.clear_form()
        self.reload_list()

    def on_edit(self):
        """Loads selected medication row into the form and switches screen to edit mode"""
        row = self.med_table.currentRow()
        # -1 means no row selected so prompt user with warning
        if row == -1:
            QMessageBox.warning(self, "⚠️ No Selection", "Please click a medication row first")
            return
        
        # Table row index lines up with self.meds after reload_list
        selected_med = self.meds[row]
        self.editing_medication_id = selected_med["medication_id"]
        self.input_name.setText(selected_med["name"])

        # NOTE: med["dosage"] = Strength field for now
        self.input_strength.setText(selected_med.get("dosage", ""))

        # NOTE: med["route"] = Directions field for now
        self.input_directions.setText(selected_med.get("route", ""))

        frequency = selected_med.get("frequency", "")
        freq_index = self.input_frequency.findText(frequency)

        # NOTE: If saved frequency text isn't in the dropdown list default to the first option
        # (older DB rows / non-dropdown values)
        if freq_index != -1:
            self.input_frequency.setCurrentIndex(freq_index)
        else:
            self.input_frequency.setCurrentIndex(0)

        # NOTE: scheduled_time is stored as comma separated timing buckets for now (e.g. Morning,Evening)
        # Check time boxes for selected medication
        timing_str = selected_med.get("scheduled_time", "")
        selected_times = [time.strip() for time in timing_str.split(",")] if timing_str else []
        for t_option in self.timing_options:
            self.timing_checkboxes[t_option].setChecked(t_option in selected_times)

        self.form_title.setText("Edit Medication")
        self.save_btn.setText("Update")
        self.cancel_edit_btn.show()

    def cancel_edit(self):
        """Cancel edit mode, reset form fields, and returns UI to add mode."""
        self.editing_medication_id = None
        self.form_title.setText("Add New Medication")
        self.save_btn.setText("Save")
        self.cancel_edit_btn.hide()
        self.clear_form()

    def reload_list(self):
        """Pull the latest rows from the DB and refresh table UI"""
        # Resets current table
        self.med_table.setRowCount(0)
        self.meds = get_medications_for_management(self.user_id)
        self.med_table.setRowCount(len(self.meds))

        # NOTE: table columns use current db keys (dosage/route/scheduled_time) until refactor
        for row, med in enumerate(self.meds):
            self.med_table.setItem(row, 0, QTableWidgetItem(med["name"]))
            self.med_table.setItem(row, 1, QTableWidgetItem(med.get("dosage", "")))
            self.med_table.setItem(row, 2, QTableWidgetItem(med.get("route", "")))
            self.med_table.setItem(row, 3, QTableWidgetItem(med.get("frequency", "")))
            # Add spaces between time entries for UI readability
            raw_timing = med.get("scheduled_time", "") or "" # None safe (e.g. DB NULL) since scheduled_time may be optional / nullable
            ui_timing = ", ".join(part.strip() for part in raw_timing.split(",") if part.strip())
            self.med_table.setItem(row, 4, QTableWidgetItem(ui_timing))

        for row in range(len(self.meds)):
            self.med_table.resizeRowToContents(row)

    def clear_form(self):
        """Clear the form fields."""
        self.input_name.clear()
        self.input_strength.clear()
        self.input_directions.clear()
        self.input_frequency.setCurrentIndex(0) # sets frequency back to first option
        
        # Uncheck checked timing boxes
        for checkbox in self.timing_checkboxes.values():
            checkbox.setChecked(False)

    def handle_back(self):
        """Triggers the callback to return to the main dashboard."""
        if self.go_back_callback:
            self.go_back_callback()
