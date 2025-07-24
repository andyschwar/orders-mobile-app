from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox,
    QDialog, QFormLayout, QDateEdit, QComboBox
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, date
from models.database import Order, Customer, Item, OrderItem, Delivery
from ..dialogs.order_dialog import OrderDialog
from ..dialogs.delivery_dialog import DeliveryDialog
from utils.permissions import get_permissions_manager

class OrdersTab(QWidget):
    order_updated = pyqtSignal()
    order_created = pyqtSignal()
    order_deleted = pyqtSignal()
    
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
        if not self.user or self.permissions_manager.has_permission(self.user, "orders", "create"):
            add_button = QPushButton("Add Order")
            add_button.clicked.connect(self.add_order)
            toolbar.addWidget(add_button)
        
        if not self.user or self.permissions_manager.has_permission(self.user, "orders", "edit"):
            edit_button = QPushButton("Edit Order")
            edit_button.clicked.connect(self.edit_order)
            toolbar.addWidget(edit_button)
        
        if not self.user or self.permissions_manager.has_permission(self.user, "orders", "delete"):
            delete_button = QPushButton("Delete Order")
            delete_button.clicked.connect(self.delete_order)
            toolbar.addWidget(delete_button)
        
        if not self.user or self.permissions_manager.has_permission(self.user, "orders", "create"):
            add_delivery_button = QPushButton("Add Delivery")
            add_delivery_button.clicked.connect(self.add_delivery)
            toolbar.addWidget(add_delivery_button)
            
            track_deliveries_button = QPushButton("Track Deliveries")
            track_deliveries_button.clicked.connect(self.track_deliveries)
            toolbar.addWidget(track_deliveries_button)
            
            manage_deliveries_button = QPushButton("Manage Deliveries")
            manage_deliveries_button.clicked.connect(self.manage_deliveries)
            toolbar.addWidget(manage_deliveries_button)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_button)
        
        # Add search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search orders...")
        self.search_input.textChanged.connect(self.search_orders)
        toolbar.addWidget(self.search_input)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Order Number", "Customer", "Order Date",
            "Total Items", "Total Value", "Status",
            "To Deliver", "Complete"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
        
        # Load initial data
        self.refresh_data()
        
    def calculate_completion(self, order):
        total_quantity = sum(item.quantity for item in order.items)
        delivered_quantity = sum(item.delivered_quantity for item in order.items)
        return f"{delivered_quantity}/{total_quantity}" if total_quantity > 0 else "0/0"
    
    def populate_table(self, orders):
        self.table.setRowCount(len(orders))
        
        # Check if user can see prices
        can_see_prices = True
        if self.user:
            can_see_prices = self.permissions_manager.can_access_column(self.user, "orders", "prices")
        
        for i, order in enumerate(orders):
            # Calculate totals
            total_items = sum(item.quantity for item in order.items)
            total_value = sum(item.quantity * (item.price or 0) for item in order.items)
            delivered_items = sum(item.delivered_quantity for item in order.items)
            
            # Calculate status
            if delivered_items == 0:
                status = "New"
            elif delivered_items < total_items:
                status = "Partial"
            else:
                status = "Completed"
            
            # Calculate remaining items to deliver
            items_to_deliver = total_items - delivered_items
            is_complete = items_to_deliver == 0
            
            self.table.setItem(i, 0, QTableWidgetItem(str(order.id)))
            self.table.setItem(i, 1, QTableWidgetItem(order.order_number))
            self.table.setItem(i, 2, QTableWidgetItem(f"{order.customer.name_index} - {order.customer.name}"))
            self.table.setItem(i, 3, QTableWidgetItem(order.order_date.strftime("%Y-%m-%d")))
            self.table.setItem(i, 4, QTableWidgetItem(str(total_items)))
            
            # Only show total value if user has permission
            if can_see_prices:
                self.table.setItem(i, 5, QTableWidgetItem(f"{total_value:.2f}"))
            else:
                self.table.setItem(i, 5, QTableWidgetItem("***"))
            
            self.table.setItem(i, 6, QTableWidgetItem(status))
            self.table.setItem(i, 7, QTableWidgetItem(str(items_to_deliver)))
            self.table.setItem(i, 8, QTableWidgetItem("Yes" if is_complete else "No"))
        
        self.table.resizeColumnsToContents()
    
    def refresh_data(self):
        orders = self.session.query(Order).join(Customer).order_by(Order.order_date.desc()).all()
        self.populate_table(orders)
        
    def search_orders(self, text):
        if not text:
            self.refresh_data()
            return
            
        search = f"%{text}%"
        orders = self.session.query(Order).join(Customer).filter(
            or_(
                Order.order_number.ilike(search),
                Customer.name_index.ilike(search),
                Customer.name.ilike(search)
            )
        ).order_by(Order.order_date.desc()).all()
        
        self.populate_table(orders)
        
    def add_order(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "orders", "create"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to add orders.")
            return
            
        dialog = OrderDialog(self.session, self, user=self.user)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            # Validate required fields
            if not data["order_number"] or not data["items"]:
                QMessageBox.warning(self, "Validation Error", "Order number and at least one item are required")
                return
            
            # Check for duplicate order number
            existing = self.session.query(Order).filter(Order.order_number == data["order_number"]).first()
            if existing:
                QMessageBox.warning(self, "Validation Error", "Order number already exists")
                return
            
            # Create order
            order = Order(
                order_number=data["order_number"],
                customer_id=data["customer_id"],
                order_date=data["order_date"]
            )
            order.updated_at = datetime.now()  # Explicitly set the timestamp
            
            # Add items
            for item_data in data["items"]:
                order_item = OrderItem(
                    item_id=item_data["item_id"],
                    quantity=item_data["quantity"],
                    price=item_data["price"],
                    delivery_date=item_data["delivery_date"]
                )
                order.items.append(order_item)
            
            try:
                self.session.add(order)
                self.session.commit()
                self.refresh_data()
                self.order_updated.emit()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error adding order: {str(e)}")
    
    def edit_order(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "orders", "edit"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit orders.")
            return
            
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select an order to edit")
            return
            
        order_id = int(self.table.item(selected_rows[0].row(), 0).text())
        order = self.session.query(Order).get(order_id)
        
        dialog = OrderDialog(self.session, self, order, user=self.user)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            # Validate required fields
            if not data["order_number"] or not data["items"]:
                QMessageBox.warning(self, "Validation Error", "Order number and at least one item are required")
                return
            
            # Check for duplicate order number
            existing = self.session.query(Order).filter(
                Order.order_number == data["order_number"],
                Order.id != order.id
            ).first()
            if existing:
                QMessageBox.warning(self, "Validation Error", "Order number already exists")
                return
            
            # Update order
            order.order_number = data["order_number"]
            order.customer_id = data["customer_id"]
            order.order_date = data["order_date"]
            order.updated_at = datetime.now()  # Explicitly update the timestamp
            
            # Create a mapping of existing items by item_id to preserve deliveries
            existing_items = {}
            for item in order.items:
                existing_items[item.item_id] = item
            
            # Process new items
            new_items = []
            for item_data in data["items"]:
                item_id = item_data["item_id"]
                
                if item_id in existing_items:
                    # Update existing item (preserves deliveries)
                    existing_item = existing_items[item_id]
                    existing_item.quantity = item_data["quantity"]
                    existing_item.price = item_data["price"]
                    existing_item.delivery_date = item_data["delivery_date"]
                    new_items.append(existing_item)
                    # Remove from existing_items so we know it's been processed
                    del existing_items[item_id]
                else:
                    # Create new item
                    order_item = OrderItem(
                        item_id=item_data["item_id"],
                        quantity=item_data["quantity"],
                        price=item_data["price"],
                        delivery_date=item_data["delivery_date"]
                    )
                    new_items.append(order_item)
            
            # Remove items that are no longer in the order
            for item in existing_items.values():
                self.session.delete(item)
            
            # Replace order items with new list
            order.items = new_items
            
            # Explicitly update the timestamp to ensure it's recorded
            order.updated_at = datetime.now()
            
            try:
                self.session.commit()
                self.refresh_data()
                self.order_updated.emit()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error updating order: {str(e)}")
    
    def delete_order(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "orders", "delete"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete orders.")
            return
            
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select an order to delete")
            return
            
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this order and all its items?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            order_id = int(self.table.item(selected_rows[0].row(), 0).text())
            order = self.session.query(Order).get(order_id)
            
            try:
                self.session.delete(order)
                self.session.commit()
                self.refresh_data()
                self.order_updated.emit()
                self.order_deleted.emit()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error deleting order: {str(e)}")
    
    def add_delivery(self):
        """Add a simple delivery to an order"""
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "orders", "create"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to add deliveries.")
            return
            
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select an order to add delivery")
            return
            
        order_id = int(self.table.item(selected_rows[0].row(), 0).text())
        order = self.session.query(Order).get(order_id)
        
        # Check if there are any items that haven't been fully delivered
        undelivered_items = [
            item for item in order.items 
            if item.delivered_quantity < item.quantity
        ]
        
        if not undelivered_items:
            QMessageBox.information(
                self,
                "No Items",
                "All items in this order have been fully delivered."
            )
            return
        
        # Show item selection dialog
        from PyQt6.QtWidgets import QInputDialog
        
        item_names = []
        for item in undelivered_items:
            remaining = item.quantity - item.delivered_quantity
            planned_date = item.delivery_date.strftime('%Y-%m-%d')
            item_names.append(f"{item.item.customer_item_name} - Remaining: {remaining} - Planned: {planned_date}")
        
        item_name, ok = QInputDialog.getItem(
            self, "Select Item", "Choose item to deliver:", item_names, 0, False
        )
        
        if not ok:
            return
            
        selected_item = undelivered_items[item_names.index(item_name)]
        
        # Get delivery quantity
        max_qty = selected_item.quantity - selected_item.delivered_quantity
        quantity, ok = QInputDialog.getInt(
            self, "Delivery Quantity", 
            f"Enter quantity to deliver (max: {max_qty}):", 
            min(10, max_qty), 1, max_qty, 1
        )
        
        if not ok:
            return
            
        # Create delivery record
        delivery = Delivery(
            order_item_id=selected_item.id,
            quantity=quantity,
            delivery_date=date.today()
        )
        
        # Update order item
        selected_item.delivered_quantity += quantity
        selected_item.last_delivery_date = date.today()
        
        try:
            self.session.add(delivery)
            self.session.commit()
            self.refresh_data()
            QMessageBox.information(self, "Success", f"Added delivery of {quantity} items")
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error adding delivery: {str(e)}")
    
    def track_deliveries(self):
        """Open detailed delivery tracking for an order item"""
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "orders", "create"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to track deliveries.")
            return
            
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select an order to track deliveries")
            return
            
        order_id = int(self.table.item(selected_rows[0].row(), 0).text())
        order = self.session.query(Order).get(order_id)
        
        # Show item selection dialog
        from PyQt6.QtWidgets import QInputDialog
        
        item_names = []
        for item in order.items:
            remaining = item.quantity - item.delivered_quantity
            planned_date = item.delivery_date.strftime('%Y-%m-%d')
            status = "Completed" if remaining == 0 else f"Remaining: {remaining}"
            item_names.append(f"{item.item.customer_item_name} - {status} - Planned: {planned_date}")
        
        item_name, ok = QInputDialog.getItem(
            self, "Select Item", "Choose item to track deliveries:", item_names, 0, False
        )
        
        if not ok:
            return
            
        selected_item = order.items[item_names.index(item_name)]
        
        # Open delivery tracking dialog
        dialog = DeliveryDialog(self.session, selected_item, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_delivery_data()
            if data:
                # Create delivery record
                delivery = Delivery(
                    order_item_id=data['order_item_id'],
                    quantity=data['quantity'],
                    delivery_date=data['delivery_date']
                )
                
                # Update order item
                selected_item.delivered_quantity += data['quantity']
                selected_item.last_delivery_date = data['delivery_date']
                
                try:
                    self.session.add(delivery)
                    self.session.commit()
                    self.refresh_data()
                    QMessageBox.information(self, "Success", f"Added delivery of {data['quantity']} items")
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error adding delivery: {str(e)}")
        
        # Refresh the table after dialog closes
        self.refresh_data()
    
    def manage_deliveries(self):
        """Open delivery management dialog for an order"""
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "orders", "edit"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to manage deliveries.")
            return
            
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select an order to manage deliveries")
            return
            
        order_id = int(self.table.item(selected_rows[0].row(), 0).text())
        order = self.session.query(Order).get(order_id)
        
        # Show delivery management dialog
        from views.dialogs.delivery_management_dialog import DeliveryManagementDialog
        dialog = DeliveryManagementDialog(self.session, order, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data() 