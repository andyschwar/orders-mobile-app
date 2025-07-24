from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QLineEdit, QMessageBox, QLabel, QComboBox, QCheckBox,
    QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from models.database import Customer
from utils.permissions import get_permissions_manager

class CustomerDialog(QDialog):
    def __init__(self, session: Session, customer=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.customer = customer
        self.setWindowTitle("Add Customer" if not customer else "Edit Customer")
        self.setModal(True)
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        
        # Create fields
        self.name_index = QLineEdit()
        self.name = QLineEdit()
        self.street = QLineEdit()
        self.city = QLineEdit()
        self.country = QLineEdit()
        self.email1 = QLineEdit()
        self.email2 = QLineEdit()
        self.email3 = QLineEdit()
        self.atest_email = QLineEdit()
        self.invoice_email = QLineEdit()
        self.ico_vat = QLineEdit()
        self.ic_dph = QLineEdit()
        self.currency = QLineEdit()
        self.is_eu = QCheckBox()
        self.delivery_address = QLineEdit()
        
        # Add fields to layout
        layout.addRow("Name Index*:", self.name_index)
        layout.addRow("Name*:", self.name)
        layout.addRow("Street:", self.street)
        layout.addRow("City:", self.city)
        layout.addRow("Country:", self.country)
        layout.addRow("Email 1:", self.email1)
        layout.addRow("Email 2:", self.email2)
        layout.addRow("Email 3:", self.email3)
        layout.addRow("Atest Email:", self.atest_email)
        layout.addRow("Invoice Email:", self.invoice_email)
        layout.addRow("VAT Number:", self.ico_vat)
        layout.addRow("Tax Number:", self.ic_dph)
        layout.addRow("Currency:", self.currency)
        layout.addRow("EU Member:", self.is_eu)
        layout.addRow("Delivery Address:", self.delivery_address)
        
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
        if self.customer:
            self.name_index.setText(self.customer.name_index)
            self.name.setText(self.customer.name)
            self.street.setText(self.customer.street or "")
            self.city.setText(self.customer.city or "")
            self.country.setText(self.customer.country or "")
            self.email1.setText(self.customer.email1 or "")
            self.email2.setText(self.customer.email2 or "")
            self.email3.setText(self.customer.email3 or "")
            self.atest_email.setText(self.customer.atest_email or "")
            self.invoice_email.setText(self.customer.invoice_email or "")
            self.ico_vat.setText(self.customer.ico_vat or "")
            self.ic_dph.setText(self.customer.ic_dph or "")
            self.currency.setText(self.customer.currency or "")
            self.is_eu.setChecked(self.customer.is_eu)
            self.delivery_address.setText(self.customer.delivery_address or "")
        
        self.setLayout(layout)
    
    def get_data(self):
        if not self.name_index.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name index is required")
            return None
            
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required")
            return None
            
        return {
            "name_index": self.name_index.text().strip(),
            "name": self.name.text().strip(),
            "street": self.street.text().strip() or None,
            "city": self.city.text().strip() or None,
            "country": self.country.text().strip() or None,
            "email1": self.email1.text().strip() or None,
            "email2": self.email2.text().strip() or None,
            "email3": self.email3.text().strip() or None,
            "atest_email": self.atest_email.text().strip() or None,
            "invoice_email": self.invoice_email.text().strip() or None,
            "ico_vat": self.ico_vat.text().strip() or None,
            "ic_dph": self.ic_dph.text().strip() or None,
            "currency": self.currency.text().strip() or None,
            "is_eu": self.is_eu.isChecked(),
            "delivery_address": self.delivery_address.text().strip() or None
        }

class CustomersTab(QWidget):
    customer_updated = pyqtSignal()
    
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
        if not self.user or self.permissions_manager.has_permission(self.user, "customers", "create"):
            add_button = QPushButton("Add Customer")
            add_button.clicked.connect(self.add_customer)
            toolbar.addWidget(add_button)
        
        if not self.user or self.permissions_manager.has_permission(self.user, "customers", "edit"):
            edit_button = QPushButton("Edit Customer")
            edit_button.clicked.connect(self.edit_customer)
            toolbar.addWidget(edit_button)
        
        if not self.user or self.permissions_manager.has_permission(self.user, "customers", "delete"):
            delete_button = QPushButton("Delete Customer")
            delete_button.clicked.connect(self.delete_customer)
            toolbar.addWidget(delete_button)
        
        # Add search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search customers...")
        self.search_input.textChanged.connect(self.search_customers)
        toolbar.addWidget(self.search_input)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Create table with dynamic columns based on permissions
        self.table = QTableWidget()
        self.setup_table_columns()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
        
        # Load initial data
        self.refresh_data()
    
    def setup_table_columns(self):
        """Setup table columns based on user permissions"""
        # Define all possible columns
        all_columns = [
            ("name_index", "Name Index", 100),
            ("name", "Name", 200),
            ("street", "Street", 150),
            ("city", "City", 100),
            ("country", "Country", 100),
            ("email1", "Email 1", 200),
            ("email2", "Email 2", 200),
            ("email3", "Email 3", 200),
            ("atest_email", "Atest Email", 200),
            ("invoice_email", "Invoice Email", 200),
            ("ico_vat", "VAT Number", 100),
            ("ic_dph", "Tax Number", 100),
            ("currency", "Currency", 80),
            ("is_eu", "EU Member", 80),
            ("delivery_address", "Delivery Address", 200)
        ]
        
        # Filter columns based on permissions
        visible_columns = []
        if self.user:
            visible_columns = self.permissions_manager.get_visible_columns(self.user, "customers")
        else:
            # If no user, show all columns (for backward compatibility)
            visible_columns = [col[0] for col in all_columns]
        
        # Create column mapping
        self.column_mapping = {}
        column_headers = []
        column_widths = []
        
        for col_key, col_name, col_width in all_columns:
            if col_key in visible_columns:
                self.column_mapping[col_key] = len(column_headers)
                column_headers.append(col_name)
                column_widths.append(col_width)
        
        # Setup table
        self.table.setColumnCount(len(column_headers))
        self.table.setHorizontalHeaderLabels(column_headers)
        
        # Set column widths
        for i, width in enumerate(column_widths):
            self.table.setColumnWidth(i, width)
    
    def populate_table(self, customers):
        self.table.setRowCount(len(customers))
        
        for i, customer in enumerate(customers):
            col_index = 0
            
            # Add columns based on permissions
            if "name_index" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["name_index"], 
                                 QTableWidgetItem(customer.name_index))
            
            if "name" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["name"], 
                                 QTableWidgetItem(customer.name))
            
            if "street" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["street"], 
                                 QTableWidgetItem(customer.street or ""))
            
            if "city" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["city"], 
                                 QTableWidgetItem(customer.city or ""))
            
            if "country" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["country"], 
                                 QTableWidgetItem(customer.country or ""))
            
            if "email1" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["email1"], 
                                 QTableWidgetItem(customer.email1 or ""))
            
            if "email2" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["email2"], 
                                 QTableWidgetItem(customer.email2 or ""))
            
            if "email3" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["email3"], 
                                 QTableWidgetItem(customer.email3 or ""))
            
            if "atest_email" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["atest_email"], 
                                 QTableWidgetItem(customer.atest_email or ""))
            
            if "invoice_email" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["invoice_email"], 
                                 QTableWidgetItem(customer.invoice_email or ""))
            
            if "ico_vat" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["ico_vat"], 
                                 QTableWidgetItem(customer.ico_vat or ""))
            
            if "ic_dph" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["ic_dph"], 
                                 QTableWidgetItem(customer.ic_dph or ""))
            
            if "currency" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["currency"], 
                                 QTableWidgetItem(customer.currency or ""))
            
            if "is_eu" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["is_eu"], 
                                 QTableWidgetItem("Yes" if customer.is_eu else "No"))
            
            if "delivery_address" in self.column_mapping:
                self.table.setItem(i, self.column_mapping["delivery_address"], 
                                 QTableWidgetItem(customer.delivery_address or ""))
    
    def refresh_data(self):
        customers = self.session.query(Customer).order_by(Customer.name_index).all()
        self.populate_table(customers)
    
    def search_customers(self, text):
        if not text:
            self.refresh_data()
            return
            
        search = f"%{text}%"
        customers = self.session.query(Customer).filter(
            or_(
                Customer.name_index.ilike(search),
                Customer.name.ilike(search),
                Customer.country.ilike(search),
                Customer.email1.ilike(search)
            )
        ).order_by(Customer.name_index).all()
        
        self.populate_table(customers)
    
    def add_customer(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "customers", "create"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to add customers.")
            return
            
        dialog = CustomerDialog(self.session, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                customer = Customer(**data)
                try:
                    self.session.add(customer)
                    self.session.commit()
                    self.refresh_data()
                    self.customer_updated.emit()
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error adding customer: {str(e)}")
    
    def edit_customer(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "customers", "edit"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit customers.")
            return
            
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a customer to edit")
            return
            
        name_index = self.table.item(selected_rows[0].row(), 0).text()
        customer = self.session.query(Customer).filter(Customer.name_index == name_index).first()
        
        dialog = CustomerDialog(self.session, customer, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    for key, value in data.items():
                        setattr(customer, key, value)
                    self.session.commit()
                    self.refresh_data()
                    self.customer_updated.emit()
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error updating customer: {str(e)}")
    
    def delete_customer(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "customers", "delete"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete customers.")
            return
            
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a customer to delete")
            return
            
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this customer? This will also delete all associated orders and items.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            name_index = self.table.item(selected_rows[0].row(), 0).text()
            customer = self.session.query(Customer).filter(Customer.name_index == name_index).first()
            
            try:
                self.session.delete(customer)
                self.session.commit()
                self.refresh_data()
                self.customer_updated.emit()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error deleting customer: {str(e)}") 