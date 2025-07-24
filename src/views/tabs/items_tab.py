from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QLineEdit, QMessageBox, QLabel, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from models.database import Item, Customer, Product
from utils.permissions import get_permissions_manager

class ItemDialog(QDialog):
    def __init__(self, session: Session, item=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.item = item
        self.setWindowTitle("Add Item" if not item else "Edit Item")
        self.setModal(True)
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        
        # Create fields
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(200)  # Make dropdown wider
        self.product_combo = QComboBox()
        self.product_combo.setMinimumWidth(200)  # Make dropdown wider
        self.customer_code = QLineEdit()
        self.customer_item_name = QLineEdit()
        self.item_type = QLineEdit()
        self.similar_item = QLineEdit()
        
        # Populate combos
        customers = self.session.query(Customer).order_by(Customer.name).all()
        for customer in customers:
            self.customer_combo.addItem(customer.name, customer.id)
            
        products = self.session.query(Product).order_by(Product.name).all()
        for product in products:
            self.product_combo.addItem(product.name, product.id)
        
        # Add fields to layout
        layout.addRow("Customer*:", self.customer_combo)
        layout.addRow("Product*:", self.product_combo)
        layout.addRow("Customer Code*:", self.customer_code)
        layout.addRow("Customer Item Name:", self.customer_item_name)
        layout.addRow("Item Type:", self.item_type)
        layout.addRow("Similar Item:", self.similar_item)
        
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
        if self.item:
            index = self.customer_combo.findData(self.item.customer_id)
            if index >= 0:
                self.customer_combo.setCurrentIndex(index)
                
            index = self.product_combo.findData(self.item.product_id)
            if index >= 0:
                self.product_combo.setCurrentIndex(index)
                
            self.customer_code.setText(self.item.customer_code)
            self.customer_item_name.setText(self.item.customer_item_name or "")
            self.item_type.setText(self.item.item_type or "")
            self.similar_item.setText(self.item.similar_item or "")
        
        self.setLayout(layout)
    
    def get_data(self):
        if not self.customer_code.text().strip():
            QMessageBox.warning(self, "Validation Error", "Customer code is required")
            return None
            
        return {
            "customer_id": self.customer_combo.currentData(),
            "product_id": self.product_combo.currentData(),
            "customer_code": self.customer_code.text().strip(),
            "customer_item_name": self.customer_item_name.text().strip() or None,
            "item_type": self.item_type.text().strip() or None,
            "similar_item": self.similar_item.text().strip() or None
        }

class ItemsTab(QWidget):
    item_updated = pyqtSignal()
    
    def __init__(self, session: Session, user=None):
        super().__init__()
        self.session = session
        self.user = user
        self.permissions_manager = get_permissions_manager()
        self.items_data = []  # Store items data for operations
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create toolbar
        toolbar = QHBoxLayout()
        
        # Add buttons based on permissions
        if not self.user or self.permissions_manager.has_permission(self.user, "items", "create"):
            add_button = QPushButton("Add Item")
            add_button.clicked.connect(self.add_item)
            toolbar.addWidget(add_button)
        
        if not self.user or self.permissions_manager.has_permission(self.user, "items", "edit"):
            edit_button = QPushButton("Edit Item")
            edit_button.clicked.connect(self.edit_item)
            toolbar.addWidget(edit_button)
        
        if not self.user or self.permissions_manager.has_permission(self.user, "items", "delete"):
            delete_button = QPushButton("Delete Item")
            delete_button.clicked.connect(self.delete_item)
            toolbar.addWidget(delete_button)
        
        # Add search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search items...")
        self.search_input.textChanged.connect(self.search_items)
        toolbar.addWidget(self.search_input)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Customer",
            "Product",
            "Customer Code",
            "Customer Item Name",
            "Item Type",
            "Similar Item",
            "Orders"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        
        # Set column widths
        self.table.setColumnWidth(0, 200)  # Customer
        self.table.setColumnWidth(1, 200)  # Product
        self.table.setColumnWidth(2, 120)  # Customer Code
        self.table.setColumnWidth(3, 200)  # Customer Item Name
        self.table.setColumnWidth(4, 100)  # Item Type
        self.table.setColumnWidth(5, 150)  # Similar Item
        self.table.setColumnWidth(6, 80)   # Orders
        
        layout.addWidget(self.table)
        self.setLayout(layout)
        
        # Load initial data
        self.refresh_data()
    
    def populate_table(self, items):
        self.items_data = items  # Store items for operations
        self.table.setRowCount(len(items))
        
        for i, item in enumerate(items):
            customer = QTableWidgetItem(f"{item.customer.name_index} - {item.customer.name}")
            product = QTableWidgetItem(item.product.name)
            customer_code = QTableWidgetItem(item.customer_code)
            customer_item_name = QTableWidgetItem(item.customer_item_name or "")
            item_type = QTableWidgetItem(item.item_type or "")
            similar_item = QTableWidgetItem(item.similar_item or "")
            orders = QTableWidgetItem(str(len(item.order_items)))
            
            # Store item ID in the first column for easy access
            customer.setData(Qt.ItemDataRole.UserRole, item.id)
            
            self.table.setItem(i, 0, customer)
            self.table.setItem(i, 1, product)
            self.table.setItem(i, 2, customer_code)
            self.table.setItem(i, 3, customer_item_name)
            self.table.setItem(i, 4, item_type)
            self.table.setItem(i, 5, similar_item)
            self.table.setItem(i, 6, orders)
    
    def get_selected_item(self):
        """Get the currently selected item from the table"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return None
            
        # Get the row index
        row = selected_rows[0].row()
        
        # Get item ID from the first column
        item_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if item_id is None:
            return None
            
        # Find the item in our stored data
        for item in self.items_data:
            if item.id == item_id:
                return item
                
        return None
    
    def refresh_data(self):
        try:
            items = self.session.query(Item).join(Customer).join(Product).order_by(
                Customer.name,
                Product.name
            ).all()
            print(f"Refreshing data: found {len(items)} items")
            self.populate_table(items)
        except Exception as e:
            print(f"Error refreshing data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error refreshing data: {str(e)}")
    
    def search_items(self, text):
        try:
            if not text:
                print("Search text is empty, refreshing data")
                # Clear the table first
                self.table.clearContents()
                self.table.setRowCount(0)
                # Then refresh data
                self.refresh_data()
                return
                
            search = f"%{text}%"
            items = self.session.query(Item).join(Customer).join(Product).filter(
                or_(
                    Customer.name.ilike(search),
                    Customer.name_index.ilike(search),
                    Product.name.ilike(search),
                    Item.customer_code.ilike(search),
                    Item.customer_item_name.ilike(search)
                )
            ).order_by(
                Customer.name,
                Product.name
            ).all()
            
            print(f"Search '{text}': found {len(items)} items")
            self.populate_table(items)
        except Exception as e:
            print(f"Error searching items: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error searching items: {str(e)}")
    
    def add_item(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "items", "create"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to add items.")
            return
            
        dialog = ItemDialog(self.session, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                item = Item(**data)
                try:
                    self.session.add(item)
                    self.session.commit()
                    self.refresh_data()
                    self.item_updated.emit()
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error adding item: {str(e)}")
    
    def edit_item(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "items", "edit"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit items.")
            return
            
        item = self.get_selected_item()
        if not item:
            QMessageBox.warning(self, "Warning", "Please select an item to edit")
            return
        
        dialog = ItemDialog(self.session, item, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    for key, value in data.items():
                        setattr(item, key, value)
                    self.session.commit()
                    self.refresh_data()
                    self.item_updated.emit()
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error updating item: {str(e)}")
    
    def delete_item(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "items", "delete"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete items.")
            return
            
        item = self.get_selected_item()
        if not item:
            QMessageBox.warning(self, "Warning", "Please select an item to delete")
            return
        
        if len(item.order_items) > 0:
            QMessageBox.warning(
                self,
                "Cannot Delete",
                f"This item is used in {len(item.order_items)} orders. Please remove these orders first."
            )
            return
            
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this item?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.session.delete(item)
                self.session.commit()
                self.refresh_data()
                self.item_updated.emit()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error deleting item: {str(e)}") 