from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QSpinBox, QDoubleSpinBox, QFileDialog, QCheckBox, QDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from sqlalchemy.orm import Session
from models.database import Customer, OrderItem, Product, Item, Order
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import os
from datetime import datetime
import subprocess
from pathlib import Path
import pandas as pd
from views.dialogs.label_print_dialog import LabelPrintDialog

class LabelsTab(QWidget):
    def __init__(self, session: Session, user=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self.labels = []
        self.filtered_mode = False
        self.filtered_orders = []
        self.filtered_order_items = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Filtered mode checkbox
        filter_layout = QHBoxLayout()
        self.filtered_mode_checkbox = QCheckBox("Filtered Mode (Customer → Order → Undelivered Items)")
        self.filtered_mode_checkbox.stateChanged.connect(self.on_filtered_mode_changed)
        filter_layout.addWidget(self.filtered_mode_checkbox)
        
        # Warning text for when filtered mode is off
        self.warning_label = QLabel("⚠️ No data validation - enter data at your own risk")
        self.warning_label.setStyleSheet("color: red; font-weight: bold;")
        self.warning_label.setVisible(False)  # Initially hidden since filtered mode is default
        filter_layout.addWidget(self.warning_label)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Order number
        order_layout = QHBoxLayout()
        order_layout.addWidget(QLabel("Order number:"))
        self.order_input = QLineEdit()
        order_layout.addWidget(self.order_input)
        layout.addLayout(order_layout)

        # Customer
        customer_layout = QHBoxLayout()
        customer_layout.addWidget(QLabel("Customer:"))
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(200)
        self.load_customers()
        self.customer_combo.currentIndexChanged.connect(self.on_customer_changed)
        customer_layout.addWidget(self.customer_combo)
        layout.addLayout(customer_layout)

        # Order selection (filtered mode only)
        order_select_layout = QHBoxLayout()
        order_select_layout.addWidget(QLabel("Order:"))
        self.order_combo = QComboBox()
        self.order_combo.setEnabled(False)
        self.order_combo.currentIndexChanged.connect(self.on_order_changed)
        order_select_layout.addWidget(self.order_combo)
        layout.addLayout(order_select_layout)

        # Item search
        item_search_layout = QHBoxLayout()
        item_search_layout.addWidget(QLabel("Search item:"))
        self.item_search_input = QLineEdit()
        self.item_search_input.setPlaceholderText("Enter item code or name to search...")
        self.item_search_input.textChanged.connect(self.filter_items)
        item_search_layout.addWidget(self.item_search_input)
        layout.addLayout(item_search_layout)

        # Item
        item_layout = QHBoxLayout()
        item_layout.addWidget(QLabel("Item:"))
        self.item_combo = QComboBox()
        self.item_combo.setMinimumWidth(300)
        self.item_combo.currentIndexChanged.connect(self.on_item_changed)
        item_layout.addWidget(self.item_combo)
        layout.addLayout(item_layout)

        # Quantity
        qty_layout = QHBoxLayout()
        qty_layout.addWidget(QLabel("Quantity:"))
        self.qty_input = QSpinBox()
        self.qty_input.setMinimum(1)
        self.qty_input.setMaximum(100000)
        qty_layout.addWidget(self.qty_input)
        layout.addLayout(qty_layout)

        # Add/Clear/Generate buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add label")
        add_btn.clicked.connect(self.add_label)
        btn_layout.addWidget(add_btn)
        
        delete_btn = QPushButton("Delete selected")
        delete_btn.clicked.connect(self.delete_selected_label)
        btn_layout.addWidget(delete_btn)
        
        clear_btn = QPushButton("Clear all")
        clear_btn.clicked.connect(self.clear_labels)
        btn_layout.addWidget(clear_btn)
        
        export_btn = QPushButton("Export to Excel")
        export_btn.clicked.connect(self.export_to_excel)
        btn_layout.addWidget(export_btn)
        
        gen_btn = QPushButton("Generate labels")
        gen_btn.clicked.connect(self.generate_labels)
        btn_layout.addWidget(gen_btn)
        
        gen_save_btn = QPushButton("Generate labels and save")
        gen_save_btn.clicked.connect(self.generate_labels_and_save)
        btn_layout.addWidget(gen_save_btn)
        
        layout.addLayout(btn_layout)

        # Labels table
        self.labels_table = QTableWidget()
        self.labels_table.setColumnCount(5)
        self.labels_table.setHorizontalHeaderLabels(["Customer", "Order Number", "Item Code", "Item Name", "Quantity"])
        self.labels_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.labels_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.labels_table)

        self.setLayout(layout)
        self.load_items()
        self.update_filtered_mode_ui()
        
        # Make filtered mode the default
        self.filtered_mode_checkbox.setChecked(True)

    def on_filtered_mode_changed(self, state):
        self.filtered_mode = self.filtered_mode_checkbox.isChecked()
        self.update_filtered_mode_ui()

    def update_filtered_mode_ui(self):
        if self.filtered_mode:
            self.order_input.setEnabled(False)
            self.item_search_input.setEnabled(True)  # Enable item search in filtered mode
            self.qty_input.setEnabled(True)  # Enable quantity input in filtered mode
            self.order_combo.setEnabled(True)
            self.customer_combo.setEnabled(True)
            # Don't reload customers here, just ensure the connection is active
            if self.customer_combo.currentIndex() >= 0:
                self.on_customer_changed(self.customer_combo.currentIndex())
            self.warning_label.setVisible(False) # Hide warning when filtered mode is on
        else:
            self.order_input.setEnabled(True)
            self.item_search_input.setEnabled(True)
            self.qty_input.setEnabled(True)
            self.order_combo.setEnabled(False)
            self.load_customers()
            self.load_items()
            self.warning_label.setVisible(True) # Show warning when filtered mode is off

    def on_customer_changed(self, index):
        if self.filtered_mode:
            if index < 0 or not hasattr(self, 'customers') or not self.customers:
                self.order_combo.clear()
                self.item_combo.clear()
                return
            customer_id = self.customers[index].id
            # Load only orders that have undelivered items for this customer
            self.filtered_orders = self.session.query(Order).join(OrderItem).filter(
                Order.customer_id == customer_id,
                OrderItem.quantity > OrderItem.delivered_quantity
            ).distinct().order_by(Order.order_date.desc()).all()
            self.order_combo.clear()
            if not self.filtered_orders:
                self.order_combo.addItem("No orders with undelivered items")
                self.item_combo.clear()
                self.item_combo.addItem("No undelivered items")
                return
            for order in self.filtered_orders:
                self.order_combo.addItem(order.order_number, order.id)
            # Manually trigger order change
            self.on_order_changed(0)  # Select first order
        else:
            self.load_items()

    def on_order_changed(self, index):
        if self.filtered_mode:
            if index < 0 or not hasattr(self, 'filtered_orders') or not self.filtered_orders:
                self.item_combo.clear()
                self.item_combo.addItem("No undelivered items")
                return
            order_id = self.filtered_orders[index].id
            # Load undelivered order items for this order, but group by item to avoid duplicates
            self.filtered_order_items = self.session.query(OrderItem).filter(
                OrderItem.order_id == order_id,
                OrderItem.quantity > OrderItem.delivered_quantity
            ).all()
            
            # Group by item to show each item only once
            unique_items = {}
            for oi in self.filtered_order_items:
                item_key = oi.item.id
                if item_key not in unique_items:
                    unique_items[item_key] = {
                        'item': oi.item,
                        'order_items': []
                    }
                unique_items[item_key]['order_items'].append(oi)
            
            self.item_combo.clear()
            if not unique_items:
                self.item_combo.addItem("No undelivered items")
                return
            
            # Store the unique items for later use
            self.unique_items = unique_items
            
            for item_key, item_data in unique_items.items():
                item = item_data['item']
                name = item.customer_item_name or item.product.name or ""
                self.item_combo.addItem(f"{name} ({item.customer_code})", item_key)
            # Manually trigger item change
            self.on_item_changed(0)  # Select first item

    def on_item_changed(self, index):
        if self.filtered_mode:
            if index < 0 or not hasattr(self, 'unique_items') or not self.unique_items:
                self.qty_input.setValue(1)
                return
            
            # Get the selected item key
            item_key = self.item_combo.currentData()
            if item_key is None:
                self.qty_input.setValue(1)
                return
            
            # Calculate total remaining quantity for this item across all order items
            total_remaining = 0
            selected_order_item = None
            
            for oi in self.filtered_order_items:
                if oi.item.id == item_key:
                    remaining = oi.quantity - oi.delivered_quantity
                    total_remaining += remaining
                    if selected_order_item is None:
                        selected_order_item = oi
            
            if selected_order_item:
                self.qty_input.setValue(total_remaining)
                self.qty_input.setMaximum(total_remaining)
                # Don't disable the quantity input - allow user to edit it
                # Set order number field
                self.order_input.setText(selected_order_item.order.order_number)
                self.order_input.setEnabled(False)

    def load_customers(self):
        self.customers = self.session.query(Customer).order_by(Customer.name_index).all()
        self.customer_combo.clear()
        for c in self.customers:
            self.customer_combo.addItem(f"{c.name_index} - {c.name}", c.id)

    def load_items(self):
        customer_idx = self.customer_combo.currentIndex()
        if customer_idx < 0:
            self.item_combo.clear()
            self.all_items = []
            return
        customer_id = self.customers[customer_idx].id
        items = self.session.query(Item).filter(Item.customer_id == customer_id).all()
        self.all_items = items  # Store all items for filtering
        self.item_search_input.clear()  # Clear search when customer changes
        self.filter_items()  # Apply current search filter

    def filter_items(self):
        if self.filtered_mode:
            # Filter the unique items in filtered mode
            search_text = self.item_search_input.text().strip().lower()
            self.item_combo.clear()
            
            if not hasattr(self, 'unique_items') or not self.unique_items:
                return
                
            for item_key, item_data in self.unique_items.items():
                item = item_data['item']
                item_code = (item.customer_code or "").lower()
                item_name = (item.customer_item_name or item.product.name or "").lower()
                
                if not search_text or search_text in item_code or search_text in item_name:
                    name = item.customer_item_name or item.product.name or ""
                    self.item_combo.addItem(f"{name} ({item.customer_code})", item_key)
        else:
            # Normal mode filtering
            search_text = self.item_search_input.text().strip().lower()
            self.item_combo.clear()
            if not hasattr(self, 'all_items'):
                return
            for item in self.all_items:
                item_code = (item.customer_code or "").lower()
                item_name = (item.customer_item_name or item.product.name or "").lower()
                if not search_text or search_text in item_code or search_text in item_name:
                    name = item.customer_item_name or item.product.name or ""
                    self.item_combo.addItem(f"{name} ({item.customer_code})", item.id)

    def refresh_items(self):
        """Refresh the items list for the current customer"""
        self.load_items()

    def refresh_all_items(self):
        """Refresh items for all customers - called when items are updated in Items tab"""
        # If we have a customer selected, refresh items for that customer
        if hasattr(self, 'all_items'):
            self.load_items()

    def add_label(self):
        if self.filtered_mode:
            customer_idx = self.customer_combo.currentIndex()
            order_idx = self.order_combo.currentIndex()
            item_idx = self.item_combo.currentIndex()
            if customer_idx < 0 or order_idx < 0 or item_idx < 0:
                QMessageBox.warning(self, "Input Error", "Please select customer, order, and item.")
                return
            customer = self.customers[customer_idx]
            
            # Get the selected item key
            item_key = self.item_combo.currentData()
            if item_key is None:
                QMessageBox.warning(self, "Input Error", "Please select a valid item.")
                return
            
            # Find the item data
            if not hasattr(self, 'unique_items') or item_key not in self.unique_items:
                QMessageBox.warning(self, "Input Error", "Selected item not found.")
                return
            
            item_data = self.unique_items[item_key]
            item = item_data['item']
            
            # Calculate total remaining quantity for this item
            total_remaining = 0
            selected_order_item = None
            for oi in self.filtered_order_items:
                if oi.item.id == item_key:
                    remaining = oi.quantity - oi.delivered_quantity
                    total_remaining += remaining
                    if selected_order_item is None:
                        selected_order_item = oi
            
            if selected_order_item:
                quantity = self.qty_input.value()  # Use the user-entered quantity
                order_number = selected_order_item.order.order_number
                label_data = {
                    "customer": f"{customer.name_index} - {customer.name}",
                    "order_number": order_number,
                    "item_code": item.customer_code,
                    "item_name": item.customer_item_name or item.product.name or "",
                    "quantity": quantity,
                    "customer_obj": customer,
                    "item_obj": item,
                    "delivery_date": selected_order_item.delivery_date
                }
                self.labels.append(label_data)
                self.update_labels_table()
        else:
            # Existing logic for normal mode
            order_number = self.order_input.text().strip()
            if not order_number:
                QMessageBox.warning(self, "Input Error", "Order number is required.")
                return
            customer_idx = self.customer_combo.currentIndex()
            if customer_idx < 0:
                QMessageBox.warning(self, "Input Error", "Customer is required.")
                return
            item_idx = self.item_combo.currentIndex()
            if item_idx < 0:
                QMessageBox.warning(self, "Input Error", "Item is required.")
                return
            quantity = self.qty_input.value()
            if quantity <= 0:
                QMessageBox.warning(self, "Input Error", "Quantity must be greater than 0.")
                return
            customer = self.customers[customer_idx]
            item_id = self.item_combo.currentData()
            item = next((item for item in self.all_items if item.id == item_id), None)
            if not item:
                QMessageBox.warning(self, "Input Error", "Selected item not found.")
                return
            # Try to find the actual order item to get the delivery date
            order_item = self.session.query(OrderItem).join(Order).join(Item).filter(
                Order.order_number == order_number,
                Item.customer_code == item.customer_code
            ).first()
            
            delivery_date = order_item.delivery_date if order_item else None
            
            label_data = {
                "customer": f"{customer.name_index} - {customer.name}",
                "order_number": order_number,
                "item_code": item.customer_code,
                "item_name": item.customer_item_name or item.product.name or "",
                "quantity": quantity,
                "customer_obj": customer,
                "item_obj": item,
                "delivery_date": delivery_date
            }
            self.labels.append(label_data)
            self.update_labels_table()

    def clear_labels(self):
        self.labels = []
        self.update_labels_table()

    def delete_selected_label(self):
        selected_items = self.labels_table.selectedIndexes()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "No label selected to delete.")
            return
        
        # Get unique row indices (in case multiple cells in same row are selected)
        rows_to_delete = set()
        for index in selected_items:
            rows_to_delete.add(index.row())
        
        # Sort rows in descending order to delete from bottom to top
        # This prevents index shifting issues
        rows_to_delete = sorted(rows_to_delete, reverse=True)
        
        # Show confirmation dialog
        if len(rows_to_delete) == 1:
            message = "Are you sure you want to delete the selected label?"
        else:
            message = f"Are you sure you want to delete {len(rows_to_delete)} selected labels?"
        
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            # Delete the selected rows
            for row in rows_to_delete:
                if 0 <= row < len(self.labels):
                    self.labels.pop(row)
            
        self.update_labels_table()

    def update_labels_table(self):
        self.labels_table.setRowCount(len(self.labels))
        for i, label in enumerate(self.labels):
            self.labels_table.setItem(i, 0, QTableWidgetItem(label["customer"]))
            self.labels_table.setItem(i, 1, QTableWidgetItem(label["order_number"]))
            self.labels_table.setItem(i, 2, QTableWidgetItem(label["item_code"]))
            self.labels_table.setItem(i, 3, QTableWidgetItem(label["item_name"]))
            self.labels_table.setItem(i, 4, QTableWidgetItem(str(label["quantity"])))

    def generate_labels(self):
        self._generate_labels_dialog(save=False)

    def generate_labels_and_save(self):
        self._generate_labels_dialog(save=True)

    def _generate_labels_dialog(self, save=False):
        if not self.labels:
            QMessageBox.warning(self, "No Labels", "No labels to generate. Please add at least one label.")
            return
        # Build fake order_item-like objects for all labels
        fake_order_items = []
        for label in self.labels:
            class FakeOrder:
                pass
            class FakeOrderItem:
                pass
            fake_order = FakeOrder()
            fake_order.order_number = label["order_number"]
            fake_order.customer = label["customer_obj"]
            fake_order_item = FakeOrderItem()
            fake_order_item.order = fake_order
            fake_order_item.item = label["item_obj"]
            fake_order_item.quantity = label["quantity"]
            fake_order_item.delivery_date = label.get("delivery_date")
            fake_order_items.append(fake_order_item)
        dialog = LabelPrintDialog(self, fake_order_items, self.session)
        
        # Show the dialog - the dialog handles generation internally
        dialog.exec()

    def print_labels(self):
        if not self.labels:
            QMessageBox.warning(self, "Warning", "No labels to print.")
            return

        doc = SimpleDocTemplate("labels.pdf", pagesize=A4)
        elements = []

        for label in self.labels:
            data = [
                ["Customer:", label["customer"]],
                ["Order Number:", label["order_number"]],
                ["Item Code:", label["item_code"]],
                ["Item Name:", label["item_name"]],
                ["Quantity:", str(label["quantity"])]
            ]
            table = Table(data, colWidths=[100, 200])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.grey),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (1, 0), (1, -1), colors.beige),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (1, 0), (1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            elements.append(Paragraph("<br/><br/>", getSampleStyleSheet()["Normal"]))

        doc.build(elements)
        QMessageBox.information(self, "Success", "Labels generated as 'labels.pdf'.") 

    def export_to_excel(self):
        if not self.labels:
            QMessageBox.warning(self, "Warning", "No labels to export.")
            return

        # Create a DataFrame from the labels
        data = [
            [label["customer"], label["order_number"], label["item_code"], label["item_name"], label["quantity"]]
            for label in self.labels
        ]
        df = pd.DataFrame(data, columns=["Customer", "Order Number", "Item Code", "Item Name", "Quantity"])

        # Save the DataFrame to an Excel file
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Labels to Excel", "", "Excel Files (*.xlsx)")
        if file_path:
            df.to_excel(file_path, index=False)
            QMessageBox.information(self, "Success", f"Labels exported to {file_path}")
        else:
            QMessageBox.warning(self, "Warning", "Export cancelled.") 

 