# ui/date_panel.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QDateEdit, QCheckBox
from PyQt6.QtCore import QDate

class DateSelectionPanel(QWidget):
    """A reusable UI component for selecting date ranges."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10) 

        # Toggle Checkbox
        self.custom_date_checkbox = QCheckBox("Use Custom Date Range")
        self.custom_date_checkbox.toggled.connect(self.toggle_date_inputs)
        layout.addWidget(self.custom_date_checkbox)

        # Date Pickers Layout
        date_layout = QVBoxLayout() 
        
        # Start Date
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True) 
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30)) 
        self.start_date_edit.setEnabled(False) 
        date_layout.addWidget(QLabel("Start Date:"))
        date_layout.addWidget(self.start_date_edit)

        # End Date
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate()) 
        self.end_date_edit.setEnabled(False) 
        date_layout.addWidget(QLabel("End Date:"))
        date_layout.addWidget(self.end_date_edit)

        layout.addLayout(date_layout)

    def toggle_date_inputs(self, is_checked):
        """Enable or disable the date pickers based on the checkbox."""
        self.start_date_edit.setEnabled(is_checked)
        self.end_date_edit.setEnabled(is_checked)

    def get_selected_dates(self):
        """Returns the dates if checked, otherwise None."""
        if self.custom_date_checkbox.isChecked():
            start = self.start_date_edit.date().toString("yyyy-MM-dd")
            end = self.end_date_edit.date().toString("yyyy-MM-dd")
            return start, end
        return None, None