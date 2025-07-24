from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox,
    QDialog, QFormLayout, QDateEdit, QCheckBox, QLabel,
    QProgressDialog
)
from PyQt6.QtCore import Qt, QDate
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, date
import pandas as pd
import os
from models.database import Order, Customer, Item, OrderItem, Delivery

class BatchDeliveryTab(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create toolbar
        toolbar = QHBoxLayout()
        
        self.select_all_button = QPushButton("Select All Incomplete")
        self.select_all_button.clicked.connect(self.select_all_incomplete)
        toolbar.addWidget(self.select_all_button)
        
        deliver_button = QPushButton("Deliver Selected")
        deliver_button.clicked.connect(self.deliver_selected)
        toolbar.addWidget(deliver_button)
        
        export_button = QPushButton("Export Selected")
        export_button.clicked.connect(self.export_selected)
        toolbar.addWidget(export_button)
        
        # Add search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search items...")
        self.search_input.textChanged.connect(self.search_items)
        toolbar.addWidget(self.search_input)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Select",
            "Customer",
            "Order Number",
            "Item Name",
            "Order Date",
            "Delivery Date",
            "Ordered",
            "Delivered",
            "Remaining"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Set column widths
        self.table.setColumnWidth(0, 60)   # Select
        self.table.setColumnWidth(1, 200)  # Customer
        self.table.setColumnWidth(2, 120)  # Order Number
        self.table.setColumnWidth(3, 250)  # Item Name
        self.table.setColumnWidth(4, 100)  # Order Date
        self.table.setColumnWidth(5, 100)  # Delivery Date
        self.table.setColumnWidth(6, 80)   # Ordered
        self.table.setColumnWidth(7, 80)   # Delivered
        self.table.setColumnWidth(8, 80)   # Remaining
        
        layout.addWidget(self.table)
        self.setLayout(layout)
        
        # Load initial data
        self.refresh_data()
    
    def populate_table(self, order_items):
        self.table.setRowCount(len(order_items))
        
        for i, order_item in enumerate(order_items):
            # Create checkbox for selection
            checkbox = QCheckBox()
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            
            remaining = order_item.quantity - order_item.delivered_quantity
            if remaining <= 0:
                checkbox.setEnabled(False)
            
            customer = QTableWidgetItem(order_item.order.customer.name)
            order_number = QTableWidgetItem(order_item.order.order_number)
            item_name = QTableWidgetItem(order_item.item.customer_item_name or order_item.item.product.name)
            order_date = QTableWidgetItem(order_item.order.order_date.strftime("%Y-%m-%d"))
            delivery_date = QTableWidgetItem(order_item.delivery_date.strftime("%Y-%m-%d"))
            ordered = QTableWidgetItem(str(order_item.quantity))
            delivered = QTableWidgetItem(str(order_item.delivered_quantity))
            remaining_item = QTableWidgetItem(str(remaining))
            
            self.table.setCellWidget(i, 0, checkbox_widget)
            self.table.setItem(i, 1, customer)
            self.table.setItem(i, 2, order_number)
            self.table.setItem(i, 3, item_name)
            self.table.setItem(i, 4, order_date)
            self.table.setItem(i, 5, delivery_date)
            self.table.setItem(i, 6, ordered)
            self.table.setItem(i, 7, delivered)
            self.table.setItem(i, 8, remaining_item)
    
    def refresh_data(self):
        order_items = self.session.query(OrderItem).join(Order).join(Customer).join(Item).order_by(
            Customer.name,
            Order.order_date.desc()
        ).all()
        self.populate_table(order_items)
    
    def search_items(self, text):
        if not text:
            self.refresh_data()
            return
            
        search = f"%{text}%"
        order_items = self.session.query(OrderItem).join(Order).join(Customer).join(Item).filter(
            or_(
                Customer.name.ilike(search),
                Order.order_number.ilike(search),
                Item.customer_item_name.ilike(search)
            )
        ).order_by(
            Customer.name,
            Order.order_date.desc()
        ).all()
        
        self.populate_table(order_items)
    
    def get_selected_items(self):
        selected_items = []
        for i in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(i, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                order_number = self.table.item(i, 2).text()
                item_name = self.table.item(i, 3).text()
                order_item = self.session.query(OrderItem).join(Order).join(Item).filter(
                    Order.order_number == order_number,
                    Item.customer_item_name == item_name
                ).first()
                if order_item:
                    selected_items.append(order_item)
        return selected_items
    
    def select_all_incomplete(self):
        for i in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(i, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox and checkbox.isEnabled():
                checkbox.setChecked(True)
    
    def deliver_selected(self):
        selected_items = self.get_selected_items()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select items to deliver")
            return
            
        # Create delivery dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Batch Delivery")
        dialog.setModal(True)
        
        layout = QFormLayout()
        delivery_date = QDateEdit()
        delivery_date.setCalendarPopup(True)
        delivery_date.setDate(QDate.currentDate())
        layout.addRow("Delivery Date:", delivery_date)
        
        button_box = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_box.addStretch()
        button_box.addWidget(save_button)
        button_box.addWidget(cancel_button)
        layout.addRow("", button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            progress = QProgressDialog("Processing deliveries...", None, 0, len(selected_items), self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            
            try:
                for i, order_item in enumerate(selected_items):
                    remaining = order_item.quantity - order_item.delivered_quantity
                    if remaining > 0:
                        delivery = Delivery(
                            order_item_id=order_item.id,
                            quantity=remaining,
                            delivery_date=delivery_date.date().toPyDate()
                        )
                        self.session.add(delivery)
                        order_item.delivered_quantity += remaining
                        order_item.last_delivery_date = delivery_date.date().toPyDate()
                    
                    progress.setValue(i + 1)
                
                self.session.commit()
                self.refresh_data()
                QMessageBox.information(self, "Success", "Batch delivery completed successfully")
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error processing deliveries: {str(e)}")
            finally:
                progress.close()
    
    def export_selected(self):
        selected_items = self.get_selected_items()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select items to export")
            return
            
        # Group items by customer
        customer_items = {}
        for order_item in selected_items:
            customer = order_item.order.customer
            if customer not in customer_items:
                customer_items[customer] = []
            customer_items[customer].append(order_item)
        
        # Create exports directory if it doesn't exist
        if not os.path.exists("exports"):
            os.makedirs("exports")
        
        # Export one file per customer
        try:
            for customer, items in customer_items.items():
                data = []
                for item in items:
                    remaining = item.quantity - item.delivered_quantity
                    data.append({
                        "Order Number": item.order.order_number,
                        "Item Name": item.item.customer_item_name or item.item.product.name,
                        "Order Date": item.order.order_date,
                        "Delivery Date": item.delivery_date,
                        "Ordered": item.quantity,
                        "Delivered": item.delivered_quantity,
                        "Remaining": remaining
                    })
                
                df = pd.DataFrame(data)
                filename = f"exports/{customer.name_index}_{date.today().strftime('%Y%m%d')}.xlsx"
                df.to_excel(filename, index=False)
            
            QMessageBox.information(self, "Success", "Export completed successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error exporting data: {str(e)}") 