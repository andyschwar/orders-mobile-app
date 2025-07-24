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

class EditDeliveryDialog(QDialog):
    """Dialog for editing existing deliveries"""
    
    def __init__(self, session: Session, delivery: Delivery, parent=None):
        super().__init__(parent)
        self.session = session
        self.delivery = delivery
        self.order_item = delivery.order_item
        # Store original values for proper calculation
        self.original_quantity = delivery.quantity
        self.original_delivery_date = delivery.delivery_date
        self.setWindowTitle(f"Edit Delivery - {self.order_item.item.customer_item_name}")
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
        
        # Edit delivery section
        layout.addWidget(QLabel("Edit Delivery:"))
        
        delivery_form = QFormLayout()
        
        # Quantity
        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(1)
        self.quantity_input.setMaximum(999999)
        self.quantity_input.setValue(self.delivery.quantity)
        delivery_form.addRow("Quantity:", self.quantity_input)
        
        # Delivery date
        self.delivery_date_input = QDateEdit()
        self.delivery_date_input.setCalendarPopup(True)
        self.delivery_date_input.setDate(self.delivery.delivery_date)
        delivery_form.addRow("Delivery Date:", self.delivery_date_input)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        self.notes_input.setPlainText(self.delivery.notes or "")
        delivery_form.addRow("Notes:", self.notes_input)
        
        layout.addLayout(delivery_form)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Save Changes")
        save_button.clicked.connect(self.save_changes)
        
        delete_button = QPushButton("Delete Delivery")
        delete_button.setStyleSheet("background-color: #ff4444; color: white;")
        delete_button.clicked.connect(self.delete_delivery)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(delete_button)
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
        
        # Delivery history table
        layout.addWidget(QLabel("All Deliveries for This Item:"))
        
        self.delivery_table = QTableWidget()
        self.delivery_table.setColumnCount(5)
        self.delivery_table.setHorizontalHeaderLabels([
            "Date", "Quantity", "Notes", "Created", "Actions"
        ])
        
        # Set column widths
        header = self.delivery_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.delivery_table)
        
        self.setLayout(layout)
        
        # Load existing deliveries
        self.load_deliveries()
        
    def load_deliveries(self):
        """Load all deliveries for this order item into the table"""
        deliveries = self.session.query(Delivery).filter(
            Delivery.order_item_id == self.order_item.id
        ).order_by(Delivery.delivery_date.desc()).all()
        
        self.delivery_table.setRowCount(len(deliveries))
        
        for i, delivery in enumerate(deliveries):
            # Date
            date_item = QTableWidgetItem(delivery.delivery_date.strftime("%Y-%m-%d"))
            self.delivery_table.setItem(i, 0, date_item)
            
            # Quantity
            qty_item = QTableWidgetItem(str(delivery.quantity))
            self.delivery_table.setItem(i, 1, qty_item)
            
            # Notes
            notes_item = QTableWidgetItem(delivery.notes or "")
            self.delivery_table.setItem(i, 2, notes_item)
            
            # Created date
            created_item = QTableWidgetItem(delivery.created_at.strftime("%Y-%m-%d %H:%M"))
            self.delivery_table.setItem(i, 3, created_item)
            
            # Actions button
            if delivery.id == self.delivery.id:
                # This is the delivery being edited
                action_item = QTableWidgetItem("(Currently Editing)")
                action_item.setBackground(Qt.GlobalColor.lightGray)
            else:
                action_item = QTableWidgetItem("")
            
            self.delivery_table.setItem(i, 4, action_item)
    
    def save_changes(self):
        """Save changes to the delivery"""
        try:
            new_quantity = self.quantity_input.value()
            new_delivery_date = self.delivery_date_input.date().toPyDate()
            new_notes = self.notes_input.toPlainText().strip()
            
            # Validate quantity
            if new_quantity <= 0:
                QMessageBox.warning(self, "Validation Error", "Quantity must be greater than 0")
                return
            
            # Calculate the difference in quantity using original values
            quantity_diff = new_quantity - self.original_quantity
            
            # Check if the new total delivered quantity would exceed the order quantity
            new_total_delivered = self.order_item.delivered_quantity + quantity_diff
            if new_total_delivered > self.order_item.quantity:
                QMessageBox.warning(
                    self, "Validation Error", 
                    f"New total delivered quantity ({new_total_delivered}) would exceed order quantity ({self.order_item.quantity})"
                )
                return
            
            # Update the delivery
            self.delivery.quantity = new_quantity
            self.delivery.delivery_date = new_delivery_date
            self.delivery.notes = new_notes if new_notes else None
            
            # Update the order item's delivered quantity
            self.order_item.delivered_quantity += quantity_diff
            
            # Update the last delivery date - recalculate based on all deliveries
            all_deliveries = self.session.query(Delivery).filter(
                Delivery.order_item_id == self.order_item.id
            ).order_by(Delivery.delivery_date.desc()).all()
            
            if all_deliveries:
                self.order_item.last_delivery_date = all_deliveries[0].delivery_date
            else:
                self.order_item.last_delivery_date = None
            
            # Commit changes
            self.session.commit()
            
            QMessageBox.information(self, "Success", "Delivery updated successfully!")
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error updating delivery: {str(e)}")
    
    def delete_delivery(self):
        """Delete the current delivery"""
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete this delivery?\n\n"
            f"Date: {self.delivery.delivery_date.strftime('%Y-%m-%d')}\n"
            f"Quantity: {self.delivery.quantity}\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Update the order item's delivered quantity using original quantity
                self.order_item.delivered_quantity -= self.original_quantity
                
                # Update last delivery date - recalculate based on remaining deliveries
                other_deliveries = self.session.query(Delivery).filter(
                    Delivery.order_item_id == self.order_item.id,
                    Delivery.id != self.delivery.id
                ).order_by(Delivery.delivery_date.desc()).all()
                
                if other_deliveries:
                    self.order_item.last_delivery_date = other_deliveries[0].delivery_date
                else:
                    self.order_item.last_delivery_date = None
                
                # Delete the delivery
                self.session.delete(self.delivery)
                self.session.commit()
                
                QMessageBox.information(self, "Success", "Delivery deleted successfully!")
                self.accept()
                
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error deleting delivery: {str(e)}") 