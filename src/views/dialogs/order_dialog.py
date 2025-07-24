from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QDateEdit, QLabel
)
from PyQt6.QtCore import Qt, QDate
from sqlalchemy.orm import Session
from datetime import datetime, date
from models.database import Order, OrderItem, Customer, Item, Delivery, Product
from utils.price_parser import parse_price
from utils.permissions import get_permissions_manager

def parse_price(price_str: str) -> float:
    """Convert price string to float, handling both comma and dot separators."""
    if not price_str:
        return 0.0
    # Replace comma with dot and try to convert to float
    try:
        return float(price_str.replace(',', '.'))
    except ValueError:
        raise ValueError("Invalid price format. Please use numbers only with dot or comma as decimal separator.")

class OrderDialog(QDialog):
    def __init__(self, session: Session, parent=None, order=None, user=None):
        super().__init__(parent)
        self.session = session
        self.order = order
        self.user = user
        self.permissions_manager = get_permissions_manager()
        self.setWindowTitle("New Order" if order is None else "Edit Order")
        self.setModal(True)
        self.setMinimumWidth(800)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Order header form
        form_layout = QFormLayout()
        
        self.order_number_input = QLineEdit()
        if not self.order:  # For new orders, suggest next order number
            last_order = self.session.query(Order).order_by(Order.order_number.desc()).first()
            if last_order:
                try:
                    last_num = int(last_order.order_number)
                    self.order_number_input.setText(str(last_num + 1))
                except ValueError:
                    pass
        
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(200)  # Make dropdown wider
        customers = self.session.query(Customer).order_by(Customer.name_index).all()
        self.customer_combo.addItems([f"{c.name_index} - {c.name}" for c in customers])
        self.customer_ids = [c.id for c in customers]
        
        self.order_date_input = QDateEdit()
        self.order_date_input.setCalendarPopup(True)
        self.order_date_input.setDate(QDate.currentDate())
        
        form_layout.addRow("Order Number*:", self.order_number_input)
        form_layout.addRow("Customer*:", self.customer_combo)
        form_layout.addRow("Order Date*:", self.order_date_input)
        
        layout.addLayout(form_layout)
        
        # Items table
        self.items_table = QTableWidget()
        
        # Check if user can see prices
        self.can_see_prices = True
        if self.user:
            self.can_see_prices = self.permissions_manager.can_access_column(self.user, "orders", "prices")
        
        # Set up columns based on permissions
        if self.can_see_prices:
            self.items_table.setColumnCount(7)
            self.items_table.setHorizontalHeaderLabels([
                "Item", "Customer Code", "Quantity", "Price",
                "Delivery Date", "Delivered", "Last Delivery"
            ])
        else:
            self.items_table.setColumnCount(6)
            self.items_table.setHorizontalHeaderLabels([
                "Item", "Customer Code", "Quantity",
                "Delivery Date", "Delivered", "Last Delivery"
            ])
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Add item button
        item_toolbar = QHBoxLayout()
        add_item_button = QPushButton("Add Item")
        add_item_button.clicked.connect(self.add_item)
        remove_item_button = QPushButton("Remove Item")
        remove_item_button.clicked.connect(self.remove_item)
        
        item_toolbar.addWidget(add_item_button)
        item_toolbar.addWidget(remove_item_button)
        item_toolbar.addStretch()
        
        layout.addLayout(item_toolbar)
        layout.addWidget(self.items_table)
        
        # Buttons
        button_box = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_box.addWidget(save_button)
        button_box.addWidget(cancel_button)
        layout.addLayout(button_box)
        
        self.setLayout(layout)
        
        # If editing, populate fields
        if self.order:
            self.order_number_input.setText(self.order.order_number)
            customer_idx = self.customer_ids.index(self.order.customer_id)
            self.customer_combo.setCurrentIndex(customer_idx)
            self.order_date_input.setDate(self.order.order_date)
            
            self.populate_items_table()
    
    def add_item(self):
        dialog = OrderItemDialog(self.session, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)
            
            item_data = dialog.get_data()
            if not item_data:
                return  # Prevent crash if dialog returns None
            item = self.session.query(Item).get(item_data["item_id"])
            
            col_index = 0
            self.items_table.setItem(row, col_index, QTableWidgetItem(item.product.name))
            col_index += 1
            self.items_table.setItem(row, col_index, QTableWidgetItem(item.customer_code))
            col_index += 1
            self.items_table.setItem(row, col_index, QTableWidgetItem(str(item_data["quantity"])))
            col_index += 1
            
            if self.can_see_prices:
                self.items_table.setItem(row, col_index, QTableWidgetItem(str(item_data["price"])))
                col_index += 1
            
            self.items_table.setItem(row, col_index, QTableWidgetItem(item_data["delivery_date"].strftime("%Y-%m-%d")))
            col_index += 1
            self.items_table.setItem(row, col_index, QTableWidgetItem("0"))  # Delivered quantity
            col_index += 1
            self.items_table.setItem(row, col_index, QTableWidgetItem(""))   # Last delivery
            
            # Store item_id in the first column's data
            self.items_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, item_data["item_id"])
    
    def remove_item(self):
        selected_rows = self.items_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select an item to remove")
            return
            
        row = selected_rows[0].row()
        self.items_table.removeRow(row)
    
    def populate_items_table(self):
        for item in self.order.items:
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)
            
            col_index = 0
            self.items_table.setItem(row, col_index, QTableWidgetItem(item.item.product.name))
            col_index += 1
            self.items_table.setItem(row, col_index, QTableWidgetItem(item.item.customer_code))
            col_index += 1
            self.items_table.setItem(row, col_index, QTableWidgetItem(str(item.quantity)))
            col_index += 1
            
            if self.can_see_prices:
                self.items_table.setItem(row, col_index, QTableWidgetItem(str(item.price or "")))
                col_index += 1
            
            self.items_table.setItem(row, col_index, QTableWidgetItem(item.delivery_date.strftime("%Y-%m-%d")))
            col_index += 1
            self.items_table.setItem(row, col_index, QTableWidgetItem(str(item.delivered_quantity)))
            col_index += 1
            self.items_table.setItem(row, col_index, QTableWidgetItem(
                item.last_delivery_date.strftime("%Y-%m-%d") if item.last_delivery_date else ""
            ))
            
            # Store item_id in the first column's data
            self.items_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, item.item_id)
    
    def get_data(self):
        items_data = []
        for row in range(self.items_table.rowCount()):
            item_id = self.items_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            quantity = int(self.items_table.item(row, 2).text())
            
            # Handle price based on permissions
            if self.can_see_prices:
                try:
                    price = parse_price(self.items_table.item(row, 3).text())
                except ValueError as e:
                    QMessageBox.warning(self, "Validation Error", str(e))
                    return None
                delivery_date_col = 4
            else:
                price = 0.0  # Default price for users who can't see prices
                delivery_date_col = 3
            
            delivery_date = datetime.strptime(self.items_table.item(row, delivery_date_col).text(), "%Y-%m-%d").date()
            
            items_data.append({
                "item_id": item_id,
                "quantity": quantity,
                "price": price,
                "delivery_date": delivery_date
            })
        
        return {
            "order_number": self.order_number_input.text(),
            "customer_id": self.customer_ids[self.customer_combo.currentIndex()],
            "order_date": self.order_date_input.date().toPyDate(),
            "items": items_data
        }

class CreateProductDialog(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Create New Product")
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()
        self.name_input = QLineEdit()
        layout.addRow("Product Name*:", self.name_input)
        # Add more fields as needed (e.g., weight, code, etc.)
        button_box = QHBoxLayout()
        save_button = QPushButton("Create")
        save_button.clicked.connect(self.create_product)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addWidget(save_button)
        button_box.addWidget(cancel_button)
        layout.addRow(button_box)
        self.setLayout(layout)

    def create_product(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Product name is required")
            return
        try:
            product = Product(name=name)
            self.session.add(product)
            self.session.commit()
            self.created_product = product
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error creating product: {str(e)}")

class CreateItemDialog(QDialog):
    def __init__(self, session: Session, customer_id: int, parent=None):
        super().__init__(parent)
        self.session = session
        self.customer_id = customer_id
        self.setWindowTitle("Create New Item")
        self.setModal(True)
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        customer = self.session.query(Customer).get(self.customer_id)
        # Product selection
        product_row = QHBoxLayout()
        self.product_combo = QComboBox()
        self.product_combo.setMinimumWidth(200)  # Make dropdown wider
        self.refresh_products()
        product_row.addWidget(self.product_combo)
        add_product_btn = QPushButton("Add Product")
        add_product_btn.clicked.connect(self.add_product)
        product_row.addWidget(add_product_btn)
        # Item fields
        self.customer_code_input = QLineEdit()
        self.customer_item_name_input = QLineEdit()
        layout.addRow("Customer:", QLabel(f"{customer.name_index} - {customer.name}"))
        layout.addRow("Product*:", product_row)
        layout.addRow("Customer Code*:", self.customer_code_input)
        layout.addRow("Customer Item Name:", self.customer_item_name_input)
        # Buttons
        button_box = QHBoxLayout()
        save_button = QPushButton("Create")
        save_button.clicked.connect(self.create_item)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addWidget(save_button)
        button_box.addWidget(cancel_button)
        layout.addRow(button_box)
        self.setLayout(layout)
    
    def refresh_products(self):
        products = self.session.query(Product).order_by(Product.name).all()
        self.products = products
        self.product_combo.clear()
        self.product_ids = []
        for p in products:
            self.product_combo.addItem(p.name)
            self.product_ids.append(p.id)
    
    def add_product(self):
        dialog = CreateProductDialog(self.session, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Refresh product list and select the new product
            self.refresh_products()
            new_product_id = dialog.created_product.id
            if new_product_id in self.product_ids:
                idx = self.product_ids.index(new_product_id)
                self.product_combo.setCurrentIndex(idx)
    
    def create_item(self):
        # Validate required fields
        if not self.customer_code_input.text():
            QMessageBox.warning(self, "Validation Error", "Customer code is required")
            return
        
        try:
            # Create new item
            item = Item(
                customer_id=self.customer_id,
                product_id=self.product_ids[self.product_combo.currentIndex()],
                customer_code=self.customer_code_input.text(),
                customer_item_name=self.customer_item_name_input.text() or None
            )
            
            self.session.add(item)
            self.session.commit()
            
            # Return the new item
            self.created_item = item
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error creating item: {str(e)}")

class OrderItemDialog(QDialog):
    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Add Order Item")
        self.setModal(True)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Get customer_id from parent OrderDialog
        parent = self.parent()
        customer_id = parent.customer_ids[parent.customer_combo.currentIndex()]
        
        # Create search and sort controls
        controls_layout = QHBoxLayout()
        
        # Search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search items...")
        self.search_input.textChanged.connect(self.filter_items)
        controls_layout.addWidget(QLabel("Search:"))
        controls_layout.addWidget(self.search_input)
        
        # Sort options
        self.sort_combo = QComboBox()
        self.sort_combo.setMinimumWidth(150)  # Make dropdown wider
        self.sort_combo.addItems(["Sort by Code", "Sort by Name"])
        self.sort_combo.currentIndexChanged.connect(self.sort_items)
        controls_layout.addWidget(QLabel("Sort:"))
        controls_layout.addWidget(self.sort_combo)
        
        # Create new item button
        create_item_button = QPushButton("Create New Item")
        create_item_button.clicked.connect(lambda: self.create_new_item(customer_id))
        controls_layout.addWidget(create_item_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Only show items for selected customer
        self.item_combo = QComboBox()
        self.item_combo.setMinimumWidth(300)  # Make dropdown wider for item names
        self.items = self.session.query(Item).filter(Item.customer_id == customer_id).all()
        self.update_item_combo()
        
        self.quantity_input = QLineEdit()
        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("Use . or , as decimal separator")
        
        self.delivery_date_input = QDateEdit()
        self.delivery_date_input.setCalendarPopup(True)
        self.delivery_date_input.setDate(QDate.currentDate())
        
        form_layout = QFormLayout()
        form_layout.addRow("Item*:", self.item_combo)
        form_layout.addRow("Quantity*:", self.quantity_input)
        form_layout.addRow("Price:", self.price_input)
        form_layout.addRow("Delivery Date*:", self.delivery_date_input)
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QHBoxLayout()
        save_button = QPushButton("Add")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_box.addWidget(save_button)
        button_box.addWidget(cancel_button)
        layout.addLayout(button_box)
        
        self.setLayout(layout)
    
    def create_new_item(self, customer_id):
        """Open dialog to create a new item"""
        dialog = CreateItemDialog(self.session, customer_id, self)
        # Pre-fill the customer code with the search text
        dialog.customer_code_input.setText(self.search_input.text())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Refresh items list and select the new item
            self.items = self.session.query(Item).filter(Item.customer_id == customer_id).all()
            self.update_item_combo()
            
            # Find and select the new item
            new_item_index = self.item_ids.index(dialog.created_item.id)
            self.item_combo.setCurrentIndex(new_item_index)
    
    def update_item_combo(self):
        """Update the item combo box with filtered and sorted items"""
        self.item_combo.clear()
        self.item_ids = []
        
        # Filter items based on search text
        search_text = self.search_input.text().lower()
        filtered_items = [
            item for item in self.items
            if search_text in item.customer_code.lower() or
               search_text in (item.customer_item_name or "").lower() or
               search_text in item.product.name.lower()
        ]
        
        # Sort items
        sort_by_code = self.sort_combo.currentIndex() == 0
        sorted_items = sorted(
            filtered_items,
            key=lambda x: x.customer_code if sort_by_code else (x.customer_item_name or x.product.name)
        )
        
        # Add items to combo box
        for item in sorted_items:
            self.item_combo.addItem(
                f"{item.customer_code} - {item.customer_item_name or item.product.name} ({item.product.name})"
            )
            self.item_ids.append(item.id)
    
    def filter_items(self):
        """Filter items based on search text"""
        self.update_item_combo()
    
    def sort_items(self):
        """Sort items based on selected sort option"""
        self.update_item_combo()
    
    def get_data(self):
        try:
            return {
                "item_id": self.item_ids[self.item_combo.currentIndex()],
                "quantity": int(self.quantity_input.text()),
                "price": parse_price(self.price_input.text()),
                "delivery_date": self.delivery_date_input.date().toPyDate()
            }
        except ValueError as e:
            QMessageBox.warning(self, "Validation Error", str(e))
            return None 