from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLineEdit, QDateEdit, QMessageBox,
    QTableWidget, QTableWidgetItem, QLabel, QCheckBox,
    QFileDialog, QSpinBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from sqlalchemy.orm import Session
from datetime import datetime
import pandas as pd
import os
from pathlib import Path
from models.database import OrderItem, Delivery
from .box_split_dialog import BoxSplitDialog

class BatchDeliveryDialog(QDialog):
    def __init__(self, session: Session, order_items, parent=None):
        super().__init__(parent)
        self.session = session
        self.order_items = order_items
        self.box_quantities = {}  # Dictionary to store box quantities for each item
        self.setWindowTitle("Add Batch Delivery")
        self.setModal(True)
        
        # Set minimum size for the dialog
        self.setMinimumSize(1200, 600)
        
        # Set up export directory in Documents
        self.export_dir = os.path.join(str(Path.home()), "Documents", "OrdersApp", "exports")
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create items table
        self.table = QTableWidget()
        self.table.setColumnCount(9)  # Added Split Boxes column
        self.table.setHorizontalHeaderLabels([
            "Select",
            "Order",
            "Customer",
            "Customer Item Name",
            "Customer Item Code",
            "Total Qty",
            "Remaining",
            "Deliver Qty",
            "Split Boxes"  # New column
        ])
        
        # Set column widths
        self.table.setColumnWidth(0, 60)  # Select checkbox
        self.table.setColumnWidth(1, 120)  # Order
        self.table.setColumnWidth(2, 150)  # Customer
        self.table.setColumnWidth(3, 350)  # Customer Item Name
        self.table.setColumnWidth(4, 150)  # Customer Item Code
        self.table.setColumnWidth(5, 100)  # Total Qty
        self.table.setColumnWidth(6, 100)  # Remaining
        self.table.setColumnWidth(7, 100)  # Deliver Qty
        self.table.setColumnWidth(8, 100)  # Split Boxes
        
        # Populate table
        self.table.setRowCount(len(self.order_items))
        self.qty_inputs = []  # Store quantity inputs
        
        for i, item in enumerate(self.order_items):
            remaining = item.quantity - item.delivered_quantity
            
            # Create checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.table.setCellWidget(i, 0, checkbox)
            
            # Add other item details
            self.table.setItem(i, 1, QTableWidgetItem(item.order.order_number))
            self.table.setItem(i, 2, QTableWidgetItem(f"{item.order.customer.name_index} - {item.order.customer.name}"))
            
            # Combine customer item name with product name
            customer_item_name = item.item.customer_item_name or ""
            if customer_item_name and item.item.product.name:
                display_name = f"{customer_item_name} ({item.item.product.name})"
            else:
                display_name = customer_item_name or item.item.product.name or ""
            
            self.table.setItem(i, 3, QTableWidgetItem(display_name))
            self.table.setItem(i, 4, QTableWidgetItem(item.item.customer_code))
            self.table.setItem(i, 5, QTableWidgetItem(str(item.quantity)))
            self.table.setItem(i, 6, QTableWidgetItem(str(remaining)))
            
            # Add quantity input
            qty_input = QSpinBox()
            qty_input.setMinimum(1)
            qty_input.setMaximum(remaining)
            qty_input.setValue(remaining)
            self.qty_inputs.append(qty_input)
            self.table.setCellWidget(i, 7, qty_input)
            
            # Add split boxes button
            split_button = QPushButton("Split")
            split_button.clicked.connect(lambda checked, row=i: self.split_boxes(row))
            self.table.setCellWidget(i, 8, split_button)
        
        # Set row heights to be more comfortable
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, 30)
        
        layout.addWidget(self.table)
        
        # Add date input with some spacing
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Delivery Date:"))
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        date_layout.addWidget(self.date_input)
        date_layout.addStretch()
        
        # Add some vertical spacing
        date_container = QVBoxLayout()
        date_container.addSpacing(10)
        date_container.addLayout(date_layout)
        date_container.addSpacing(10)
        layout.addLayout(date_container)
        
        # Add buttons
        button_box = QHBoxLayout()
        
        save_button = QPushButton("Save")
        save_button.setMinimumWidth(100)
        save_button.clicked.connect(self.accept)
        
        export_button = QPushButton("Save & Export")
        export_button.setMinimumWidth(100)
        export_button.clicked.connect(self.save_and_export)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        
        button_box.addStretch()
        button_box.addWidget(save_button)
        button_box.addWidget(export_button)
        button_box.addWidget(cancel_button)
        layout.addLayout(button_box)
        
        # Set margins for the main layout
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)
    
    def get_data(self):
        deliveries = []
        delivery_date = self.date_input.date().toPyDate()
        
        for i, item in enumerate(self.order_items):
            checkbox = self.table.cellWidget(i, 0)
            if not checkbox.isChecked():
                continue
                
            qty_input = self.qty_inputs[i]
            try:
                quantity = int(qty_input.text() or "0")
                if quantity <= 0:
                    continue
                    
                remaining = item.quantity - item.delivered_quantity
                if quantity > remaining:
                    raise ValueError(f"Invalid quantity for {item.order.order_number}: {quantity} > {remaining}")
                    
                deliveries.append({
                    "order_item": item,
                    "quantity": quantity,
                    "delivery_date": delivery_date,
                    "boxes": self.box_quantities.get(i, [quantity])  # Include box quantities if split
                })
                
            except ValueError as e:
                QMessageBox.warning(self, "Validation Error", str(e))
                return None
        
        if not deliveries:
            QMessageBox.warning(self, "Validation Error", "No valid deliveries specified")
            return None
            
        return deliveries
        
    def save_and_export(self):
        deliveries = self.get_data()
        if not deliveries:
            return
            
        # Get directory for saving files
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory for Delivery Exports"
        )
        
        if not directory:
            return
            
        delivery_date = deliveries[0]["delivery_date"]
        
        # Group deliveries by customer
        customer_deliveries = {}
        for delivery in deliveries:
            item = delivery["order_item"]
            customer = item.order.customer
            if customer.id not in customer_deliveries:
                customer_deliveries[customer.id] = {
                    "customer": customer,
                    "deliveries": []
                }
            customer_deliveries[customer.id]["deliveries"].append(delivery)
        
        try:
            # Create an Excel file for each customer
            for customer_data in customer_deliveries.values():
                customer = customer_data["customer"]
                customer_deliveries = customer_data["deliveries"]
                
                # Create filename with date and customer
                filename = f"delivery_{delivery_date.strftime('%Y%m%d')}_{customer.name_index}.xlsx"
                file_path = os.path.join(directory, filename)
                
                # Create export data for this customer
                export_data = []
                for delivery in customer_deliveries:
                    item = delivery["order_item"]
                    export_data.append({
                        "Delivery Date": delivery["delivery_date"].strftime("%Y-%m-%d"),
                        "Order Number": item.order.order_number,
                        "Item Code": item.item.customer_code,
                        "Product Name": item.item.product.name,
                        "Quantity": delivery["quantity"]
                    })
                
                # Create DataFrame and export to Excel
                if export_data:
                    df = pd.DataFrame(export_data)
                    df.to_excel(file_path, index=False)
            
            # Save deliveries to database
            delivery_date = self.date_input.date().toPyDate()
            for delivery in deliveries:
                order_item = delivery["order_item"]
                quantity = delivery["quantity"]
                
                delivery_obj = Delivery(
                    order_item_id=order_item.id,
                    quantity=quantity,
                    delivery_date=delivery_date
                )
                self.session.add(delivery_obj)
                order_item.delivered_quantity += quantity
                order_item.last_delivery_date = delivery_date
            
            self.session.commit()
            
            QMessageBox.information(
                self,
                "Export Complete",
                f"Exported {len(customer_deliveries)} delivery files to {directory}"
            )
            
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Export Error", f"Error exporting deliveries: {str(e)}")
    
    def split_boxes(self, row):
        quantity = self.qty_inputs[row].value()
        item = self.order_items[row]
        item_name = item.item.customer_item_name or item.item.product.name
        
        dialog = BoxSplitDialog(item_name, quantity, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.box_quantities[row] = dialog.get_box_quantities()
            split_button = self.table.cellWidget(row, 8)
            split_button.setText(f"Split ({len(self.box_quantities[row])} boxes)")
    
    def open_export_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.export_dir)) 