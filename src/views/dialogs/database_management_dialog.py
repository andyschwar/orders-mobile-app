from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QMessageBox, QGroupBox,
    QCheckBox, QTextEdit, QProgressBar, QFrame, QScrollArea,
    QWidget, QHeaderView, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont, QIcon
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import os
import shutil
from pathlib import Path

class DatabaseManagementDialog(QDialog):
    """Admin interface for database management operations"""
    
    operation_completed = pyqtSignal(str)  # Signal emitted when operation completes
    
    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Database Management")
        self.setModal(True)
        self.resize(1200, 800)  # Increased window size
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Database Management")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Warning message
        warning_label = QLabel("⚠️  WARNING: These operations will permanently delete data!")
        warning_label.setStyleSheet("color: red; font-weight: bold; font-size: 12px;")
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning_label)
        
        # Create main content area with split layout
        main_layout = QHBoxLayout()
        
        # Left side - Operations
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Backup section
        backup_group = QGroupBox("Backup Operations")
        backup_layout = QVBoxLayout(backup_group)
        
        backup_info = QLabel("Create a backup before clearing data:")
        backup_layout.addWidget(backup_info)
        
        # Show backup directory info
        backup_dir_info = QLabel("Backups are saved to: backups/ folder")
        backup_dir_info.setStyleSheet("color: gray; font-size: 10px;")
        backup_layout.addWidget(backup_dir_info)
        
        backup_button = QPushButton("Create Backup Now")
        backup_button.clicked.connect(self.create_backup)
        backup_layout.addWidget(backup_button)
        
        left_layout.addWidget(backup_group)
        
        # Table clearing section
        clear_group = QGroupBox("Clear Tables")
        clear_layout = QVBoxLayout(clear_group)
        
        clear_info = QLabel("Select tables to clear (data will be permanently deleted):")
        clear_layout.addWidget(clear_info)
        
        # Create table with checkboxes
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(5)  # Added Actions column
        self.table_widget.setHorizontalHeaderLabels([
            "Select", "Table Name", "Record Count", "Description", "Actions"
        ])
        
        # Set column widths
        self.table_widget.setColumnWidth(0, 60)   # Select
        self.table_widget.setColumnWidth(1, 180)  # Table Name (increased)
        self.table_widget.setColumnWidth(2, 120)  # Record Count (increased)
        self.table_widget.setColumnWidth(3, 300)  # Description
        self.table_widget.setColumnWidth(4, 120)  # Actions
        
        # Set table properties
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_widget.verticalHeader().setDefaultSectionSize(30)  # Set row height
        
        # Disable sorting for checkbox column
        self.table_widget.horizontalHeader().setSortIndicatorShown(False)
        
        self.populate_tables()
        clear_layout.addWidget(self.table_widget)
        
        # Clear buttons
        clear_buttons_layout = QHBoxLayout()
        
        clear_selected_button = QPushButton("Clear Selected Tables")
        clear_selected_button.clicked.connect(self.clear_selected_tables)
        clear_buttons_layout.addWidget(clear_selected_button)
        
        clear_all_button = QPushButton("Clear All Tables")
        clear_all_button.clicked.connect(self.clear_all_tables)
        clear_buttons_layout.addWidget(clear_all_button)
        
        clear_layout.addLayout(clear_buttons_layout)
        left_layout.addWidget(clear_group)
        
        # Specific operations section
        operations_group = QGroupBox("Specific Operations")
        operations_layout = QVBoxLayout(operations_group)
        
        # Clear orders and related data
        orders_layout = QHBoxLayout()
        orders_layout.addWidget(QLabel("Orders & Deliveries:"))
        clear_orders_button = QPushButton("Clear Orders & Order Items")
        clear_orders_button.clicked.connect(self.clear_orders_and_items)
        orders_layout.addWidget(clear_orders_button)
        orders_layout.addStretch()
        operations_layout.addLayout(orders_layout)
        
        # Clear deliveries only
        deliveries_layout = QHBoxLayout()
        deliveries_layout.addWidget(QLabel("Deliveries Only:"))
        clear_deliveries_button = QPushButton("Clear All Deliveries")
        clear_deliveries_button.clicked.connect(self.clear_deliveries)
        deliveries_layout.addWidget(clear_deliveries_button)
        deliveries_layout.addStretch()
        operations_layout.addLayout(deliveries_layout)
        
        # Clear production plans
        plans_layout = QHBoxLayout()
        plans_layout.addWidget(QLabel("Production Plans:"))
        clear_plans_button = QPushButton("Clear Production Plans")
        clear_plans_button.clicked.connect(self.clear_production_plans)
        plans_layout.addWidget(clear_plans_button)
        plans_layout.addStretch()
        operations_layout.addLayout(plans_layout)
        
        # Clear components
        components_layout = QHBoxLayout()
        components_layout.addWidget(QLabel("Components:"))
        clear_components_button = QPushButton("Clear Components")
        clear_components_button.clicked.connect(self.clear_components)
        components_layout.addWidget(clear_components_button)
        components_layout.addStretch()
        operations_layout.addLayout(components_layout)
        
        left_layout.addWidget(operations_group)
        
        # Progress and status
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        left_layout.addWidget(self.status_text)
        
        # Add left side to main layout
        main_layout.addWidget(left_widget)
        
        # Right side - Table Data Viewer
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Table data viewer section
        data_group = QGroupBox("Table Data Viewer")
        data_layout = QVBoxLayout(data_group)
        
        data_info = QLabel("View data from any table in the database:")
        data_layout.addWidget(data_info)
        
        # Table selector
        table_selector_layout = QHBoxLayout()
        table_selector_layout.addWidget(QLabel("Select Table:"))
        self.table_selector = QComboBox()
        self.table_selector.addItems([
            "orders", "order_items", "deliveries", "production_plans",
            "customers", "employees", "products", "items", "components",
            "product_components", "component_stock", "users"
        ])
        self.table_selector.currentTextChanged.connect(self.load_table_data)
        table_selector_layout.addWidget(self.table_selector)
        table_selector_layout.addStretch()
        data_layout.addLayout(table_selector_layout)
        
        # Data table
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.data_table.verticalHeader().setDefaultSectionSize(25)
        data_layout.addWidget(self.data_table)
        
        # Data table info
        self.data_info_label = QLabel("Select a table to view its data")
        self.data_info_label.setStyleSheet("color: gray; font-size: 11px;")
        data_layout.addWidget(self.data_info_label)
        
        right_layout.addWidget(data_group)
        right_layout.addStretch()
        
        # Add right side to main layout
        main_layout.addWidget(right_widget)
        
        # Add main layout to dialog
        layout.addLayout(main_layout)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        refresh_button = QPushButton("Refresh Counts")
        refresh_button.clicked.connect(self.refresh_table_counts)
        button_layout.addWidget(refresh_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
    def populate_tables(self):
        """Populate the table with database tables and their record counts"""
        tables = [
            ("orders", "Orders", "Customer orders with delivery information"),
            ("order_items", "Order Items", "Individual items within orders"),
            ("deliveries", "Deliveries", "Delivery tracking records"),
            ("production_plans", "Production Plans", "Production planning data"),
            ("customers", "Customers", "Customer information"),
            ("employees", "Employees", "Employee information"),
            ("products", "Products", "Product catalog"),
            ("items", "Items", "Customer-specific items"),
            ("components", "Components", "Component parts and materials"),
            ("product_components", "Product Components", "Product-component assignments"),
            ("users", "Users", "System users and roles")
        ]
        
        self.table_widget.setRowCount(len(tables))
        
        for i, (table_name, display_name, description) in enumerate(tables):
            # Checkbox
            checkbox = QCheckBox()
            self.table_widget.setCellWidget(i, 0, checkbox)
            
            # Table name
            self.table_widget.setItem(i, 1, QTableWidgetItem(display_name))
            
            # Record count
            count = self.get_table_count(table_name)
            self.table_widget.setItem(i, 2, QTableWidgetItem(str(count)))
            
            # Description
            self.table_widget.setItem(i, 3, QTableWidgetItem(description))
            
            # Actions button
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            
            view_button = QPushButton("View Data")
            view_button.setMaximumWidth(80)
            view_button.clicked.connect(lambda checked, tn=table_name: self.view_table_data(tn))
            actions_layout.addWidget(view_button)
            
            self.table_widget.setCellWidget(i, 4, actions_widget)
            
            # Store table name in first column data
            self.table_widget.item(i, 1).setData(Qt.ItemDataRole.UserRole, table_name)
    
    def get_table_count(self, table_name: str) -> int:
        """Get the record count for a table"""
        try:
            result = self.session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar()
        except Exception:
            return 0
    
    def refresh_table_counts(self):
        """Refresh the record counts in the table"""
        for row in range(self.table_widget.rowCount()):
            table_name = self.table_widget.item(row, 1).data(Qt.ItemDataRole.UserRole)
            count = self.get_table_count(table_name)
            self.table_widget.setItem(row, 2, QTableWidgetItem(str(count)))
        
        self.log_status("Table counts refreshed")
    
    def create_backup(self):
        """Create a backup of the database"""
        try:
            from utils.backup import create_backup
            backup_path = create_backup()
            self.log_status(f"Backup created successfully: {backup_path}")
            QMessageBox.information(self, "Backup Created", f"Backup saved to:\n{backup_path}")
        except Exception as e:
            self.log_status(f"Backup failed: {str(e)}")
            QMessageBox.critical(self, "Backup Failed", f"Could not create backup: {str(e)}")
    
    def get_selected_tables(self):
        """Get list of selected table names"""
        selected_tables = []
        for row in range(self.table_widget.rowCount()):
            checkbox = self.table_widget.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                table_name = self.table_widget.item(row, 1).data(Qt.ItemDataRole.UserRole)
                selected_tables.append(table_name)
        return selected_tables
    
    def clear_selected_tables(self):
        """Clear selected tables"""
        selected_tables = self.get_selected_tables()
        if not selected_tables:
            QMessageBox.warning(self, "No Selection", "Please select tables to clear")
            return
        
        # Confirm deletion
        table_names = ", ".join(selected_tables)
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to permanently delete all data from:\n\n{table_names}\n\nThis action cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.perform_clear_operation(selected_tables, "selected tables")
    
    def clear_all_tables(self):
        """Clear all tables"""
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to permanently delete ALL data from ALL tables?\n\nThis action cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            all_tables = []
            for row in range(self.table_widget.rowCount()):
                table_name = self.table_widget.item(row, 1).data(Qt.ItemDataRole.UserRole)
                all_tables.append(table_name)
            
            self.perform_clear_operation(all_tables, "all tables")
    
    def clear_orders_and_items(self):
        """Clear orders and order items"""
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to clear all orders and order items?\n\nThis will also clear related deliveries.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.perform_clear_operation(["deliveries", "order_items", "orders"], "orders and related data")
    
    def clear_deliveries(self):
        """Clear all deliveries"""
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to clear all delivery records?\n\nThis will reset delivery tracking for all items.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.perform_clear_operation(["deliveries"], "deliveries")
    
    def clear_production_plans(self):
        """Clear production plans"""
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to clear all production plans?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.perform_clear_operation(["production_plans"], "production plans")
    
    def clear_components(self):
        """Clear components and product-component assignments"""
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to clear all components and product-component assignments?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.perform_clear_operation(["product_components", "components"], "components and product components")
    
    def perform_clear_operation(self, tables: list, operation_name: str):
        """Perform the actual clear operation"""
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(len(tables))
            self.progress_bar.setValue(0)
            
            self.log_status(f"Starting to clear {operation_name}...")
            
            for i, table_name in enumerate(tables):
                self.progress_bar.setValue(i + 1)
                self.log_status(f"Clearing table: {table_name}")
                
                # Clear the table
                self.session.execute(text(f"DELETE FROM {table_name}"))
                
                # Reset auto-increment if applicable
                try:
                    self.session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'"))
                except:
                    pass  # Not all tables have auto-increment
            
            self.session.commit()
            self.log_status(f"Successfully cleared {operation_name}")
            
            # Refresh counts
            self.refresh_table_counts()
            
            QMessageBox.information(self, "Operation Complete", f"Successfully cleared {operation_name}")
            
        except Exception as e:
            self.session.rollback()
            self.log_status(f"Error clearing {operation_name}: {str(e)}")
            QMessageBox.critical(self, "Operation Failed", f"Error clearing {operation_name}: {str(e)}")
        
        finally:
            self.progress_bar.setVisible(False)
    
    def log_status(self, message: str):
        """Add a status message to the log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
        self.status_text.ensureCursorVisible()
    
    def view_table_data(self, table_name: str):
        """View data from a specific table"""
        self.table_selector.setCurrentText(table_name)
        self.load_table_data(table_name)
    
    def load_table_data(self, table_name: str = None):
        """Load and display data from the selected table"""
        if not table_name:
            table_name = self.table_selector.currentText()
        
        if not table_name:
            return
        
        try:
            # Get table data
            result = self.session.execute(text(f"SELECT * FROM {table_name} LIMIT 100"))
            rows = result.fetchall()
            
            if not rows:
                self.data_table.setRowCount(0)
                self.data_table.setColumnCount(0)
                self.data_info_label.setText(f"No data found in {table_name}")
                return
            
            # Get column names
            columns = result.keys()
            
            # Set up table
            self.data_table.setColumnCount(len(columns))
            self.data_table.setHorizontalHeaderLabels(columns)
            
            # Set column widths
            for i, column in enumerate(columns):
                # Auto-size columns based on content
                max_width = len(str(column)) * 10  # Base width on column name
                for row in rows:
                    cell_width = len(str(row[i])) * 8
                    max_width = max(max_width, cell_width)
                self.data_table.setColumnWidth(i, min(max_width, 200))  # Cap at 200px
            
            # Populate data
            self.data_table.setRowCount(len(rows))
            for row_idx, row in enumerate(rows):
                for col_idx, value in enumerate(row):
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    self.data_table.setItem(row_idx, col_idx, item)
            
            # Update info label
            total_count = self.get_table_count(table_name)
            displayed_count = len(rows)
            if total_count > displayed_count:
                self.data_info_label.setText(f"Showing {displayed_count} of {total_count} records from {table_name}")
            else:
                self.data_info_label.setText(f"Showing all {total_count} records from {table_name}")
                
        except Exception as e:
            self.data_info_label.setText(f"Error loading data from {table_name}: {str(e)}")
            self.log_status(f"Error loading table data: {str(e)}") 