from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QLabel, QLineEdit, QComboBox, QSpinBox,
    QDateEdit, QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
    QHeaderView, QCheckBox, QGroupBox, QTextEdit, QTabWidget,
    QProgressBar, QSplitter, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QThread, pyqtSlot
from PyQt6.QtGui import QFont
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from utils.permissions import get_permissions_manager
import pandas as pd
import os

class ReportGenerator(QThread):
    """Background thread for generating reports"""
    progress_updated = pyqtSignal(int)
    report_completed = pyqtSignal(str, object)  # report_type, data
    error_occurred = pyqtSignal(str)
    
    def __init__(self, session: Session, report_type: str, params: dict):
        super().__init__()
        self.session = session
        self.report_type = report_type
        self.params = params
    
    def run(self):
        try:
            if self.report_type == "sales_summary":
                data = self.generate_sales_summary()
            elif self.report_type == "production_status":
                data = self.generate_production_status()
            elif self.report_type == "customer_analysis":
                data = self.generate_customer_analysis()
            elif self.report_type == "delivery_tracking":
                data = self.generate_delivery_tracking()
            elif self.report_type == "inventory_status":
                data = self.generate_inventory_status()
            elif self.report_type == "prices_by_customer":
                data = self.generate_prices_by_customer()
            else:
                raise ValueError(f"Unknown report type: {self.report_type}")
            
            self.report_completed.emit(self.report_type, data)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def generate_sales_summary(self):
        """Generate sales summary report"""
        from models.database import Order, OrderItem, Customer, Product
        
        # Get date range
        start_date = self.params.get('start_date', date.today() - timedelta(days=30))
        end_date = self.params.get('end_date', date.today())
        
        # Query orders in date range
        orders = self.session.query(Order).filter(
            Order.order_date >= start_date,
            Order.order_date <= end_date
        ).all()
        
        # Calculate summary
        total_orders = len(orders)
        total_value = sum(order.total_value for order in orders if hasattr(order, 'total_value'))
        
        # Group by customer
        customer_sales = {}
        for order in orders:
            customer_name = order.customer.name if order.customer else "Unknown"
            if customer_name not in customer_sales:
                customer_sales[customer_name] = 0
            customer_sales[customer_name] += order.total_value if hasattr(order, 'total_value') else 0
        
        return {
            'period': f"{start_date} to {end_date}",
            'total_orders': total_orders,
            'total_value': total_value,
            'customer_sales': customer_sales
        }
    
    def generate_production_status(self):
        """Generate production status report"""
        # This will be implemented when we have ProductionPlan model
        return {
            'message': 'Production status report not yet implemented'
        }
    
    def generate_customer_analysis(self):
        """Generate customer analysis report"""
        from models.database import Customer, Order
        
        customers = self.session.query(Customer).all()
        
        customer_data = []
        for customer in customers:
            orders = self.session.query(Order).filter(Order.customer_id == customer.id).all()
            total_orders = len(orders)
            total_value = sum(order.total_value for order in orders if hasattr(order, 'total_value'))
            
            customer_data.append({
                'customer_name': customer.name,
                'total_orders': total_orders,
                'total_value': total_value,
                'last_order': max([order.order_date for order in orders]) if orders else None
            })
        
        return {
            'customers': customer_data
        }
    
    def generate_delivery_tracking(self):
        """Generate delivery tracking report"""
        from models.database import Order, OrderItem, Delivery
        
        # Get deliveries in date range
        start_date = self.params.get('start_date', date.today() - timedelta(days=30))
        end_date = self.params.get('end_date', date.today())
        
        deliveries = self.session.query(Delivery).filter(
            Delivery.delivery_date >= start_date,
            Delivery.delivery_date <= end_date
        ).all()
        
        delivery_data = []
        for delivery in deliveries:
            delivery_data.append({
                'order_number': delivery.order_item.order.order_number if delivery.order_item and delivery.order_item.order else 'N/A',
                'customer': delivery.order_item.order.customer.name if delivery.order_item and delivery.order_item.order and delivery.order_item.order.customer else 'N/A',
                'item': delivery.order_item.item.customer_item_name if delivery.order_item and delivery.order_item.item else 'N/A',
                'quantity': delivery.quantity,
                'delivery_date': delivery.delivery_date,
                'status': delivery.status
            })
        
        return {
            'period': f"{start_date} to {end_date}",
            'deliveries': delivery_data
        }
    
    def generate_inventory_status(self):
        """Generate inventory status report"""
        from models.database import Item, Product
        
        items = self.session.query(Item).join(Product).all()
        
        inventory_data = []
        for item in items:
            # Count orders for this item
            order_count = len(item.order_items) if hasattr(item, 'order_items') else 0
            
            inventory_data.append({
                'customer': item.customer.name if item.customer else 'N/A',
                'product': item.product.name if item.product else 'N/A',
                'item_code': item.customer_code,
                'item_name': item.customer_item_name,
                'order_count': order_count
            })
        
        return {
            'items': inventory_data
        }

    def generate_prices_by_customer(self):
        """Generate prices by customer report"""
        from models.database import Order, OrderItem, Customer, Product, Item
        
        # Get parameters
        customer_id = self.params.get('customer_id')
        product_id = self.params.get('product_id')
        start_date = self.params.get('start_date', date.today() - timedelta(days=365))
        end_date = self.params.get('end_date', date.today())
        
        # Build query for order items with prices
        query = self.session.query(OrderItem).join(Order).join(Customer).join(Item).join(Product)
        
        # Apply filters
        if customer_id:
            query = query.filter(Order.customer_id == customer_id)
        if product_id:
            query = query.filter(Item.product_id == product_id)
        
        query = query.filter(Order.order_date >= start_date, Order.order_date <= end_date)
        
        order_items = query.all()
        
        # Table 1: Price for each order (with order date)
        order_prices = []
        for item in order_items:
            order_prices.append({
                'customer': item.order.customer.name,
                'order_number': item.order.order_number,
                'order_date': item.order.order_date.strftime('%Y-%m'),
                'product': item.item.product.name,
                'item_name': item.item.customer_item_name,
                'item_code': item.item.customer_code,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total_price': item.quantity * item.unit_price
            })
        
        # Table 2: Price of selected product for each customer
        customer_product_prices = []
        if product_id:
            # Group by customer and get price variations for the selected product
            customer_prices = {}
            for item in order_items:
                if item.item.product_id == product_id:
                    customer_name = item.order.customer.name
                    if customer_name not in customer_prices:
                        customer_prices[customer_name] = []
                    customer_prices[customer_name].append({
                        'order_date': item.order.order_date.strftime('%Y-%m'),
                        'unit_price': item.unit_price,
                        'quantity': item.quantity
                    })
            
            for customer_name, prices in customer_prices.items():
                # Sort by date to show price evolution
                prices.sort(key=lambda x: x['order_date'])
                customer_product_prices.append({
                    'customer': customer_name,
                    'price_variations': prices,
                    'min_price': min(p['unit_price'] for p in prices),
                    'max_price': max(p['unit_price'] for p in prices),
                    'avg_price': sum(p['unit_price'] for p in prices) / len(prices)
                })
        
        return {
            'customer_id': customer_id,
            'product_id': product_id,
            'period': f"{start_date} to {end_date}",
            'order_prices': order_prices,
            'customer_product_prices': customer_product_prices
        }

class ReportDialog(QDialog):
    """Dialog for configuring report parameters"""
    def __init__(self, report_type: str, parent=None):
        super().__init__(parent)
        self.report_type = report_type
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle(f"Generate {self.report_type.replace('_', ' ').title()} Report")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QFormLayout()
        
        # Date range
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        layout.addRow("Start Date:", self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        layout.addRow("End Date:", self.end_date)
        
        # Additional parameters based on report type
        if self.report_type == "customer_analysis":
            self.customer_filter = QLineEdit()
            self.customer_filter.setPlaceholderText("Filter by customer name (optional)")
            layout.addRow("Customer Filter:", self.customer_filter)
        
        elif self.report_type == "inventory_status":
            self.show_zero_orders = QCheckBox("Show items with no orders")
            self.show_zero_orders.setChecked(False)
            layout.addRow("", self.show_zero_orders)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow("", button_box)
        
        self.setLayout(layout)
    
    def get_params(self):
        params = {
            'start_date': self.start_date.date().toPyDate(),
            'end_date': self.end_date.date().toPyDate()
        }
        
        if self.report_type == "customer_analysis" and hasattr(self, 'customer_filter'):
            params['customer_filter'] = self.customer_filter.text().strip()
        
        elif self.report_type == "inventory_status" and hasattr(self, 'show_zero_orders'):
            params['show_zero_orders'] = self.show_zero_orders.isChecked()
        
        return params

class ReportsTab(QWidget):
    report_generated = pyqtSignal()
    
    def __init__(self, session: Session, user=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self.permissions_manager = get_permissions_manager()
        self.current_report_data = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Create toolbar
        toolbar = QHBoxLayout()
        
        # Report type selection
        report_label = QLabel("Report Type:")
        self.report_combo = QComboBox()
        self.report_combo.addItems([
            "Sales Summary",
            "Production Status", 
            "Customer Analysis",
            "Delivery Tracking",
            "Inventory Status",
            "Prices by Customer"
        ])
        toolbar.addWidget(report_label)
        toolbar.addWidget(self.report_combo)
        
        # Generate button
        generate_button = QPushButton("Generate Report")
        generate_button.clicked.connect(self.generate_report)
        toolbar.addWidget(generate_button)
        
        # Export button
        export_button = QPushButton("Export to Excel")
        export_button.clicked.connect(self.export_report)
        toolbar.addWidget(export_button)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Create splitter for report display
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Report summary panel
        summary_group = QGroupBox("Report Summary")
        summary_layout = QVBoxLayout()
        self.summary_text = QTextEdit()
        self.summary_text.setMaximumHeight(200)
        summary_layout.addWidget(self.summary_text)
        summary_group.setLayout(summary_layout)
        splitter.addWidget(summary_group)
        
        # Report details panel
        details_group = QGroupBox("Report Details")
        details_layout = QVBoxLayout()
        self.details_table = QTableWidget()
        details_layout.addWidget(self.details_table)
        details_group.setLayout(details_layout)
        splitter.addWidget(details_group)
        
        layout.addWidget(splitter)
        
        self.setLayout(layout)
    
    def generate_report(self):
        """Generate the selected report"""
        if self.user and not self.permissions_manager.has_permission(self.user, "reports", "generate"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to generate reports.")
            return
        
        report_type = self.report_combo.currentText().lower().replace(' ', '_')
        
        # Show parameter dialog
        dialog = ReportDialog(report_type, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_params()
            
            # Show progress bar
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            
            # Generate report in background thread
            self.generator = ReportGenerator(self.session, report_type, params)
            self.generator.progress_updated.connect(self.progress_bar.setValue)
            self.generator.report_completed.connect(self.on_report_completed)
            self.generator.error_occurred.connect(self.on_report_error)
            self.generator.start()
    
    def on_report_completed(self, report_type: str, data: dict):
        """Handle completed report"""
        self.progress_bar.setVisible(False)
        self.current_report_data = data
        
        # Update summary
        summary = self.generate_summary_text(report_type, data)
        self.summary_text.setPlainText(summary)
        
        # Update details table
        self.populate_details_table(report_type, data)
        
        QMessageBox.information(self, "Report Generated", f"{report_type.replace('_', ' ').title()} report has been generated successfully!")
    
    def on_report_error(self, error_message: str):
        """Handle report generation error"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Report Error", f"Error generating report: {error_message}")
    
    def generate_summary_text(self, report_type: str, data: dict) -> str:
        """Generate summary text for the report"""
        if report_type == "sales_summary":
            return f"""Sales Summary Report
Period: {data.get('period', 'N/A')}
Total Orders: {data.get('total_orders', 0)}
Total Value: {data.get('total_value', 0):,.2f}

Top Customers:
{chr(10).join([f"- {customer}: {value:,.2f}" for customer, value in list(data.get('customer_sales', {}).items())[:5]])}"""
        
        elif report_type == "customer_analysis":
            customers = data.get('customers', [])
            total_customers = len(customers)
            total_orders = sum(c['total_orders'] for c in customers)
            total_value = sum(c['total_value'] for c in customers)
            
            return f"""Customer Analysis Report
Total Customers: {total_customers}
Total Orders: {total_orders}
Total Value: {total_value:,.2f}

Top Customers by Value:
{chr(10).join([f"- {c['customer_name']}: {c['total_value']:,.2f} ({c['total_orders']} orders)" for c in sorted(customers, key=lambda x: x['total_value'], reverse=True)[:5]])}"""
        
        elif report_type == "delivery_tracking":
            deliveries = data.get('deliveries', [])
            total_deliveries = len(deliveries)
            
            return f"""Delivery Tracking Report
Period: {data.get('period', 'N/A')}
Total Deliveries: {total_deliveries}"""
        
        elif report_type == "inventory_status":
            items = data.get('items', [])
            total_items = len(items)
            items_with_orders = len([i for i in items if i['order_count'] > 0])
            
            return f"""Inventory Status Report
Total Items: {total_items}
Items with Orders: {items_with_orders}
Items without Orders: {total_items - items_with_orders}"""
        
        else:
            return f"{report_type.replace('_', ' ').title()} Report\n\nReport data available in the details table below."
    
    def populate_details_table(self, report_type: str, data: dict):
        """Populate the details table with report data"""
        if report_type == "sales_summary":
            customer_sales = data.get('customer_sales', {})
            self.details_table.setColumnCount(2)
            self.details_table.setHorizontalHeaderLabels(["Customer", "Total Sales"])
            self.details_table.setRowCount(len(customer_sales))
            
            for row, (customer, sales) in enumerate(customer_sales.items()):
                self.details_table.setItem(row, 0, QTableWidgetItem(customer))
                self.details_table.setItem(row, 1, QTableWidgetItem(f"{sales:,.2f}"))
        
        elif report_type == "customer_analysis":
            customers = data.get('customers', [])
            self.details_table.setColumnCount(4)
            self.details_table.setHorizontalHeaderLabels(["Customer", "Total Orders", "Total Value", "Last Order"])
            self.details_table.setRowCount(len(customers))
            
            for row, customer in enumerate(customers):
                self.details_table.setItem(row, 0, QTableWidgetItem(customer['customer_name']))
                self.details_table.setItem(row, 1, QTableWidgetItem(str(customer['total_orders'])))
                self.details_table.setItem(row, 2, QTableWidgetItem(f"{customer['total_value']:,.2f}"))
                last_order = customer['last_order']
                self.details_table.setItem(row, 3, QTableWidgetItem(str(last_order) if last_order else "N/A"))
        
        elif report_type == "delivery_tracking":
            deliveries = data.get('deliveries', [])
            self.details_table.setColumnCount(6)
            self.details_table.setHorizontalHeaderLabels(["Order", "Customer", "Item", "Quantity", "Delivery Date", "Status"])
            self.details_table.setRowCount(len(deliveries))
            
            for row, delivery in enumerate(deliveries):
                self.details_table.setItem(row, 0, QTableWidgetItem(delivery['order_number']))
                self.details_table.setItem(row, 1, QTableWidgetItem(delivery['customer']))
                self.details_table.setItem(row, 2, QTableWidgetItem(delivery['item']))
                self.details_table.setItem(row, 3, QTableWidgetItem(str(delivery['quantity'])))
                self.details_table.setItem(row, 4, QTableWidgetItem(str(delivery['delivery_date'])))
                self.details_table.setItem(row, 5, QTableWidgetItem(delivery['status']))
        
        elif report_type == "inventory_status":
            items = data.get('items', [])
            self.details_table.setColumnCount(5)
            self.details_table.setHorizontalHeaderLabels(["Customer", "Product", "Item Code", "Item Name", "Order Count"])
            self.details_table.setRowCount(len(items))
            
            for row, item in enumerate(items):
                self.details_table.setItem(row, 0, QTableWidgetItem(item['customer']))
                self.details_table.setItem(row, 1, QTableWidgetItem(item['product']))
                self.details_table.setItem(row, 2, QTableWidgetItem(item['item_code']))
                self.details_table.setItem(row, 3, QTableWidgetItem(item['item_name']))
                self.details_table.setItem(row, 4, QTableWidgetItem(str(item['order_count'])))
        
        # Resize columns
        self.details_table.resizeColumnsToContents()
    
    def export_report(self):
        """Export current report to Excel"""
        if not self.current_report_data:
            QMessageBox.warning(self, "No Report", "Please generate a report first.")
            return
        
        try:
            # Create DataFrame from current report data
            report_type = self.report_combo.currentText().lower().replace(' ', '_')
            
            if report_type == "sales_summary":
                df = pd.DataFrame([
                    {'Customer': customer, 'Total Sales': sales}
                    for customer, sales in self.current_report_data.get('customer_sales', {}).items()
                ])
            
            elif report_type == "customer_analysis":
                df = pd.DataFrame(self.current_report_data.get('customers', []))
            
            elif report_type == "delivery_tracking":
                df = pd.DataFrame(self.current_report_data.get('deliveries', []))
            
            elif report_type == "inventory_status":
                df = pd.DataFrame(self.current_report_data.get('items', []))
            
            else:
                QMessageBox.warning(self, "Export Error", "Export not supported for this report type.")
                return
            
            # Save to file
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Report", 
                f"{report_type.replace('_', '_').title()}_Report.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if filename:
                df.to_excel(filename, index=False)
                QMessageBox.information(self, "Export Successful", f"Report exported to {filename}")
        
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting report: {str(e)}") 