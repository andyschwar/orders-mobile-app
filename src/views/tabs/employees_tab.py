from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox,
    QDialog, QFormLayout, QDateEdit, QCheckBox, QLabel,
    QComboBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from models.database import Employee
from views.dialogs.employee_profile_dialog import EmployeeProfileDialog
from utils.permissions import get_permissions_manager

class EmployeeDialog(QDialog):
    def __init__(self, session: Session, employee=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.employee = employee
        self.setWindowTitle("Add Employee" if not employee else "Edit Employee")
        self.setModal(True)
        self.resize(700, 800)  # Make dialog wider and taller
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        
        # Create fields
        self.name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.address_input = QLineEdit()
        self.birthday_input = QDateEdit()
        self.birthday_input.setCalendarPopup(True)
        
        # Create name day input with custom display format
        self.nameday_input = QDateEdit()
        self.nameday_input.setCalendarPopup(True)
        self.nameday_input.setDisplayFormat("dd-MM")
        # Set a default date to avoid null values
        default_date = QDate.currentDate()
        self.nameday_input.setDate(default_date)
        
        self.is_active_input = QCheckBox()
        self.is_active_input.setChecked(True)
        
                # Add documents path field
        self.documents_path_input = QLineEdit()
        self.documents_path_input.setPlaceholderText("/Volumes/NAS/Employees/JohnDoe")
        browse_button = QPushButton("Browse")
        def browse():
            from PyQt6.QtWidgets import QFileDialog
            folder = QFileDialog.getExistingDirectory(self, "Select Documents Folder")
            if folder:
                self.documents_path_input.setText(folder)
        browse_button.clicked.connect(browse)
        doc_path_layout = QHBoxLayout()
        doc_path_layout.addWidget(self.documents_path_input)
        doc_path_layout.addWidget(browse_button)

        # Add employment fields
        self.employment_start_input = QDateEdit()
        self.employment_start_input.setCalendarPopup(True)
        self.employment_start_input.setDisplayFormat("yyyy-MM-dd")
        
        self.employment_end_input = QDateEdit()
        self.employment_end_input.setCalendarPopup(True)
        self.employment_end_input.setDisplayFormat("yyyy-MM-dd")
        self.employment_end_input.setDate(QDate.currentDate())
        
        # Add checkbox for indefinite employment
        self.indefinite_employment = QCheckBox("Indefinite")
        self.indefinite_employment.setChecked(True)
        
        def toggle_employment_end():
            self.employment_end_input.setEnabled(not self.indefinite_employment.isChecked())
        self.indefinite_employment.stateChanged.connect(toggle_employment_end)
        
        self.employment_type_input = QComboBox()
        self.employment_type_input.setMinimumWidth(180)  # Make dropdown wider
        self.employment_type_input.addItems([
            "Full-time Indefinite",
            "Part-time Indefinite", 
            "Full-time Fixed-term",
            "Part-time Fixed-term",
            "Temporary",
            "Contractor"
        ])
        
        # Add contract renewal date fields
        self.contract_renewal_1_input = QDateEdit()
        self.contract_renewal_1_input.setCalendarPopup(True)
        self.contract_renewal_1_input.setDisplayFormat("yyyy-MM-dd")
        self.contract_renewal_1_input.setDate(QDate.currentDate())
        
        self.contract_renewal_2_input = QDateEdit()
        self.contract_renewal_2_input.setCalendarPopup(True)
        self.contract_renewal_2_input.setDisplayFormat("yyyy-MM-dd")
        self.contract_renewal_2_input.setDate(QDate.currentDate())
        
        self.contract_renewal_3_input = QDateEdit()
        self.contract_renewal_3_input.setCalendarPopup(True)
        self.contract_renewal_3_input.setDisplayFormat("yyyy-MM-dd")
        self.contract_renewal_3_input.setDate(QDate.currentDate())
        
        self.last_contract_renewal_input = QDateEdit()
        self.last_contract_renewal_input.setCalendarPopup(True)
        self.last_contract_renewal_input.setDisplayFormat("yyyy-MM-dd")
        self.last_contract_renewal_input.setDate(QDate.currentDate())
        self.last_contract_renewal_input.setEnabled(False)  # Make it read-only
        self.last_contract_renewal_input.setStyleSheet("QDateEdit:disabled { background-color: #f0f0f0; color: #666; }")
        
        # Add checkboxes for contract renewals
        self.has_renewal_1 = QCheckBox("Has 1st")
        self.has_renewal_1.setChecked(False)
        
        self.has_renewal_2 = QCheckBox("Has 2nd")
        self.has_renewal_2.setChecked(False)
        
        self.has_renewal_3 = QCheckBox("Has 3rd")
        self.has_renewal_3.setChecked(False)
        
        # Connect checkboxes to enable/disable date fields
        def toggle_renewal_1():
            self.contract_renewal_1_input.setEnabled(self.has_renewal_1.isChecked())
            self.update_last_renewal_date()
        self.has_renewal_1.stateChanged.connect(toggle_renewal_1)
        
        def toggle_renewal_2():
            self.contract_renewal_2_input.setEnabled(self.has_renewal_2.isChecked())
            self.update_last_renewal_date()
        self.has_renewal_2.stateChanged.connect(toggle_renewal_2)
        
        def toggle_renewal_3():
            self.contract_renewal_3_input.setEnabled(self.has_renewal_3.isChecked())
            self.update_last_renewal_date()
        self.has_renewal_3.stateChanged.connect(toggle_renewal_3)
        
        # Connect date changes to update last renewal
        self.employment_start_input.dateChanged.connect(self.update_last_renewal_date)
        self.contract_renewal_1_input.dateChanged.connect(self.update_last_renewal_date)
        self.contract_renewal_2_input.dateChanged.connect(self.update_last_renewal_date)
        self.contract_renewal_3_input.dateChanged.connect(self.update_last_renewal_date)
        
        # Initially disable all renewal date fields
        self.contract_renewal_1_input.setEnabled(False)
        self.contract_renewal_2_input.setEnabled(False)
        self.contract_renewal_3_input.setEnabled(False)

        # Create horizontal layouts for fields with checkboxes
        employment_end_layout = QHBoxLayout()
        employment_end_layout.addWidget(self.employment_end_input)
        employment_end_layout.addWidget(self.indefinite_employment)
        employment_end_layout.addStretch()
        
        renewal_1_layout = QHBoxLayout()
        renewal_1_layout.addWidget(self.contract_renewal_1_input)
        renewal_1_layout.addWidget(self.has_renewal_1)
        renewal_1_layout.addStretch()
        
        renewal_2_layout = QHBoxLayout()
        renewal_2_layout.addWidget(self.contract_renewal_2_input)
        renewal_2_layout.addWidget(self.has_renewal_2)
        renewal_2_layout.addStretch()
        
        renewal_3_layout = QHBoxLayout()
        renewal_3_layout.addWidget(self.contract_renewal_3_input)
        renewal_3_layout.addWidget(self.has_renewal_3)
        renewal_3_layout.addStretch()
        
        # Add fields to layout
        layout.addRow("Name*:", self.name_input)
        layout.addRow("Email:", self.email_input)
        layout.addRow("Phone:", self.phone_input)
        layout.addRow("Address:", self.address_input)
        layout.addRow("Birthday:", self.birthday_input)
        layout.addRow("Name Day (DD-MM):", self.nameday_input)
        layout.addRow("Employment Start:", self.employment_start_input)
        layout.addRow("Employment End:", employment_end_layout)
        layout.addRow("Employment Type:", self.employment_type_input)
        layout.addRow("1st Contract Renewal:", renewal_1_layout)
        layout.addRow("2nd Contract Renewal:", renewal_2_layout)
        layout.addRow("3rd Contract Renewal:", renewal_3_layout)
        layout.addRow("Last Contract Renewal (Auto):", self.last_contract_renewal_input)
        layout.addRow("Active:", self.is_active_input)
        layout.addRow("Documents Path:", doc_path_layout)
        
        # Add buttons
        button_box = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_box.addStretch()
        button_box.addWidget(save_button)
        button_box.addWidget(cancel_button)
        layout.addRow("", button_box)
        
        # If editing, populate fields
        if self.employee:
            self.name_input.setText(self.employee.name)
            self.email_input.setText(self.employee.email or "")
            self.phone_input.setText(self.employee.phone or "")
            self.address_input.setText(self.employee.address or "")
            if self.employee.birthday:
                self.birthday_input.setDate(QDate(self.employee.birthday))
            if self.employee.name_day:
                try:
                    month, day = map(int, self.employee.name_day.split('-'))
                    self.nameday_input.setDate(QDate(2000, month, day))
                except (ValueError, AttributeError):
                    self.nameday_input.setDate(QDate.currentDate())
            # Pre-fill employment fields
            if hasattr(self.employee, 'employment_start') and self.employee.employment_start:
                self.employment_start_input.setDate(QDate(self.employee.employment_start))
            
            # Handle employment end date
            if hasattr(self.employee, 'employment_end') and self.employee.employment_end:
                self.employment_end_input.setDate(QDate(self.employee.employment_end))
                self.indefinite_employment.setChecked(False)
                self.employment_end_input.setEnabled(True)
            else:
                self.indefinite_employment.setChecked(True)
                self.employment_end_input.setEnabled(False)
                
            if hasattr(self.employee, 'employment_type') and self.employee.employment_type:
                index = self.employment_type_input.findText(self.employee.employment_type)
                if index >= 0:
                    self.employment_type_input.setCurrentIndex(index)
            
            # Pre-fill contract renewal fields
            if hasattr(self.employee, 'contract_renewal_1') and self.employee.contract_renewal_1:
                self.contract_renewal_1_input.setDate(QDate(self.employee.contract_renewal_1))
                self.has_renewal_1.setChecked(True)
                self.contract_renewal_1_input.setEnabled(True)
            if hasattr(self.employee, 'contract_renewal_2') and self.employee.contract_renewal_2:
                self.contract_renewal_2_input.setDate(QDate(self.employee.contract_renewal_2))
                self.has_renewal_2.setChecked(True)
                self.contract_renewal_2_input.setEnabled(True)
            if hasattr(self.employee, 'contract_renewal_3') and self.employee.contract_renewal_3:
                self.contract_renewal_3_input.setDate(QDate(self.employee.contract_renewal_3))
                self.has_renewal_3.setChecked(True)
                self.contract_renewal_3_input.setEnabled(True)
            
            # Calculate and display the last renewal date
            employment_start = self.employee.employment_start if hasattr(self.employee, 'employment_start') else None
            renewal_1 = self.employee.contract_renewal_1 if hasattr(self.employee, 'contract_renewal_1') else None
            renewal_2 = self.employee.contract_renewal_2 if hasattr(self.employee, 'contract_renewal_2') else None
            renewal_3 = self.employee.contract_renewal_3 if hasattr(self.employee, 'contract_renewal_3') else None
            
            self.calculate_last_renewal_date(employment_start, renewal_1, renewal_2, renewal_3)
            
            # Pre-fill documents path
            if hasattr(self.employee, 'documents_path') and self.employee.documents_path:
                self.documents_path_input.setText(self.employee.documents_path)
        
        self.setLayout(layout)
    
    def calculate_last_renewal_date(self, employment_start, renewal_1, renewal_2, renewal_3):
        """Calculate the most recent date from employment start and renewal dates"""
        from datetime import date
        
        dates = []
        if employment_start:
            dates.append(employment_start)
        if renewal_1:
            dates.append(renewal_1)
        if renewal_2:
            dates.append(renewal_2)
        if renewal_3:
            dates.append(renewal_3)
        
        if dates:
            latest_date = max(dates)
            # Update the display field
            self.last_contract_renewal_input.setDate(QDate(latest_date))
            return latest_date
        else:
            self.last_contract_renewal_input.setDate(QDate.currentDate())
            return None
    
    def update_last_renewal_date(self):
        """Update the last renewal date based on current values"""
        employment_start_qdate = self.employment_start_input.date()
        employment_start = employment_start_qdate.toPyDate() if employment_start_qdate else None
        
        contract_renewal_1 = None
        if self.has_renewal_1.isChecked():
            renewal_1_qdate = self.contract_renewal_1_input.date()
            contract_renewal_1 = renewal_1_qdate.toPyDate() if renewal_1_qdate else None
        
        contract_renewal_2 = None
        if self.has_renewal_2.isChecked():
            renewal_2_qdate = self.contract_renewal_2_input.date()
            contract_renewal_2 = renewal_2_qdate.toPyDate() if renewal_2_qdate else None
        
        contract_renewal_3 = None
        if self.has_renewal_3.isChecked():
            renewal_3_qdate = self.contract_renewal_3_input.date()
            contract_renewal_3 = renewal_3_qdate.toPyDate() if renewal_3_qdate else None
        
        self.calculate_last_renewal_date(employment_start, contract_renewal_1, contract_renewal_2, contract_renewal_3)
    
    def get_data(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required")
            return None
            
        # Get the birthday date
        birthday_qdate = self.birthday_input.date()
        birthday = birthday_qdate.toPyDate() if birthday_qdate else None
            
        # Get the name day date and extract only month and day
        nameday_qdate = self.nameday_input.date()
        # Format as MM-DD string since we only care about month and day
        name_day = f"{nameday_qdate.month():02d}-{nameday_qdate.day():02d}" if nameday_qdate else None
            
        # Get employment dates
        employment_start_qdate = self.employment_start_input.date()
        employment_start = employment_start_qdate.toPyDate() if employment_start_qdate else None
        
        # Handle employment end date based on indefinite checkbox
        if self.indefinite_employment.isChecked():
            employment_end = None
        else:
            employment_end_qdate = self.employment_end_input.date()
            employment_end = employment_end_qdate.toPyDate() if employment_end_qdate else None
        
        # Get contract renewal dates based on checkboxes
        if self.has_renewal_1.isChecked():
            contract_renewal_1_qdate = self.contract_renewal_1_input.date()
            contract_renewal_1 = contract_renewal_1_qdate.toPyDate() if contract_renewal_1_qdate else None
        else:
            contract_renewal_1 = None
        
        if self.has_renewal_2.isChecked():
            contract_renewal_2_qdate = self.contract_renewal_2_input.date()
            contract_renewal_2 = contract_renewal_2_qdate.toPyDate() if contract_renewal_2_qdate else None
        else:
            contract_renewal_2 = None
        
        if self.has_renewal_3.isChecked():
            contract_renewal_3_qdate = self.contract_renewal_3_input.date()
            contract_renewal_3 = contract_renewal_3_qdate.toPyDate() if contract_renewal_3_qdate else None
        else:
            contract_renewal_3 = None
        
        # Automatically calculate the last contract renewal date
        last_contract_renewal = self.calculate_last_renewal_date(
            employment_start, contract_renewal_1, contract_renewal_2, contract_renewal_3
        )
        
        data = {
            "name": self.name_input.text().strip(),
            "email": self.email_input.text().strip() or None,
            "phone": self.phone_input.text().strip() or None,
            "address": self.address_input.text().strip() or None,
            "birthday": birthday,
            "name_day": name_day,
            "employment_start": employment_start,
            "employment_end": employment_end,
            "employment_type": self.employment_type_input.currentText(),
            "contract_renewal_1": contract_renewal_1,
            "contract_renewal_2": contract_renewal_2,
            "contract_renewal_3": contract_renewal_3,
            "last_contract_renewal": last_contract_renewal,
            "is_active": self.is_active_input.isChecked(),
            "documents_path": self.documents_path_input.text().strip() or None
        }
        

        return data

class EmployeesTab(QWidget):
    def __init__(self, session: Session, user=None):
        super().__init__()
        self.session = session
        self.user = user
        self.permissions_manager = get_permissions_manager()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create toolbar
        toolbar = QHBoxLayout()
        
        # Add buttons based on permissions
        if not self.user or self.permissions_manager.has_permission(self.user, "employees", "create"):
            add_button = QPushButton("Add Employee")
            add_button.clicked.connect(self.add_employee)
            toolbar.addWidget(add_button)
        
        if not self.user or self.permissions_manager.has_permission(self.user, "employees", "edit"):
            edit_button = QPushButton("Edit Employee")
            edit_button.clicked.connect(self.edit_employee)
            toolbar.addWidget(edit_button)
        
        if not self.user or self.permissions_manager.has_permission(self.user, "employees", "delete"):
            delete_button = QPushButton("Delete Employee")
            delete_button.clicked.connect(self.delete_employee)
            toolbar.addWidget(delete_button)
        
        # Add search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search employees...")
        self.search_input.textChanged.connect(self.search_employees)
        toolbar.addWidget(self.search_input)
        
        # Add status filter
        self.show_inactive = QCheckBox("Show Inactive")
        self.show_inactive.stateChanged.connect(self.refresh_data)
        toolbar.addWidget(self.show_inactive)
        
        # Add employment data filter
        self.show_employment_data = QCheckBox("Show Employment Data")
        self.show_employment_data.stateChanged.connect(self.refresh_data)
        toolbar.addWidget(self.show_employment_data)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Create table
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
        
        # Add double-click handler
        self.table.cellDoubleClicked.connect(self.open_employee_profile)
        
        # Setup initial table structure
        self.setup_table_columns()
        
        # Load initial data
        self.refresh_data()
    
    def setup_table_columns(self):
        """Setup table columns based on the current view mode and user permissions"""
        # Get visible columns based on permissions
        visible_columns = []
        if self.user:
            visible_columns = self.permissions_manager.get_visible_columns(self.user, "employees")
        else:
            # If no user, show all columns (for backward compatibility)
            visible_columns = ["name", "email", "phone", "address", "birthday", "name_day", "documents_path", 
                             "employment_start", "employment_end", "employment_type", "contract_renewal_1", 
                             "contract_renewal_2", "contract_renewal_3", "last_contract_renewal", "is_active"]
        
        if self.show_employment_data.isChecked():
            # Employment data view - filter based on permissions
            employment_columns = ["name", "is_active", "employment_start", "employment_end", 
                               "employment_type", "contract_renewal_1", "contract_renewal_2", "contract_renewal_3"]
            
            # Filter to only show columns user has permission to see
            visible_employment_columns = [col for col in employment_columns if col in visible_columns]
            
            self.table.setColumnCount(len(visible_employment_columns))
            
            # Create headers based on visible columns
            headers = []
            for col in visible_employment_columns:
                if col == "name":
                    headers.append("Name")
                elif col == "is_active":
                    headers.append("Status")
                elif col == "employment_start":
                    headers.append("Employment Start")
                elif col == "employment_end":
                    headers.append("Employment End")
                elif col == "employment_type":
                    headers.append("Employment Type")
                elif col == "contract_renewal_1":
                    headers.append("1st Renewal")
                elif col == "contract_renewal_2":
                    headers.append("2nd Renewal")
                elif col == "contract_renewal_3":
                    headers.append("3rd Renewal")
            
            self.table.setHorizontalHeaderLabels(headers)
            
            # Set column widths for employment view
            for i, col in enumerate(visible_employment_columns):
                if col == "name":
                    self.table.setColumnWidth(i, 200)
                elif col == "is_active":
                    self.table.setColumnWidth(i, 80)
                elif col in ["employment_start", "employment_end"]:
                    self.table.setColumnWidth(i, 120)
                elif col == "employment_type":
                    self.table.setColumnWidth(i, 150)
                elif col in ["contract_renewal_1", "contract_renewal_2", "contract_renewal_3"]:
                    self.table.setColumnWidth(i, 100)
        else:
            # Basic employee data view - filter based on permissions
            basic_columns = ["name", "email", "phone", "address", "is_active", "birthday", "name_day"]
            
            # Filter to only show columns user has permission to see
            visible_basic_columns = [col for col in basic_columns if col in visible_columns]
            
            self.table.setColumnCount(len(visible_basic_columns))
            
            # Create headers based on visible columns
            headers = []
            for col in visible_basic_columns:
                if col == "name":
                    headers.append("Name")
                elif col == "email":
                    headers.append("Email")
                elif col == "phone":
                    headers.append("Phone")
                elif col == "address":
                    headers.append("Address")
                elif col == "is_active":
                    headers.append("Status")
                elif col == "birthday":
                    headers.append("Birthday")
                elif col == "name_day":
                    headers.append("Name Day")
            
            self.table.setHorizontalHeaderLabels(headers)
            
            # Set column widths for basic view
            for i, col in enumerate(visible_basic_columns):
                if col == "name":
                    self.table.setColumnWidth(i, 200)
                elif col == "email":
                    self.table.setColumnWidth(i, 200)
                elif col == "phone":
                    self.table.setColumnWidth(i, 120)
                elif col == "address":
                    self.table.setColumnWidth(i, 250)
                elif col == "is_active":
                    self.table.setColumnWidth(i, 80)
                elif col == "birthday":
                    self.table.setColumnWidth(i, 100)
                elif col == "name_day":
                    self.table.setColumnWidth(i, 100)
    
    def calculate_age(self, birthday):
        if not birthday:
            return ""
        today = date.today()
        age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
        return str(age)
    
    def calculate_days_until(self, target_date):
        if not target_date:
            return None
            
        today = date.today()
        next_occurrence = date(today.year, target_date.month, target_date.day)
        
        if next_occurrence < today:
            next_occurrence = date(today.year + 1, target_date.month, target_date.day)
            
        return (next_occurrence - today).days
    
    def should_highlight(self, target_date, is_birthday=False):
        """
        Determine if a date should be highlighted based on proximity to today.
        
        Args:
            target_date: For birthdays, a datetime.date object. For name days, a MM-DD string.
            is_birthday: True if checking a birthday, False if checking a name day.
            
        Returns:
            bool: True if the date should be highlighted, False otherwise.
        """
        if not target_date:
            return False
        
        today = date.today()
        
        try:
            # For birthdays (full date), check if it's in current or next month
            if is_birthday and isinstance(target_date, date):
                # Get this year's birthday
                this_year_date = date(today.year, target_date.month, target_date.day)
                # Get next month's range
                if today.month == 12:
                    next_month_start = date(today.year + 1, 1, 1)
                    next_month_end = date(today.year + 1, 1, 31)
                else:
                    next_month_start = date(today.year, today.month + 1, 1)
                    next_month_end = (next_month_start + relativedelta(months=1, days=-1))
                
                # Check if birthday is in current or next month
                return (today.month == target_date.month) or (this_year_date >= next_month_start and this_year_date <= next_month_end)
            
            # For name days (MM-DD string), check if it's in current or next month
            if not is_birthday and isinstance(target_date, str):
                try:
                    # Split MM-DD format
                    month, day = map(int, target_date.split('-'))
                    
                    # Calculate name day date for this year
                    name_day_date = date(today.year, month, day)
                    
                    # If the name day has already passed this year, check next year
                    if name_day_date < today:
                        name_day_date = date(today.year + 1, month, day)
                    
                    # Get next month's range
                    if today.month == 12:
                        next_month_start = date(today.year + 1, 1, 1)
                        next_month_end = date(today.year + 1, 1, 31)
                    else:
                        next_month_start = date(today.year, today.month + 1, 1)
                        next_month_end = (next_month_start + relativedelta(months=1, days=-1))
                    
                    # Highlight if name day is in current or next month
                    should_highlight = (today.month == month) or (name_day_date >= next_month_start and name_day_date <= next_month_end)
                    return should_highlight
                    
                except (ValueError, TypeError) as e:
                    return False
            
            return False
            
        except Exception as e:
    
            return False
    
    def highlight_row(self, row, color):
        """Highlight an entire row with the given color using text color and bold font."""
        from PyQt6.QtGui import QFont, QBrush
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                # Use QBrush to set text color and make it bold for better visibility
                item.setForeground(QBrush(color))
                font = item.font()
                font.setBold(True)
                item.setFont(font)

    def format_phone_number(self, phone):
        """Format phone number for display"""
        if not phone:
            return ""
        
        # Convert to string if it's a number
        phone_str = str(phone)
        
        # Remove any non-digit characters
        digits = ''.join(filter(str.isdigit, phone_str))
        
        if not digits:
            return phone_str  # Return original if no digits found
        
        # Format based on length
        if len(digits) == 9:  # Czech mobile number
            return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
        elif len(digits) == 10:  # Czech mobile number with country code
            return f"+{digits[:2]} {digits[2:5]} {digits[5:8]} {digits[8:]}"
        elif len(digits) == 13:  # International format
            return f"+{digits[:2]} {digits[2:5]} {digits[5:8]} {digits[8:10]} {digits[10:]}"
        else:
            # For other lengths, just add spaces every 3 digits
            formatted = ""
            for i in range(0, len(digits), 3):
                if formatted:
                    formatted += " "
                formatted += digits[i:i+3]
            return formatted

    def highlight_employment_issues(self, row, employee):
        """Highlight employment issues in the employment data view"""
        from datetime import date, timedelta
        
        today = date.today()
        current_year = today.year
        
        # Check for missing employment start date
        if not hasattr(employee, 'employment_start') or not employee.employment_start:
            self.highlight_row(row, QColor(255, 165, 0))  # Orange for missing data
            return
        
        # Check for contract expiration issues
        if hasattr(employee, 'employment_end') and employee.employment_end:
            days_until_end = (employee.employment_end - today).days
            
            # Contract already expired (urgent - red)
            if days_until_end < 0:
                self.highlight_row(row, QColor(255, 0, 0))  # Red for expired
                return
            
            # Contract ending within 30 days (warning - orange)
            elif days_until_end <= 30:
                self.highlight_row(row, QColor(255, 165, 0))  # Orange for urgent
                return
            
            # Contract ending this year (needs attention - dark green)
            elif employee.employment_end.year == current_year:
                self.highlight_row(row, QColor(0, 100, 0))  # Dark green for this year
                return
        
        # Check for renewal issues
        renewal_dates = []
        if hasattr(employee, 'contract_renewal_1') and employee.contract_renewal_1:
            renewal_dates.append(employee.contract_renewal_1)
        if hasattr(employee, 'contract_renewal_2') and employee.contract_renewal_2:
            renewal_dates.append(employee.contract_renewal_2)
        if hasattr(employee, 'contract_renewal_3') and employee.contract_renewal_3:
            renewal_dates.append(employee.contract_renewal_3)
        
        # Check if any renewal dates are this year and not yet passed
        for renewal_date in renewal_dates:
            if renewal_date.year == current_year and renewal_date >= today:
                days_until_renewal = (renewal_date - today).days
                
                # Renewal within 30 days (urgent - orange)
                if days_until_renewal <= 30:
                    self.highlight_row(row, QColor(255, 165, 0))  # Orange for urgent renewal
                    return
                
                # Renewal this year (needs attention - dark green)
                elif days_until_renewal <= 90:
                    self.highlight_row(row, QColor(0, 100, 0))  # Dark green for upcoming renewal
                    return

    def populate_table(self, employees):
        """Populate table with employees based on current view and permissions"""
        try:
            self.table.setRowCount(0)  # Clear the table first
            
            if not employees:
                return
                
            self.table.setRowCount(len(employees))
            
            # Get visible columns based on permissions
            visible_columns = []
            if self.user:
                visible_columns = self.permissions_manager.get_visible_columns(self.user, "employees")
            else:
                # If no user, show all columns (for backward compatibility)
                visible_columns = ["name", "email", "phone", "address", "birthday", "name_day", "documents_path", 
                                 "employment_start", "employment_end", "employment_type", "contract_renewal_1", 
                                 "contract_renewal_2", "contract_renewal_3", "last_contract_renewal", "is_active"]
            
            for i, emp in enumerate(employees):
                if emp is None or not hasattr(emp, 'name'):
                    continue
                
                try:
                    col_index = 0
                    
                    if self.show_employment_data.isChecked():
                        # Employment data view - filter based on permissions
                        employment_columns = ["name", "is_active", "employment_start", "employment_end", 
                                           "employment_type", "contract_renewal_1", "contract_renewal_2", "contract_renewal_3"]
                        
                        # Filter to only show columns user has permission to see
                        visible_employment_columns = [col for col in employment_columns if col in visible_columns]
                        
                        for col in visible_employment_columns:
                            if col == "name":
                                self.table.setItem(i, col_index, QTableWidgetItem(str(emp.name) if emp.name else ""))
                            elif col == "is_active":
                                self.table.setItem(i, col_index, QTableWidgetItem("Active" if getattr(emp, 'is_active', False) else "Inactive"))
                            elif col == "employment_start":
                                self.table.setItem(i, col_index, QTableWidgetItem(emp.employment_start.strftime("%Y-%m-%d") if hasattr(emp, 'employment_start') and emp.employment_start else ""))
                            elif col == "employment_end":
                                self.table.setItem(i, col_index, QTableWidgetItem(emp.employment_end.strftime("%Y-%m-%d") if hasattr(emp, 'employment_end') and emp.employment_end else "Indefinite"))
                            elif col == "employment_type":
                                self.table.setItem(i, col_index, QTableWidgetItem(emp.employment_type if hasattr(emp, 'employment_type') and emp.employment_type else ""))
                            elif col == "contract_renewal_1":
                                self.table.setItem(i, col_index, QTableWidgetItem(emp.contract_renewal_1.strftime("%Y-%m-%d") if hasattr(emp, 'contract_renewal_1') and emp.contract_renewal_1 else ""))
                            elif col == "contract_renewal_2":
                                self.table.setItem(i, col_index, QTableWidgetItem(emp.contract_renewal_2.strftime("%Y-%m-%d") if hasattr(emp, 'contract_renewal_2') and emp.contract_renewal_2 else ""))
                            elif col == "contract_renewal_3":
                                self.table.setItem(i, col_index, QTableWidgetItem(emp.contract_renewal_3.strftime("%Y-%m-%d") if hasattr(emp, 'contract_renewal_3') and emp.contract_renewal_3 else ""))
                            col_index += 1
                        
                        # Apply highlighting for employment issues
                        self.highlight_employment_issues(i, emp)
                        
                    else:
                        # Basic employee data view - filter based on permissions
                        basic_columns = ["name", "email", "phone", "address", "is_active", "birthday", "name_day"]
                        
                        # Filter to only show columns user has permission to see
                        visible_basic_columns = [col for col in basic_columns if col in visible_columns]
                        
                        for col in visible_basic_columns:
                            if col == "name":
                                self.table.setItem(i, col_index, QTableWidgetItem(str(emp.name) if emp.name else ""))
                            elif col == "email":
                                self.table.setItem(i, col_index, QTableWidgetItem(str(emp.email) if emp.email else ""))
                            elif col == "phone":
                                self.table.setItem(i, col_index, QTableWidgetItem(self.format_phone_number(emp.phone)))
                            elif col == "address":
                                self.table.setItem(i, col_index, QTableWidgetItem(str(emp.address) if emp.address else ""))
                            elif col == "is_active":
                                self.table.setItem(i, col_index, QTableWidgetItem("Active" if getattr(emp, 'is_active', False) else "Inactive"))
                            elif col == "birthday":
                                birthday_str = ""
                                if emp.birthday:
                                    try:
                                        birthday_str = emp.birthday.strftime("%Y-%m-%d")
                                    except Exception as e:
                                        pass
                                self.table.setItem(i, col_index, QTableWidgetItem(birthday_str))
                            elif col == "name_day":
                                name_day_str = ""
                                if emp.name_day:
                                    try:
                                        month, day = map(int, emp.name_day.split('-'))
                                        name_day_str = f"{day:02d}-{month:02d}"
                                    except Exception as e:
                                        pass
                                self.table.setItem(i, col_index, QTableWidgetItem(name_day_str))
                            col_index += 1
                        
                        # Apply highlighting for upcoming events (only in basic view)
                        highlight_birthday = self.should_highlight(emp.birthday, is_birthday=True)
                        highlight_nameday = self.should_highlight(emp.name_day, is_birthday=False)
                        
                        if highlight_birthday and highlight_nameday:
                            self.highlight_row(i, QColor(128, 0, 128))  # Purple for both
                        elif highlight_birthday:
                            self.highlight_row(i, QColor(255, 0, 0))  # Red for birthdays
                        elif highlight_nameday:
                            self.highlight_row(i, QColor(0, 128, 0))  # Green for name days
                    
                except Exception as e:
                    continue
                
        except Exception as e:
            raise
    
    def refresh_data(self):
        try:
            # Setup table columns based on current view
            self.setup_table_columns()
            
            # Clear any expired objects and refresh session
            self.session.expire_all()
            self.session.commit()
            
            # Create a fresh query
            query = self.session.query(Employee)
            
            if not self.show_inactive.isChecked():
                query = query.filter(Employee.is_active == True)
                
            # Execute query and get results
            employees = query.all()
            
            # Validate each employee
            valid_employees = []
            for emp in employees:
                if emp is None:
                    continue
                    
                # Access the name attribute to force load the object
                try:
                    _ = emp.name
                    valid_employees.append(emp)
                except Exception as e:
                    continue
            
            self.populate_table(valid_employees)
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error refreshing data: {str(e)}")
    
    def search_employees(self, text):
        if not text:
            self.refresh_data()
            return
            
        query = self.session.query(Employee)
        
        if not self.show_inactive.isChecked():
            query = query.filter(Employee.is_active == True)
            
        search = f"%{text}%"
        
        if self.show_employment_data.isChecked():
            # Search in employment-related fields
            employees = query.filter(
                or_(
                    Employee.name.ilike(search),
                    Employee.employment_type.ilike(search),
                    Employee.is_active.ilike(search)
                )
            ).order_by(Employee.name).all()
        else:
            # Search in basic employee fields
            employees = query.filter(
                or_(
                    Employee.name.ilike(search),
                    Employee.email.ilike(search),
                    Employee.phone.ilike(search),
                    Employee.address.ilike(search)
                )
            ).order_by(Employee.name).all()
        
        self.populate_table(employees)
    
    def add_employee(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "employees", "create"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to add employees.")
            return
            
        dialog = EmployeeDialog(self.session, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    # Create new employee
                    employee = Employee(**data)
                    self.session.add(employee)
                    self.session.commit()
                    
                    # Force a refresh of the session
                    self.session.expire_all()
                    self.refresh_data()
                    
                    # Show success message
                    QMessageBox.information(self, "Success", "Employee added successfully!")
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error adding employee: {str(e)}")
                    return
    
    def edit_employee(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "employees", "edit"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit employees.")
            return
            
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select an employee to edit")
            return
            
        name = self.table.item(selected_rows[0].row(), 0).text()
        employee = self.session.query(Employee).filter(Employee.name == name).first()
        
        dialog = EmployeeDialog(self.session, employee, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    for key, value in data.items():
                        setattr(employee, key, value)
                    self.session.commit()
                    self.refresh_data()
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error updating employee: {str(e)}")
    
    def delete_employee(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "employees", "delete"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete employees.")
            return
            
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select an employee to delete")
            return
            
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this employee?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            name = self.table.item(selected_rows[0].row(), 0).text()
            employee = self.session.query(Employee).filter(Employee.name == name).first()
            
            try:
                self.session.delete(employee)
                self.session.commit()
                self.refresh_data()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error deleting employee: {str(e)}")

    def check_upcoming_events(self):
        """Check for upcoming birthdays and name days."""
        try:
            # Refresh the data to update the table
            self.refresh_data()
        except Exception as e:
            raise

    def open_employee_profile(self, row, column):
        # Get the employee for the selected row
        if row < 0 or row >= self.table.rowCount():
            return
        # Find the employee by name (assuming names are unique)
        name_item = self.table.item(row, 0)
        if not name_item:
            return
        name = name_item.text()
        # Query the employee from the database
        emp = self.session.query(Employee).filter_by(name=name).first()
        if not emp:
            return
        dialog = EmployeeProfileDialog(emp, parent=self)
        dialog.exec() 