from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QDateEdit, QSpinBox, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QMessageBox,
    QHeaderView, QComboBox, QTextEdit, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QDate
from sqlalchemy.orm import Session
from datetime import datetime, date
from models.database import Order, OrderItem, Delivery
from typing import Optional, Dict, Any
from .edit_delivery_dialog import EditDeliveryDialog
from sqlalchemy import func

class DeliveryManagementDialog(QDialog):
    """Dialog for managing all deliveries for an order"""
    
    def __init__(self, session: Session, order: Order, parent=None):
        super().__init__(parent)
        self.session = session
        self.order = order
        self.setWindowTitle(f"Manage Deliveries - Order {order.order_number}")
        self.setModal(True)
        self.setMinimumSize(1000, 600)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Order info header
        header_layout = QHBoxLayout()
        
        order_info = QLabel(f"Order: {self.order.order_number}")
        order_info.setStyleSheet("font-weight: bold; font-size: 16px;")
        header_layout.addWidget(order_info)
        
        customer_info = QLabel(f"Customer: {self.order.customer.name}")
        customer_info.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(customer_info)
        
        order_date = QLabel(f"Order Date: {self.order.order_date.strftime('%Y-%m-%d')}")
        order_date.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(order_date)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Summary info
        summary_layout = QHBoxLayout()
        
        total_items = sum(item.quantity for item in self.order.items)
        delivered_items = sum(item.delivered_quantity for item in self.order.items)
        remaining_items = total_items - delivered_items
        
        summary_layout.addWidget(QLabel(f"Total Items: {total_items}"))
        summary_layout.addWidget(QLabel(f"Delivered: {delivered_items}"))
        summary_layout.addWidget(QLabel(f"Remaining: {remaining_items}"))
        
        if total_items > 0:
            completion_percentage = (delivered_items / total_items) * 100
            summary_layout.addWidget(QLabel(f"Completion: {completion_percentage:.1f}%"))
        
        summary_layout.addStretch()
        layout.addLayout(summary_layout)
        
        # Deliveries table
        layout.addWidget(QLabel("All Deliveries:"))
        
        self.deliveries_table = QTableWidget()
        self.deliveries_table.setColumnCount(8)
        self.deliveries_table.setHorizontalHeaderLabels([
            "Item Code", "Item Name", "Order Quantity", "Delivered", "Remaining",
            "Delivery Date", "Quantity", "Notes"
        ])
        
        # Set column widths
        header = self.deliveries_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.deliveries_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.load_deliveries)
        button_layout.addWidget(refresh_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Load deliveries
        self.load_deliveries()
        
        # Connect double-click to edit delivery
        self.deliveries_table.cellDoubleClicked.connect(self.edit_delivery)
        
    def load_deliveries(self):
        """Load all deliveries for this order into the table"""
        # Get all deliveries for this order
        deliveries = self.session.query(Delivery).join(OrderItem).filter(
            OrderItem.order_id == self.order.id
        ).order_by(Delivery.delivery_date.desc()).all()
        
        self.deliveries_table.setRowCount(len(deliveries))
        
        for i, delivery in enumerate(deliveries):
            order_item = delivery.order_item
            item = order_item.item
            
            # Item Code
            self.deliveries_table.setItem(i, 0, QTableWidgetItem(item.customer_code))
            
            # Item Name
            item_name = item.customer_item_name or item.product.name
            self.deliveries_table.setItem(i, 1, QTableWidgetItem(item_name))
            
            # Order Quantity
            self.deliveries_table.setItem(i, 2, QTableWidgetItem(str(order_item.quantity)))
            
            # Delivered (total for this item)
            self.deliveries_table.setItem(i, 3, QTableWidgetItem(str(order_item.delivered_quantity)))
            
            # Remaining
            remaining = order_item.quantity - order_item.delivered_quantity
            self.deliveries_table.setItem(i, 4, QTableWidgetItem(str(remaining)))
            
            # Delivery Date
            self.deliveries_table.setItem(i, 5, QTableWidgetItem(delivery.delivery_date.strftime("%Y-%m-%d")))
            
            # Quantity (for this specific delivery)
            self.deliveries_table.setItem(i, 6, QTableWidgetItem(str(delivery.quantity)))
            
            # Notes
            notes = delivery.notes or ""
            self.deliveries_table.setItem(i, 7, QTableWidgetItem(notes))
            
            # Store delivery ID in the first column for easy access
            self.deliveries_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, delivery.id)
    
    def edit_delivery(self, row, column):
        """Edit the delivery when double-clicked"""
        delivery_id = self.deliveries_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        delivery = self.session.query(Delivery).get(delivery_id)
        
        if delivery:
            dialog = EditDeliveryDialog(self.session, delivery, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Refresh the table after editing
                self.load_deliveries()
        else:
            QMessageBox.warning(self, "Error", "Could not find the selected delivery")
    
    def get_delivery_summary(self):
        """Get a summary of all deliveries for this order"""
        total_deliveries = self.session.query(Delivery).join(OrderItem).filter(
            OrderItem.order_id == self.order.id
        ).count()
        
        total_quantity = self.session.query(Delivery).join(OrderItem).filter(
            OrderItem.order_id == self.order.id
        ).with_entities(func.sum(Delivery.quantity)).scalar() or 0
        
        return {
            'total_deliveries': total_deliveries,
            'total_quantity': total_quantity
        } 