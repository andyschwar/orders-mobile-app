from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox,
    QDialog, QFormLayout, QDoubleSpinBox, QSplitter, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from models.database import Product
from utils.permissions import get_permissions_manager
from utils.database_decorators import with_connection_test
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
        
        # Add Refresh Components button (for manual refresh)
        self.refresh_components_button = QPushButton("Refresh Components")
        self.refresh_components_button.clicked.connect(self.manage_components)
        # Disable for user/viewer
        if not self.permissions_manager.can_access_feature(self.user, "manage_components"):
            self.refresh_components_button.setEnabled(False)
        toolbar.addWidget(self.refresh_components_button)
        
        # Add Edit Components button
        self.edit_components_button = QPushButton("Edit Components")
        self.edit_components_button.clicked.connect(self.edit_components)
        # Disable for user/viewer
        if not self.permissions_manager.can_access_feature(self.user, "manage_components"):
            self.edit_components_button.setEnabled(False)
        toolbar.addWidget(self.edit_components_button)
        
        # Add search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search products...")
        self.search_input.textChanged.connect(self.search_products)
        toolbar.addWidget(self.search_input)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Create horizontal splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Products
        products_group = QGroupBox("Products")
        products_layout = QVBoxLayout()
        
        # Create products table
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
        
        # Connect selection change to auto-update components
        self.table.itemSelectionChanged.connect(self.on_product_selection_changed)
        
        # Set column widths
        self.table.setColumnWidth(0, 200)  # Name
        self.table.setColumnWidth(1, 300)  # Description
        self.table.setColumnWidth(2, 100)  # Weight
        self.table.setColumnWidth(3, 100)  # Items Using
        
        products_layout.addWidget(self.table)
        products_group.setLayout(products_layout)
        splitter.addWidget(products_group)
        
        # Right panel - Components
        components_group = QGroupBox("Components")
        components_layout = QVBoxLayout()
        
        # Create components table
        self.components_table = QTableWidget()
        
        # Determine visible columns based on permissions
        # For user and viewer accounts, hide cost information
        if self.user and self.user.role.value in ['user', 'viewer']:
            self.show_costs = False
        else:
            self.show_costs = self.permissions_manager.can_access_column(self.user, "components", "unit_cost")
        
        if self.show_costs:
            self.components_table.setColumnCount(4)
            self.components_table.setHorizontalHeaderLabels([
                "Component Name",
                "Quantity",
                "Unit Cost (CZK)",
                "Total Cost (CZK)"
            ])
        else:
            self.components_table.setColumnCount(2)
            self.components_table.setHorizontalHeaderLabels([
                "Component Name",
                "Quantity"
            ])
        self.components_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.components_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.components_table.setSortingEnabled(True)
        
        components_layout.addWidget(self.components_table)
        components_group.setLayout(components_layout)
        splitter.addWidget(components_group)
        
        # Set splitter proportions (60% products, 40% components)
        splitter.setSizes([600, 400])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # Load initial data
        self.refresh_data()
        
        # Initialize components table
        self.clear_components_table()
    
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
    
    @with_connection_test
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
    
    @with_connection_test
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
    
    @with_connection_test
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
    
    @with_connection_test
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
    
    def on_product_selection_changed(self):
        """Automatically update components when product selection changes"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            self.clear_components_table()
            return
            
        name = self.table.item(selected_rows[0].row(), 0).text()
        product = self.session.query(Product).filter(Product.name == name).first()
        
        if product:
            self.populate_components_table(product)
        else:
            self.clear_components_table()
    
    def manage_components(self):
        """Show components for selected product in the right panel (legacy method)"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a product to view components")
            return
            
        name = self.table.item(selected_rows[0].row(), 0).text()
        product = self.session.query(Product).filter(Product.name == name).first()
        
        if product:
            self.populate_components_table(product)
        else:
            QMessageBox.warning(self, "Error", "Product not found")
    
    def populate_components_table(self, product):
        """Populate the components table with product components"""
        from models.database import ProductComponent, Component
        
        # Get all components for this product
        product_components = self.session.query(ProductComponent).filter(
            ProductComponent.product_id == product.id
        ).all()
        
        self.components_table.setRowCount(len(product_components))
        
        total_cost = 0.0
        
        for i, pc in enumerate(product_components):
            component = pc.component
            
            # Component Name
            name_item = QTableWidgetItem(component.name)
            self.components_table.setItem(i, 0, name_item)
            
            # Quantity
            quantity_item = QTableWidgetItem(str(pc.quantity))
            self.components_table.setItem(i, 1, quantity_item)
            
            # Only show costs if user has permission
            if self.show_costs:
                # Unit Cost
                unit_cost = component.unit_cost or 0.0
                unit_cost_item = QTableWidgetItem(f"{unit_cost:.2f}")
                self.components_table.setItem(i, 2, unit_cost_item)
                
                # Total Cost
                total_item_cost = unit_cost * pc.quantity
                total_cost += total_item_cost
                total_cost_item = QTableWidgetItem(f"{total_item_cost:.2f}")
                self.components_table.setItem(i, 3, total_cost_item)
            else:
                # Calculate total cost for title but don't display it
                unit_cost = component.unit_cost or 0.0
                total_item_cost = unit_cost * pc.quantity
                total_cost += total_item_cost
        
        # Update the group box title
        components_group = None
        for child in self.findChildren(QGroupBox):
            if "Components" in child.title():
                components_group = child
                break
        if components_group:
            if product_components:
                if self.show_costs:
                    components_group.setTitle(f"Components - {product.name} (Total: {total_cost:.2f} CZK)")
                else:
                    components_group.setTitle(f"Components - {product.name}")
            else:
                components_group.setTitle(f"Components - {product.name} (No components)")
    
    def edit_components(self):
        """Open the product components management dialog for editing"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a product to edit components")
            return
            
        name = self.table.item(selected_rows[0].row(), 0).text()
        product = self.session.query(Product).filter(Product.name == name).first()
        
        if product:
            dialog = ProductComponentsDialog(self.session, product, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Refresh the components table after editing
                self.populate_components_table(product)
                # Also refresh the products table to update "Items Using" count
                self.refresh_data()
        else:
            QMessageBox.warning(self, "Error", "Product not found")
    
    def clear_components_table(self):
        """Clear the components table"""
        self.components_table.setRowCount(0)
        # Find the components group box
        components_group = None
        for child in self.findChildren(QGroupBox):
            if "Components" in child.title():
                components_group = child
                break
        if components_group:
            components_group.setTitle("Components - Select a product to view components")
    
    def refresh_for_user(self):
        """Refresh the UI when user changes"""
        try:
            # Recalculate show_costs based on new user
            if self.user and self.user.role.value in ['user', 'viewer']:
                self.show_costs = False
            else:
                self.show_costs = self.permissions_manager.can_access_column(self.user, "components", "unit_cost")
            
            # Recreate components table with correct columns
            self.recreate_components_table()
            
        except Exception as e:
            print(f"Error refreshing ProductsTab for user: {e}")
    
    def recreate_components_table(self):
        """Recreate the components table with correct column configuration"""
        try:
            # Find the components group box
            components_group = None
            for child in self.findChildren(QGroupBox):
                if "Components" in child.title():
                    components_group = child
                    break
            
            if components_group:
                # Remove the old table
                old_table = components_group.findChild(QTableWidget)
                if old_table:
                    old_table.deleteLater()
                
                # Create new table with correct columns
                self.components_table = QTableWidget()
                
                if self.show_costs:
                    self.components_table.setColumnCount(4)
                    self.components_table.setHorizontalHeaderLabels([
                        "Component Name",
                        "Quantity",
                        "Unit Cost (CZK)",
                        "Total Cost (CZK)"
                    ])
                else:
                    self.components_table.setColumnCount(2)
                    self.components_table.setHorizontalHeaderLabels([
                        "Component Name",
                        "Quantity"
                    ])
                
                self.components_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
                self.components_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
                self.components_table.setSortingEnabled(True)
                
                # Add the new table to the group box
                layout = components_group.layout()
                if layout:
                    layout.addWidget(self.components_table)
                
        except Exception as e:
            print(f"Error recreating components table: {e}")
    
 