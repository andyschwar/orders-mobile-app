from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox,
    QDialog, QFormLayout, QDateEdit, QCheckBox, QLabel,
    QComboBox, QSpinBox, QSizePolicy, QHeaderView, QDialogButtonBox,
    QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, extract
from datetime import datetime, date, timedelta
import pandas as pd
import os
from pathlib import Path
from models.database import OrderItem, Order, Customer, Item, Delivery, Product
from views.dialogs.batch_delivery_dialog import BatchDeliveryDialog
from views.dialogs.label_print_dialog import LabelPrintDialog
import calendar
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import subprocess
import logging

logger = logging.getLogger(__name__)

class BatchDeliveryDialog(QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items
        self.setWindowTitle("Batch Delivery")
        self.setModal(True)
        
        # Calculate total width needed:
        # Customer (250) + Order Number (120) + Item Code (120) + Item Name (300) + 
        # Ordered (80) + Delivered (80) + Remaining (80) + Deliver Now (100) = 1130
        # Add 50px buffer for window frame and scrollbar
        self.resize(1180, 600)
        self.setMinimumSize(1180, 400)
        
        # Set up export directory in Documents
        self.export_dir = os.path.join(str(Path.home()), "Documents", "OrdersApp", "exports")
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)
            
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Add delivery date selector
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Delivery Date:"))
        self.delivery_date = QDateEdit()
        self.delivery_date.setCalendarPopup(True)
        self.delivery_date.setDate(QDate.currentDate())
        date_layout.addWidget(self.delivery_date)
        date_layout.addStretch()
        layout.addLayout(date_layout)
        
        # Create table for items
        self.table = QTableWidget()
        self.table.setColumnCount(8)  # Added Item Code column
        self.table.setHorizontalHeaderLabels([
            "Customer",
            "Order Number",
            "Item Code",  # New column
            "Item Name",
            "Ordered",
            "Delivered",
            "Remaining",
            "Deliver Now"
        ])
        
        # Set column widths
        self.table.setColumnWidth(0, 250)  # Customer
        self.table.setColumnWidth(1, 120)  # Order Number
        self.table.setColumnWidth(2, 120)  # Item Code
        self.table.setColumnWidth(3, 300)  # Item Name
        self.table.setColumnWidth(4, 80)   # Ordered
        self.table.setColumnWidth(5, 80)   # Delivered
        self.table.setColumnWidth(6, 80)   # Remaining
        self.table.setColumnWidth(7, 100)  # Deliver Now
        
        # Make the table take up any extra space
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Populate table
        self.table.setRowCount(len(self.items))
        self.quantity_spinners = []
        
        for i, item in enumerate(self.items):
            remaining = item.quantity - item.delivered_quantity
            
            customer = QTableWidgetItem(f"{item.order.customer.name_index} - {item.order.customer.name}")
            order_number = QTableWidgetItem(item.order.order_number)
            item_code = QTableWidgetItem(item.item.customer_code)  # New column
            item_name = QTableWidgetItem(item.item.customer_item_name or item.item.product.name)
            ordered = QTableWidgetItem(str(item.quantity))
            delivered = QTableWidgetItem(str(item.delivered_quantity))
            remaining_item = QTableWidgetItem(str(remaining))
            
            quantity_spinner = QSpinBox()
            quantity_spinner.setMinimum(1)
            quantity_spinner.setMaximum(remaining)
            quantity_spinner.setValue(remaining)
            self.quantity_spinners.append(quantity_spinner)
            
            self.table.setItem(i, 0, customer)
            self.table.setItem(i, 1, order_number)
            self.table.setItem(i, 2, item_code)  # New column
            self.table.setItem(i, 3, item_name)
            self.table.setItem(i, 4, ordered)
            self.table.setItem(i, 5, delivered)
            self.table.setItem(i, 6, remaining_item)
            self.table.setCellWidget(i, 7, quantity_spinner)
        
        self.table.setSortingEnabled(True)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        
        layout.addWidget(self.table)
        
        # Add buttons
        button_box = QHBoxLayout()
        
        export_button = QPushButton("Export to Excel")
        export_button.clicked.connect(self.export_to_excel)
        button_box.addWidget(export_button)
        
        self.open_folder_button = QPushButton("Open Export Folder")
        self.open_folder_button.clicked.connect(self.open_export_folder)
        self.open_folder_button.setVisible(False)  # Hidden initially
        button_box.addWidget(self.open_folder_button)
        
        button_box.addStretch()
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addWidget(save_button)
        button_box.addWidget(cancel_button)
        layout.addLayout(button_box)
        
        self.setLayout(layout)
    
    def open_export_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.export_dir))
    
    def export_to_excel(self):
        try:
            # Group items by customer for separate files
            customer_items = {}
            for i, item in enumerate(self.items):
                customer = item.order.customer
                if customer not in customer_items:
                    customer_items[customer] = []
                
                quantity = self.quantity_spinners[i].value()
                if quantity > 0:  # Only include items with quantity > 0
                    customer_items[customer].append({
                        "Item Code": item.item.customer_code,
                        "Order Number": item.order.order_number,
                        "Quantity": quantity
                    })
            
            # Create one file per customer
            delivery_date = self.delivery_date.date().toPyDate()
            exported_files = []
            
            for customer, items in customer_items.items():
                if items:  # Only create file if customer has items
                    df = pd.DataFrame(items)
                    filename = f"{customer.name_index}_delivery_{delivery_date.strftime('%Y%m%d')}.xlsx"
                    full_path = os.path.join(self.export_dir, filename)
                    df.to_excel(full_path, index=False)
                    exported_files.append(filename)
            
            if exported_files:
                files_text = "\n".join(exported_files)
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Files exported successfully to:\n{self.export_dir}\n\nFiles created:\n{files_text}"
                )
                self.open_folder_button.setVisible(True)
            else:
                QMessageBox.warning(
                    self,
                    "No Files Created",
                    "No files were created because no items had quantities greater than 0."
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error exporting data: {str(e)}")
    
    def get_data(self):
        return {
            "delivery_date": self.delivery_date.date().toPyDate(),
            "items": [
                {
                    "order_item": self.items[i],
                    "quantity": spinner.value()
                }
                for i, spinner in enumerate(self.quantity_spinners)
            ]
        }

class QuantitySplitDialog(QDialog):
    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self.quantities = []
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Split Quantity")
        layout = QVBoxLayout()
        
        # Info label
        info_text = f"Item: {self.item.item.customer_item_name or self.item.item.product.name}\n"
        info_text += f"Total Quantity: {self.item.quantity}\n"
        if hasattr(self.item.item.product, 'weight_per_unit') and self.item.item.product.weight_per_unit:
            info_text += f"Weight per piece: {self.item.item.product.weight_per_unit:.3f} kg"
        info_label = QLabel(info_text)
        layout.addWidget(info_label)
        
        # Quantities list
        self.quantities_layout = QVBoxLayout()
        layout.addLayout(self.quantities_layout)
        
        # Add first quantity box
        self.add_quantity_box()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_button = QPushButton("Add Box")
        add_button.clicked.connect(self.add_quantity_box)
        button_layout.addWidget(add_button)
        
        remove_button = QPushButton("Remove Box")
        remove_button.clicked.connect(self.remove_quantity_box)
        button_layout.addWidget(remove_button)
        
        layout.addLayout(button_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def add_quantity_box(self):
        box_layout = QHBoxLayout()
        
        # Quantity spinbox
        qty_box = QSpinBox()
        qty_box.setMinimum(1)
        qty_box.setMaximum(self.item.quantity)
        qty_box.setValue(self.item.quantity if not self.quantities else 0)
        qty_label = QLabel("Quantity:")
        box_layout.addWidget(qty_label)
        box_layout.addWidget(qty_box)
        
        # Weight label (calculated)
        if hasattr(self.item.item.product, 'weight_per_unit') and self.item.item.product.weight_per_unit:
            weight = self.item.item.product.weight_per_unit * qty_box.value()
            weight_label = QLabel(f"Weight: {weight:.2f} kg")
            qty_box.valueChanged.connect(lambda v: weight_label.setText(
                f"Weight: {self.item.item.product.weight_per_unit * v:.2f} kg"))
            box_layout.addWidget(weight_label)
        
        self.quantities_layout.addLayout(box_layout)
        self.quantities.append(qty_box)
        self.update_remaining()
    
    def remove_quantity_box(self):
        if len(self.quantities) > 1:
            # Remove the last quantity box and its layout
            qty_box = self.quantities.pop()
            # Get the layout containing the box
            box_layout = qty_box.parent().layout()
            # Remove and delete all widgets in the layout
            while box_layout.count():
                item = box_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            # Delete the layout itself
            box_layout.deleteLater()
            self.update_remaining()
    
    def update_remaining(self):
        total = sum(box.value() for box in self.quantities)
        remaining = self.item.quantity - total
        for box in self.quantities:
            box.setMaximum(box.value() + remaining)
    
    def validate_and_accept(self):
        total = sum(box.value() for box in self.quantities)
        if total != self.item.quantity:
            QMessageBox.warning(
                self,
                "Invalid Split",
                f"Total quantity must equal {self.item.quantity}. Current total: {total}"
            )
            return
        self.accept()
    
    def get_quantities(self):
        return [box.value() for box in self.quantities]

class OrderItemsTab(QWidget):
    def __init__(self, session, user=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self.items = []
        from utils.permissions import get_permissions_manager
        self.permissions_manager = get_permissions_manager()
        self.setup_ui()
        self.refresh_data()  # Initial load
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()
        
        # Create toolbar
        toolbar = QHBoxLayout()
        
        batch_delivery_button = QPushButton("Batch Delivery")
        batch_delivery_button.clicked.connect(self.batch_delivery)
        toolbar.addWidget(batch_delivery_button)
        
        print_labels_button = QPushButton("Print Labels")
        print_labels_button.clicked.connect(self.print_labels)
        toolbar.addWidget(print_labels_button)
        
        # Add Edit button
        edit_button = QPushButton("Edit Item")
        edit_button.clicked.connect(self.edit_selected_item)
        # Disable for user and viewer accounts
        if self.user and not self.permissions_manager.has_permission(self.user, "orders", "edit"):
            edit_button.setEnabled(False)
        toolbar.addWidget(edit_button)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_button)
        
        # Add search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search order items...")
        self.search_input.textChanged.connect(self.search_order_items)
        toolbar.addWidget(self.search_input)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Filter section
        filter_layout = QHBoxLayout()
        
        # Customer filter
        customer_layout = QVBoxLayout()
        customer_label = QLabel("Customer:")
        self.customer_filter = QLineEdit()
        self.customer_filter.setPlaceholderText("Filter by customer...")
        self.customer_filter.textChanged.connect(self.apply_filters)
        customer_layout.addWidget(customer_label)
        customer_layout.addWidget(self.customer_filter)
        filter_layout.addLayout(customer_layout)
        
        # Order number filter
        order_layout = QVBoxLayout()
        order_label = QLabel("Order Number:")
        self.order_filter = QLineEdit()
        self.order_filter.setPlaceholderText("Filter by order number...")
        self.order_filter.textChanged.connect(self.apply_filters)
        order_layout.addWidget(order_label)
        order_layout.addWidget(self.order_filter)
        filter_layout.addLayout(order_layout)
        
        # Item code filter
        code_layout = QVBoxLayout()
        code_label = QLabel("Item Code:")
        self.code_filter = QLineEdit()
        self.code_filter.setPlaceholderText("Filter by item code...")
        self.code_filter.textChanged.connect(self.apply_filters)
        code_layout.addWidget(code_label)
        code_layout.addWidget(self.code_filter)
        filter_layout.addLayout(code_layout)
        
        # Item name filter
        name_layout = QVBoxLayout()
        name_label = QLabel("Item Name:")
        self.name_filter = QLineEdit()
        self.name_filter.setPlaceholderText("Filter by item name...")
        self.name_filter.textChanged.connect(self.apply_filters)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_filter)
        filter_layout.addLayout(name_layout)
        
        # Delivery date filter (month and year)
        date_layout = QVBoxLayout()
        date_label = QLabel("Delivery Date:")
        date_filter_layout = QHBoxLayout()
        
        # Month combo box
        self.month_filter = QComboBox()
        self.month_filter.setMinimumWidth(120)  # Make dropdown wider
        for i in range(1, 13):
            self.month_filter.addItem(calendar.month_name[i], i)
        self.month_filter.setCurrentIndex(datetime.now().month - 1)
        self.month_filter.currentIndexChanged.connect(self.apply_filters)
        
        # Year combo box
        self.year_filter = QComboBox()
        self.year_filter.setMinimumWidth(80)  # Make dropdown wider
        current_year = datetime.now().year
        for year in range(current_year - 2, current_year + 3):
            self.year_filter.addItem(str(year), year)
        self.year_filter.setCurrentText(str(current_year))
        self.year_filter.currentIndexChanged.connect(self.apply_filters)
        
        date_filter_layout.addWidget(self.month_filter)
        date_filter_layout.addWidget(self.year_filter)
        
        self.date_filter_enabled = QCheckBox("Enable")
        self.date_filter_enabled.stateChanged.connect(self.apply_filters)
        
        date_layout.addWidget(date_label)
        date_layout.addLayout(date_filter_layout)
        date_layout.addWidget(self.date_filter_enabled)
        filter_layout.addLayout(date_layout)
        
        # Show incomplete checkbox
        self.show_incomplete = QCheckBox("Show Incomplete")
        self.show_incomplete.setChecked(False)  # Changed from True to False
        self.show_incomplete.stateChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.show_incomplete)
        
        # Add filter layout to main layout
        layout.addLayout(filter_layout)
        
        # Table setup
        self.table = QTableWidget()
        self.setup_table()
        # Connect double-click signal
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        layout.addWidget(self.table)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        
        # Select All Filtered button
        self.select_all_filtered_btn = QPushButton("Select All Filtered")
        self.select_all_filtered_btn.clicked.connect(self.select_all_filtered)
        button_layout.addWidget(self.select_all_filtered_btn)
        
        # Print Labels button
        self.print_labels_btn = QPushButton("Print Labels")
        self.print_labels_btn.clicked.connect(self.print_labels)
        button_layout.addWidget(self.print_labels_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def setup_table(self):
        """Setup the table columns and properties"""
        # Check if user can see prices
        self.can_see_prices = True
        if self.user:
            from utils.permissions import get_permissions_manager
            permissions_manager = get_permissions_manager()
            self.can_see_prices = permissions_manager.can_access_column(self.user, "orders", "prices")
        
        # Set up columns based on permissions
        if self.can_see_prices:
            self.table.setColumnCount(13)
            self.table.setHorizontalHeaderLabels([
                "Select",
                "Customer",
                "Order Number",
                "Item Code",
                "Item Name",
                "Surface Treatment",
                "Quantity",
                "Delivered",
                "Remaining",
                "Delivery Date",
                "Last Delivery",
                "Price",
                "Note"
            ])
            
            # Set column widths
            self.table.setColumnWidth(0, 60)   # Select checkbox
            self.table.setColumnWidth(1, 200)  # Customer
            self.table.setColumnWidth(2, 120)  # Order Number
            self.table.setColumnWidth(3, 120)  # Item Code
            self.table.setColumnWidth(4, 300)  # Item Name
            self.table.setColumnWidth(5, 120)  # Surface Treatment
            self.table.setColumnWidth(6, 80)   # Quantity
            self.table.setColumnWidth(7, 80)   # Delivered
            self.table.setColumnWidth(8, 80)   # Remaining
            self.table.setColumnWidth(9, 100)  # Delivery Date
            self.table.setColumnWidth(10, 100) # Last Delivery
            self.table.setColumnWidth(11, 80)  # Price
            self.table.setColumnWidth(12, 150) # Note
        else:
            self.table.setColumnCount(12)
            self.table.setHorizontalHeaderLabels([
                "Select",
                "Customer",
                "Order Number",
                "Item Code",
                "Item Name",
                "Surface Treatment",
                "Quantity",
                "Delivered",
                "Remaining",
                "Delivery Date",
                "Last Delivery",
                "Note"
            ])
            
            # Set column widths
            self.table.setColumnWidth(0, 60)   # Select checkbox
            self.table.setColumnWidth(1, 200)  # Customer
            self.table.setColumnWidth(2, 120)  # Order Number
            self.table.setColumnWidth(3, 120)  # Item Code
            self.table.setColumnWidth(4, 300)  # Item Name
            self.table.setColumnWidth(5, 120)  # Surface Treatment
            self.table.setColumnWidth(6, 80)   # Quantity
            self.table.setColumnWidth(7, 80)   # Delivered
            self.table.setColumnWidth(8, 80)   # Remaining
            self.table.setColumnWidth(9, 100)  # Delivery Date
            self.table.setColumnWidth(10, 100) # Last Delivery
            self.table.setColumnWidth(11, 150) # Note
        
        # Disable row selection mode since we're using checkboxes
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

    def populate_table(self, order_items):
        """Populate the table with order items"""
        self.items = order_items
        self.table.setRowCount(len(order_items))
        
        for i, item in enumerate(order_items):
            # Add checkbox
            checkbox = QCheckBox()
            self.table.setCellWidget(i, 0, checkbox)
            
            # Add other item details
            self.table.setItem(i, 1, QTableWidgetItem(f"{item.order.customer.name_index} - {item.order.customer.name}"))
            self.table.setItem(i, 2, QTableWidgetItem(item.order.order_number))
            self.table.setItem(i, 3, QTableWidgetItem(item.item.customer_code))
            
            # Combine customer item name with product name
            customer_item_name = item.item.customer_item_name or ""
            if customer_item_name and item.item.product.name:
                display_name = f"{customer_item_name} ({item.item.product.name})"
            else:
                display_name = customer_item_name or item.item.product.name or ""
            
            self.table.setItem(i, 4, QTableWidgetItem(display_name))
            
            # Get surface treatment from order item
            surface_treatment = item.surface_treatment or ""
            self.table.setItem(i, 5, QTableWidgetItem(surface_treatment))
            
            self.table.setItem(i, 6, QTableWidgetItem(str(item.quantity)))
            self.table.setItem(i, 7, QTableWidgetItem(str(item.delivered_quantity)))
            self.table.setItem(i, 8, QTableWidgetItem(str(item.quantity - item.delivered_quantity)))
            
            delivery_date = QTableWidgetItem(item.delivery_date.strftime("%Y-%m-%d") if item.delivery_date else "")
            delivery_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 9, delivery_date)
            
            last_delivery = QTableWidgetItem(item.last_delivery_date.strftime("%Y-%m-%d") if item.last_delivery_date else "")
            last_delivery.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 10, last_delivery)
            
            if self.can_see_prices:
                price = QTableWidgetItem(f"{item.price:.2f}" if item.price else "")
                price.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, 11, price)
                # Add notes column (index 12)
                notes = QTableWidgetItem(item.notes or "")
                self.table.setItem(i, 12, notes)
            else:
                # Add notes column (index 11) for users who can't see prices
                notes = QTableWidgetItem(item.notes or "")
                self.table.setItem(i, 11, notes)
    
    def refresh_data(self):
        try:
            # Apply current filters instead of loading all items
            self.apply_filters()
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            QMessageBox.critical(self, "Error", f"Error refreshing data: {str(e)}")

    def get_selected_items(self):
        """Get selected items from the table"""
        selected_items = []
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget and isinstance(checkbox_widget, QCheckBox) and checkbox_widget.isChecked():
                # Get the order item directly from the stored data
                if hasattr(self, 'items') and row < len(self.items):
                    order_item = self.items[row]
                    selected_items.append(order_item)

                else:
                    logger.warning(f"Could not find item for row {row}")
        

        return selected_items
    
    def select_all(self):
        """Select all items in the table"""
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget and isinstance(checkbox_widget, QCheckBox):
                checkbox_widget.setChecked(True)
    
    def batch_delivery(self):
        selected_items = self.get_selected_items()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select items for batch delivery")
            return
        
        dialog = BatchDeliveryDialog(selected_items, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                delivered_count = 0
                fully_delivered_count = 0
                
                for item_data in data["items"]:
                    order_item = item_data["order_item"]
                    quantity = item_data["quantity"]
                    
                    if quantity > 0:
                        delivery = Delivery(
                            order_item_id=order_item.id,
                            quantity=quantity,
                            delivery_date=data["delivery_date"]
                        )
                        self.session.add(delivery)
                        order_item.delivered_quantity += quantity
                        order_item.last_delivery_date = data["delivery_date"]
                        delivered_count += 1
                        
                        # Check if item is now fully delivered
                        if order_item.delivered_quantity >= order_item.quantity:
                            fully_delivered_count += 1
                
                self.session.commit()
                self.refresh_data()
                
                # Provide detailed feedback
                message = f"Batch delivery completed successfully!\n\n"
                message += f"• {delivered_count} items delivered\n"
                if fully_delivered_count > 0:
                    message += f"• {fully_delivered_count} items are now fully delivered"
                    if self.show_incomplete.isChecked():
                        message += f"\n• These items may no longer be visible (filtered out by 'Show Incomplete')"
                
                QMessageBox.information(self, "Success", message)
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error processing deliveries: {str(e)}")
    
    def print_labels(self):
        """Generate and print labels for selected items using LabelPrintDialog (with barcode support)"""
        selected_items = self.get_selected_items()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select at least one item to print labels for.")
            return
        # Use the barcode-enabled LabelPrintDialog
        from views.dialogs.label_print_dialog import LabelPrintDialog
        dialog = LabelPrintDialog(self, selected_items, self.session)
        dialog.exec()

    def export_selected(self):
        selected_items = self.get_selected_items()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select items to export")
            return
            
        # Group items by customer
        customer_items = {}
        for order_item in selected_items:
            customer = order_item.order.customer
            if customer not in customer_items:
                customer_items[customer] = []
            customer_items[customer].append(order_item)
        
        # Create exports directory if it doesn't exist
        if not os.path.exists("exports"):
            os.makedirs("exports")
        
        # Export one file per customer
        try:
            for customer, items in customer_items.items():
                data = []
                for item in items:
                    remaining = item.quantity - item.delivered_quantity
                    data.append({
                        "Order Number": item.order.order_number,
                        "Item Name": item.item.customer_item_name or item.item.product.name,
                        "Order Date": item.order.order_date,
                        "Delivery Date": item.delivery_date,
                        "Ordered": item.quantity,
                        "Delivered": item.delivered_quantity,
                        "Remaining": remaining
                    })
                
                df = pd.DataFrame(data)
                filename = f"exports/{customer.name_index}_{date.today().strftime('%Y%m%d')}.xlsx"
                df.to_excel(filename, index=False)
            
            QMessageBox.information(self, "Success", "Export completed successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error exporting data: {str(e)}")

    def search_order_items(self, text):
        """Search order items based on text input"""
        if not text:
            self.refresh_data()
            return
            
        search = f"%{text}%"
        order_items = self.session.query(OrderItem).join(Order).join(Customer).join(Item, OrderItem.item_id == Item.id).filter(
            or_(
                Order.order_number.ilike(search),
                Customer.name.ilike(search),
                Customer.name_index.ilike(search),
                Item.customer_code.ilike(search),
                Item.customer_item_name.ilike(search)
            )
        ).order_by(Order.order_date.desc()).all()
        
        self.populate_table(order_items)

    def apply_filters(self):
        """Apply all filters to the table by rebuilding the data"""
        try:
            # Start with all order items
            query = self.session.query(OrderItem).join(Order).join(Customer).join(Item, OrderItem.item_id == Item.id)
            
            # Apply customer filter
            if self.customer_filter.text():
                customer_search = f"%{self.customer_filter.text()}%"
                query = query.filter(
                    or_(
                        Customer.name.ilike(customer_search),
                        Customer.name_index.ilike(customer_search)
                    )
                )
            
            # Apply order number filter
            if self.order_filter.text():
                order_search = f"%{self.order_filter.text()}%"
                query = query.filter(Order.order_number.ilike(order_search))
            
            # Apply item code filter
            if self.code_filter.text():
                code_search = f"%{self.code_filter.text()}%"
                query = query.filter(Item.customer_code.ilike(code_search))
            
            # Apply item name filter
            if self.name_filter.text():
                name_search = f"%{self.name_filter.text()}%"
                query = query.filter(
                    or_(
                        Item.customer_item_name.ilike(name_search),
                        Item.product.has(Product.name.ilike(name_search))
                    )
                )
            
            # Apply delivery date filter if enabled
            if self.date_filter_enabled.isChecked():
                filter_month = self.month_filter.currentData()
                filter_year = self.year_filter.currentData()
                query = query.filter(
                    extract('month', OrderItem.delivery_date) == filter_month,
                    extract('year', OrderItem.delivery_date) == filter_year
                )
            
            # Apply incomplete filter
            if self.show_incomplete.isChecked():
                query = query.filter(OrderItem.quantity > OrderItem.delivered_quantity)
            else:
                pass
            
            # Order by delivery date descending
            order_items = query.order_by(OrderItem.delivery_date.desc()).all()
            

            
            # Update the table with filtered data
            self.populate_table(order_items)
            
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            QMessageBox.critical(self, "Error", f"Error applying filters: {str(e)}")

    def select_all_filtered(self):
        """Select or deselect all items currently visible in the table after filtering"""
        # Check if all visible items are currently selected
        all_selected = True
        visible_count = 0
        
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                visible_count += 1
                checkbox = self.table.cellWidget(row, 0)
                if checkbox and not checkbox.isChecked():
                    all_selected = False
                    break
        
        # If all visible items are selected, deselect them. Otherwise, select all visible items.
        select_all = not all_selected
        
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                checkbox = self.table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(select_all)
        
        # Update button text
        self.select_all_filtered_btn.setText("Deselect All Filtered" if select_all else "Select All Filtered")
        
        if visible_count > 0:
            action = "selected" if select_all else "deselected"
            QMessageBox.information(self, "Selection Complete", f"All {visible_count} currently visible items have been {action}.")
        else:
            QMessageBox.information(self, "No Items", "No items are currently visible to select.")

    def edit_selected_item(self):
        """Edit the selected order item"""
        # Check permissions for editing
        if self.user and not self.permissions_manager.has_permission(self.user, "orders", "edit"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit order items.")
            return
            
        selected_items = self.get_selected_items()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select an item to edit")
            return
        
        if len(selected_items) > 1:
            QMessageBox.warning(self, "Warning", "Please select only one item to edit")
            return
        
        order_item = selected_items[0]
        dialog = EditOrderItemDialog(self.session, order_item, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()

    def on_table_double_clicked(self, row, column):
        """Handle double-click to edit the item in the table"""
        if column == 0: # Only edit if double-clicked on the checkbox column
            return

        # Check permissions for editing
        if self.user and not self.permissions_manager.has_permission(self.user, "orders", "edit"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit order items.")
            return
        
        # Check if double-clicked on notes column
        notes_column_index = 12 if self.can_see_prices else 11
        if column == notes_column_index:
            # Edit notes directly in the table
            self.edit_notes_inline(row, column)
            return

        order_item = self.items[row] # Get the order item from the populated list
        dialog = EditOrderItemDialog(self.session, order_item, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()
    
    def edit_notes_inline(self, row, column):
        """Edit notes directly in the table"""
        from PyQt6.QtWidgets import QInputDialog
        
        # Get current notes
        current_notes = self.table.item(row, column).text() if self.table.item(row, column) else ""
        
        # Show input dialog for notes
        notes, ok = QInputDialog.getMultiLineText(
            self, 
            "Edit Notes", 
            "Enter notes for this order item:",
            current_notes
        )
        
        if ok:
            # Update the table item
            self.table.setItem(row, column, QTableWidgetItem(notes))
            
            # Update the database
            try:
                order_item = self.items[row]
                order_item.notes = notes
                self.session.commit()
                QMessageBox.information(self, "Success", "Notes updated successfully!")
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error updating notes: {str(e)}")

class EditOrderItemDialog(QDialog):
    def __init__(self, session, order_item, parent=None):
        super().__init__(parent)
        self.session = session
        # Re-query the order_item with its relationships to avoid detached instance error
        from models.database import OrderItem, Item, Product, Order, Customer
        from sqlalchemy.orm import joinedload
        self.order_item = session.query(OrderItem).options(
            joinedload(OrderItem.item).joinedload(Item.product),
            joinedload(OrderItem.order).joinedload(Order.customer)
        ).filter(OrderItem.id == order_item.id).first()
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
        
        # Notes field
        from PyQt6.QtWidgets import QTextEdit
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)  # Limit height for notes
        self.notes_input.setPlainText(self.order_item.notes or "")
        layout.addRow("Notes:", self.notes_input)
        
        # Recalculate button
        recalc_button = QPushButton("Recalculate Surface Treatment")
        recalc_button.clicked.connect(self.recalculate_surface_treatment)
        layout.addRow("", recalc_button)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow("", button_box)
        
        self.setLayout(layout)
    
    def recalculate_surface_treatment(self):
        """Recalculate surface treatment based on business logic"""
        # Ask user for confirmation before recalculating
        reply = QMessageBox.question(
            self, 
            "Confirm Recalculation", 
            "This will recalculate the surface treatment based on the item name and customer.\n\n"
            "Any custom surface treatment value will be overwritten.\n\n"
            "Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            calculated_treatment = self.order_item.calculate_surface_treatment()
            index = self.surface_treatment_combo.findText(calculated_treatment)
            if index >= 0:
                self.surface_treatment_combo.setCurrentIndex(index)
                QMessageBox.information(self, "Recalculated", f"Surface treatment recalculated to: {calculated_treatment}")
            else:
                QMessageBox.warning(self, "Error", f"Could not set calculated treatment: {calculated_treatment}")
    
    def accept(self):
        """Save changes to the order item"""
        try:
            # Update order item
            self.order_item.quantity = self.quantity_input.value()
            self.order_item.price = self.price_input.value()
            self.order_item.delivery_date = self.delivery_date_input.date().toPyDate()
            self.order_item.surface_treatment = self.surface_treatment_combo.currentText()
            self.order_item.notes = self.notes_input.toPlainText()
            
            # Commit changes
            self.session.commit()
            
            QMessageBox.information(self, "Success", "Order item updated successfully!")
            super().accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error updating order item: {str(e)}") 