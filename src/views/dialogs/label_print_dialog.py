from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QCheckBox, QSpinBox, QMessageBox,
    QHeaderView, QComboBox, QGroupBox, QGridLayout,
    QRadioButton, QButtonGroup, QSlider
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from sqlalchemy.orm import Session
from datetime import datetime
import os
from pathlib import Path
from models.database import OrderItem, Customer, Order
from utils.label_generator import LabelGenerator
import traceback
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph, PageBreak
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPM
from io import BytesIO
from views.dialogs.box_split_dialog import BoxSplitDialog
import tempfile

class LabelPrintDialog(QDialog):
    def __init__(self, parent, order_items, session=None, user=None):
        super().__init__(parent)
        self.order_items = order_items
        self.session = session
        self.user = user
        
        # Set up export directory in /Users/andyschwar/orders/export
        self.export_dir = "/Users/andyschwar/orders/export"
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)
            
        self.label_generator = LabelGenerator(self.export_dir)
        self.preview_file = None
        self.final_file = None
        
        # Filtered mode variables
        self.filtered_mode = False
        self.customers = []
        self.filtered_orders = []
        self.filtered_order_items = []
        
        # Formatting options
        self.label_size = "standard"  # standard, large, small
        self.layout_type = "2x3"  # 2x3, 3x2, 1x4, 4x1
        self.include_barcodes = self.get_customer_barcode_setting()
        self.include_weight = True
        self.include_delivery_date = True
        self.include_supplier_info = True
        self.font_size = 12
        self.label_style = "modern"  # modern, classic, compact
        
        self.setWindowTitle("Print Labels")
        self.setModal(True)
        self.setMinimumSize(1200, 800)
        
        self.init_ui()
    
    def get_customer_barcode_setting(self):
        """Get the customer's default barcode setting from the database"""
        try:
            if not self.session or not self.order_items:
                print("[DEBUG] No session or order items, defaulting to barcodes enabled")
                return True
                
            # Get the first order item to find the customer
            first_item = self.order_items[0]
            if hasattr(first_item, 'order') and hasattr(first_item.order, 'customer'):
                customer = first_item.order.customer
                barcode_setting = customer.barcodes_enabled if customer.barcodes_enabled is not None else False
                print(f"[DEBUG] Customer {customer.name_index} barcode setting: {barcode_setting}")
                return barcode_setting
            else:
                print("[DEBUG] Could not find customer, defaulting to barcodes enabled")
                return True
        except Exception as e:
            print(f"[DEBUG] Error getting customer barcode setting: {e}, defaulting to barcodes enabled")
            return True
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Add filtered mode checkbox at the top
        filter_layout = QHBoxLayout()
        self.filtered_mode_checkbox = QCheckBox("Filtered Mode (Customer → Orders → Undelivered Items)")
        self.filtered_mode_checkbox.stateChanged.connect(self.on_filtered_mode_changed)
        filter_layout.addWidget(self.filtered_mode_checkbox)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Add customer and order selection (initially disabled)
        selection_layout = QHBoxLayout()
        
        # Customer selection
        customer_label = QLabel("Customer:")
        self.customer_combo = QComboBox()
        self.customer_combo.setEnabled(False)
        self.customer_combo.currentIndexChanged.connect(self.on_customer_changed)
        selection_layout.addWidget(customer_label)
        selection_layout.addWidget(self.customer_combo)
        
        # Order selection
        order_label = QLabel("Order:")
        self.order_combo = QComboBox()
        self.order_combo.setEnabled(False)
        self.order_combo.currentIndexChanged.connect(self.on_order_changed)
        selection_layout.addWidget(order_label)
        selection_layout.addWidget(self.order_combo)
        
        selection_layout.addStretch()
        layout.addLayout(selection_layout)
        
        # Create items table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Select",
            "Order",
            "Customer",
            "Customer Item Name",
            "Customer Item Code",
            "Total Qty",
            "Print Qty",
            "Split"
        ])
        
        # Set column widths
        self.table.setColumnWidth(0, 60)   # Select checkbox
        self.table.setColumnWidth(1, 120)  # Order
        self.table.setColumnWidth(2, 150)  # Customer
        self.table.setColumnWidth(3, 350)  # Customer Item Name
        self.table.setColumnWidth(4, 150)  # Customer Item Code
        self.table.setColumnWidth(5, 100)  # Total Qty
        self.table.setColumnWidth(6, 100)  # Print Qty
        self.table.setColumnWidth(7, 100)  # Split
        
        layout.addWidget(self.table)
        
        # Add help text
        help_text = QLabel("Select items and specify quantities to print labels. Choose between 6 labels per page or 4 labels per page with bigger text.")
        help_text.setStyleSheet("color: #666;")
        layout.addWidget(help_text)
        
        # Add formatting options section
        formatting_group = QGroupBox("Label Formatting Options")
        formatting_layout = QGridLayout()
        
        # Label size options (simplified)
        size_label = QLabel("Label Size:")
        self.size_combo = QComboBox()
        self.size_combo.addItems(["Standard"])
        self.size_combo.setCurrentText("Standard")
        self.size_combo.currentTextChanged.connect(self.on_size_changed)
        formatting_layout.addWidget(size_label, 0, 0)
        formatting_layout.addWidget(self.size_combo, 0, 1)
        
        # Layout options
        layout_label = QLabel("Layout:")
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["6 labels per page", "4 labels per page (bigger text)"])
        self.layout_combo.setCurrentText("6 labels per page")
        self.layout_combo.currentTextChanged.connect(self.on_layout_changed)
        formatting_layout.addWidget(layout_label, 0, 2)
        formatting_layout.addWidget(self.layout_combo, 0, 3)
        
        # Style options (simplified)
        style_label = QLabel("Style:")
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Modern"])
        self.style_combo.setCurrentText("Modern")
        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        formatting_layout.addWidget(style_label, 1, 0)
        formatting_layout.addWidget(self.style_combo, 1, 1)
        
        # Font size (auto-adjusted based on layout)
        font_label = QLabel("Font Size:")
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setMinimum(8)
        self.font_slider.setMaximum(16)
        self.font_slider.setValue(12)
        self.font_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.font_slider.setTickInterval(2)
        self.font_slider.valueChanged.connect(self.on_font_size_changed)
        self.font_size_label = QLabel("12")
        formatting_layout.addWidget(font_label, 1, 2)
        formatting_layout.addWidget(self.font_slider, 1, 3)
        formatting_layout.addWidget(self.font_size_label, 1, 4)
        
        # Checkboxes for content options
        self.barcode_checkbox = QCheckBox("Include Barcodes")
        self.barcode_checkbox.setChecked(self.include_barcodes)  # Use customer's default setting
        print(f"[DEBUG] Initial barcode checkbox state: {self.include_barcodes}")
        self.barcode_checkbox.stateChanged.connect(self.on_barcode_changed)
        formatting_layout.addWidget(self.barcode_checkbox, 2, 0)
        
        self.weight_checkbox = QCheckBox("Include Weight")
        self.weight_checkbox.setChecked(True)
        self.weight_checkbox.stateChanged.connect(self.on_weight_changed)
        formatting_layout.addWidget(self.weight_checkbox, 2, 1)
        
        self.delivery_checkbox = QCheckBox("Include Delivery Date")
        self.delivery_checkbox.setChecked(True)
        self.delivery_checkbox.stateChanged.connect(self.on_delivery_changed)
        formatting_layout.addWidget(self.delivery_checkbox, 2, 2)
        
        self.supplier_checkbox = QCheckBox("Include Supplier Info")
        self.supplier_checkbox.setChecked(True)
        self.supplier_checkbox.stateChanged.connect(self.on_supplier_changed)
        formatting_layout.addWidget(self.supplier_checkbox, 2, 3)
        
        formatting_group.setLayout(formatting_layout)
        layout.addWidget(formatting_group)
        
        # Add buttons
        button_box = QHBoxLayout()
        
        preview_button = QPushButton("Preview Labels")
        preview_button.clicked.connect(self.preview_labels)
        button_box.addWidget(preview_button)
        
        generate_labels_button = QPushButton("Generate Labels")
        generate_labels_button.clicked.connect(self.generate_labels_and_close)
        button_box.addWidget(generate_labels_button)
        
        generate_labels_save_button = QPushButton("Generate and Save")
        generate_labels_save_button.clicked.connect(self.generate_labels_and_save_and_close)
        button_box.addWidget(generate_labels_save_button)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_box.addWidget(close_button)
        layout.addLayout(button_box)
        
        # Set margins for the main layout
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)
        
        # Load initial data
        self.load_customers()
        self.populate_table()
    
    def on_size_changed(self, size_text):
        """Handle label size change"""
        size_mapping = {
            "Standard": "standard",
            "Large": "large", 
            "Small": "small",
            "Custom": "custom"
        }
        self.label_size = size_mapping.get(size_text, "standard")
    
    def on_layout_changed(self, layout_text):
        """Handle layout type change"""
        layout_mapping = {
            "6 labels per page": "2x3",
            "4 labels per page (bigger text)": "2x2"
        }
        self.layout_type = layout_mapping.get(layout_text, "2x3")
        
        # Automatically adjust font size for 4 labels per page
        if layout_text == "4 labels per page (bigger text)":
            self.font_slider.setValue(14)  # Bigger font for 4 labels
        else:
            self.font_slider.setValue(10)  # Standard font for 6 labels
    
    def on_style_changed(self, style_text):
        """Handle label style change"""
        style_mapping = {
            "Modern": "modern",
            "Classic": "classic",
            "Compact": "compact"
        }
        self.label_style = style_mapping.get(style_text, "modern")
    
    def on_font_size_changed(self, value):
        """Handle font size change"""
        self.font_size = value
        self.font_size_label.setText(str(value))
    
    def on_barcode_changed(self, state):
        """Handle barcode checkbox change"""
        self.include_barcodes = state == Qt.CheckState.Checked.value
        print(f"[DEBUG] Barcode checkbox changed: state={state}, include_barcodes={self.include_barcodes}")
    
    def on_weight_changed(self, state):
        """Handle weight checkbox change"""
        self.include_weight = state == Qt.CheckState.Checked
    
    def on_delivery_changed(self, state):
        """Handle delivery date checkbox change"""
        self.include_delivery_date = state == Qt.CheckState.Checked
    
    def on_supplier_changed(self, state):
        """Handle supplier info checkbox change"""
        self.include_supplier_info = state == Qt.CheckState.Checked
    
    def on_filtered_mode_changed(self, state):
        """Handle filtered mode checkbox state change"""
        self.filtered_mode = state == Qt.CheckState.Checked
        self.customer_combo.setEnabled(self.filtered_mode)
        self.order_combo.setEnabled(False)
        self.order_combo.clear()
        
        if self.filtered_mode:
            # Clear the table and show filtered items
            self.populate_table()
        else:
            # Show all original items
            self.populate_table()
    
    def load_customers(self):
        """Load customers for the dropdown"""
        if not self.session:
            return
            
        self.customers = self.session.query(Customer).order_by(Customer.name_index).all()
        self.customer_combo.clear()
        for customer in self.customers:
            self.customer_combo.addItem(f"{customer.name_index} - {customer.name}", customer.id)
    
    def on_customer_changed(self, index):
        """Handle customer selection change"""
        if not self.filtered_mode or index < 0:
            self.order_combo.clear()
            self.order_combo.setEnabled(False)
            return
            
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            return
            
        # Load orders for this customer
        self.filtered_orders = self.session.query(Order).filter(
            Order.customer_id == customer_id
        ).order_by(Order.order_date.desc()).all()
        
        self.order_combo.clear()
        self.order_combo.setEnabled(True)
        for order in self.filtered_orders:
            self.order_combo.addItem(order.order_number, order.id)
    
    def on_order_changed(self, index):
        """Handle order selection change"""
        if not self.filtered_mode or index < 0:
            self.populate_table()
            return
            
        order_id = self.order_combo.currentData()
        if not order_id:
            return
            
        # Load undelivered order items for this order
        self.filtered_order_items = self.session.query(OrderItem).filter(
            OrderItem.order_id == order_id,
            OrderItem.quantity > OrderItem.delivered_quantity
        ).all()
        
        self.populate_table()
    
    def populate_table(self):
        """Populate the table with items based on current mode"""
        if self.filtered_mode:
            items_to_show = self.filtered_order_items
        else:
            items_to_show = self.order_items
        
        # Clear existing table
        self.table.setRowCount(0)
        self.qty_inputs = []
        
        if not items_to_show:
            return
        
        # Populate table
        self.table.setRowCount(len(items_to_show))
        
        for i, item in enumerate(items_to_show):
            # Create checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.table.setCellWidget(i, 0, checkbox)
            
            # Add other item details
            self.table.setItem(i, 1, QTableWidgetItem(item.order.order_number))
            self.table.setItem(i, 2, QTableWidgetItem(f"{item.order.customer.name_index} - {item.order.customer.name}"))
            
            # Combine customer item name with product name
            customer_item_name = item.item.customer_item_name or ""
            if customer_item_name and item.item.product.name:
                display_name = f"{customer_item_name} ({item.item.product.name})"
            else:
                display_name = customer_item_name or item.item.product.name or ""
            
            self.table.setItem(i, 3, QTableWidgetItem(display_name))
            self.table.setItem(i, 4, QTableWidgetItem(item.item.customer_code))
            
            # Show remaining quantity for filtered mode
            if self.filtered_mode:
                remaining_qty = item.quantity - item.delivered_quantity
                self.table.setItem(i, 5, QTableWidgetItem(f"{remaining_qty} (of {item.quantity})"))
            else:
                self.table.setItem(i, 5, QTableWidgetItem(str(item.quantity)))
            
            # Add quantity input
            qty_input = QSpinBox()
            qty_input.setMinimum(1)
            if self.filtered_mode:
                remaining_qty = item.quantity - item.delivered_quantity
                qty_input.setMaximum(remaining_qty)
                qty_input.setValue(remaining_qty)
            else:
                qty_input.setMaximum(item.quantity)
                qty_input.setValue(item.quantity)
            self.qty_inputs.append(qty_input)
            self.table.setCellWidget(i, 6, qty_input)
            
            # Add split boxes button
            split_button = QPushButton("Split Boxes")
            split_button.clicked.connect(lambda checked, row=i: self.split_boxes(row))
            self.table.setCellWidget(i, 7, split_button)
        
        # Set row heights to be more comfortable
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, 30)
    
    def get_data(self):
        items_data = []
        
        try:
            # Get the items to process based on current mode
            if self.filtered_mode:
                items_to_process = self.filtered_order_items
            else:
                items_to_process = self.order_items
            
            print(f"[DEBUG] get_data: Processing {len(items_to_process)} items")
            
            for i, item in enumerate(items_to_process):
                try:
                    checkbox = self.table.cellWidget(i, 0)
                    if not checkbox.isChecked():
                        continue
                        
                    qty_input = self.qty_inputs[i]
                    try:
                        quantity = int(qty_input.text() or "0")
                        if quantity <= 0:
                            continue
                        
                        # Validate quantity based on mode
                        if self.filtered_mode:
                            # Handle None values for delivered_quantity
                            delivered_qty = item.delivered_quantity or 0
                            remaining_qty = (item.quantity or 0) - delivered_qty
                            if quantity > remaining_qty:
                                raise ValueError(f"Invalid quantity for {item.order.order_number}: {quantity} > {remaining_qty} (remaining)")
                        else:
                            item_qty = item.quantity or 0
                            if quantity > item_qty:
                                raise ValueError(f"Invalid quantity for {item.order.order_number}: {quantity} > {item_qty}")
                            
                        items_data.append({
                            "order_item": item,
                            "quantity": quantity,
                            "formatting_options": {
                                "label_size": self.label_size,
                                "layout_type": self.layout_type,
                                "include_barcodes": self.include_barcodes,
                                "include_weight": self.include_weight,
                                "include_delivery_date": self.include_delivery_date,
                                "include_supplier_info": self.include_supplier_info,
                                "font_size": self.font_size,
                                "label_style": self.label_style
                            }
                        })
                        
                    except ValueError as e:
                        QMessageBox.warning(self, "Validation Error", str(e))
                        return None
                        
                except Exception as e:
                    continue
            
            if not items_data:
                QMessageBox.warning(self, "Validation Error", "No items selected for label printing")
                return None
                
            print(f"[DEBUG] get_data: Returning {len(items_data)} items for label generation")
            return items_data
            
        except Exception as e:
            print(f"[DEBUG] get_data: Error processing data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error processing data: {str(e)}")
            return None
    
    def preview_labels(self):
        """Generate preview of labels without barcodes"""
        try:
            items_data = self.get_data()
            if not items_data:
                return
            
            # Extract formatting options from the first item
            formatting_options = None
            if items_data and "formatting_options" in items_data[0]:
                formatting_options = items_data[0]["formatting_options"]
                # Override barcodes setting for preview
                formatting_options["include_barcodes"] = False
                
            # Generate labels without barcodes
            self.preview_file = self.label_generator.generate_labels(items_data, include_barcodes=False, formatting_options=formatting_options, printed_by=self.user.username if self.user else "Unknown", session=self.session)
            
            # Open the PDF file
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.preview_file))
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating preview: {str(e)}")
            
    def generate_barcodes(self):
        print("[DEBUG] generate_barcodes called")
        """Generate final labels with barcodes"""
        try:
            print("\n=== Generating final labels with barcodes ===")
            items_data = self.get_data()
            if not items_data:
                return
                
            # Generate labels with barcodes (use checkbox setting)
            print(f"[DEBUG] Generating labels with include_barcodes={self.include_barcodes}")
            self.final_file = self.label_generator.generate_labels(items_data, include_barcodes=self.include_barcodes, printed_by=self.user.username if self.user else "Unknown", session=self.session)
            print(f"Final labels saved to: {self.final_file}")
            
            # Open the PDF file
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.final_file))
            
            # Show success message
            QMessageBox.information(
                self,
                "Success",
                f"Labels with barcodes generated successfully!\n\nLabels saved to:\n{self.final_file}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating barcodes: {str(e)}")
            
    def closeEvent(self, event):
        """Clean up temporary files when dialog is closed"""
        try:
            if hasattr(self, 'preview_file') and self.preview_file and os.path.exists(self.preview_file):
                os.unlink(self.preview_file)
            # Don't delete the final file as it's the actual generated file
        except Exception as e:
            pass
        event.accept()

    def split_boxes(self, row):
        """Open the box split dialog for the selected item"""
        item = self.order_items[row]
        quantity = self.qty_inputs[row].value()
        item_name = item.item.customer_item_name or item.item.product.name
        
        dialog = BoxSplitDialog(item_name, quantity, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            box_quantities = dialog.get_box_quantities()
            # Update the quantity input to reflect the total
            self.qty_inputs[row].setValue(sum(box_quantities))
            # Store the box quantities for label generation
            if not hasattr(self, 'box_quantities'):
                self.box_quantities = {}
            self.box_quantities[row] = box_quantities
            # Update the split button text
            split_button = self.table.cellWidget(row, 7)
            split_button.setText(f"Split ({len(box_quantities)} boxes)")

    def create_barcode(self, code):
        """Create a Code128 barcode Flowable for ReportLab"""
        return code128.Code128(code, barHeight=30, barWidth=1.0)

    def generate_labels(self):
        """Generate labels for selected items with formatting options"""
        try:
            items_data = self.get_data()
            if not items_data:
                return
            
            # Extract formatting options from the first item
            formatting_options = None
            if items_data and "formatting_options" in items_data[0]:
                formatting_options = items_data[0]["formatting_options"]
                # Use the barcode setting from the UI
                formatting_options["include_barcodes"] = self.include_barcodes
                
            # Generate labels with formatting options
            self.final_file = self.label_generator.generate_labels(items_data, include_barcodes=self.include_barcodes, formatting_options=formatting_options, printed_by=self.user.username if self.user else "Unknown", session=self.session)
            
            # Show success message
            QMessageBox.information(
                self,
                "Success",
                f"Labels generated successfully!\n\nLabels saved to:\n{self.final_file}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating labels: {str(e)}") 

    def generate_labels_and_close(self):
        """Generate labels and close the dialog"""
        try:
            self.generate_labels()
            self.accept()  # Close the dialog
        except Exception as e:
            # Don't close on error, let user see the error message
            pass

    def generate_labels_and_save_and_close(self):
        """Generate labels, save to user-specified location, and close the dialog"""
        try:
            self.generate_labels_and_save()
            self.accept()  # Close the dialog
        except Exception as e:
            # Don't close on error, let user see the error message
            pass

    def generate_labels_and_save(self):
        """Generate labels and save to user-specified location with formatting options"""
        from PyQt6.QtWidgets import QFileDialog
        
        # Ask user for save location
        pdf_path, _ = QFileDialog.getSaveFileName(self, "Save Labels PDF", str(Path.home() / "labels.pdf"), "PDF Files (*.pdf)")
        if not pdf_path:
            return
            
        try:
            items_data = self.get_data()
            if not items_data:
                return
            
            # Extract formatting options from the first item
            formatting_options = None
            if items_data and "formatting_options" in items_data[0]:
                formatting_options = items_data[0]["formatting_options"]
                # Use the barcode setting from the UI
                formatting_options["include_barcodes"] = self.include_barcodes
                
            # Generate labels with formatting options
            self.final_file = self.label_generator.generate_labels(items_data, include_barcodes=self.include_barcodes, formatting_options=formatting_options, printed_by=self.user.username if self.user else "Unknown", session=self.session)
            
            # Copy the generated file to the user-specified location
            import shutil
            shutil.copy2(self.final_file, pdf_path)
            
            # Show success message
            QMessageBox.information(
                self,
                "Success",
                f"Labels generated and saved successfully!\n\nLabels saved to:\n{pdf_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating labels: {str(e)}") 

def replace_czech_chars(text):
    """Replace Czech characters with ASCII equivalents for better font compatibility"""
    replacements = {
        'Á': 'A', 'á': 'a',
        'Č': 'C', 'č': 'c',
        'Ď': 'D', 'ď': 'd',
        'É': 'E', 'é': 'e',
        'Ě': 'E', 'ě': 'e',
        'Í': 'I', 'í': 'i',
        'Ň': 'N', 'ň': 'n',
        'Ó': 'O', 'ó': 'o',
        'Ř': 'R', 'ř': 'r',
        'Š': 'S', 'š': 's',
        'Ť': 'T', 'ť': 't',
        'Ú': 'U', 'ú': 'u',
        'Ů': 'U', 'ů': 'u',
        'Ý': 'Y', 'ý': 'y',
        'Ž': 'Z', 'ž': 'z'
    }
    
    for czech_char, ascii_char in replacements.items():
        text = text.replace(czech_char, ascii_char)
    
    return text 