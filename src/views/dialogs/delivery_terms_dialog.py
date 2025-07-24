from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QDateEdit, QSpinBox, QFormLayout, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
from datetime import date, timedelta
from typing import List, Dict, Any

class DeliveryTermsDialog(QDialog):
    """Dialog for managing delivery terms for an order item"""
    
    def __init__(self, order_item=None, parent=None):
        super().__init__(parent)
        self.order_item = order_item
        self.delivery_terms = []  # List of delivery term dictionaries
        self.setup_ui()
        if order_item:
            self.load_existing_terms()
    
    def setup_ui(self):
        self.setWindowTitle("Manage Delivery Terms")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Delivery Terms")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Add new term section
        add_term_group = QVBoxLayout()
        add_term_group.addWidget(QLabel("Add New Delivery Term:"))
        
        # Form for new term
        form_layout = QFormLayout()
        
        self.term_name_input = QLineEdit()
        self.term_name_input.setPlaceholderText("e.g., May, June, July")
        form_layout.addRow("Term Name:", self.term_name_input)
        
        self.planned_quantity_input = QSpinBox()
        self.planned_quantity_input.setMinimum(1)
        self.planned_quantity_input.setMaximum(999999)
        form_layout.addRow("Planned Quantity:", self.planned_quantity_input)
        
        self.planned_date_input = QDateEdit()
        self.planned_date_input.setCalendarPopup(True)
        self.planned_date_input.setDate(QDate.currentDate())
        form_layout.addRow("Planned Date:", self.planned_date_input)
        
        add_term_group.addLayout(form_layout)
        
        # Add button
        add_button = QPushButton("Add Term")
        add_button.clicked.connect(self.add_term)
        add_term_group.addWidget(add_button)
        
        layout.addLayout(add_term_group)
        
        # Terms table
        self.terms_table = QTableWidget()
        self.terms_table.setColumnCount(5)
        self.terms_table.setHorizontalHeaderLabels([
            "Term Name", "Planned Quantity", "Planned Date", "Delivered", "Status"
        ])
        self.terms_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Set column widths
        header = self.terms_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.terms_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self.delete_selected_term)
        button_layout.addWidget(delete_button)
        
        button_layout.addStretch()
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def add_term(self):
        """Add a new delivery term"""
        term_name = self.term_name_input.text().strip()
        planned_quantity = self.planned_quantity_input.value()
        planned_date = self.planned_date_input.date().toPyDate()
        
        if not term_name:
            QMessageBox.warning(self, "Validation Error", "Term name is required")
            return
        
        if planned_quantity <= 0:
            QMessageBox.warning(self, "Validation Error", "Planned quantity must be greater than 0")
            return
        
        # Check if term name already exists
        for term in self.delivery_terms:
            if term['term_name'] == term_name:
                QMessageBox.warning(self, "Validation Error", f"Term '{term_name}' already exists")
                return
        
        # Add new term
        new_term = {
            'term_name': term_name,
            'planned_quantity': planned_quantity,
            'planned_date': planned_date,
            'delivered_quantity': 0,
            'is_complete': False
        }
        
        self.delivery_terms.append(new_term)
        self.update_table()
        
        # Clear inputs
        self.term_name_input.clear()
        self.planned_quantity_input.setValue(1)
        self.planned_date_input.setDate(QDate.currentDate())
    
    def delete_selected_term(self):
        """Delete the selected delivery term"""
        selected_rows = self.terms_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a term to delete")
            return
        
        row = selected_rows[0].row()
        if 0 <= row < len(self.delivery_terms):
            term_name = self.delivery_terms[row]['term_name']
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                f"Are you sure you want to delete the '{term_name}' term?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                del self.delivery_terms[row]
                self.update_table()
    
    def update_table(self):
        """Update the terms table"""
        self.terms_table.setRowCount(len(self.delivery_terms))
        
        for row, term in enumerate(self.delivery_terms):
            self.terms_table.setItem(row, 0, QTableWidgetItem(term['term_name']))
            self.terms_table.setItem(row, 1, QTableWidgetItem(str(term['planned_quantity'])))
            self.terms_table.setItem(row, 2, QTableWidgetItem(term['planned_date'].strftime('%Y-%m-%d')))
            self.terms_table.setItem(row, 3, QTableWidgetItem(str(term['delivered_quantity'])))
            
            # Status column
            if term['is_complete']:
                status = "Complete"
            elif term['delivered_quantity'] > 0:
                status = "Partial"
            else:
                status = "Pending"
            
            self.terms_table.setItem(row, 4, QTableWidgetItem(status))
    
    def load_existing_terms(self):
        """Load existing delivery terms from the order item"""
        if self.order_item and hasattr(self.order_item, 'delivery_terms'):
            for term in self.order_item.delivery_terms:
                self.delivery_terms.append({
                    'term_name': term.term_name,
                    'planned_quantity': term.planned_quantity,
                    'planned_date': term.planned_date,
                    'delivered_quantity': term.delivered_quantity,
                    'is_complete': term.is_complete
                })
            self.update_table()
    
    def get_delivery_terms(self) -> List[Dict[str, Any]]:
        """Get the delivery terms data"""
        return self.delivery_terms
    
    def validate_terms(self) -> bool:
        """Validate that delivery terms are properly configured"""
        if not self.delivery_terms:
            QMessageBox.warning(self, "Validation Error", "At least one delivery term is required")
            return False
        
        # Check if total planned quantity matches order item quantity
        total_planned = sum(term['planned_quantity'] for term in self.delivery_terms)
        if self.order_item and total_planned != self.order_item.quantity:
            QMessageBox.warning(
                self, "Validation Error", 
                f"Total planned quantity ({total_planned}) does not match order item quantity ({self.order_item.quantity})"
            )
            return False
        
        return True
    
    def accept(self):
        """Override accept to validate terms"""
        if not self.validate_terms():
            return
        
        super().accept() 