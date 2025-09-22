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

class CustomCheckBox(QCheckBox):
    """Custom checkbox that stores customer object and handles signals"""
    def __init__(self, customer, parent=None):
        super().__init__(parent)
        self.customer = customer
        self.stateChanged.connect(self.on_state_changed)
    
    def on_state_changed(self, state):
        """Handle state change directly"""
        print(f"[DEBUG] Custom checkbox signal for {self.customer.name_index}! State: {state}")
        print(f"[DEBUG] Qt.CheckState.Checked = {Qt.CheckState.Checked}")
        print(f"[DEBUG] Qt.CheckState.Unchecked = {Qt.CheckState.Unchecked}")
        # Use the correct comparison - state is an integer, CheckState.Checked is an enum
        is_checked = (state == Qt.CheckState.Checked.value)
        self.customer.barcodes_enabled = is_checked
        print(f"[DEBUG] Custom checkbox changed for {self.customer.name_index}: {is_checked}")

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
    
    def showEvent(self, event):
        """Refresh data when dialog is shown"""
        super().showEvent(event)
        print(f"[DEBUG] Dialog shown, refreshing customer data")
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
            # Refresh the session to get latest data
            self.session.commit()  # Commit any pending changes first
            customers = self.session.query(Customer).order_by(Customer.name_index).all()
            print(f"[DEBUG] Loading {len(customers)} customers for barcode settings")
            self.customer_table.setRowCount(len(customers))
            
            for row, customer in enumerate(customers):
                # Debug output for each customer
                print(f"[DEBUG] Loading customer {customer.name_index}:")
                print(f"[DEBUG]   barcodes_enabled: {customer.barcodes_enabled} (type: {type(customer.barcodes_enabled)})")
                print(f"[DEBUG]   item_prefix: {customer.item_barcode_prefix}")
                print(f"[DEBUG]   order_prefix: {customer.order_barcode_prefix}")
                print(f"[DEBUG]   quantity_prefix: {customer.quantity_barcode_prefix}")
                
                # Check if this is one of the customers that should have barcodes enabled
                if customer.name_index in ['POPRAD', 'TLMACE', 'TREBISOV', 'ZAHREB']:
                    print(f"[DEBUG]   *** {customer.name_index} should have barcodes enabled but shows: {customer.barcodes_enabled} ***")
                
                # Customer name
                customer_text = f"{customer.name_index} - {customer.name}"
                customer_item = QTableWidgetItem(customer_text)
                customer_item.setData(Qt.ItemDataRole.UserRole, customer.id)
                customer_item.setFlags(customer_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.customer_table.setItem(row, 0, customer_item)
                
                # Barcodes enabled checkbox - use custom checkbox
                enabled_checkbox = CustomCheckBox(customer)
                checkbox_state = customer.barcodes_enabled or False
                enabled_checkbox.setChecked(checkbox_state)
                print(f"[DEBUG] Setting custom checkbox for {customer.name_index}: {checkbox_state}")
                self.customer_table.setCellWidget(row, 1, enabled_checkbox)
                
                # Order prefix
                order_prefix = QLineEdit()
                order_prefix.setText(customer.order_barcode_prefix or '')
                order_prefix.setMaximumWidth(80)
                order_prefix.textChanged.connect(lambda text, c=customer: self.on_prefix_changed(c, 'order', text))
                self.customer_table.setCellWidget(row, 2, order_prefix)
                
                # Item prefix
                item_prefix = QLineEdit()
                item_prefix.setText(customer.item_barcode_prefix or '')
                item_prefix.setMaximumWidth(80)
                item_prefix.textChanged.connect(lambda text, c=customer: self.on_prefix_changed(c, 'item', text))
                self.customer_table.setCellWidget(row, 3, item_prefix)
                
                # Quantity prefix
                qty_prefix = QLineEdit()
                qty_prefix.setText(customer.quantity_barcode_prefix or '')
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
    
    def on_checkbox_changed(self, checkbox, state):
        """Handle checkbox change - simple approach"""
        print(f"[DEBUG] Checkbox signal received! State: {state}")
        if hasattr(checkbox, 'customer'):
            customer = checkbox.customer
            is_checked = (state == Qt.CheckState.Checked)
            customer.barcodes_enabled = is_checked
            print(f"[DEBUG] Barcode enabled changed for {customer.name_index}: {is_checked} (state: {state})")
        else:
            print(f"[DEBUG] No customer object found in checkbox!")
    
    def on_barcode_enabled_changed(self, state):
        """Handle barcode enabled checkbox change"""
        print(f"[DEBUG] Signal received! State: {state}")
        # Get the checkbox that sent the signal
        checkbox = self.sender()
        if not checkbox:
            print(f"[DEBUG] No sender found!")
            return
            
        # Get customer ID from the checkbox property
        customer_id = checkbox.property("customer_id")
        if not customer_id:
            return
            
        # Find the customer in the session
        customer = self.session.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return
            
        is_checked = (state == Qt.CheckState.Checked)
        customer.barcodes_enabled = is_checked
        print(f"[DEBUG] Barcode enabled changed for {customer.name_index}: {is_checked} (state: {state}, Checked: {Qt.CheckState.Checked})")
    
    def on_prefix_changed(self, customer, prefix_type, text):
        """Handle prefix field changes"""
        # If field is cleared, set to None (no prefix)
        if not text.strip():
            if prefix_type == 'order':
                customer.order_barcode_prefix = None
            elif prefix_type == 'item':
                customer.item_barcode_prefix = None
            elif prefix_type == 'quantity':
                customer.quantity_barcode_prefix = None
        else:
            if prefix_type == 'order':
                customer.order_barcode_prefix = text
            elif prefix_type == 'item':
                customer.item_barcode_prefix = text
            elif prefix_type == 'quantity':
                customer.quantity_barcode_prefix = text
        print(f"[DEBUG] {prefix_type} prefix changed for {customer.name_index}: '{text}' -> {getattr(customer, f'{prefix_type}_barcode_prefix')}")
    
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
            print(f"[DEBUG] Starting to save barcode settings...")
            
            # Check if there are any pending changes
            if self.session.dirty:
                print(f"[DEBUG] Found {len(self.session.dirty)} dirty objects")
                for obj in self.session.dirty:
                    print(f"[DEBUG] Dirty object: {obj}")
            else:
                print(f"[DEBUG] No dirty objects found")
            
            # Force refresh the session to ensure changes are detected
            self.session.flush()
            print(f"[DEBUG] Session flushed")
            
            # Commit the changes
            self.session.commit()
            print(f"[DEBUG] Barcode settings committed successfully")
            
            # Verify the changes were saved by querying the database
            from models.database import Customer
            test_customer = self.session.query(Customer).filter(Customer.name_index == "CARACAL").first()
            if test_customer:
                print(f"[DEBUG] Verification - Caracal barcode settings after save:")
                print(f"[DEBUG]   barcodes_enabled: {test_customer.barcodes_enabled}")
                print(f"[DEBUG]   item_prefix: {test_customer.item_barcode_prefix}")
                print(f"[DEBUG]   order_prefix: {test_customer.order_barcode_prefix}")
                print(f"[DEBUG]   quantity_prefix: {test_customer.quantity_barcode_prefix}")
            
            QMessageBox.information(self, "Success", "Barcode settings saved successfully!")
            self.settings_updated.emit()
        except Exception as e:
            print(f"[DEBUG] Error saving barcode settings: {e}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
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