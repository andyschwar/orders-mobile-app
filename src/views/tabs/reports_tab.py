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
from dateutil.relativedelta import relativedelta
from utils.permissions import get_permissions_manager
from models.database import get_session_with_retry, execute_with_retry
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
            # Use retry logic for all database operations
            if self.report_type == "sales_summary":
                def wrapper(session):
                    return self.generate_sales_summary(session)
                data = execute_with_retry(wrapper)
            elif self.report_type == "production_status":
                def wrapper(session):
                    return self.generate_production_status(session)
                data = execute_with_retry(wrapper)
            elif self.report_type == "customer_analysis":
                def wrapper(session):
                    return self.generate_customer_analysis(session)
                data = execute_with_retry(wrapper)
            elif self.report_type == "delivery_tracking":
                def wrapper(session):
                    return self.generate_delivery_tracking(session)
                data = execute_with_retry(wrapper)
            elif self.report_type == "inventory_status":
                def wrapper(session):
                    return self.generate_inventory_status(session)
                data = execute_with_retry(wrapper)
            elif self.report_type == "prices_by_customer":
                def wrapper(session):
                    return self.generate_prices_by_customer(session)
                data = execute_with_retry(wrapper)
            elif self.report_type == "component_requirements":
                def wrapper(session):
                    return self.generate_component_requirements(session)
                data = execute_with_retry(wrapper)
            elif self.report_type == "stock_analysis":
                def wrapper(session):
                    return self.generate_stock_analysis(session)
                data = execute_with_retry(wrapper)
            else:
                raise ValueError(f"Unknown report type: {self.report_type}")
            
            self.report_completed.emit(self.report_type, data)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def generate_sales_summary(self, session):
        """Generate sales summary report"""
        from models.database import Order, OrderItem, Customer, Product
        
        # Get date range from params
        start_date = self.params.get('start_date')
        end_date = self.params.get('end_date')
        
        # Build query
        query = session.query(
            Order.id,
            Order.order_number,
            Order.order_date,
            Customer.name.label('customer_name'),
            Product.name.label('product_name'),
            OrderItem.quantity,
            OrderItem.price,
            (OrderItem.quantity * OrderItem.price).label('total_value')
        ).join(
            OrderItem, Order.id == OrderItem.order_id
        ).join(
            Customer, Order.customer_id == Customer.id
        ).join(
            Product, OrderItem.item_id == Product.id
        )
        
        # Apply date filters if provided
        if start_date and end_date:
            query = query.filter(
                Order.order_date >= start_date,
                Order.order_date <= end_date
            )
        
        # Execute query
        results = query.all()
        
        # Process results
        data = {
            'total_orders': len(set(r.id for r in results)),
            'total_items': len(results),
            'total_value': sum(r.total_value or 0 for r in results),
            'orders_by_customer': {},
            'orders_by_product': {},
            'daily_sales': {},
            'details': results
        }
        
        # Group by customer
        for result in results:
            customer = result.customer_name
            if customer not in data['orders_by_customer']:
                data['orders_by_customer'][customer] = {
                    'orders': 0,
                    'items': 0,
                    'value': 0
                }
            data['orders_by_customer'][customer]['orders'] += 1
            data['orders_by_customer'][customer]['items'] += result.quantity or 0
            data['orders_by_customer'][customer]['value'] += result.total_value or 0
        
        # Group by product
        for result in results:
            product = result.product_name
            if product not in data['orders_by_product']:
                data['orders_by_product'][product] = {
                    'quantity': 0,
                    'value': 0
                }
            data['orders_by_product'][product]['quantity'] += result.quantity or 0
            data['orders_by_product'][product]['value'] += result.total_value or 0
        
        # Group by date
        for result in results:
            date_str = result.order_date.strftime('%Y-%m-%d')
            if date_str not in data['daily_sales']:
                data['daily_sales'][date_str] = {
                    'orders': 0,
                    'value': 0
                }
            data['daily_sales'][date_str]['orders'] += 1
            data['daily_sales'][date_str]['value'] += result.total_value or 0
        
        return data
    
    def generate_production_status(self, session):
        """Generate production status report"""
        # This will be implemented when we have ProductionPlan model
        return {
            'message': 'Production status report not yet implemented'
        }
    
    def generate_customer_analysis(self, session):
        """Generate customer analysis report"""
        from models.database import Customer, Order
        from utils.currency_converter import convert_to_target_currency, get_currency_info
        
        # Get parameters
        target_currency = self.params.get('target_currency', 'EUR')
        
        customers = session.query(Customer).all()
        
        customer_data = []
        total_value_target = 0
        
        for customer in customers:
            orders = session.query(Order).filter(Order.customer_id == customer.id).all()
            total_orders = len(orders)
            
            # Calculate total value in original currency
            total_value_original = sum(sum(item.quantity * (item.price or 0) for item in order.items) for order in orders)
            
            # Get currency info and convert to target currency
            currency_info = get_currency_info(customer.currency, customer.is_eu)
            total_value_target_converted = convert_to_target_currency(total_value_original, customer.currency, target_currency)
            total_value_target += total_value_target_converted
            
            customer_data.append({
                'customer_name': customer.name,
                'customer_currency': currency_info['currency'],
                'customer_is_eu': customer.is_eu,
                'total_orders': total_orders,
                'total_value_original': total_value_original,
                'total_value_target': total_value_target_converted,
                'last_order': max([order.order_date for order in orders]) if orders else None
            })
        
        return {
            'customers': customer_data,
            'total_value_target': total_value_target,
            'target_currency': target_currency
        }
    
    def generate_component_requirements(self, session):
        """Generate component requirements report for undelivered items"""
        from models.database import Order, OrderItem, Product, Component, ProductComponent, Delivery, Item
        from datetime import datetime
        
        # Get parameters
        start_date = self.params.get('start_date', date.today())
        end_date = self.params.get('end_date', date.today())
        use_all_records = self.params.get('use_all_records', False)
        delivery_status = self.params.get('delivery_status', 'undelivered')  # 'delivered', 'undelivered', 'all'
        currency = self.params.get('currency', 'EUR')  # 'EUR' or 'CZK'
        component_category = self.params.get('component_category')  # Category filter
        split_by_month = self.params.get('split_by_month', False)  # New parameter for monthly splitting
        split_by_surface_treatment = self.params.get('split_by_surface_treatment', False)  # New parameter for surface treatment splitting
        
        # Get undelivered order items
        query = session.query(OrderItem).join(Order).join(Item).join(Product)
        
        # Filter by delivery date if not using all records
        if not use_all_records:
            query = query.filter(
                OrderItem.delivery_date >= start_date,
                OrderItem.delivery_date <= end_date
            )
        
        # Filter by delivery status
        if delivery_status == 'delivered':
            query = query.filter(OrderItem.delivered_quantity >= OrderItem.quantity)
        elif delivery_status == 'undelivered':
            query = query.filter(OrderItem.delivered_quantity < OrderItem.quantity)
        # 'all' means no additional filter
        
        order_items = query.all()
        
        if split_by_surface_treatment:
            # Generate surface treatment split data
            return self._generate_component_requirements_by_surface_treatment(order_items, delivery_status, currency, component_category, use_all_records, start_date, end_date)
        elif split_by_month and not use_all_records:
            # Generate monthly split data
            return self._generate_component_requirements_monthly(order_items, start_date, end_date, delivery_status, currency, component_category)
        else:
            # Generate traditional aggregated data
            return self._generate_component_requirements_aggregated(order_items, delivery_status, currency, component_category, use_all_records, start_date, end_date)
    
    def _generate_component_requirements_aggregated(self, order_items, delivery_status, currency, component_category, use_all_records, start_date, end_date):
        """Generate aggregated component requirements (original behavior)"""
        component_requirements = {}
        total_items = 0
        total_components_needed = 0
        
        for order_item in order_items:
            # Use the delivered_quantity field directly instead of calculating from deliveries
            delivered_qty = order_item.delivered_quantity or 0
            
            # Handle different delivery status filters
            if delivery_status == 'delivered':
                # For delivered items, use the delivered quantity
                remaining_qty = delivered_qty
            elif delivery_status == 'undelivered':
                # For undelivered items, use the remaining quantity
                remaining_qty = order_item.quantity - delivered_qty
            else:  # 'all'
                # For all items, use the total ordered quantity
                remaining_qty = order_item.quantity
            
            if remaining_qty > 0:
                total_items += remaining_qty
                
                # Get product components
                product = order_item.item.product
                if product:
                    for product_component in product.components:
                        component = product_component.component
                        
                        # Filter by component category if specified
                        if component_category:
                            # Compare as strings, handle None/empty
                            if (component.category or "") != component_category:
                                continue
                        
                        component_key = component.description or 'No description'
                        
                        # Calculate required quantity for this component
                        required_qty = product_component.quantity * remaining_qty
                        
                        if component_key not in component_requirements:
                            # Get unit cost in selected currency
                            if currency == 'EUR':
                                unit_cost = component.unit_cost_eur or (component.unit_cost * 0.041)  # Convert CZK to EUR
                            else:  # CZK
                                unit_cost = component.unit_cost or 0
                            
                            # Convert component to simple dictionary to avoid session detachment issues
                            component_data = {
                                'id': component.id,
                                'name': component.name,
                                'description': component.description,
                                'category': component.category,
                                'unit_cost': component.unit_cost,
                                'unit_cost_eur': component.unit_cost_eur
                            }
                            
                            component_requirements[component_key] = {
                                'component': component_data,
                                'total_required': 0,
                                'unit_cost': unit_cost,
                                'total_cost': 0,
                                'items_using': []
                            }
                        
                        component_requirements[component_key]['total_required'] += required_qty
                        component_requirements[component_key]['total_cost'] += required_qty * component_requirements[component_key]['unit_cost']
                        
                        # Track which items are using this component
                        item_info = {
                            'order_number': order_item.order.order_number,
                            'customer': order_item.order.customer.name if order_item.order.customer else 'Unknown',
                            'item_name': order_item.item.customer_item_name if order_item.item else 'Unknown',
                            'remaining_qty': remaining_qty,
                            'component_qty_per_item': product_component.quantity,
                            'component_qty_needed': required_qty
                        }
                        component_requirements[component_key]['items_using'].append(item_info)
        
        # Calculate totals
        total_cost = sum(comp['total_cost'] for comp in component_requirements.values())
        
        return {
            'component_requirements': component_requirements,
            'total_items': total_items,
            'total_components_needed': len(component_requirements),
            'total_cost': total_cost,
            'period': "All records" if use_all_records else f"{start_date} to {end_date}",
            'delivery_status': delivery_status,
            'currency': currency,
            'component_category': component_category,
            'split_by_month': False
        }
    
    def _generate_component_requirements_monthly(self, order_items, start_date, end_date, delivery_status, currency, component_category):
        """Generate component requirements split by calendar month"""
        from dateutil.relativedelta import relativedelta
        
        # Generate list of months in the date range
        months = []
        current_date = date(start_date.year, start_date.month, 1)
        end_month = date(end_date.year, end_date.month, 1)
        
        while current_date <= end_month:
            months.append(current_date)
            current_date = current_date + relativedelta(months=1)
        
        # Initialize monthly data structure
        monthly_requirements = {}
        total_items = 0
        total_components_needed = set()
        
        for month_start in months:
            month_end = month_start + relativedelta(months=1) - timedelta(days=1)
            month_key = month_start.strftime('%Y-%m')
            
            # Filter order items for this month
            month_items = []
            for order_item in order_items:
                if order_item.delivery_date and month_start <= order_item.delivery_date <= month_end:
                    month_items.append(order_item)
            
            # Process items for this month
            month_requirements = {}
            month_total_items = 0
            
            for order_item in month_items:
                # Use the delivered_quantity field directly instead of calculating from deliveries
                delivered_qty = order_item.delivered_quantity or 0
                
                # Handle different delivery status filters
                if delivery_status == 'delivered':
                    # For delivered items, use the delivered quantity
                    remaining_qty = delivered_qty
                elif delivery_status == 'undelivered':
                    # For undelivered items, use the remaining quantity
                    remaining_qty = order_item.quantity - delivered_qty
                else:  # 'all'
                    # For all items, use the total ordered quantity
                    remaining_qty = order_item.quantity
                
                if remaining_qty > 0:
                    month_total_items += remaining_qty
                    
                    # Get product components
                    product = order_item.item.product
                    if product:
                        for product_component in product.components:
                            component = product_component.component
                            
                            # Filter by component category if specified
                            if component_category:
                                # Compare as strings, handle None/empty
                                if (component.category or "") != component_category:
                                    continue
                            
                            component_key = component.description or 'No description'
                            total_components_needed.add(component_key)
                            
                            # Calculate required quantity for this component
                            required_qty = product_component.quantity * remaining_qty
                            
                            if component_key not in month_requirements:
                                # Get unit cost in selected currency
                                if currency == 'EUR':
                                    unit_cost = component.unit_cost_eur or (component.unit_cost * 0.041)  # Convert CZK to EUR
                                else:  # CZK
                                    unit_cost = component.unit_cost or 0
                                
                                # Convert component to simple dictionary to avoid session detachment issues
                                component_data = {
                                    'id': component.id,
                                    'name': component.name,
                                    'description': component.description,
                                    'category': component.category,
                                    'unit_cost': component.unit_cost,
                                    'unit_cost_eur': component.unit_cost_eur
                                }
                                
                                month_requirements[component_key] = {
                                    'component': component_data,
                                    'total_required': 0,
                                    'unit_cost': unit_cost,
                                    'total_cost': 0,
                                    'items_using': []
                                }
                            
                            month_requirements[component_key]['total_required'] += required_qty
                            month_requirements[component_key]['total_cost'] += required_qty * month_requirements[component_key]['unit_cost']
                            
                            # Track which items are using this component
                            item_info = {
                                'order_number': order_item.order.order_number,
                                'customer': order_item.order.customer.name if order_item.order.customer else 'Unknown',
                                'item_name': order_item.item.customer_item_name if order_item.item else 'Unknown',
                                'remaining_qty': remaining_qty,
                                'component_qty_per_item': product_component.quantity,
                                'component_qty_needed': required_qty
                            }
                            month_requirements[component_key]['items_using'].append(item_info)
            
            monthly_requirements[month_key] = {
                'requirements': month_requirements,
                'total_items': month_total_items,
                'total_cost': sum(comp['total_cost'] for comp in month_requirements.values()),
                'month_name': month_start.strftime('%B %Y')
            }
            total_items += month_total_items
        
        # Calculate overall totals
        total_cost = sum(month_data['total_cost'] for month_data in monthly_requirements.values())
        
        return {
            'monthly_requirements': monthly_requirements,
            'total_items': total_items,
            'total_components_needed': len(total_components_needed),
            'total_cost': total_cost,
            'period': f"{start_date} to {end_date}",
            'delivery_status': delivery_status,
            'currency': currency,
            'component_category': component_category,
            'split_by_month': True
        }
    
    def _generate_component_requirements_by_surface_treatment(self, order_items, delivery_status, currency, component_category, use_all_records, start_date, end_date):
        """Generate component requirements split by surface treatment"""
        # Group by surface treatment
        surface_treatment_requirements = {}
        total_items = 0
        total_components_needed = set()
        
        for order_item in order_items:
            # Use the delivered_quantity field directly instead of calculating from deliveries
            delivered_qty = order_item.delivered_quantity or 0
            
            # Handle different delivery status filters
            if delivery_status == 'delivered':
                # For delivered items, use the delivered quantity
                remaining_qty = delivered_qty
            elif delivery_status == 'undelivered':
                # For undelivered items, use the remaining quantity
                remaining_qty = order_item.quantity - delivered_qty
            else:  # 'all'
                # For all items, use the total ordered quantity
                remaining_qty = order_item.quantity
            
            if remaining_qty > 0:
                # Get surface treatment (default to KATAFOREZA if not specified)
                surface_treatment = order_item.surface_treatment or 'KATAFOREZA'
                
                if surface_treatment not in surface_treatment_requirements:
                    surface_treatment_requirements[surface_treatment] = {
                        'requirements': {},
                        'total_items': 0,
                        'total_cost': 0
                    }
                
                surface_treatment_requirements[surface_treatment]['total_items'] += remaining_qty
                total_items += remaining_qty
                
                # Get product components
                product = order_item.item.product
                if product:
                    for product_component in product.components:
                        component = product_component.component
                        
                        # Filter by component category if specified
                        if component_category:
                            # Compare as strings, handle None/empty
                            if (component.category or "") != component_category:
                                continue
                        
                        component_key = component.description or 'No description'
                        total_components_needed.add(component_key)
                        
                        # Calculate required quantity for this component
                        required_qty = product_component.quantity * remaining_qty
                        
                        if component_key not in surface_treatment_requirements[surface_treatment]['requirements']:
                            # Get unit cost in selected currency
                            if currency == 'EUR':
                                unit_cost = component.unit_cost_eur or (component.unit_cost * 0.041)  # Convert CZK to EUR
                            else:  # CZK
                                unit_cost = component.unit_cost or 0
                            
                            # Convert component to simple dictionary to avoid session detachment issues
                            component_data = {
                                'id': component.id,
                                'name': component.name,
                                'description': component.description,
                                'category': component.category,
                                'unit_cost': component.unit_cost,
                                'unit_cost_eur': component.unit_cost_eur
                            }
                            
                            surface_treatment_requirements[surface_treatment]['requirements'][component_key] = {
                                'component': component_data,
                                'total_required': 0,
                                'unit_cost': unit_cost,
                                'total_cost': 0,
                                'items_using': []
                            }
                        
                        surface_treatment_requirements[surface_treatment]['requirements'][component_key]['total_required'] += required_qty
                        surface_treatment_requirements[surface_treatment]['requirements'][component_key]['total_cost'] += required_qty * surface_treatment_requirements[surface_treatment]['requirements'][component_key]['unit_cost']
                        
                        # Track which items are using this component
                        item_info = {
                            'order_number': order_item.order.order_number,
                            'customer': order_item.order.customer.name if order_item.order.customer else 'Unknown',
                            'item_name': order_item.item.customer_item_name if order_item.item else 'Unknown',
                            'remaining_qty': remaining_qty,
                            'component_qty_per_item': product_component.quantity,
                            'component_qty_needed': required_qty
                        }
                        surface_treatment_requirements[surface_treatment]['requirements'][component_key]['items_using'].append(item_info)
        
        # Calculate totals for each surface treatment
        for surface_treatment in surface_treatment_requirements:
            surface_treatment_requirements[surface_treatment]['total_cost'] = sum(
                comp['total_cost'] for comp in surface_treatment_requirements[surface_treatment]['requirements'].values()
            )
        
        # Calculate overall totals
        total_cost = sum(treatment_data['total_cost'] for treatment_data in surface_treatment_requirements.values())
        
        return {
            'surface_treatment_requirements': surface_treatment_requirements,
            'total_items': total_items,
            'total_components_needed': len(total_components_needed),
            'total_cost': total_cost,
            'period': "All records" if use_all_records else f"{start_date} to {end_date}",
            'delivery_status': delivery_status,
            'currency': currency,
            'component_category': component_category,
            'split_by_surface_treatment': True
        }
    
    def generate_delivery_tracking(self, session):
        """Generate delivery tracking report"""
        from models.database import Order, OrderItem, Delivery
        
        # Get deliveries in date range
        start_date = self.params.get('start_date', date.today() - timedelta(days=30))
        end_date = self.params.get('end_date', date.today())
        use_all_records = self.params.get('use_all_records', False)
        
        query = session.query(Delivery)
        
        # Only apply date filter if not using all records
        if not use_all_records:
            query = query.filter(
                Delivery.delivery_date >= start_date,
                Delivery.delivery_date <= end_date
            )
        
        deliveries = query.all()
        
        delivery_data = []
        for delivery in deliveries:
            # Calculate delivery status based on quantity delivered vs ordered
            status = "Completed"
            if delivery.order_item:
                ordered_qty = delivery.order_item.quantity
                delivered_qty = delivery.quantity
                if delivered_qty < ordered_qty:
                    status = "Partial"
                elif delivered_qty == 0:
                    status = "Pending"
            
            # Calculate weight per unit and total weight
            weight_per_unit = 0.0
            if delivery.order_item and delivery.order_item.item and delivery.order_item.item.product:
                weight_per_unit = delivery.order_item.item.product.weight_per_unit or 0.0
            
            total_weight = weight_per_unit * delivery.quantity if weight_per_unit > 0 else 0.0
            
            delivery_data.append({
                'order_number': delivery.order_item.order.order_number if delivery.order_item and delivery.order_item.order else 'N/A',
                'customer': delivery.order_item.order.customer.name_index if delivery.order_item and delivery.order_item.order and delivery.order_item.order.customer else 'N/A',
                'item_code': delivery.order_item.item.customer_code if delivery.order_item and delivery.order_item.item else 'N/A',
                'item_name': delivery.order_item.item.customer_item_name if delivery.order_item and delivery.order_item.item else 'N/A',
                'quantity': delivery.quantity,
                'weight_per_unit': weight_per_unit,
                'total_weight': total_weight,
                'delivery_date': delivery.delivery_date,
                'status': status,
                'delivery_created_at': delivery.created_at.strftime('%Y-%m-%d %H:%M:%S') if delivery.created_at else 'N/A'
            })
        
        # Determine period text
        if use_all_records:
            period_text = "All records"
        else:
            period_text = f"{start_date} to {end_date}"
        
        return {
            'period': period_text,
            'deliveries': delivery_data
        }
    
    def generate_inventory_status(self, session):
        """Generate inventory status report"""
        from models.database import Item, Product
        
        items = session.query(Item).join(Product).all()
        
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

    def generate_prices_by_customer(self, session):
        """Generate prices by customer report"""
        from models.database import Order, OrderItem, Customer, Product, Item
        from utils.currency_converter import convert_to_target_currency, get_currency_info
        
        # Get parameters
        customer_id = self.params.get('customer_id')
        product_id = self.params.get('product_id')
        use_all_records = self.params.get('use_all_records', False)
        start_date = self.params.get('start_date', date.today() - timedelta(days=365))
        end_date = self.params.get('end_date', date.today())
        target_currency = self.params.get('target_currency', 'EUR')
        
        # Build query for order items with prices
        query = session.query(OrderItem).join(Order).join(Customer).join(Item).join(Product)
        
        # Apply filters
        if customer_id:
            query = query.filter(Order.customer_id == customer_id)
        if product_id:
            query = query.filter(Item.product_id == product_id)
        
        # Only apply date filter if not using all records
        if not use_all_records:
            query = query.filter(Order.order_date >= start_date, Order.order_date <= end_date)
        
        order_items = query.all()
        
        # Table 1: Price for each order (with order date) - only show selected product if specified
        order_prices = []
        for item in order_items:
            # If a specific product is selected, only include items for that product
            if product_id and item.item.product_id != product_id:
                continue
            
            # Get currency info and convert prices
            customer_currency = item.order.customer.currency if item.order.customer else 'EUR'
            unit_price_original = item.price or 0
            unit_price_target = convert_to_target_currency(unit_price_original, customer_currency, target_currency)
            total_price_original = item.quantity * unit_price_original
            total_price_target = convert_to_target_currency(total_price_original, customer_currency, target_currency)
                
            order_prices.append({
                'customer': item.order.customer.name,
                'customer_currency': customer_currency,
                'order_number': item.order.order_number,
                'order_date': item.order.order_date.strftime('%Y-%m'),
                'product': item.item.product.name,
                'item_name': item.item.customer_item_name,
                'item_code': item.item.customer_code,
                'quantity': item.quantity,
                'unit_price_original': unit_price_original,
                'unit_price_target': unit_price_target,
                'total_price_original': total_price_original,
                'total_price_target': total_price_target
            })
        
        # Table 2: Price of selected product for each customer
        customer_product_prices = []
        if product_id:
            # Group by customer and get price variations for the selected product
            customer_prices = {}
            for item in order_items:
                if item.item.product_id == product_id:
                    customer_name = item.order.customer.name
                    customer_currency = item.order.customer.currency if item.order.customer else 'EUR'
                    if customer_name not in customer_prices:
                        customer_prices[customer_name] = {
                            'currency': customer_currency,
                            'prices': []
                        }
                    customer_prices[customer_name]['prices'].append({
                        'order_date': item.order.order_date.strftime('%Y-%m'),
                        'unit_price_original': item.price or 0,
                        'unit_price_target': convert_to_target_currency(item.price or 0, customer_currency, target_currency),
                        'quantity': item.quantity
                    })
            
            for customer_name, price_data in customer_prices.items():
                # Sort by date to show price evolution
                prices = price_data['prices']
                prices.sort(key=lambda x: x['order_date'])
                
                # Calculate min/max/avg in target currency for comparison
                target_prices = [p['unit_price_target'] for p in prices]
                original_prices = [p['unit_price_original'] for p in prices]
                
                customer_product_prices.append({
                    'customer': customer_name,
                    'currency': price_data['currency'],
                    'price_variations': prices,
                    'min_price_original': min(original_prices),
                    'max_price_original': max(original_prices),
                    'avg_price_original': sum(original_prices) / len(original_prices),
                    'min_price_target': min(target_prices),
                    'max_price_target': max(target_prices),
                    'avg_price_target': sum(target_prices) / len(target_prices)
                })
        
        return {
            'customer_id': customer_id,
            'product_id': product_id,
            'use_all_records': use_all_records,
            'target_currency': target_currency,
            'period': "All records" if use_all_records else f"{start_date} to {end_date}",
            'order_prices': order_prices,
            'customer_product_prices': customer_product_prices
        }

    def generate_stock_analysis(self, session):
        """Generate stock analysis report comparing needs vs available stock"""
        from models.database import Order, OrderItem, Product, Component, ProductComponent, ComponentStock, Item
        
        # Get parameters
        start_date = self.params.get('start_date', date.today())
        end_date = self.params.get('end_date', date.today())
        use_all_records = self.params.get('use_all_records', False)
        delivery_status = self.params.get('delivery_status', 'undelivered')  # 'delivered', 'undelivered', 'all'
        
        # Get order items that need components
        query = session.query(OrderItem).join(Order).join(Item).join(Product)
        
        # Filter by delivery date if not using all records
        if not use_all_records:
            query = query.filter(
                OrderItem.delivery_date >= start_date,
                OrderItem.delivery_date <= end_date
            )
        
        # Filter by delivery status
        if delivery_status == 'delivered':
            query = query.filter(OrderItem.delivered_quantity >= OrderItem.quantity)
        elif delivery_status == 'undelivered':
            query = query.filter(OrderItem.delivered_quantity < OrderItem.quantity)
        # 'all' means no additional filter
        
        order_items = query.all()
        
        # Calculate component requirements
        component_needs = {}
        total_items = 0
        
        for order_item in order_items:
            # Calculate remaining quantity (ordered - delivered)
            delivered_qty = sum(d.quantity for d in order_item.deliveries)
            
            # Handle different delivery status filters
            if delivery_status == 'delivered':
                # For delivered items, use the delivered quantity
                remaining_qty = delivered_qty
            elif delivery_status == 'undelivered':
                # For undelivered items, use the remaining quantity
                remaining_qty = order_item.quantity - delivered_qty
            else:  # 'all'
                # For all items, use the total ordered quantity
                remaining_qty = order_item.quantity
            
            if remaining_qty > 0:
                total_items += remaining_qty
                
                # Get product components
                product = order_item.item.product
                if product:
                    for product_component in product.components:
                        component = product_component.component
                        
                        # Calculate required quantity for this component
                        required_qty = product_component.quantity * remaining_qty
                        
                        if component.id not in component_needs:
                            component_needs[component.id] = {
                                'component': component,
                                'total_needed': 0,
                                'items_using': []
                            }
                        
                        component_needs[component.id]['total_needed'] += required_qty
                        
                        # Track which items are using this component
                        item_info = {
                            'order_number': order_item.order.order_number,
                            'customer': order_item.order.customer.name if order_item.order.customer else 'Unknown',
                            'item_name': order_item.item.customer_item_name if order_item.item else 'Unknown',
                            'remaining_qty': remaining_qty,
                            'component_qty_per_item': product_component.quantity,
                            'component_qty_needed': required_qty
                        }
                        component_needs[component.id]['items_using'].append(item_info)
        
        # Get stock information for components that have stock tracking
        stock_analysis = []
        
        for component_id, need_data in component_needs.items():
            component = need_data['component']
            total_needed = need_data['total_needed']
            
            # Get stock information
            stock = session.query(ComponentStock).filter(
                ComponentStock.component_id == component_id
            ).first()
            
            if stock:
                current_stock = stock.current_stock
                minimum_stock = stock.minimum_stock
                unit = stock.unit_of_measure
                
                # Calculate stock status
                available_after_orders = current_stock - total_needed
                stock_status = "✅ Sufficient"
                if available_after_orders < minimum_stock:
                    if available_after_orders < 0:
                        stock_status = "❌ Insufficient"
                    else:
                        stock_status = "⚠️ Low"
                
                stock_analysis.append({
                    'component': component,
                    'category': component.category or "",
                    'total_needed': total_needed,
                    'current_stock': current_stock,
                    'minimum_stock': minimum_stock,
                    'available_after_orders': available_after_orders,
                    'stock_status': stock_status,
                    'unit': unit,
                    'items_using': need_data['items_using']
                })
        
        # Sort by stock status (insufficient first, then low, then sufficient)
        def sort_key(item):
            status = item['stock_status']
            if '❌' in status:
                return 0
            elif '⚠️' in status:
                return 1
            else:
                return 2
        
        stock_analysis.sort(key=sort_key)
        
        return {
            'stock_analysis': stock_analysis,
            'total_items': total_items,
            'components_with_stock': len(stock_analysis),
            'period': "All records" if use_all_records else f"{start_date} to {end_date}",
            'delivery_status': delivery_status
        }

class ReportDialog(QDialog):
    """Dialog for configuring report parameters"""
    def __init__(self, report_type: str, session: Session, parent=None):
        super().__init__(parent)
        self.report_type = report_type
        self.session = session
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle(f"Generate {self.report_type.replace('_', ' ').title()} Report")
        self.setModal(True)
        self.resize(450, 350)
        
        layout = QFormLayout()
        
        # Quick date range selection
        date_range_label = QLabel("Quick Date Range:")
        self.date_range_combo = QComboBox()
        self.date_range_combo.addItems([
            "Custom Range",
            "All Records",
            "Today",
            "This Year",
            "Previous Year", 
            "This Month",
            "Previous Month",
            "Last 30 Days",
            "Last 90 Days",
            "Last 6 Months",
            "Last Year",
            "Next Month",
            "Next 3 Months"
        ])
        self.date_range_combo.setCurrentText("Last 30 Days")
        self.date_range_combo.setMinimumWidth(150)  # Make dropdown wider
        self.date_range_combo.currentTextChanged.connect(self.on_date_range_changed)
        layout.addRow(date_range_label, self.date_range_combo)
        
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
        
        elif self.report_type == "prices_by_customer":
            # Use all records checkbox
            self.use_all_records = QCheckBox("Use all records (no date filtering)")
            self.use_all_records.setChecked(False)
            layout.addRow("", self.use_all_records)
            
            # Customer selection
            from models.database import Customer, Product
            
            # Use the original session for dialog setup (simpler approach)
            try:
                customers = self.session.query(Customer).order_by(Customer.name_index).all()
                # Convert to simple data structures to avoid session issues
                customer_data = []
                for customer in customers:
                    customer_data.append({
                        'id': customer.id,
                        'name_index': customer.name_index or '',
                        'name': customer.name or ''
                    })
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to load customers: {str(e)}")
                customer_data = []
            
            self.customer_combo = QComboBox()
            self.customer_combo.setMinimumWidth(200)  # Make dropdown wider
            self.customer_combo.addItem("All Customers", None)
            for customer in customer_data:
                self.customer_combo.addItem(f"{customer['name_index']} - {customer['name']}", customer['id'])
            layout.addRow("Customer:", self.customer_combo)
            
            # Product selection
            try:
                products = self.session.query(Product).order_by(Product.name).all()
                # Convert to simple data structures to avoid session issues
                product_data = []
                for product in products:
                    product_data.append({
                        'id': product.id,
                        'name': product.name or ''
                    })
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to load products: {str(e)}")
                product_data = []
            
            self.product_combo = QComboBox()
            self.product_combo.setMinimumWidth(200)  # Make dropdown wider
            self.product_combo.addItem("All Products", None)
            for product in product_data:
                self.product_combo.addItem(product['name'], product['id'])
            layout.addRow("Product:", self.product_combo)
            
        elif self.report_type == "component_requirements":
            # Delivery status filter
            self.delivery_status_combo = QComboBox()
            self.delivery_status_combo.addItems(["Undelivered", "Delivered", "All"])
            self.delivery_status_combo.setCurrentText("Undelivered")
            self.delivery_status_combo.setMinimumWidth(200)
            layout.addRow("Delivery Status:", self.delivery_status_combo)
            
            # Component category filter
            from models.database import Component
            
            try:
                categories = self.session.query(Component.category).filter(
                    Component.category.isnot(None),
                    Component.category != ""
                ).distinct().order_by(Component.category).all()
                # Convert to simple data structures to avoid session issues
                category_data = []
                for (category,) in categories:
                    if category and category.strip():
                        category_data.append(category.strip())
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to load component categories: {str(e)}")
                category_data = []
            
            self.category_combo = QComboBox()
            self.category_combo.addItem("All Categories", None)
            for category in category_data:
                self.category_combo.addItem(category, category)
            self.category_combo.setMinimumWidth(200)
            layout.addRow("Component Category:", self.category_combo)
            
            # Monthly split switch
            self.split_by_month = QCheckBox("Split by calendar month")
            self.split_by_month.setChecked(False)
            self.split_by_month.setToolTip("When enabled, component requirements will be split by calendar month instead of showing totals for the entire period")
            layout.addRow("", self.split_by_month)
            
            # Surface treatment split switch
            self.split_by_surface_treatment = QCheckBox("Split by surface treatment")
            self.split_by_surface_treatment.setChecked(False)
            self.split_by_surface_treatment.setToolTip("When enabled, component requirements will be split by surface treatment (KATAFOREZA, FOSFAT, etc.)")
            layout.addRow("", self.split_by_surface_treatment)
        elif self.report_type == "stock_analysis":
            # Delivery status filter
            self.delivery_status_combo = QComboBox()
            self.delivery_status_combo.addItems(["Undelivered", "Delivered", "All"])
            self.delivery_status_combo.setCurrentText("Undelivered")
            self.delivery_status_combo.setMinimumWidth(200)
            layout.addRow("Delivery Status:", self.delivery_status_combo)
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow("", button_box)
        
        self.setLayout(layout)
    
    def on_date_range_changed(self, selected_range: str):
        """Handle date range selection changes"""
        from datetime import date, timedelta
        
        today = date.today()
        
        if selected_range == "All Records":
            # Set dates to None to indicate no filtering
            self.start_date.setDate(QDate(1900, 1, 1))
            self.end_date.setDate(QDate(2100, 12, 31))
            
        elif selected_range == "Today":
            # Set both start and end date to today
            self.start_date.setDate(QDate(today.year, today.month, today.day))
            self.end_date.setDate(QDate(today.year, today.month, today.day))
            
        elif selected_range == "This Year":
            start_date = date(today.year, 1, 1)
            end_date = date(today.year, 12, 31)
            self.start_date.setDate(QDate(start_date.year, start_date.month, start_date.day))
            self.end_date.setDate(QDate(end_date.year, end_date.month, end_date.day))
            
        elif selected_range == "Previous Year":
            start_date = date(today.year - 1, 1, 1)
            end_date = date(today.year - 1, 12, 31)
            self.start_date.setDate(QDate(start_date.year, start_date.month, start_date.day))
            self.end_date.setDate(QDate(end_date.year, end_date.month, end_date.day))
            
        elif selected_range == "This Month":
            start_date = date(today.year, today.month, 1)
            end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
            self.start_date.setDate(QDate(start_date.year, start_date.month, start_date.day))
            self.end_date.setDate(QDate(end_date.year, end_date.month, end_date.day))
            
        elif selected_range == "Previous Month":
            start_date = (date(today.year, today.month, 1) - relativedelta(months=1))
            end_date = date(today.year, today.month, 1) - timedelta(days=1)
            self.start_date.setDate(QDate(start_date.year, start_date.month, start_date.day))
            self.end_date.setDate(QDate(end_date.year, end_date.month, end_date.day))
            
        elif selected_range == "Last 30 Days":
            start_date = today - timedelta(days=30)
            end_date = today
            self.start_date.setDate(QDate(start_date.year, start_date.month, start_date.day))
            self.end_date.setDate(QDate(end_date.year, end_date.month, end_date.day))
            
        elif selected_range == "Last 90 Days":
            start_date = today - timedelta(days=90)
            end_date = today
            self.start_date.setDate(QDate(start_date.year, start_date.month, start_date.day))
            self.end_date.setDate(QDate(end_date.year, end_date.month, end_date.day))
            
        elif selected_range == "Last 6 Months":
            start_date = today - relativedelta(months=6)
            end_date = today
            self.start_date.setDate(QDate(start_date.year, start_date.month, start_date.day))
            self.end_date.setDate(QDate(end_date.year, end_date.month, end_date.day))
            
        elif selected_range == "Last Year":
            start_date = today - relativedelta(years=1)
            end_date = today
            self.start_date.setDate(QDate(start_date.year, start_date.month, start_date.day))
            self.end_date.setDate(QDate(end_date.year, end_date.month, end_date.day))
            
        elif selected_range == "Next Month":
            start_date = date(today.year, today.month + 1, 1) if today.month < 12 else date(today.year + 1, 1, 1)
            end_date = date(start_date.year, start_date.month + 1, 1) - timedelta(days=1) if start_date.month < 12 else date(start_date.year + 1, 1, 1) - timedelta(days=1)
            self.start_date.setDate(QDate(start_date.year, start_date.month, start_date.day))
            self.end_date.setDate(QDate(end_date.year, end_date.month, end_date.day))
            
        elif selected_range == "Next 3 Months":
            start_date = date(today.year, today.month + 1, 1) if today.month < 12 else date(today.year + 1, 1, 1)
            end_date = date(start_date.year, start_date.month + 3, 1) - timedelta(days=1) if start_date.month <= 9 else date(start_date.year + 1, start_date.month - 9, 1) - timedelta(days=1)
            self.start_date.setDate(QDate(start_date.year, start_date.month, start_date.day))
            self.end_date.setDate(QDate(end_date.year, end_date.month, end_date.day))
            
        # For "Custom Range", do nothing - let user set dates manually
    
    def get_params(self):
        # Check if "All Records" is selected
        use_all_records = self.date_range_combo.currentText() == "All Records"
        
        params = {
            'start_date': self.start_date.date().toPyDate(),
            'end_date': self.end_date.date().toPyDate(),
            'use_all_records': use_all_records
        }
        
        if self.report_type == "customer_analysis" and hasattr(self, 'customer_filter'):
            params['customer_filter'] = self.customer_filter.text().strip()
        
        elif self.report_type == "inventory_status" and hasattr(self, 'show_zero_orders'):
            params['show_zero_orders'] = self.show_zero_orders.isChecked()
        
        elif self.report_type == "prices_by_customer" and hasattr(self, 'customer_combo'):
            params['customer_id'] = self.customer_combo.currentData()
            params['product_id'] = self.product_combo.currentData()
            # For prices_by_customer, combine the checkbox with the date range selection
            if hasattr(self, 'use_all_records'):
                params['use_all_records'] = self.use_all_records.isChecked() or use_all_records
            else:
                params['use_all_records'] = use_all_records
        
        elif self.report_type == "component_requirements" and hasattr(self, 'delivery_status_combo'):
            params['delivery_status'] = self.delivery_status_combo.currentText().lower()
            if hasattr(self, 'category_combo'):
                params['component_category'] = self.category_combo.currentData()
            if hasattr(self, 'split_by_month'):
                params['split_by_month'] = self.split_by_month.isChecked()
            if hasattr(self, 'split_by_surface_treatment'):
                params['split_by_surface_treatment'] = self.split_by_surface_treatment.isChecked()
        elif self.report_type == "stock_analysis" and hasattr(self, 'delivery_status_combo'):
            params['delivery_status'] = self.delivery_status_combo.currentText().lower()
        
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
            "Prices by Customer",
            "Component Requirements",
            "Stock Analysis"
        ])
        self.report_combo.setMinimumWidth(150)  # Make dropdown wider
        toolbar.addWidget(report_label)
        toolbar.addWidget(self.report_combo)
        
        # Currency selection
        currency_label = QLabel("Display Currency:")
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["EUR", "CZK"])
        self.currency_combo.setCurrentText("EUR")  # Default to EUR
        self.currency_combo.setMinimumWidth(80)  # Make dropdown wider
        toolbar.addWidget(currency_label)
        toolbar.addWidget(self.currency_combo)
        

        
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
        self.summary_text.setMaximumHeight(600)
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
        currency = self.currency_combo.currentText()
        
        # Show parameter dialog for all reports
        dialog = ReportDialog(report_type, self.session, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_params()
            params['currency'] = currency
            

        else:
            return  # User cancelled
        
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
            customer_sales = data.get('customer_sales', {})
            target_currency = data.get('target_currency', 'EUR')
            # Sort customers by target currency value
            sorted_customers = sorted(customer_sales.items(), key=lambda x: x[1]['target_value'], reverse=True)
            
            return f"""Sales Summary Report
Period: {data.get('period', 'N/A')}
Total Orders: {data.get('total_orders', 0)}
Total Value (converted to {target_currency}): {data.get('total_value_target', 0):,.2f} {target_currency}

Top Customers by Value ({target_currency}):
{chr(10).join([f"- {customer}: {value['original_value']:,.2f} {value['currency']} ({value['target_value']:,.2f} {target_currency})" for customer, value in sorted_customers[:5]])}"""
        
        elif report_type == "customer_analysis":
            customers = data.get('customers', [])
            total_customers = len(customers)
            total_orders = sum(c['total_orders'] for c in customers)
            total_value_target = data.get('total_value_target', 0)
            target_currency = data.get('target_currency', 'EUR')
            
            # Sort customers by target currency value for comparison
            customers_sorted = sorted(customers, key=lambda x: x['total_value_target'], reverse=True)
            
            summary = f"""Customer Analysis Report
Total Customers: {total_customers}
Total Orders: {total_orders}
Total Value (converted to {target_currency}): {total_value_target:,.2f} {target_currency}

Top Customers by Value ({target_currency}):
{chr(10).join([f"- {c['customer_name']}: {c['total_value_original']:,.2f} {c['customer_currency']} ({c['total_value_target']:,.2f} {target_currency}) - {c['total_orders']} orders" for c in customers_sorted[:5]])}"""
            
            return summary
        
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
        
        elif report_type == "prices_by_customer":
            order_prices = data.get('order_prices', [])
            customer_product_prices = data.get('customer_product_prices', [])
            product_id = data.get('product_id')
            target_currency = data.get('target_currency', 'EUR')
            
            summary = f"""Prices by Customer Report
Period: {data.get('period', 'N/A')}
Total Orders Analyzed: {len(order_prices)}"""
            
            if data.get('use_all_records', False):
                summary += f"\nUsing all available records (no date filtering)"
            
            if product_id:
                summary += f"\nFiltered by specific product"
            
            summary += f"\nCustomers with Price Data: {len(customer_product_prices)}"
            
            if customer_product_prices:
                price_analysis = []
                for c in customer_product_prices:
                    price_analysis.append(f"- {c['customer']}: Min {c['min_price_original']:,.2f} {c['currency']} ({c['min_price_target']:,.2f} {target_currency}), Max {c['max_price_original']:,.2f} {c['currency']} ({c['max_price_target']:,.2f} {target_currency}), Avg {c['avg_price_original']:,.2f} {c['currency']} ({c['avg_price_target']:,.2f} {target_currency})")
                summary += f"\n\nPrice Analysis:\n{chr(10).join(price_analysis)}"
            
            return summary
        
        elif report_type == "component_requirements":
            split_by_month = data.get('split_by_month', False)
            split_by_surface_treatment = data.get('split_by_surface_treatment', False)
            total_items = data.get('total_items', 0)
            total_components_needed = data.get('total_components_needed', 0)
            total_cost = data.get('total_cost', 0)
            period = data.get('period', 'N/A')
            delivery_status = data.get('delivery_status', 'undelivered')
            currency = data.get('currency', 'EUR')
            component_category = data.get('component_category')
            
            if split_by_surface_treatment:
                surface_treatment_requirements = data.get('surface_treatment_requirements', {})
                
                summary = f"""Component Requirements Report (Surface Treatment Split)
Period: {period}
Delivery Status: {delivery_status.title()}
Component Category: {component_category if component_category else 'All Categories'}
Total Items: {total_items}
Total Components Needed: {total_components_needed}
Total Component Cost: {total_cost:,.2f} {currency}

Surface Treatment Breakdown:"""
                
                # Sort surface treatments alphabetically
                sorted_treatments = sorted(surface_treatment_requirements.items())
                
                for surface_treatment, treatment_data in sorted_treatments:
                    treatment_total_items = treatment_data['total_items']
                    treatment_total_cost = treatment_data['total_cost']
                    treatment_requirements = treatment_data['requirements']
                    
                    summary += f"\n\n{surface_treatment}:"
                    summary += f"\n  Total Items: {treatment_total_items}"
                    summary += f"\n  Total Cost: {treatment_total_cost:,.2f} {currency}"
                    summary += f"\n  Components: {len(treatment_requirements)}"
                    
                    # Show top 3 components by cost for this treatment
                    sorted_components = sorted(treatment_requirements.items(), key=lambda x: x[1]['total_cost'], reverse=True)
                    for component_name, comp_data in sorted_components[:3]:
                        summary += f"\n  - {component_name}: {comp_data['total_required']:.2f} units ({currency} {comp_data['total_cost']:.2f})"
                
                return summary
            elif split_by_month:
                monthly_requirements = data.get('monthly_requirements', {})
                
                summary = f"""Component Requirements Report (Monthly Split)
Period: {period}
Delivery Status: {delivery_status.title()}
Component Category: {component_category if component_category else 'All Categories'}
Total Items: {total_items}
Total Components Needed: {total_components_needed}
Total Component Cost: {total_cost:,.2f} {currency}

Monthly Breakdown:"""
                
                # Sort months chronologically
                sorted_months = sorted(monthly_requirements.items())
                
                for month_key, month_data in sorted_months:
                    month_name = month_data['month_name']
                    month_total_items = month_data['total_items']
                    month_total_cost = month_data['total_cost']
                    month_requirements = month_data['requirements']
                    
                    summary += f"\n\n{month_name}:"
                    summary += f"\n  Total Items: {month_total_items}"
                    summary += f"\n  Total Cost: {month_total_cost:,.2f} {currency}"
                    
                    if month_requirements:
                        summary += f"\n  Components:"
                        # Sort components by total cost for this month
                        sorted_components = sorted(month_requirements.items(), key=lambda x: x[1]['total_cost'], reverse=True)
                        
                        for component_name, comp_data in sorted_components:
                            summary += f"\n    - {component_name}: {comp_data['total_required']:.2f} units ({currency} {comp_data['total_cost']:.2f})"
                    else:
                        summary += f"\n  No components required"
                
                return summary
            else:
                component_requirements = data.get('component_requirements', {})
                
                summary = f"""Component Requirements Report
Period: {period}
Delivery Status: {delivery_status.title()}
Component Category: {component_category if component_category else 'All Categories'}
Total Items: {total_items}
Total Components Needed: {total_components_needed}
Total Component Cost: {total_cost:,.2f} {currency}

Component Summary:"""
                
                # Sort components by total cost
                sorted_components = sorted(component_requirements.items(), key=lambda x: x[1]['total_cost'], reverse=True)
                
                for component_name, comp_data in sorted_components:
                    summary += f"\n- {component_name}: {comp_data['total_required']:.2f} units ({currency} {comp_data['total_cost']:.2f})"
                
                return summary
        
        elif report_type == "stock_analysis":
            stock_analysis = data.get('stock_analysis', [])
            total_items = data.get('total_items', 0)
            components_with_stock = data.get('components_with_stock', 0)
            period = data.get('period', 'N/A')
            delivery_status = data.get('delivery_status', 'undelivered')
            
            summary = f"""Stock Analysis Report
Period: {period}
Delivery Status: {delivery_status.title()}
Total Items Requiring Components: {total_items}
Components with Stock Tracking: {components_with_stock}

Stock Status:"""
            
            for item in stock_analysis:
                summary += f"\n- {item['component'].description or 'N/A'} (Category: {item['category']}): {item['current_stock']} {item['unit']} (Needed: {item['total_needed']:.2f} {item['unit']}, Available After Orders: {item['available_after_orders']:.2f} {item['unit']}) - Status: {item['stock_status']}"
            
            return summary
        
        else:
            return f"{report_type.replace('_', ' ').title()} Report\n\nReport data available in the details table below."
    
    def populate_details_table(self, report_type: str, data: dict):
        """Populate the details table with report data"""
        if report_type == "sales_summary":
            customer_sales = data.get('customer_sales', {})
            target_currency = data.get('target_currency', 'EUR')
            self.details_table.setColumnCount(3)
            self.details_table.setHorizontalHeaderLabels(["Customer", "Total Sales (Original)", f"Total Sales ({target_currency})"])
            self.details_table.setRowCount(len(customer_sales))
            
            # Sort by target currency value for better comparison
            sorted_customers = sorted(customer_sales.items(), key=lambda x: x[1]['target_value'], reverse=True)
            
            for row, (customer, sales_data) in enumerate(sorted_customers):
                self.details_table.setItem(row, 0, QTableWidgetItem(customer))
                self.details_table.setItem(row, 1, QTableWidgetItem(f"{sales_data['original_value']:,.2f} {sales_data['currency']}"))
                self.details_table.setItem(row, 2, QTableWidgetItem(f"{sales_data['target_value']:,.2f} {target_currency}"))
        
        elif report_type == "customer_analysis":
            customers = data.get('customers', [])
            target_currency = data.get('target_currency', 'EUR')
            self.details_table.setColumnCount(7)
            self.details_table.setHorizontalHeaderLabels(["Customer", "Currency", "EU Member", "Total Orders", "Total Value (Original)", f"Total Value ({target_currency})", "Last Order"])
            self.details_table.setRowCount(len(customers))
            
            for row, customer in enumerate(customers):
                self.details_table.setItem(row, 0, QTableWidgetItem(customer['customer_name']))
                self.details_table.setItem(row, 1, QTableWidgetItem(customer['customer_currency']))
                self.details_table.setItem(row, 2, QTableWidgetItem("Yes" if customer['customer_is_eu'] else "No"))
                self.details_table.setItem(row, 3, QTableWidgetItem(str(customer['total_orders'])))
                self.details_table.setItem(row, 4, QTableWidgetItem(f"{customer['total_value_original']:,.2f} {customer['customer_currency']}"))
                self.details_table.setItem(row, 5, QTableWidgetItem(f"{customer['total_value_target']:,.2f} {target_currency}"))
                last_order = customer['last_order']
                self.details_table.setItem(row, 6, QTableWidgetItem(str(last_order) if last_order else "N/A"))
        
        elif report_type == "delivery_tracking":
            deliveries = data.get('deliveries', [])
            self.details_table.setColumnCount(9)
            self.details_table.setHorizontalHeaderLabels(["Order", "Customer", "Item Code", "Item Name", "Quantity", "Weight/Unit (kg)", "Total Weight (kg)", "Delivery Date", "Status"])
            self.details_table.setRowCount(len(deliveries))
            
            for row, delivery in enumerate(deliveries):
                self.details_table.setItem(row, 0, QTableWidgetItem(delivery['order_number']))
                self.details_table.setItem(row, 1, QTableWidgetItem(delivery['customer']))
                self.details_table.setItem(row, 2, QTableWidgetItem(delivery['item_code']))
                self.details_table.setItem(row, 3, QTableWidgetItem(delivery['item_name']))
                self.details_table.setItem(row, 4, QTableWidgetItem(str(delivery['quantity'])))
                self.details_table.setItem(row, 5, QTableWidgetItem(f"{delivery['weight_per_unit']:.3f}" if delivery['weight_per_unit'] > 0 else "N/A"))
                self.details_table.setItem(row, 6, QTableWidgetItem(f"{delivery['total_weight']:.3f}" if delivery['total_weight'] > 0 else "N/A"))
                self.details_table.setItem(row, 7, QTableWidgetItem(str(delivery['delivery_date'])))
                self.details_table.setItem(row, 8, QTableWidgetItem(delivery['status']))
        
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
        
        elif report_type == "prices_by_customer":
            order_prices = data.get('order_prices', [])
            product_id = data.get('product_id')
            target_currency = data.get('target_currency', 'EUR')
            
            # Adjust column count and headers based on whether a product is selected
            if product_id:
                self.details_table.setColumnCount(11)
                self.details_table.setHorizontalHeaderLabels([
                    "Customer", "Currency", "Order Number", "Order Date", "Item Name", 
                    "Item Code", "Quantity", "Unit Price (Original)", f"Unit Price ({target_currency})", "Total Price (Original)", f"Total Price ({target_currency})"
                ])
            else:
                self.details_table.setColumnCount(12)
                self.details_table.setHorizontalHeaderLabels([
                    "Customer", "Currency", "Order Number", "Order Date", "Product", "Item Name", 
                    "Item Code", "Quantity", "Unit Price (Original)", f"Unit Price ({target_currency})", "Total Price (Original)", f"Total Price ({target_currency})"
                ])
            
            self.details_table.setRowCount(len(order_prices))
            
            for row, price_data in enumerate(order_prices):
                col = 0
                self.details_table.setItem(row, col, QTableWidgetItem(price_data['customer']))
                col += 1
                self.details_table.setItem(row, col, QTableWidgetItem(price_data['customer_currency']))
                col += 1
                self.details_table.setItem(row, col, QTableWidgetItem(price_data['order_number']))
                col += 1
                self.details_table.setItem(row, col, QTableWidgetItem(price_data['order_date']))
                col += 1
                
                # Only show product column if no specific product is selected
                if not product_id:
                    self.details_table.setItem(row, col, QTableWidgetItem(price_data['product']))
                    col += 1
                
                self.details_table.setItem(row, col, QTableWidgetItem(price_data['item_name']))
                col += 1
                self.details_table.setItem(row, col, QTableWidgetItem(price_data['item_code']))
                col += 1
                self.details_table.setItem(row, col, QTableWidgetItem(str(price_data['quantity'])))
                col += 1
                self.details_table.setItem(row, col, QTableWidgetItem(f"{price_data['unit_price_original']:,.2f} {price_data['customer_currency']}"))
                col += 1
                self.details_table.setItem(row, col, QTableWidgetItem(f"{price_data['unit_price_target']:,.2f} {target_currency}"))
                col += 1
                self.details_table.setItem(row, col, QTableWidgetItem(f"{price_data['total_price_original']:,.2f} {price_data['customer_currency']}"))
                col += 1
                self.details_table.setItem(row, col, QTableWidgetItem(f"{price_data['total_price_target']:,.2f} {target_currency}"))
        
        elif report_type == "component_requirements":
            split_by_month = data.get('split_by_month', False)
            split_by_surface_treatment = data.get('split_by_surface_treatment', False)
            currency = data.get('currency', 'EUR')
            
            if split_by_surface_treatment:
                surface_treatment_requirements = data.get('surface_treatment_requirements', {})
                
                # Calculate total rows needed (sum of components across all surface treatments)
                total_rows = 0
                for treatment_data in surface_treatment_requirements.values():
                    total_rows += len(treatment_data['requirements'])
                
                self.details_table.setColumnCount(7)
                self.details_table.setHorizontalHeaderLabels([
                    "Surface Treatment", "Component", "Category", "Description", f"Unit Cost ({currency})", "Total Required", f"Total Cost ({currency})"
                ])
                self.details_table.setRowCount(total_rows)
                
                row = 0
                # Sort surface treatments alphabetically
                sorted_treatments = sorted(surface_treatment_requirements.items())
                
                for surface_treatment, treatment_data in sorted_treatments:
                    treatment_requirements = treatment_data['requirements']
                    
                    # Sort components by total cost for this treatment
                    sorted_components = sorted(treatment_requirements.items(), key=lambda x: x[1]['total_cost'], reverse=True)
                    
                    for component_name, comp_data in sorted_components:
                        component = comp_data['component']
                        
                        self.details_table.setItem(row, 0, QTableWidgetItem(surface_treatment))
                        self.details_table.setItem(row, 1, QTableWidgetItem(component_name))
                        self.details_table.setItem(row, 2, QTableWidgetItem(component.get('category') or ""))
                        self.details_table.setItem(row, 3, QTableWidgetItem(component.get('description') or ""))
                        self.details_table.setItem(row, 4, QTableWidgetItem(f"{comp_data['unit_cost']:,.2f}"))
                        self.details_table.setItem(row, 5, QTableWidgetItem(f"{comp_data['total_required']:,.2f}"))
                        self.details_table.setItem(row, 6, QTableWidgetItem(f"{comp_data['total_cost']:,.2f}"))
                        
                        row += 1
            elif split_by_month:
                monthly_requirements = data.get('monthly_requirements', {})
                
                # Calculate total rows needed (sum of components across all months)
                total_rows = 0
                for month_data in monthly_requirements.values():
                    total_rows += len(month_data['requirements'])
                
                self.details_table.setColumnCount(7)
                self.details_table.setHorizontalHeaderLabels([
                    "Month", "Component", "Category", "Description", f"Unit Cost ({currency})", "Total Required", f"Total Cost ({currency})"
                ])
                self.details_table.setRowCount(total_rows)
                
                row = 0
                # Sort months chronologically
                sorted_months = sorted(monthly_requirements.items())
                
                for month_key, month_data in sorted_months:
                    month_name = month_data['month_name']
                    month_requirements = month_data['requirements']
                    
                    # Sort components by total cost for this month
                    sorted_components = sorted(month_requirements.items(), key=lambda x: x[1]['total_cost'], reverse=True)
                    
                    for component_name, comp_data in sorted_components:
                        component = comp_data['component']
                        self.details_table.setItem(row, 0, QTableWidgetItem(month_name))
                        self.details_table.setItem(row, 1, QTableWidgetItem(component_name))
                        self.details_table.setItem(row, 2, QTableWidgetItem(component.get('category') or ""))
                        self.details_table.setItem(row, 3, QTableWidgetItem(component.get('description') or ""))
                        self.details_table.setItem(row, 4, QTableWidgetItem(f"{comp_data['unit_cost']:.2f}"))
                        self.details_table.setItem(row, 5, QTableWidgetItem(f"{comp_data['total_required']:.2f}"))
                        self.details_table.setItem(row, 6, QTableWidgetItem(f"{comp_data['total_cost']:.2f}"))
                        row += 1
            else:
                component_requirements = data.get('component_requirements', {})
                self.details_table.setColumnCount(6)
                self.details_table.setHorizontalHeaderLabels([
                    "Component", "Category", "Description", f"Unit Cost ({currency})", "Total Required", f"Total Cost ({currency})"
                ])
                self.details_table.setRowCount(len(component_requirements))
                
                # Sort components by total cost
                sorted_components = sorted(component_requirements.items(), key=lambda x: x[1]['total_cost'], reverse=True)
                
                for row, (component_name, comp_data) in enumerate(sorted_components):
                    component = comp_data['component']
                    self.details_table.setItem(row, 0, QTableWidgetItem(component_name))
                    self.details_table.setItem(row, 1, QTableWidgetItem(component.get('category') or ""))
                    self.details_table.setItem(row, 2, QTableWidgetItem(component.get('description') or ""))
                    self.details_table.setItem(row, 3, QTableWidgetItem(f"{comp_data['unit_cost']:.2f}"))
                    self.details_table.setItem(row, 4, QTableWidgetItem(f"{comp_data['total_required']:.2f}"))
                    self.details_table.setItem(row, 5, QTableWidgetItem(f"{comp_data['total_cost']:.2f}"))
        
        elif report_type == "stock_analysis":
            stock_analysis = data.get('stock_analysis', [])
            self.details_table.setColumnCount(7)
            self.details_table.setHorizontalHeaderLabels(["Component", "Category", "Description", "Current Stock", "Minimum Stock", "Available After Orders", "Status"])
            self.details_table.setRowCount(len(stock_analysis))
            
            for row, item in enumerate(stock_analysis):
                self.details_table.setItem(row, 0, QTableWidgetItem(item['component'].description or "N/A"))
                self.details_table.setItem(row, 1, QTableWidgetItem(item['category']))
                self.details_table.setItem(row, 2, QTableWidgetItem(item['component'].description or "N/A"))
                self.details_table.setItem(row, 3, QTableWidgetItem(f"{item['current_stock']} {item['unit']}"))
                self.details_table.setItem(row, 4, QTableWidgetItem(f"{item['minimum_stock']} {item['unit']}"))
                self.details_table.setItem(row, 5, QTableWidgetItem(f"{item['available_after_orders']:.2f} {item['unit']}"))
                self.details_table.setItem(row, 6, QTableWidgetItem(item['stock_status']))
        
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
            
            elif report_type == "prices_by_customer":
                df = pd.DataFrame(self.current_report_data.get('order_prices', []))
            
            elif report_type == "component_requirements":
                split_by_month = self.current_report_data.get('split_by_month', False)
                split_by_surface_treatment = self.current_report_data.get('split_by_surface_treatment', False)
                currency = self.current_report_data.get('currency', 'EUR')
                
                if split_by_surface_treatment:
                    surface_treatment_requirements = self.current_report_data.get('surface_treatment_requirements', {})
                    export_data = []
                    
                    # Sort surface treatments alphabetically
                    sorted_treatments = sorted(surface_treatment_requirements.items())
                    
                    for surface_treatment, treatment_data in sorted_treatments:
                        treatment_requirements = treatment_data['requirements']
                        
                        # Sort components by total cost for this treatment
                        sorted_components = sorted(treatment_requirements.items(), key=lambda x: x[1]['total_cost'], reverse=True)
                        
                        for component_name, comp_data in sorted_components:
                            component = comp_data['component']
                            export_data.append({
                                'Surface Treatment': surface_treatment,
                                'Component': component_name,
                                'Category': component.get('category') or "",
                                'Description': component.get('description') or "",
                                f'Unit Cost ({currency})': comp_data['unit_cost'],
                                'Total Required': comp_data['total_required'],
                                f'Total Cost ({currency})': comp_data['total_cost']
                            })
                    
                    df = pd.DataFrame(export_data)
                elif split_by_month:
                    monthly_requirements = self.current_report_data.get('monthly_requirements', {})
                    export_data = []
                    
                    # Sort months chronologically
                    sorted_months = sorted(monthly_requirements.items())
                    
                    for month_key, month_data in sorted_months:
                        month_name = month_data['month_name']
                        month_requirements = month_data['requirements']
                        
                        # Sort components by total cost for this month
                        sorted_components = sorted(month_requirements.items(), key=lambda x: x[1]['total_cost'], reverse=True)
                        
                        for component_name, comp_data in sorted_components:
                            component = comp_data['component']
                            export_data.append({
                                'Month': month_name,
                                'Component': component_name,
                                'Category': component.get('category') or "",
                                'Description': component.get('description') or "",
                                f'Unit Cost ({currency})': comp_data['unit_cost'],
                                'Total Required': comp_data['total_required'],
                                f'Total Cost ({currency})': comp_data['total_cost']
                            })
                    
                    df = pd.DataFrame(export_data)
                else:
                    component_requirements = self.current_report_data.get('component_requirements', {})
                    export_data = []
                    
                    for component_name, comp_data in component_requirements.items():
                        component = comp_data['component']
                        export_data.append({
                            'Component': component_name,
                            'Category': component.get('category') or "",
                            'Description': component.get('description') or "",
                            f'Unit Cost ({currency})': comp_data['unit_cost'],
                            'Total Required': comp_data['total_required'],
                            f'Total Cost ({currency})': comp_data['total_cost']
                        })
                    
                    df = pd.DataFrame(export_data)
            
            elif report_type == "stock_analysis":
                stock_analysis = self.current_report_data.get('stock_analysis', [])
                export_data = []
                
                for item in stock_analysis:
                    export_data.append({
                        'Component': item['component'].description or "N/A",
                        'Category': item['category'],
                        'Description': item['component'].description or "N/A",
                        'Current Stock': f"{item['current_stock']} {item['unit']}",
                        'Minimum Stock': f"{item['minimum_stock']} {item['unit']}",
                        'Available After Orders': f"{item['available_after_orders']:.2f} {item['unit']}",
                        'Status': item['stock_status']
                    })
                
                df = pd.DataFrame(export_data)
            
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