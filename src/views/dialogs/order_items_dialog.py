from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QDateEdit, QLabel,
    QSpinBox, QDoubleSpinBox, QHeaderView
)
from PyQt6.QtCore import Qt, QDate
from sqlalchemy.orm import Session
from datetime import datetime, date
from models.database import Order, OrderItem, Customer, Item, Product
from utils.permissions import get_permissions_manager

class OrderItemsDialog(QDialog):
    def __init__(self, session: Session, order: Order, parent=None, user=None):
        super().__init__(parent)
        self.session = session
        self.order = order
        self.user = user
        self.permissions_manager = get_permissions_manager()
        self.setWindowTitle(f"Order Items - {order.order_number}")
        self.setModal(True)
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Order header
        header_layout = QHBoxLayout()
        order_info = QLabel(f"Order: {self.order.order_number} | Customer: {self.order.customer.name_index} - {self.order.customer.name}")
        order_info.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(order_info)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Items table
        self.items_table = QTableWidget()
        
        # Check if user can see prices
        self.can_see_prices = True
        if self.user:
            self.can_see_prices = self.permissions_manager.can_access_column(self.user, "orders", "prices")
        
        if self.can_see_prices:
            self.items_table.setColumnCount(8)
            self.items_table.setHorizontalHeaderLabels([
                "Item", "Customer Code", "Quantity", "Price",
                "Delivery Date", "Delivered", "Last Delivery", "Surface Treatment"
            ])
        else:
            self.items_table.setColumnCount(7)
            self.items_table.setHorizontalHeaderLabels([
                "Item", "Customer Code", "Quantity",
                "Delivery Date", "Delivered", "Last Delivery", "Surface Treatment"
            ])
        
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.items_table.setSortingEnabled(True)
        
        # Set column widths
        self.items_table.setColumnWidth(0, 200)  # Item
        self.items_table.setColumnWidth(1, 120)  # Customer Code
        self.items_table.setColumnWidth(2, 80)   # Quantity
        if self.can_see_prices:
            self.items_table.setColumnWidth(3, 80)   # Price
            self.items_table.setColumnWidth(4, 100)  # Delivery Date
            self.items_table.setColumnWidth(5, 80)   # Delivered
            self.items_table.setColumnWidth(6, 100)  # Last Delivery
            self.items_table.setColumnWidth(7, 120)  # Surface Treatment
        else:
            self.items_table.setColumnWidth(3, 100)  # Delivery Date
            self.items_table.setColumnWidth(4, 80)   # Delivered
            self.items_table.setColumnWidth(5, 100)  # Last Delivery
            self.items_table.setColumnWidth(6, 120)  # Surface Treatment
        
        layout.addWidget(self.items_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        edit_button = QPushButton("Edit Selected Item")
        edit_button.clicked.connect(self.edit_selected_item)
        button_layout.addWidget(edit_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Populate table
        self.populate_table()
        
        # Connect double-click to edit
        self.items_table.cellDoubleClicked.connect(self.on_cell_double_clicked)
    
    def populate_table(self):
        """Populate the table with order items"""
        self.items_table.setRowCount(len(self.order.items))
        
        for i, item in enumerate(self.order.items):
            col_index = 0
            
            # Item name
            item_name = f"{item.item.customer_item_name or item.item.product.name} ({item.item.product.name})"
            self.items_table.setItem(i, col_index, QTableWidgetItem(item_name))
            col_index += 1
            
            # Customer code
            self.items_table.setItem(i, col_index, QTableWidgetItem(item.item.customer_code))
            col_index += 1
            
            # Quantity
            self.items_table.setItem(i, col_index, QTableWidgetItem(str(item.quantity)))
            col_index += 1
            
            # Price (if user can see prices)
            if self.can_see_prices:
                if item.price is None or item.price == 0.0:
                    price_display = ""
                else:
                    price_display = f"{item.price:.2f}" if item.price % 1 == 0 else str(item.price)
                self.items_table.setItem(i, col_index, QTableWidgetItem(price_display))
                col_index += 1
            
            # Delivery date
            delivery_date = item.delivery_date.strftime("%Y-%m-%d") if item.delivery_date else ""
            self.items_table.setItem(i, col_index, QTableWidgetItem(delivery_date))
            col_index += 1
            
            # Delivered quantity
            self.items_table.setItem(i, col_index, QTableWidgetItem(str(item.delivered_quantity or 0)))
            col_index += 1
            
            # Last delivery date
            last_delivery = item.last_delivery_date.strftime("%Y-%m-%d") if item.last_delivery_date else ""
            self.items_table.setItem(i, col_index, QTableWidgetItem(last_delivery))
            col_index += 1
            
            # Surface treatment
            surface_treatment = item.surface_treatment or "KATAFOREZA"
            self.items_table.setItem(i, col_index, QTableWidgetItem(surface_treatment))
            
            # Store order item ID in the first column for easy access
            self.items_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, item.id)
    
    def get_selected_item(self):
        """Get the currently selected order item"""
        selected_rows = self.items_table.selectedItems()
        if not selected_rows:
            return None
            
        row = selected_rows[0].row()
        order_item_id = self.items_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        return self.session.query(OrderItem).get(order_item_id)
    
    def edit_selected_item(self):
        """Edit the selected order item"""
        order_item = self.get_selected_item()
        if not order_item:
            QMessageBox.warning(self, "Warning", "Please select an item to edit")
            return
        
        dialog = EditOrderItemDialog(self.session, order_item, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.populate_table()  # Refresh the table
    
    def on_cell_double_clicked(self, row, column):
        """Handle double-click to edit the item"""
        if column == 0:  # Don't edit if double-clicked on the item name column
            return
        
        order_item_id = self.items_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        order_item = self.session.query(OrderItem).get(order_item_id)
        
        if order_item:
            dialog = EditOrderItemDialog(self.session, order_item, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.populate_table()  # Refresh the table


class EditOrderItemDialog(QDialog):
    def __init__(self, session: Session, order_item: OrderItem, parent=None):
        super().__init__(parent)
        self.session = session
        self.order_item = order_item
        self.setWindowTitle("Edit Order Item")
        self.setModal(True)
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        
        # Item information (read-only)
        item_info = QLabel(f"{self.order_item.item.customer_code} - {self.order_item.item.customer_item_name or self.order_item.item.product.name}")
        item_info.setStyleSheet("font-weight: bold; color: #333;")
        layout.addRow("Item:", item_info)
        
        # Order information (read-only)
        order_info = QLabel(f"{self.order_item.order.order_number} ({self.order_item.order.customer.name_index})")
        order_info.setStyleSheet("font-weight: bold; color: #333;")
        layout.addRow("Order:", order_info)
        
        # Quantity
        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(1)
        self.quantity_input.setMaximum(999999)
        self.quantity_input.setValue(self.order_item.quantity)
        layout.addRow("Quantity:", self.quantity_input)
        
        # Price (always show, but may be hidden from view in tables)
        self.price_input = QDoubleSpinBox()
        self.price_input.setMinimum(0.0)
        self.price_input.setMaximum(999999.99)
        self.price_input.setDecimals(2)
        self.price_input.setValue(self.order_item.price or 0.0)
        layout.addRow("Price:", self.price_input)
        
        # Delivery date
        self.delivery_date_input = QDateEdit()
        self.delivery_date_input.setCalendarPopup(True)
        self.delivery_date_input.setDate(self.order_item.delivery_date)
        layout.addRow("Delivery Date:", self.delivery_date_input)
        
        # Surface treatment
        self.surface_treatment_combo = QComboBox()
        self.surface_treatment_combo.addItems(["KATAFOREZA", "FOSFAT", "ZINEK", "NONE"])
        current_treatment = self.order_item.surface_treatment or "KATAFOREZA"
        index = self.surface_treatment_combo.findText(current_treatment)
        if index >= 0:
            self.surface_treatment_combo.setCurrentIndex(index)
        layout.addRow("Surface Treatment:", self.surface_treatment_combo)
        
        # Add note about surface treatment
        treatment_note = QLabel("Note: Surface treatment will not be automatically recalculated when changing price or quantity.")
        treatment_note.setStyleSheet("color: #666; font-size: 10px;")
        layout.addRow("", treatment_note)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_changes)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addRow(button_layout)
        
        self.setLayout(layout)
    
    def save_changes(self):
        """Save changes to the order item"""
        try:
            # Get the new surface treatment value
            new_surface_treatment = self.surface_treatment_combo.currentText()
            
            # Update order item
            self.order_item.quantity = self.quantity_input.value()
            self.order_item.price = self.price_input.value()
            self.order_item.delivery_date = self.delivery_date_input.date().toPyDate()
            self.order_item.surface_treatment = new_surface_treatment
            
            # Update the timestamp
            self.order_item.updated_at = datetime.now()
            
            # Commit changes
            self.session.commit()
            
            QMessageBox.information(self, "Success", "Order item updated successfully!")
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error updating order item: {str(e)}") 