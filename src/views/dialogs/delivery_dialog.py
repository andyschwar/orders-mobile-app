from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QDateEdit, QSpinBox, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QMessageBox,
    QHeaderView, QComboBox, QTextEdit, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QDate
from sqlalchemy.orm import Session
from datetime import datetime, date
from models.database import OrderItem, Delivery
from typing import Optional, Dict, Any

class DeliveryDialog(QDialog):
    """Dialog for creating a new delivery"""
    
    def __init__(self, session: Session, order_item: OrderItem, parent=None):
        super().__init__(parent)
        self.session = session
        self.order_item = order_item
        self.setWindowTitle(f"Track Deliveries - {order_item.item.customer_item_name}")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Order item info
        info_layout = QFormLayout()
        
        # Item details
        item_info = QLabel(f"Item: {self.order_item.item.customer_item_name}")
        item_info.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(item_info)
        
        customer_info = QLabel(f"Customer: {self.order_item.item.customer.name}")
        layout.addWidget(customer_info)
        
        order_info = QLabel(f"Order: {self.order_item.order.order_number}")
        layout.addWidget(order_info)
        
        # Quantity info
        total_qty = QLabel(f"Total Quantity: {self.order_item.quantity}")
        delivered_qty = QLabel(f"Delivered: {self.order_item.delivered_quantity}")
        remaining_qty = QLabel(f"Remaining: {self.order_item.quantity - self.order_item.delivered_quantity}")
        
        layout.addWidget(total_qty)
        layout.addWidget(delivered_qty)
        layout.addWidget(remaining_qty)
        
        # Add new delivery section
        layout.addWidget(QLabel("Add New Delivery:"))
        
        delivery_form = QFormLayout()
        
        # Planned delivery date selection
        self.planned_date_combo = QComboBox()
        self.planned_date_combo.setMinimumWidth(200)
        delivery_form.addRow("Planned Delivery Date:", self.planned_date_combo)
        
        # Quantity
        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(1)
        self.quantity_input.setMaximum(999999)
        delivery_form.addRow("Quantity:", self.quantity_input)
        
        # Delivery date
        self.delivery_date_input = QDateEdit()
        self.delivery_date_input.setCalendarPopup(True)
        self.delivery_date_input.setDate(QDate.currentDate())
        delivery_form.addRow("Actual Delivery Date:", self.delivery_date_input)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        delivery_form.addRow("Notes:", self.notes_input)
        
        layout.addLayout(delivery_form)
        
        # Add delivery button
        add_button = QPushButton("Add Delivery")
        add_button.clicked.connect(self.accept)
        layout.addWidget(add_button)
        
        # Delivery history table
        layout.addWidget(QLabel("Delivery History:"))
        
        self.delivery_table = QTableWidget()
        self.delivery_table.setColumnCount(4)
        self.delivery_table.setHorizontalHeaderLabels([
            "Date", "Quantity", "Remaining", "Created"
        ])
        
        # Set column widths
        header = self.delivery_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.delivery_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Load existing deliveries and planned dates
        self.load_planned_dates()
        self.load_deliveries()
        
    def load_planned_dates(self):
        """Load planned delivery dates for the order item"""
        self.planned_date_combo.clear()
        
        # Add the main planned delivery date
        planned_date = self.order_item.delivery_date
        display_text = f"{planned_date.strftime('%Y-%m-%d')} (Planned)"
        self.planned_date_combo.addItem(display_text, planned_date)
        
        # Set maximum quantity to remaining quantity
        remaining = self.order_item.quantity - self.order_item.delivered_quantity
        self.quantity_input.setMaximum(remaining)
        self.quantity_input.setValue(min(self.quantity_input.value(), remaining))
        
    def load_deliveries(self):
        """Load existing deliveries into the table"""
        deliveries = self.session.query(Delivery).filter(
            Delivery.order_item_id == self.order_item.id
        ).order_by(Delivery.delivery_date.desc()).all()
        
        self.delivery_table.setRowCount(len(deliveries))
        
        remaining = self.order_item.quantity
        
        for i, delivery in enumerate(deliveries):
            # Date
            date_item = QTableWidgetItem(delivery.delivery_date.strftime("%Y-%m-%d"))
            self.delivery_table.setItem(i, 0, date_item)
            
            # Quantity
            qty_item = QTableWidgetItem(str(delivery.quantity))
            self.delivery_table.setItem(i, 1, qty_item)
            
            # Remaining after this delivery
            remaining -= delivery.quantity
            remaining_item = QTableWidgetItem(str(remaining))
            self.delivery_table.setItem(i, 2, remaining_item)
            
            # Created date
            created_item = QTableWidgetItem(delivery.created_at.strftime("%Y-%m-%d %H:%M"))
            self.delivery_table.setItem(i, 3, created_item)
    
    def get_delivery_data(self) -> Optional[Dict[str, Any]]:
        """Get the delivery data"""
        if self.planned_date_combo.count() == 0:
            return None
        
        planned_date = self.planned_date_combo.currentData()
        quantity = self.quantity_input.value()
        delivery_date = self.delivery_date_input.date().toPyDate()
        notes = self.notes_input.toPlainText().strip()
        
        return {
            'order_item_id': self.order_item.id,
            'planned_date': planned_date,
            'quantity': quantity,
            'delivery_date': delivery_date,
            'notes': notes if notes else None
        }
    
    def accept(self):
        """Override accept to validate delivery data"""
        if self.planned_date_combo.count() == 0:
            QMessageBox.warning(self, "Validation Error", "No planned delivery dates available")
            return
        
        quantity = self.quantity_input.value()
        if quantity <= 0:
            QMessageBox.warning(self, "Validation Error", "Quantity must be greater than 0")
            return
        
        # Check if quantity exceeds remaining quantity
        remaining = self.order_item.quantity - self.order_item.delivered_quantity
        if quantity > remaining:
            QMessageBox.warning(
                self, "Validation Error", 
                f"Quantity ({quantity}) exceeds remaining quantity ({remaining})"
            )
            return
        
        super().accept() 