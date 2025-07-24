from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox,
    QDialog, QFormLayout, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from models.database import Product
from utils.permissions import get_permissions_manager
from views.dialogs.product_components_dialog import ProductComponentsDialog


class ProductDialog(QDialog):
    def __init__(self, session: Session, product=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.product = product
        self.setWindowTitle("Add Product" if not product else "Edit Product")
        self.setModal(True)
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        
        # Create fields
        self.name = QLineEdit()
        self.description = QLineEdit()
        self.weight = QDoubleSpinBox()
        self.weight.setDecimals(3)
        self.weight.setMaximum(10000.0)
        
        # Add fields to layout
        layout.addRow("Name*:", self.name)
        layout.addRow("Description:", self.description)
        layout.addRow("Weight (kg):", self.weight)
        
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
        if self.product:
            self.name.setText(self.product.name)
            self.description.setText(self.product.description or "")
            if self.product.weight_per_unit:
                self.weight.setValue(self.product.weight_per_unit)
        
        self.setLayout(layout)
    
    def get_data(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required")
            return None
            
        return {
            "name": self.name.text().strip(),
            "description": self.description.text().strip() or None,
            "weight_per_unit": self.weight.value() if self.weight.value() > 0 else None
        }

class ProductsTab(QWidget):
    product_updated = pyqtSignal()
    
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
        if not self.user or self.permissions_manager.has_permission(self.user, "products", "create"):
            add_button = QPushButton("Add Product")
            add_button.clicked.connect(self.add_product)
            toolbar.addWidget(add_button)
        
        if not self.user or self.permissions_manager.has_permission(self.user, "products", "edit"):
            edit_button = QPushButton("Edit Product")
            edit_button.clicked.connect(self.edit_product)
            toolbar.addWidget(edit_button)
        
        if not self.user or self.permissions_manager.has_permission(self.user, "products", "delete"):
            delete_button = QPushButton("Delete Product")
            delete_button.clicked.connect(self.delete_product)
            toolbar.addWidget(delete_button)
        
        # Add Manage Components button
        self.manage_components_button = QPushButton("Manage Components")
        self.manage_components_button.clicked.connect(self.manage_components)
        # Disable for user/viewer
        if not self.permissions_manager.can_access_feature(self.user, "manage_components"):
            self.manage_components_button.setEnabled(False)
        toolbar.addWidget(self.manage_components_button)
        
        # Add search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search products...")
        self.search_input.textChanged.connect(self.search_products)
        toolbar.addWidget(self.search_input)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Name",
            "Description",
            "Weight (kg)",
            "Items Using"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        
        # Set column widths
        self.table.setColumnWidth(0, 200)  # Name
        self.table.setColumnWidth(1, 300)  # Description
        self.table.setColumnWidth(2, 100)  # Weight
        self.table.setColumnWidth(3, 100)  # Items Using
        
        layout.addWidget(self.table)
        self.setLayout(layout)
        
        # Load initial data
        self.refresh_data()
    
    def populate_table(self, products):
        self.table.setRowCount(len(products))
        
        for i, product in enumerate(products):
            name = QTableWidgetItem(product.name)
            description = QTableWidgetItem(product.description or "")
            weight = QTableWidgetItem(f"{product.weight_per_unit:.3f}" if product.weight_per_unit else "")
            items_using = QTableWidgetItem(str(len(product.items)))
            
            self.table.setItem(i, 0, name)
            self.table.setItem(i, 1, description)
            self.table.setItem(i, 2, weight)
            self.table.setItem(i, 3, items_using)
    
    def refresh_data(self):
        products = self.session.query(Product).order_by(Product.name).all()
        self.populate_table(products)
    
    def search_products(self, text):
        if not text:
            self.refresh_data()
            return
            
        search = f"%{text}%"
        products = self.session.query(Product).filter(
            or_(
                Product.name.ilike(search),
                Product.description.ilike(search)
            )
        ).order_by(Product.name).all()
        
        self.populate_table(products)
    
    def add_product(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "products", "create"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to add products.")
            return
            
        dialog = ProductDialog(self.session, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                product = Product(**data)
                try:
                    self.session.add(product)
                    self.session.commit()
                    self.refresh_data()
                    self.product_updated.emit()
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error adding product: {str(e)}")
    
    def edit_product(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "products", "edit"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit products.")
            return
            
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a product to edit")
            return
            
        name = self.table.item(selected_rows[0].row(), 0).text()
        product = self.session.query(Product).filter(Product.name == name).first()
        
        dialog = ProductDialog(self.session, product, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    for key, value in data.items():
                        setattr(product, key, value)
                    self.session.commit()
                    self.refresh_data()
                    self.product_updated.emit()
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error updating product: {str(e)}")
    
    def delete_product(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "products", "delete"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete products.")
            return
            
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a product to delete")
            return
            
        name = self.table.item(selected_rows[0].row(), 0).text()
        product = self.session.query(Product).filter(Product.name == name).first()
        
        if len(product.items) > 0:
            QMessageBox.warning(
                self,
                "Cannot Delete",
                f"This product is used by {len(product.items)} items. Please remove these items first."
            )
            return
            
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this product?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.session.delete(product)
                self.session.commit()
                self.refresh_data()
                self.product_updated.emit()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error deleting product: {str(e)}")
    
    def manage_components(self):
        """Open the product components management dialog"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a product to manage components")
            return
            
        name = self.table.item(selected_rows[0].row(), 0).text()
        product = self.session.query(Product).filter(Product.name == name).first()
        
        if product:
            dialog = ProductComponentsDialog(self.session, product, self)
            dialog.exec()
        else:
            QMessageBox.warning(self, "Error", "Product not found")
    
 