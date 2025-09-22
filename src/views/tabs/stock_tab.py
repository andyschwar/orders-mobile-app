from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox,
    QLabel, QHeaderView, QComboBox, QDialog,
    QFormLayout, QDoubleSpinBox, QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from sqlalchemy.orm import Session
from models.database import Component, ComponentStock
from views.dialogs.stock_dialog import StockDialog, StockTransactionDialog
from utils.permissions import get_permissions_manager
from datetime import datetime

class StockTab(QWidget):
    stock_updated = pyqtSignal()
    
    def __init__(self, session: Session, user=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self.permissions_manager = get_permissions_manager()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("Component Stock Management")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(header_label)
        
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
        
        self.add_stock_button = QPushButton("Add Stock Entry")
        self.add_stock_button.clicked.connect(self.add_stock)
        button_layout.addWidget(self.add_stock_button)
        
        self.edit_stock_button = QPushButton("Edit Stock")
        self.edit_stock_button.clicked.connect(self.edit_stock)
        button_layout.addWidget(self.edit_stock_button)
        
        self.add_transaction_button = QPushButton("Add to Stock")
        self.add_transaction_button.clicked.connect(self.add_transaction)
        button_layout.addWidget(self.add_transaction_button)
        
        self.remove_transaction_button = QPushButton("Remove from Stock")
        self.remove_transaction_button.clicked.connect(self.remove_transaction)
        button_layout.addWidget(self.remove_transaction_button)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        button_layout.addWidget(self.refresh_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Summary statistics
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-weight: bold; color: blue; margin: 10px;")
        layout.addWidget(self.summary_label)
        
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
        
        # Load initial data
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
        
        # Update summary
        category_text = f" (Category: {selected_category})" if selected_category else ""
        self.summary_label.setText(
            f"Total Components with Stock Tracking: {total_components}{category_text} | "
            f"In Stock: {in_stock} | "
            f"Low Stock: {low_stock} | "
            f"Out of Stock: {out_of_stock}"
        )
    
    def add_stock(self):
        """Add a new stock entry"""
        if self.user and not self.permissions_manager.has_permission(self.user, "stock", "create"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to add stock entries.")
            return
        
        try:
            dialog = StockDialog(self.session, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                if data:
                    try:
                        from models.database import ComponentStock
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
            pass
            QMessageBox.critical(self, "Error", f"Error opening stock dialog: {str(e)}")
    
    def edit_stock(self):
        """Edit selected stock entry"""
        if self.user and not self.permissions_manager.has_permission(self.user, "stock", "edit"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit stock entries.")
            return
        
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
            pass
            QMessageBox.critical(self, "Error", f"Error editing stock: {str(e)}")
    
    def add_transaction(self):
        """Add stock transaction (add to stock)"""
        if self.user and not self.permissions_manager.has_permission(self.user, "stock", "edit"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to modify stock.")
            return
        
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
            pass
            QMessageBox.critical(self, "Error", f"Error adding transaction: {str(e)}")
    
    def remove_transaction(self):
        """Remove stock transaction (remove from stock)"""
        if self.user and not self.permissions_manager.has_permission(self.user, "stock", "edit"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to modify stock.")
            return
        
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
        except Exception as e:
            pass
            QMessageBox.critical(self, "Error", f"Error removing transaction: {str(e)}") 