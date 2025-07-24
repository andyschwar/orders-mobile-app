from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QCheckBox, QFormLayout, QComboBox, QGroupBox,
    QScrollArea, QWidget, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from sqlalchemy.orm import Session
from models.database import Customer

class BarcodeSettingsDialog(QDialog):
    """Dialog for managing barcode settings per customer (Admin only)"""
    
    settings_updated = pyqtSignal()  # Signal emitted when settings are saved
    
    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Barcode Settings Management")
        self.setModal(True)
        self.resize(900, 700)  # Increased dialog size
        self.init_ui()
        self.load_customers()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Barcode Settings Management")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "Configure barcode generation settings for each customer.\n"
            "Only customers with barcodes enabled will have barcodes generated on their labels."
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(desc_label)
        
        # Create scroll area for customer table
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Customer table
        self.customer_table = QTableWidget()
        self.customer_table.setColumnCount(6)
        self.customer_table.setHorizontalHeaderLabels([
            "Customer",
            "Barcodes Enabled",
            "Order Prefix",
            "Item Prefix", 
            "Quantity Prefix",
            "Actions"
        ])
        
        # Set column widths
        self.customer_table.setColumnWidth(0, 200)  # Customer name
        self.customer_table.setColumnWidth(1, 120)  # Barcodes enabled
        self.customer_table.setColumnWidth(2, 100)  # Order prefix
        self.customer_table.setColumnWidth(3, 100)  # Item prefix
        self.customer_table.setColumnWidth(4, 100)  # Quantity prefix
        self.customer_table.setColumnWidth(5, 120)  # Actions (increased width)
        
        # Set table properties
        self.customer_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.customer_table.setAlternatingRowColors(True)
        self.customer_table.horizontalHeader().setStretchLastSection(True)
        self.customer_table.verticalHeader().setDefaultSectionSize(35)  # Set minimum row height
        
        scroll_layout.addWidget(self.customer_table)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Save All Changes")
        self.save_button.clicked.connect(self.save_settings)
        
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_to_defaults)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def load_customers(self):
        """Load all customers into the table"""
        try:
            customers = self.session.query(Customer).order_by(Customer.name_index).all()
            self.customer_table.setRowCount(len(customers))
            
            for row, customer in enumerate(customers):
                # Customer name
                customer_text = f"{customer.name_index} - {customer.name}"
                customer_item = QTableWidgetItem(customer_text)
                customer_item.setData(Qt.ItemDataRole.UserRole, customer.id)
                customer_item.setFlags(customer_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.customer_table.setItem(row, 0, customer_item)
                
                # Barcodes enabled checkbox
                enabled_checkbox = QCheckBox()
                enabled_checkbox.setChecked(customer.barcodes_enabled or False)
                enabled_checkbox.stateChanged.connect(lambda state, c=customer: self.on_barcode_enabled_changed(c, state))
                self.customer_table.setCellWidget(row, 1, enabled_checkbox)
                
                # Order prefix
                order_prefix = QLineEdit()
                order_prefix.setText(customer.order_barcode_prefix or 'N')
                order_prefix.setMaximumWidth(80)
                order_prefix.textChanged.connect(lambda text, c=customer: self.on_prefix_changed(c, 'order', text))
                self.customer_table.setCellWidget(row, 2, order_prefix)
                
                # Item prefix
                item_prefix = QLineEdit()
                item_prefix.setText(customer.item_barcode_prefix or 'P')
                item_prefix.setMaximumWidth(80)
                item_prefix.textChanged.connect(lambda text, c=customer: self.on_prefix_changed(c, 'item', text))
                self.customer_table.setCellWidget(row, 3, item_prefix)
                
                # Quantity prefix
                qty_prefix = QLineEdit()
                qty_prefix.setText(customer.quantity_barcode_prefix or 'U')
                qty_prefix.setMaximumWidth(80)
                qty_prefix.textChanged.connect(lambda text, c=customer: self.on_prefix_changed(c, 'quantity', text))
                self.customer_table.setCellWidget(row, 4, qty_prefix)
                
                # Actions button
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(4, 4, 4, 4)  # Increased all margins
                actions_layout.setSpacing(4)  # Add spacing between elements
                
                test_button = QPushButton("Test Settings")
                test_button.setMinimumWidth(80)  # Increased minimum width
                test_button.setMaximumWidth(100)  # Increased maximum width
                test_button.setMinimumHeight(25)  # Set minimum height
                test_button.clicked.connect(lambda checked, c=customer: self.test_barcode_settings(c))
                actions_layout.addWidget(test_button)
                
                self.customer_table.setCellWidget(row, 5, actions_widget)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load customers: {str(e)}")
    
    def on_barcode_enabled_changed(self, customer, state):
        """Handle barcode enabled checkbox change"""
        customer.barcodes_enabled = (state == Qt.CheckState.Checked)
    
    def on_prefix_changed(self, customer, prefix_type, text):
        """Handle prefix field changes"""
        if prefix_type == 'order':
            customer.order_barcode_prefix = text
        elif prefix_type == 'item':
            customer.item_barcode_prefix = text
        elif prefix_type == 'quantity':
            customer.quantity_barcode_prefix = text
    
    def test_barcode_settings(self, customer):
        """Test barcode settings for a customer"""
        if not customer.barcodes_enabled:
            QMessageBox.information(self, "Test Barcode Settings", 
                                  f"Barcodes are disabled for {customer.name_index}")
            return
        
        # Create test barcode data
        test_order = "TEST-001"
        test_item = "TEST-ITEM-001"
        test_qty = "100"
        
        order_barcode = f"{customer.order_barcode_prefix}{test_order}"
        item_barcode = f"{customer.item_barcode_prefix}{test_item}"
        qty_barcode = f"{customer.quantity_barcode_prefix}{test_qty}"
        
        message = f"Test barcode data for {customer.name_index}:\n\n"
        message += f"Order barcode: {order_barcode}\n"
        message += f"Item barcode: {item_barcode}\n"
        message += f"Quantity barcode: {qty_barcode}\n\n"
        message += "These would be the barcode values generated for this customer."
        
        QMessageBox.information(self, "Test Barcode Settings", message)
    
    def save_settings(self):
        """Save all barcode settings"""
        try:
            self.session.commit()
            QMessageBox.information(self, "Success", "Barcode settings saved successfully!")
            self.settings_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
            self.session.rollback()
    
    def reset_to_defaults(self):
        """Reset all customers to default barcode settings"""
        reply = QMessageBox.question(
            self, "Reset to Defaults",
            "This will reset all customers to default barcode settings:\n"
            "- Barcodes disabled for all customers\n"
            "- Order prefix: N\n"
            "- Item prefix: P\n"
            "- Quantity prefix: U\n\n"
            "Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                customers = self.session.query(Customer).all()
                for customer in customers:
                    customer.barcodes_enabled = False
                    customer.order_barcode_prefix = 'N'
                    customer.item_barcode_prefix = 'P'
                    customer.quantity_barcode_prefix = 'U'
                
                self.session.commit()
                self.load_customers()  # Reload the table
                QMessageBox.information(self, "Success", "All customers reset to default settings!")
                self.settings_updated.emit()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset settings: {str(e)}")
                self.session.rollback() 