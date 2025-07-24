from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTabWidget, QWidget, QCheckBox, QGroupBox, QScrollArea,
    QMessageBox, QComboBox, QLineEdit, QTextEdit, QSplitter,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
import json
import os
from typing import Dict, Any, List

class PermissionsDialog(QDialog):
    """Admin interface for managing role permissions"""
    
    permissions_updated = pyqtSignal()  # Signal emitted when permissions are saved
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.permissions_file = "role_permissions.json"
        self.permissions_data = {}
        self.load_permissions()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Role Permissions Management")
        self.setModal(True)
        self.resize(1200, 800)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Role-Based Access Control")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(14)  # Reduced from 16
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setMaximumHeight(40)  # Limit height
        layout.addWidget(title_label)
        
        # Role selector
        role_layout = QHBoxLayout()
        role_label = QLabel("Select Role:")
        self.role_combo = QComboBox()
        self.role_combo.addItems(["admin", "manager", "user", "viewer"])
        self.role_combo.setMinimumWidth(120)  # Make dropdown wider
        self.role_combo.currentTextChanged.connect(self.on_role_changed)
        role_layout.addWidget(role_label)
        role_layout.addWidget(self.role_combo)
        role_layout.addStretch()
        layout.addLayout(role_layout)
        
        # Main content area
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Module permissions
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_title = QLabel("Module Permissions")
        left_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        left_layout.addWidget(left_title)
        
        self.module_scroll = QScrollArea()
        self.module_widget = QWidget()
        self.module_layout = QVBoxLayout(self.module_widget)
        self.module_scroll.setWidget(self.module_widget)
        self.module_scroll.setWidgetResizable(True)
        left_layout.addWidget(self.module_scroll)
        
        # Right side - Column permissions
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        right_title = QLabel("Column-Level Permissions")
        right_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        right_layout.addWidget(right_title)
        
        self.column_scroll = QScrollArea()
        self.column_widget = QWidget()
        self.column_layout = QVBoxLayout(self.column_widget)
        self.column_scroll.setWidget(self.column_widget)
        self.column_scroll.setWidgetResizable(True)
        right_layout.addWidget(self.column_scroll)
        
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([600, 600])
        layout.addWidget(main_splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Save Permissions")
        self.save_button.clicked.connect(self.save_permissions)
        
        self.reset_button = QPushButton("Reset to Default")
        self.reset_button.clicked.connect(self.reset_permissions)
        
        self.export_button = QPushButton("Export Configuration")
        self.export_button.clicked.connect(self.export_config)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.export_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Initialize with first role
        self.on_role_changed("admin")
        
    def load_permissions(self):
        """Load permissions from file or use default"""
        if os.path.exists(self.permissions_file):
            try:
                with open(self.permissions_file, 'r') as f:
                    self.permissions_data = json.load(f)
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Could not load permissions file: {e}")
                self.load_default_permissions()
        else:
            self.load_default_permissions()
            
    def load_default_permissions(self):
        """Load default permissions from template"""
        template_file = "role_permissions_template.json"
        if os.path.exists(template_file):
            try:
                with open(template_file, 'r') as f:
                    self.permissions_data = json.load(f)
            except Exception:
                self.create_default_permissions()
        else:
            self.create_default_permissions()
            
    def create_default_permissions(self):
        """Create basic default permissions"""
        self.permissions_data = {
            "role_permissions": {
                "admin": {"permissions": {}},
                "manager": {"permissions": {}},
                "user": {"permissions": {}},
                "viewer": {"permissions": {}}
            },
            "tab_access": {},
            "feature_access": {}
        }
        
    def on_role_changed(self, role_name: str):
        """Handle role selection change"""
        self.current_role = role_name
        self.update_module_permissions()
        self.update_column_permissions()
        
    def update_module_permissions(self):
        """Update the module permissions display"""
        # Clear existing widgets safely
        while self.module_layout.count():
            item = self.module_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
            
        if self.current_role not in self.permissions_data.get("role_permissions", {}):
            return
            
        role_data = self.permissions_data["role_permissions"][self.current_role]
        permissions = role_data.get("permissions", {})
        
        # Create module permission groups
        modules = [
            ("orders", "Orders Management"),
            ("customers", "Customer Management"),
            ("employees", "Employee Management"),
            ("products", "Product Management"),
            ("items", "Item Management"),
            ("components", "Component Management"),
            ("stock", "Stock Management"),
            ("labels", "Label Generation"),
            ("import", "Data Import"),
            ("settings", "Application Settings"),
            ("users", "User Management"),
            ("reports", "Reports"),
            ("backup", "Backup & Restore")
        ]
        
        for module_key, module_name in modules:
            if module_key in permissions:
                group = self.create_module_permission_group(module_key, module_name, permissions[module_key])
                self.module_layout.addWidget(group)
                
        self.module_layout.addStretch()
        
    def create_module_permission_group(self, module_key: str, module_name: str, permissions: Dict[str, Any]) -> QGroupBox:
        """Create a permission group for a module"""
        group = QGroupBox(module_name)
        layout = QVBoxLayout(group)
        
        # Basic permissions
        basic_permissions = [
            ("view", "View"),
            ("create", "Create"),
            ("edit", "Edit"),
            ("delete", "Delete"),
            ("print", "Print"),
            ("export", "Export")
        ]
        
        for perm_key, perm_name in basic_permissions:
            if perm_key in permissions:
                checkbox = QCheckBox(perm_name)
                checkbox.setChecked(permissions[perm_key])
                checkbox.toggled.connect(lambda checked, m=module_key, p=perm_key: self.update_permission(m, p, checked))
                layout.addWidget(checkbox)
                
        # Special permissions
        special_permissions = [
            ("view_employment_data", "View Employment Data"),
            ("view_documents", "View Documents"),
            ("import_data", "Import Data"),
            ("download_templates", "Download Templates"),
            ("change_database", "Change Database"),
            ("change_roles", "Change User Roles"),
            ("generate", "Generate Reports"),
            ("restore", "Restore Backups"),
            ("view_backups", "View Backups")
        ]
        
        for perm_key, perm_name in special_permissions:
            if perm_key in permissions:
                checkbox = QCheckBox(perm_name)
                checkbox.setChecked(permissions[perm_key])
                checkbox.toggled.connect(lambda checked, m=module_key, p=perm_key: self.update_permission(m, p, checked))
                layout.addWidget(checkbox)
                
        return group
        
    def update_column_permissions(self):
        """Update the column permissions display"""
        # Clear existing widgets safely
        while self.column_layout.count():
            item = self.column_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
            
        if self.current_role not in self.permissions_data.get("role_permissions", {}):
            return
            
        role_data = self.permissions_data["role_permissions"][self.current_role]
        permissions = role_data.get("permissions", {})
        
        # Create column permission groups
        modules_with_columns = [
            ("orders", "Orders", [
                "order_number", "customer", "order_date", "items", "quantities",
                "prices", "delivery_dates", "delivered_quantities", "surface_treatment", "status"
            ]),
            ("customers", "Customers", [
                "name_index", "name", "street", "city", "country", "email1", "email2", "email3",
                "atest_email", "invoice_email", "ico_vat", "ic_dph", "currency", "is_eu", "delivery_address"
            ]),
            ("employees", "Employees", [
                "name", "address", "phone", "email", "birthday", "name_day", "documents_path",
                "employment_start", "employment_end", "employment_type", "contract_renewal_1",
                "contract_renewal_2", "contract_renewal_3", "last_contract_renewal", "is_active"
            ]),
            ("products", "Products", [
                "name", "description", "weight_per_unit"
            ]),
            ("items", "Items", [
                "customer", "product", "customer_code", "customer_item_name", "item_type", "similar_item"
            ]),
            ("components", "Components", [
                "name", "description", "category", "buy_price", "material_price", "manufacturing_price",
                "surface_treatment_price", "unit_cost", "unit_cost_eur", "cost_currency", "supplier", "component_type"
            ]),
            ("stock", "Stock", [
                "component", "current_stock", "minimum_stock", "unit_of_measure", "last_updated", "notes"
            ])
        ]
        
        for module_key, module_name, columns in modules_with_columns:
            if module_key in permissions and "columns" in permissions[module_key]:
                group = self.create_column_permission_group(module_key, module_name, permissions[module_key]["columns"])
                self.column_layout.addWidget(group)
                
        self.column_layout.addStretch()
        
    def create_column_permission_group(self, module_key: str, module_name: str, columns: Dict[str, bool]) -> QGroupBox:
        """Create a permission group for column access"""
        group = QGroupBox(f"{module_name} Columns")
        layout = QVBoxLayout(group)
        
        for column_key, column_name in self.get_column_display_names(module_key).items():
            if column_key in columns:
                checkbox = QCheckBox(column_name)
                checkbox.setChecked(columns[column_key])
                checkbox.toggled.connect(lambda checked, m=module_key, c=column_key: self.update_column_permission(m, c, checked))
                layout.addWidget(checkbox)
                
        return group
        
    def get_column_display_names(self, module_key: str) -> Dict[str, str]:
        """Get display names for columns"""
        display_names = {
            "orders": {
                "order_number": "Order Number",
                "customer": "Customer",
                "order_date": "Order Date",
                "items": "Items",
                "quantities": "Quantities",
                "prices": "Prices",
                "delivery_dates": "Delivery Dates",
                "delivered_quantities": "Delivered Quantities",
                "surface_treatment": "Surface Treatment",
                "status": "Status"
            },
            "customers": {
                "name_index": "Name Index",
                "name": "Name",
                "street": "Street",
                "city": "City",
                "country": "Country",
                "email1": "Email 1",
                "email2": "Email 2",
                "email3": "Email 3",
                "atest_email": "Atest Email",
                "invoice_email": "Invoice Email",
                "ico_vat": "ICO/VAT",
                "ic_dph": "IC DPH",
                "currency": "Currency",
                "is_eu": "EU Status",
                "delivery_address": "Delivery Address"
            },
            "employees": {
                "name": "Name",
                "address": "Address",
                "phone": "Phone",
                "email": "Email",
                "birthday": "Birthday",
                "name_day": "Name Day",
                "documents_path": "Documents Path",
                "employment_start": "Employment Start",
                "employment_end": "Employment End",
                "employment_type": "Employment Type",
                "contract_renewal_1": "Contract Renewal 1",
                "contract_renewal_2": "Contract Renewal 2",
                "contract_renewal_3": "Contract Renewal 3",
                "last_contract_renewal": "Last Contract Renewal",
                "is_active": "Active Status"
            },
            "products": {
                "name": "Name",
                "description": "Description",
                "weight_per_unit": "Weight per Unit"
            },
            "items": {
                "customer": "Customer",
                "product": "Product",
                "customer_code": "Customer Code",
                "customer_item_name": "Customer Item Name",
                "item_type": "Item Type",
                "similar_item": "Similar Item"
            },
            "components": {
                "name": "Name",
                "description": "Description",
                "category": "Category",
                "buy_price": "Buy Price (CZK)",
                "material_price": "Material Price (CZK)",
                "manufacturing_price": "Manufacturing Price (CZK)",
                "surface_treatment_price": "Surface Treatment Price (CZK)",
                "unit_cost": "Total Cost (CZK)",
                "unit_cost_eur": "Total Cost (EUR)",
                "cost_currency": "Currency",
                "supplier": "Supplier",
                "component_type": "Type"
            },
            "stock": {
                "component": "Component",
                "current_stock": "Current Stock",
                "minimum_stock": "Minimum Stock",
                "unit_of_measure": "Unit of Measure",
                "last_updated": "Last Updated",
                "notes": "Notes"
            }
        }
        
        return display_names.get(module_key, {})
        
    def update_permission(self, module: str, permission: str, value: bool):
        """Update a permission value"""
        if self.current_role not in self.permissions_data["role_permissions"]:
            self.permissions_data["role_permissions"][self.current_role] = {"permissions": {}}
            
        if module not in self.permissions_data["role_permissions"][self.current_role]["permissions"]:
            self.permissions_data["role_permissions"][self.current_role]["permissions"][module] = {}
            
        self.permissions_data["role_permissions"][self.current_role]["permissions"][module][permission] = value
        
    def update_column_permission(self, module: str, column: str, value: bool):
        """Update a column permission value"""
        if self.current_role not in self.permissions_data["role_permissions"]:
            self.permissions_data["role_permissions"][self.current_role] = {"permissions": {}}
            
        if module not in self.permissions_data["role_permissions"][self.current_role]["permissions"]:
            self.permissions_data["role_permissions"][self.current_role]["permissions"][module] = {}
            
        if "columns" not in self.permissions_data["role_permissions"][self.current_role]["permissions"][module]:
            self.permissions_data["role_permissions"][self.current_role]["permissions"][module]["columns"] = {}
            
        self.permissions_data["role_permissions"][self.current_role]["permissions"][module]["columns"][column] = value
        
    def save_permissions(self):
        """Save permissions to file"""
        try:
            with open(self.permissions_file, 'w') as f:
                json.dump(self.permissions_data, f, indent=2)
            QMessageBox.information(self, "Success", "Permissions saved successfully!")
            self.permissions_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save permissions: {e}")
            
    def reset_permissions(self):
        """Reset permissions to default"""
        reply = QMessageBox.question(
            self, "Reset Permissions", 
            "Are you sure you want to reset all permissions to default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.load_default_permissions()
            self.on_role_changed(self.current_role)
            QMessageBox.information(self, "Reset Complete", "Permissions have been reset to default values.")
            
    def export_config(self):
        """Export current configuration"""
        try:
            export_file = f"permissions_export_{self.current_role}.json"
            with open(export_file, 'w') as f:
                json.dump(self.permissions_data, f, indent=2)
            QMessageBox.information(self, "Export Complete", f"Configuration exported to {export_file}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Could not export configuration: {e}")
            
    def get_permissions_data(self) -> Dict[str, Any]:
        """Get the current permissions data"""
        return self.permissions_data 