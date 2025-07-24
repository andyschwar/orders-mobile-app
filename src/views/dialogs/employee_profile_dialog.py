from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFormLayout, QTextEdit, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import os
import subprocess
import platform

class EmployeeProfileDialog(QDialog):
    def __init__(self, employee, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.setWindowTitle(f"Employee Profile - {employee.name}")
        self.setModal(True)
        self.resize(500, 400)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel(f"Employee Profile: {self.employee.name}")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Employee details
        details_layout = QFormLayout()
        
        # Basic info
        details_layout.addRow("Name:", QLabel(self.employee.name))
        details_layout.addRow("Email:", QLabel(self.employee.email or "Not provided"))
        details_layout.addRow("Phone:", QLabel(self.employee.phone or "Not provided"))
        details_layout.addRow("Address:", QLabel(self.employee.address or "Not provided"))
        
        # Status
        status = "Active" if getattr(self.employee, 'is_active', True) else "Inactive"
        status_label = QLabel(status)
        status_label.setStyleSheet("color: green;" if status == "Active" else "color: red;")
        details_layout.addRow("Status:", status_label)
        
        # Birthday
        if self.employee.birthday:
            birthday_str = self.employee.birthday.strftime("%Y-%m-%d")
            age = self.calculate_age(self.employee.birthday)
            birthday_label = QLabel(f"{birthday_str} (Age: {age})")
        else:
            birthday_label = QLabel("Not provided")
        details_layout.addRow("Birthday:", birthday_label)
        
        # Name day
        if self.employee.name_day:
            try:
                month, day = map(int, self.employee.name_day.split('-'))
                name_day_str = f"{day:02d}-{month:02d}"
            except:
                name_day_str = self.employee.name_day
        else:
            name_day_str = "Not provided"
        details_layout.addRow("Name Day:", QLabel(name_day_str))
        
        # Employment information
        if hasattr(self.employee, 'employment_start') and self.employee.employment_start:
            employment_start_str = self.employee.employment_start.strftime("%Y-%m-%d")
        else:
            employment_start_str = "Not set"
        details_layout.addRow("Employment Start:", QLabel(employment_start_str))
        
        if hasattr(self.employee, 'employment_end') and self.employee.employment_end:
            employment_end_str = self.employee.employment_end.strftime("%Y-%m-%d")
        else:
            employment_end_str = "Not set (Indefinite)"
        details_layout.addRow("Employment End:", QLabel(employment_end_str))
        
        if hasattr(self.employee, 'employment_type') and self.employee.employment_type:
            employment_type_str = self.employee.employment_type
        else:
            employment_type_str = "Not set"
        details_layout.addRow("Employment Type:", QLabel(employment_type_str))
        
        # Contract renewal history
        if hasattr(self.employee, 'contract_renewal_1') and self.employee.contract_renewal_1:
            renewal_1_str = self.employee.contract_renewal_1.strftime("%Y-%m-%d")
        else:
            renewal_1_str = "Not set"
        details_layout.addRow("1st Contract Renewal:", QLabel(renewal_1_str))
        
        if hasattr(self.employee, 'contract_renewal_2') and self.employee.contract_renewal_2:
            renewal_2_str = self.employee.contract_renewal_2.strftime("%Y-%m-%d")
        else:
            renewal_2_str = "Not set"
        details_layout.addRow("2nd Contract Renewal:", QLabel(renewal_2_str))
        
        if hasattr(self.employee, 'contract_renewal_3') and self.employee.contract_renewal_3:
            renewal_3_str = self.employee.contract_renewal_3.strftime("%Y-%m-%d")
        else:
            renewal_3_str = "Not set"
        details_layout.addRow("3rd Contract Renewal:", QLabel(renewal_3_str))
        
        if hasattr(self.employee, 'last_contract_renewal') and self.employee.last_contract_renewal:
            last_renewal_str = self.employee.last_contract_renewal.strftime("%Y-%m-%d")
        else:
            last_renewal_str = "Not set"
        details_layout.addRow("Last Contract Renewal:", QLabel(last_renewal_str))
        
        # Documents path
        if self.employee.documents_path:
            docs_label = QLabel(self.employee.documents_path)
            docs_label.setWordWrap(True)
        else:
            docs_label = QLabel("Not set")
        details_layout.addRow("Documents Path:", docs_label)
        
        layout.addLayout(details_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Open Documents button
        self.open_docs_button = QPushButton("Open Documents")
        self.open_docs_button.clicked.connect(self.open_documents)
        self.open_docs_button.setEnabled(bool(self.employee.documents_path))
        button_layout.addWidget(self.open_docs_button)
        
        # Set Documents Path button
        set_path_button = QPushButton("Set Documents Path")
        set_path_button.clicked.connect(self.set_documents_path)
        button_layout.addWidget(set_path_button)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def calculate_age(self, birthday):
        """Calculate age from birthday"""
        from datetime import date
        today = date.today()
        age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
        return str(age)
        
    def open_documents(self):
        """Open the employee's documents folder"""
        if not self.employee.documents_path:
            QMessageBox.warning(self, "No Documents Path", "No documents path has been set for this employee.")
            return
            
        path = self.employee.documents_path
        
        # Check if path exists
        if not os.path.exists(path):
            QMessageBox.warning(self, "Path Not Found", f"The documents path does not exist:\n{path}")
            return
            
        try:
            # Open folder in file manager
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", path])
            elif platform.system() == "Windows":
                subprocess.run(["explorer", path])
            else:  # Linux
                subprocess.run(["xdg-open", path])
                
            QMessageBox.information(self, "Success", f"Opened documents folder:\n{path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open documents folder:\n{str(e)}")
            
    def set_documents_path(self):
        """Set the documents path for this employee"""
        # Show folder selection dialog
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Employee Documents Folder",
            os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder_path:
            try:
                # Update the employee's documents_path
                self.employee.documents_path = folder_path
                
                # Save to database
                from sqlalchemy.orm import Session
                from models.database import get_database_path
                from sqlalchemy import create_engine
                
                db_path = get_database_path()
                engine = create_engine(f'sqlite:///{db_path}')
                
                with Session(engine) as session:
                    # Get the employee from the session
                    employee = session.merge(self.employee)
                    employee.documents_path = folder_path
                    session.commit()
                
                # Update the UI
                docs_label = self.findChild(QLabel, "")
                if docs_label:
                    docs_label.setText(folder_path)
                
                self.open_docs_button.setEnabled(True)
                
                QMessageBox.information(self, "Success", f"Documents path set to:\n{folder_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save documents path:\n{str(e)}") 