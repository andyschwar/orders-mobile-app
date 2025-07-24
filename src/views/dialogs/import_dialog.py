from PyQt6.QtWidgets import (
    QDialog,
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

class ImportDialog(QDialog):
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
        self.setWindowTitle("Import Data")
        self.setModal(True)
        self.resize(500, 300)
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
            
            QMessageBox.information(self, "Import Complete", message)
            
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Error during import: {str(e)}")
    
    def export_template(self):
        """Export template for the selected data type"""
        data_type = self.type_combo.currentText()
        
        try:
            if data_type == "Customers":
                template_path = "templates/customers.xlsx"
            elif data_type == "Products":
                template_path = "templates/products.xlsx"
            elif data_type == "Items":
                template_path = "templates/items.xlsx"
            elif data_type == "Orders":
                template_path = "templates/orders_template.xlsx"
            elif data_type == "Order Items":
                template_path = "templates/orders_template.xlsx"
            elif data_type == "Employees":
                template_path = "templates/employees.xlsx"
            elif data_type == "Components":
                template_path = "templates/components_template.xlsx"
            elif data_type == "Product Component Assignments":
                template_path = "templates/product_components_template.xlsx"
            elif data_type == "Deliveries":
                template_path = "templates/deliveries_template.xlsx"
            else:
                QMessageBox.warning(self, "Error", f"No template available for {data_type}")
                return
            
            # Check if template exists
            import os
            if not os.path.exists(template_path):
                QMessageBox.warning(self, "Error", f"Template file not found: {template_path}")
                return
            
            # Ask user where to save the template
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                f"Save {data_type} Template",
                f"{data_type.lower()}_template.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if save_path:
                import shutil
                shutil.copy2(template_path, save_path)
                QMessageBox.information(self, "Template Exported", f"Template saved to: {save_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting template: {str(e)}")
    
    def on_data_type_changed(self, data_type: str):
        """Show/hide export current data button based on data type"""
        self.export_current_btn.setVisible(data_type == "Deliveries")
    
    def export_current_data(self):
        """Export current data from database for the selected data type"""
        data_type = self.type_combo.currentText()
        
        if data_type != "Deliveries":
            QMessageBox.information(self, "Not Available", "Export current data is only available for Deliveries.")
            return
        
        try:
            # Ask user where to save the file
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Current Deliveries",
                f"current_deliveries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if save_path:
                from utils.excel_import import export_current_deliveries
                result = export_current_deliveries(self.session, save_path)
                
                if result['success']:
                    QMessageBox.information(self, "Export Complete", result['message'])
                else:
                    QMessageBox.warning(self, "Export Failed", result['message'])
                    
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting current data: {str(e)}") 