from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox
)
import pandas as pd
from PyQt6.QtCore import Qt, pyqtSignal
from sqlalchemy.orm import Session
from datetime import datetime
from utils.excel_import import (
    import_customers, import_products, import_items,
    import_employees, import_orders_and_items, import_new_orders_only, import_deliveries,
    import_components_from_excel, import_product_components_from_excel
)
from utils.permissions import get_permissions_manager

class ImportTab(QWidget):
    # Add signals for each type of import
    customers_imported = pyqtSignal()
    products_imported = pyqtSignal()
    items_imported = pyqtSignal()
    orders_imported = pyqtSignal()
    order_items_imported = pyqtSignal()
    employees_imported = pyqtSignal()
    components_imported = pyqtSignal()
    
    def __init__(self, session: Session, user=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self.permissions_manager = get_permissions_manager()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Data type selection
        type_layout = QHBoxLayout()
        type_label = QLabel("Data Type:")
        self.type_combo = QComboBox()
        self.type_combo.setMinimumWidth(150)  # Make dropdown wider
        self.type_combo.addItems([
            "Customers",
            "Products",
            "Items",
            "Orders",
            "New Orders Only",
            "Order Items",
            "Employees",
            "Components",
            "Product Component Assignments",
            "Deliveries"
        ])
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_path = QLabel("No file selected")
        select_file_btn = QPushButton("Select File")
        select_file_btn.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_path)
        file_layout.addWidget(select_file_btn)
        layout.addLayout(file_layout)
        
        # Import button
        import_btn = QPushButton("Import Data")
        import_btn.clicked.connect(self.import_data)
        layout.addWidget(import_btn)
        
        # Template export button
        template_btn = QPushButton("Export Template")
        template_btn.clicked.connect(self.export_template)
        layout.addWidget(template_btn)
        
        # Export current data button (only for Deliveries)
        self.export_current_btn = QPushButton("Export Current Data")
        self.export_current_btn.clicked.connect(self.export_current_data)
        self.export_current_btn.setVisible(False)  # Hidden by default
        layout.addWidget(self.export_current_btn)
        
        # Connect type combo to show/hide export current button
        self.type_combo.currentTextChanged.connect(self.on_data_type_changed)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        self.setLayout(layout)
    
    def select_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File",
            "",
            "Excel Files (*.xlsx *.xlsm *.xls)"
        )
        if file_name:
            self.file_path.setText(file_name)
    
    def import_data(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "import", "import_data"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to import data.")
            return
            
        if self.file_path.text() == "No file selected":
            QMessageBox.warning(
                self,
                "Error",
                "Please select a file first"
            )
            return
        
        try:
            data_type = self.type_combo.currentText()
            file_path = self.file_path.text()
            
            if data_type == "Customers":
                count = import_customers(self.session, file_path)
                self.customers_imported.emit()
                message = f"Successfully processed {count} customers"
                
            elif data_type == "Products":
                count = import_products(self.session, file_path)
                self.products_imported.emit()
                message = f"Successfully processed {count} products"
                
            elif data_type == "Items":
                count = import_items(self.session, file_path)
                self.items_imported.emit()
                message = f"Successfully processed {count} items"
                
            elif data_type == "Orders":
                orders_count, items_count = import_orders_and_items(self.session, file_path)
                self.orders_imported.emit()
                message = f"Successfully processed {orders_count} orders with {items_count} order items"
                
            elif data_type == "New Orders Only":
                orders_count, items_count = import_new_orders_only(self.session, file_path)
                self.orders_imported.emit()
                message = f"Successfully created {orders_count} new orders with {items_count} order items (existing orders skipped)"
                
            elif data_type == "Order Items":
                # Order Items are imported together with Orders
                orders_count, items_count = import_orders_and_items(self.session, file_path)
                self.order_items_imported.emit()
                message = f"Successfully processed {orders_count} orders with {items_count} order items"
                
            elif data_type == "Employees":
                count = import_employees(self.session, file_path)
                self.employees_imported.emit()
                message = f"Successfully processed {count} employees"
                
            elif data_type == "Components":
                success, message = import_components_from_excel(self.session, file_path, self)
                if success:
                    self.components_imported.emit()
                # Don't show duplicate message - the import function already shows it
                return
                
            elif data_type == "Product Component Assignments":
                success, message = import_product_components_from_excel(self.session, file_path, self)
                if success:
                    self.components_imported.emit()
                # Don't show duplicate message - the import function already shows it
                return
                
            elif data_type == "Deliveries":
                result = import_deliveries(self.session, file_path)
                if result['success']:
                    message = result['message']
                    if result['errors']:
                        error_details = "\n".join(result['errors'][:5])  # Show first 5 errors
                        if len(result['errors']) > 5:
                            error_details += f"\n... and {len(result['errors']) - 5} more errors"
                        message += f"\n\nErrors:\n{error_details}"
                else:
                    message = result['message']
                    if result['errors']:
                        error_details = "\n".join(result['errors'][:5])
                        if len(result['errors']) > 5:
                            error_details += f"\n... and {len(result['errors']) - 5} more errors"
                        message += f"\n\nErrors:\n{error_details}"
            else:
                message = f"Unknown data type: {data_type}"
            
            QMessageBox.information(
                self,
                "Import Complete",
                message
            )
            
            # Clear the file selection after successful import
            self.file_path.setText("No file selected")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error importing data: {str(e)}"
            )
    
    def export_template(self):
        """Export template for the selected data type"""
        data_type = self.type_combo.currentText()
        
        if data_type == "Components":
            self.export_components_template()
        elif data_type == "Product Component Assignments":
            self.export_product_components_template()
        elif data_type == "Deliveries":
            self.export_deliveries_template()
        else:
            QMessageBox.information(
                self,
                "Template Export",
                f"Template export for '{data_type}' is not yet implemented."
            )
    
    def export_components_template(self):
        """Export components template"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Components Template", "components_template.xlsx", "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                # Create template with sample data
                template_data = {
                    'name': ['M6 Nut', 'M8 Bolt', 'O-ring 10mm', 'Steel Washer', 'Aluminum Plate'],
                    'description': ['Standard M6 hex nut', 'M8x20 hex head bolt', '10mm diameter rubber o-ring', 'M6 steel washer', '2mm thick aluminum plate'],
                    'supplier': ['Fastener Supply', 'Fastener Supply', 'Seal Supplier', 'Fastener Supply', 'Metal Supplier'],
                    'buy_price': [0.10, 0.15, 0.02, 0.05, 1.50],
                    'material_price': [0.02, 0.05, 0.01, 0.01, 0.50],
                    'manufacturing_price': [0.02, 0.03, 0.01, 0.01, 0.30],
                    'surface_treatment_price': [0.01, 0.02, 0.01, 0.01, 0.20],
                    'cost_currency': ['EUR', 'EUR', 'EUR', 'EUR', 'EUR']
                }
                
                df = pd.DataFrame(template_data)
                df.to_excel(file_path, index=False)
                
                QMessageBox.information(self, "Success", f"Components template exported to {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error exporting template: {str(e)}")
    
    def export_deliveries_template(self):
        """Export deliveries template"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Deliveries Template", "deliveries_template.xlsx", "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                import shutil
                import os
                
                # Copy the template file
                template_path = "templates/deliveries_template.xlsx"
                if os.path.exists(template_path):
                    shutil.copy2(template_path, file_path)
                    QMessageBox.information(self, "Success", f"Deliveries template exported to {file_path}")
                else:
                    QMessageBox.warning(self, "Error", "Deliveries template file not found. Please contact support.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error exporting template: {str(e)}")
    
    def export_product_components_template(self):
        """Export product-component assignment template"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Assignment Template", "product_components_template.xlsx", "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                # Get existing products and components for template
                from models.database import Product, Component
                products = self.session.query(Product).order_by(Product.name).all()
                components = self.session.query(Component).order_by(Component.name).all()
                
                # Create template with sample data
                template_data = {
                    'product_name': ['Product A', 'Product A', 'Product A', 'Product B', 'Product B', 'Product B'],
                    'component_name': ['M6 Nut', 'M8 Bolt', 'O-ring 10mm', 'Aluminum Plate', 'Steel Washer', 'M6 Nut'],
                    'quantity': [4, 2, 1, 1, 6, 8]
                }
                
                df = pd.DataFrame(template_data)
                df.to_excel(file_path, index=False)
                
                # Create additional sheets with available products and components
                with pd.ExcelWriter(file_path, engine='openpyxl', mode='a') as writer:
                    # Products sheet
                    products_df = pd.DataFrame([{'product_name': p.name} for p in products])
                    products_df.to_excel(writer, sheet_name='Available Products', index=False)
                    
                    # Components sheet
                    components_df = pd.DataFrame([{'component_name': c.name} for c in components])
                    components_df.to_excel(writer, sheet_name='Available Components', index=False)
                
                QMessageBox.information(self, "Success", f"Assignment template exported to {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error exporting template: {str(e)}") 