from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QDoubleSpinBox, QComboBox,
    QTextEdit, QLabel, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from sqlalchemy.orm import Session
from datetime import datetime
from models.database import Component, ComponentStock

class StockTransactionDialog(QDialog):
    """Dialog for adding/removing stock with transaction history"""
    def __init__(self, session: Session, component_stock=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.component_stock = component_stock
        self.setWindowTitle("Stock Transaction")
        self.setModal(True)
        self.resize(500, 400)
        self.init_ui()
        
    def closeEvent(self, event):
        """Handle close event to prevent application crash"""
        try:
            event.accept()
        except Exception as e:
            print(f"Error in closeEvent: {e}")
            event.accept()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Transaction type
        form_layout = QFormLayout()
        
        self.transaction_type = QComboBox()
        self.transaction_type.addItems(["Add to Stock", "Remove from Stock"])
        self.transaction_type.currentTextChanged.connect(self.on_transaction_type_changed)
        form_layout.addRow("Transaction Type:", self.transaction_type)
        
        # Quantity
        self.quantity = QDoubleSpinBox()
        self.quantity.setDecimals(2)
        self.quantity.setMaximum(999999.99)
        self.quantity.setMinimum(0.01)
        self.quantity.setValue(1.0)
        form_layout.addRow("Quantity:", self.quantity)
        
        # Reason
        self.reason = QComboBox()
        self.reason.setEditable(True)
        self.reason.addItems([
            "Received from vendor",
            "Production usage",
            "Quality control",
            "Inventory adjustment",
            "Return from production",
            "Other"
        ])
        form_layout.addRow("Reason:", self.reason)
        
        # Notes
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(100)
        form_layout.addRow("Notes:", self.notes)
        
        layout.addLayout(form_layout)
        
        # Current stock display
        if self.component_stock:
            current_stock_group = QGroupBox("Current Stock")
            current_layout = QVBoxLayout()
            
            # Add null check for unit_of_measure
            unit = getattr(self.component_stock, 'unit_of_measure', 'pcs') or 'pcs'
            current_stock = getattr(self.component_stock, 'current_stock', 0.0) or 0.0
            
            self.current_stock_label = QLabel(f"Current Stock: {current_stock} {unit}")
            self.current_stock_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            current_layout.addWidget(self.current_stock_label)
            
            # Preview of new stock level
            self.preview_label = QLabel()
            self.preview_label.setStyleSheet("color: blue; font-weight: bold;")
            current_layout.addWidget(self.preview_label)
            
            current_stock_group.setLayout(current_layout)
            layout.addWidget(current_stock_group)
            
            # Update preview when quantity changes
            self.quantity.valueChanged.connect(self.update_preview)
            self.transaction_type.currentTextChanged.connect(self.update_preview)
            self.update_preview()
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save Transaction")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def on_transaction_type_changed(self, text):
        """Handle transaction type change"""
        if text == "Remove from Stock" and self.component_stock:
            current_stock = getattr(self.component_stock, 'current_stock', 0.0) or 0.0
            self.quantity.setMaximum(current_stock)
        else:
            self.quantity.setMaximum(999999.99)
        self.update_preview()
    
    def update_preview(self):
        """Update the preview of new stock level"""
        if not self.component_stock:
            return
            
        current = getattr(self.component_stock, 'current_stock', 0.0) or 0.0
        quantity = self.quantity.value()
        transaction_type = self.transaction_type.currentText()
        unit = getattr(self.component_stock, 'unit_of_measure', 'pcs') or 'pcs'
        
        if transaction_type == "Add to Stock":
            new_stock = current + quantity
            self.preview_label.setText(f"New Stock Level: {new_stock:.2f} {unit}")
            self.preview_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            new_stock = current - quantity
            self.preview_label.setText(f"New Stock Level: {new_stock:.2f} {unit}")
            self.preview_label.setStyleSheet("color: orange; font-weight: bold;")
    
    def get_data(self):
        """Get the transaction data"""
        return {
            'transaction_type': self.transaction_type.currentText(),
            'quantity': self.quantity.value(),
            'reason': self.reason.currentText(),
            'notes': self.notes.toPlainText().strip() or None
        }

class StockDialog(QDialog):
    def __init__(self, session: Session, component_stock=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.component_stock = component_stock
        self.setWindowTitle("Add Stock" if not component_stock else "Edit Stock")
        self.setModal(True)
        self.resize(500, 400)
        self.init_ui()
        
    def closeEvent(self, event):
        """Handle close event to prevent application crash"""
        try:
            event.accept()
        except Exception as e:
            print(f"Error in closeEvent: {e}")
            event.accept()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Component selection (only for new stock entries)
        if not self.component_stock:
            form_layout = QFormLayout()
            
            # Category filter for component selection
            self.category_filter = QComboBox()
            self.category_filter.addItem("All Categories", None)
            self.load_categories()
            self.category_filter.currentTextChanged.connect(self.load_components)
            form_layout.addRow("Filter by Category:", self.category_filter)
            
            # Component selection
            self.component_combo = QComboBox()
            self.component_combo.setMinimumWidth(300)
            self.load_components()
            form_layout.addRow("Component:", self.component_combo)
            
            layout.addLayout(form_layout)
        
        # Stock information form
        form_layout = QFormLayout()
        
        # Current stock
        self.current_stock = QDoubleSpinBox()
        self.current_stock.setDecimals(2)
        self.current_stock.setMaximum(999999.99)
        self.current_stock.setMinimum(0.0)
        form_layout.addRow("Current Stock:", self.current_stock)
        
        # Minimum stock (reorder point)
        self.minimum_stock = QDoubleSpinBox()
        self.minimum_stock.setDecimals(2)
        self.minimum_stock.setMaximum(999999.99)
        self.minimum_stock.setMinimum(0.0)
        form_layout.addRow("Minimum Stock:", self.minimum_stock)
        
        # Unit of measure
        self.unit_of_measure = QComboBox()
        self.unit_of_measure.addItems(["pcs", "kg", "m", "l", "g", "mm", "cm"])
        self.unit_of_measure.setEditable(True)
        form_layout.addRow("Unit of Measure:", self.unit_of_measure)
        
        # Notes
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(100)
        form_layout.addRow("Notes:", self.notes)
        
        layout.addLayout(form_layout)
        
        # Stock status display
        if self.component_stock:
            status_layout = QVBoxLayout()
            status_layout.addWidget(QLabel("Stock Status:"))
            
            self.status_label = QLabel()
            self.status_label.setStyleSheet("font-weight: bold; padding: 10px; border: 1px solid gray;")
            status_layout.addWidget(self.status_label)
            
            layout.addLayout(status_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Populate fields if editing
        if self.component_stock:
            self.populate_fields()
            self.update_status()
    
    def load_categories(self):
        """Load component categories for filter"""
        try:
            categories = self.session.query(Component.category).distinct().filter(
                Component.category.isnot(None)
            ).order_by(Component.category).all()
            
            self.category_filter.clear()
            self.category_filter.addItem("All Categories", None)
            for category in categories:
                self.category_filter.addItem(category[0], category[0])
        except Exception as e:
            print(f"Error loading categories: {e}")
            self.category_filter.clear()
            self.category_filter.addItem("All Categories", None)
    
    def load_components(self):
        """Load components that don't have stock entries yet, filtered by category"""
        try:
            # Get components that don't have stock entries
            from sqlalchemy import select
            components_with_stock = select(ComponentStock.component_id)
            query = self.session.query(Component).filter(
                ~Component.id.in_(components_with_stock)
            )
            
            # Apply category filter
            selected_category = self.category_filter.currentData()
            if selected_category:
                query = query.filter(Component.category == selected_category)
            
            components = query.order_by(Component.name).all()
            
            self.component_combo.clear()
            for component in components:
                self.component_combo.addItem(component.name, component.id)
        except Exception as e:
            print(f"Error loading components: {e}")
            self.component_combo.clear()
    
    def populate_fields(self):
        """Populate fields with existing stock data"""
        self.current_stock.setValue(self.component_stock.current_stock or 0.0)
        self.minimum_stock.setValue(self.component_stock.minimum_stock or 0.0)
        
        if self.component_stock.unit_of_measure:
            index = self.unit_of_measure.findText(self.component_stock.unit_of_measure)
            if index >= 0:
                self.unit_of_measure.setCurrentIndex(index)
            else:
                self.unit_of_measure.setCurrentText(self.component_stock.unit_of_measure)
        
        if self.component_stock.notes:
            self.notes.setPlainText(self.component_stock.notes)
    
    def update_status(self):
        """Update the stock status display"""
        current = self.current_stock.value()
        minimum = self.minimum_stock.value()
        
        if current >= minimum:
            status = f"✅ In Stock: {current:.2f} {self.unit_of_measure.currentText()}"
            self.status_label.setStyleSheet("font-weight: bold; padding: 10px; border: 1px solid green; background-color: #e8f5e8;")
        else:
            needed = minimum - current
            status = f"⚠️ Low Stock: {current:.2f} {self.unit_of_measure.currentText()} (Need {needed:.2f} more)"
            self.status_label.setStyleSheet("font-weight: bold; padding: 10px; border: 1px solid orange; background-color: #fff3cd;")
        
        self.status_label.setText(status)
    
    def get_data(self):
        """Get the form data"""
        if not self.component_stock and self.component_combo.count() == 0:
            QMessageBox.warning(self, "Validation Error", "No components available for stock tracking")
            return None
        
        if not self.component_stock and self.component_combo.currentData() is None:
            QMessageBox.warning(self, "Validation Error", "Please select a component")
            return None
        
        return {
            'component_id': self.component_combo.currentData() if not self.component_stock else self.component_stock.component_id,
            'current_stock': self.current_stock.value(),
            'minimum_stock': self.minimum_stock.value(),
            'unit_of_measure': self.unit_of_measure.currentText(),
            'notes': self.notes.toPlainText().strip() or None
        }

class StockManagementDialog(QDialog):
    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Stock Management")
        self.setModal(True)
        self.resize(1000, 700)
        self.init_ui()
        
    def closeEvent(self, event):
        """Handle close event to prevent application crash"""
        try:
            event.accept()
        except Exception as e:
            print(f"Error in closeEvent: {e}")
            event.accept()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Filter section
        filter_layout = QHBoxLayout()
        
        # Category filter
        filter_layout.addWidget(QLabel("Filter by Category:"))
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories", None)
        self.load_categories()
        self.category_filter.currentTextChanged.connect(self.refresh_data)
        filter_layout.addWidget(self.category_filter)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_button = QPushButton("Add Stock Entry")
        add_button.clicked.connect(self.add_stock)
        button_layout.addWidget(add_button)
        
        edit_button = QPushButton("Edit Stock")
        edit_button.clicked.connect(self.edit_stock)
        button_layout.addWidget(edit_button)
        
        # Add transaction buttons
        add_transaction_button = QPushButton("Add to Stock")
        add_transaction_button.clicked.connect(self.add_transaction)
        button_layout.addWidget(add_transaction_button)
        
        remove_transaction_button = QPushButton("Remove from Stock")
        remove_transaction_button.clicked.connect(self.remove_transaction)
        button_layout.addWidget(remove_transaction_button)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_data)
        button_layout.addWidget(refresh_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Stock table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Component", "Category", "Current Stock", "Minimum Stock", 
            "Status", "Unit", "Last Updated", "Notes"
        ])
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Component
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Category
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Current Stock
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Minimum Stock
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Unit
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Last Updated
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Notes
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
        self.refresh_data()
    
    def load_categories(self):
        """Load component categories for filter"""
        categories = self.session.query(Component.category).distinct().filter(
            Component.category.isnot(None)
        ).order_by(Component.category).all()
        
        for category in categories:
            self.category_filter.addItem(category[0], category[0])
    
    def refresh_data(self):
        """Refresh the stock table data"""
        query = self.session.query(ComponentStock).join(Component)
        
        # Apply category filter
        selected_category = self.category_filter.currentData()
        if selected_category:
            query = query.filter(Component.category == selected_category)
        
        stock_entries = query.order_by(Component.name).all()
        
        self.table.setRowCount(len(stock_entries))
        
        total_components = len(stock_entries)
        in_stock = 0
        low_stock = 0
        out_of_stock = 0
        
        for i, stock in enumerate(stock_entries):
            component = stock.component
            
            # Component name
            self.table.setItem(i, 0, QTableWidgetItem(component.name))
            
            # Category
            self.table.setItem(i, 1, QTableWidgetItem(component.category or ""))
            
            # Current stock
            self.table.setItem(i, 2, QTableWidgetItem(f"{stock.current_stock:.2f}"))
            
            # Minimum stock
            self.table.setItem(i, 3, QTableWidgetItem(f"{stock.minimum_stock:.2f}"))
            
            # Status
            status_item = QTableWidgetItem()
            if stock.current_stock >= stock.minimum_stock:
                status = "✅ In Stock"
                status_item.setBackground(QColor(200, 255, 200))  # Light green
                in_stock += 1
            else:
                needed = stock.minimum_stock - stock.current_stock
                if stock.current_stock == 0:
                    status = "❌ Out of Stock"
                    status_item.setBackground(QColor(255, 200, 200))  # Light red
                    out_of_stock += 1
                else:
                    status = f"⚠️ Low ({needed:.2f} needed)"
                    status_item.setBackground(QColor(255, 255, 200))  # Light yellow
                    low_stock += 1
            
            status_item.setText(status)
            self.table.setItem(i, 4, status_item)
            
            # Unit
            self.table.setItem(i, 5, QTableWidgetItem(stock.unit_of_measure))
            
            # Last updated
            if stock.last_updated:
                last_updated = stock.last_updated.strftime('%Y-%m-%d %H:%M')
            else:
                last_updated = "Never"
            self.table.setItem(i, 6, QTableWidgetItem(last_updated))
            
            # Notes
            self.table.setItem(i, 7, QTableWidgetItem(stock.notes or ""))
    
    def add_stock(self):
        """Add a new stock entry"""
        try:
            dialog = StockDialog(self.session, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                if data:
                    try:
                        stock = ComponentStock(**data)
                        stock.last_updated = datetime.now()
                        self.session.add(stock)
                        self.session.commit()
                        self.refresh_data()
                        QMessageBox.information(self, "Success", "Stock entry added successfully")
                    except Exception as e:
                        self.session.rollback()
                        QMessageBox.critical(self, "Error", f"Error adding stock entry: {str(e)}")
        except Exception as e:
            print(f"Error in add_stock: {e}")
            QMessageBox.critical(self, "Error", f"Error opening stock dialog: {str(e)}")
    
    def edit_stock(self):
        """Edit selected stock entry"""
        try:
            selected_rows = self.table.selectedItems()
            if not selected_rows:
                QMessageBox.warning(self, "Warning", "Please select a stock entry to edit")
                return
            
            component_name = self.table.item(selected_rows[0].row(), 0).text()
            component = self.session.query(Component).filter(Component.name == component_name).first()
            
            if component:
                stock = self.session.query(ComponentStock).filter(
                    ComponentStock.component_id == component.id
                ).first()
                
                if stock:
                    dialog = StockDialog(self.session, stock, self)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        data = dialog.get_data()
                        if data:
                            try:
                                stock.current_stock = data['current_stock']
                                stock.minimum_stock = data['minimum_stock']
                                stock.unit_of_measure = data['unit_of_measure']
                                stock.notes = data['notes']
                                stock.last_updated = datetime.now()
                                
                                self.session.commit()
                                self.refresh_data()
                                QMessageBox.information(self, "Success", "Stock updated successfully")
                            except Exception as e:
                                self.session.rollback()
                                QMessageBox.critical(self, "Error", f"Error updating stock: {str(e)}")
                else:
                    QMessageBox.warning(self, "Error", "Stock entry not found")
            else:
                QMessageBox.warning(self, "Error", "Component not found")
        except Exception as e:
            print(f"Error in edit_stock: {e}")
            QMessageBox.critical(self, "Error", f"Error editing stock: {str(e)}")
    
    def add_transaction(self):
        """Add stock transaction (add to stock)"""
        try:
            selected_rows = self.table.selectedItems()
            if not selected_rows:
                QMessageBox.warning(self, "Warning", "Please select a stock entry to modify")
                return
            
            component_name = self.table.item(selected_rows[0].row(), 0).text()
            component = self.session.query(Component).filter(Component.name == component_name).first()
            
            if component:
                stock = self.session.query(ComponentStock).filter(
                    ComponentStock.component_id == component.id
                ).first()
                
                if stock:
                    dialog = StockTransactionDialog(self.session, stock, self)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        data = dialog.get_data()
                        if data:
                            try:
                                # Update stock level
                                if data['transaction_type'] == "Add to Stock":
                                    stock.current_stock += data['quantity']
                                else:
                                    stock.current_stock -= data['quantity']
                                
                                stock.last_updated = datetime.now()
                                
                                # TODO: Add transaction history table
                                # For now, just update the stock level
                                
                                self.session.commit()
                                self.refresh_data()
                                QMessageBox.information(self, "Success", f"Stock transaction completed: {data['transaction_type']}")
                            except Exception as e:
                                self.session.rollback()
                                QMessageBox.critical(self, "Error", f"Error processing transaction: {str(e)}")
                else:
                    QMessageBox.warning(self, "Error", "Stock entry not found")
            else:
                QMessageBox.warning(self, "Error", "Component not found")
        except Exception as e:
            print(f"Error in add_transaction: {e}")
            QMessageBox.critical(self, "Error", f"Error adding transaction: {str(e)}")
    
    def remove_transaction(self):
        """Remove stock transaction (remove from stock)"""
        # Same as add_transaction but pre-select "Remove from Stock"
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a stock entry to modify")
            return
        
        component_name = self.table.item(selected_rows[0].row(), 0).text()
        component = self.session.query(Component).filter(Component.name == component_name).first()
        
        if component:
            stock = self.session.query(ComponentStock).filter(
                ComponentStock.component_id == component.id
            ).first()
            
            if stock:
                dialog = StockTransactionDialog(self.session, stock, self)
                dialog.transaction_type.setCurrentText("Remove from Stock")
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    data = dialog.get_data()
                    if data:
                        try:
                            # Update stock level
                            if data['transaction_type'] == "Add to Stock":
                                stock.current_stock += data['quantity']
                            else:
                                stock.current_stock -= data['quantity']
                            
                            stock.last_updated = datetime.now()
                            
                            self.session.commit()
                            self.refresh_data()
                            QMessageBox.information(self, "Success", f"Stock transaction completed: {data['transaction_type']}")
                        except Exception as e:
                            self.session.rollback()
                            QMessageBox.critical(self, "Error", f"Error processing transaction: {str(e)}")
            else:
                QMessageBox.warning(self, "Error", "Stock entry not found")
        else:
            QMessageBox.warning(self, "Error", "Component not found") 