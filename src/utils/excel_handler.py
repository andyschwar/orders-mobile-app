import pandas as pd
from typing import List, Dict, Any
import xlrd
import openpyxl
from datetime import datetime
from sqlalchemy.orm import Session
from models.database import Customer, Product, Item, Employee, Component, Order, OrderItem

class ExcelHandler:
    @staticmethod
    def read_excel(file_path: str) -> pd.DataFrame:
        """
        Read an Excel file and return a pandas DataFrame.
        Supports .xlsx, .xlsm, and .xls formats.
        """
        try:
            if file_path.endswith('.xls'):
                # For older .xls files
                return pd.read_excel(file_path, engine='xlrd')
            else:
                # For .xlsx and .xlsm files
                return pd.read_excel(file_path, engine='openpyxl')
        except Exception as e:
            raise Exception(f"Error reading Excel file: {str(e)}")

    @staticmethod
    def import_customers(session: Session, file_path: str) -> List[Dict[str, Any]]:
        """
        Import customers from Excel file
        Required columns:
        - name: Customer name
        - name_index: Index for sorting/reference
        Optional columns:
        - street: Street address
        - city: City
        - country: Country
        - email1: Primary email
        - email2: Secondary email
        - email3: Third email
        - atest_email: Email for test certificates
        - invoice_email: Email for invoices
        - ico_vat: VAT identification number
        - ic_dph: Tax identification number
        - currency: Currency code (default: EUR)
        - is_eu: EU status (1/0 or True/False)
        - delivery_address: Delivery address
        """
        df = ExcelHandler.read_excel(file_path)
        required_columns = ['name']
        
        if not all(col in df.columns for col in required_columns):
            raise ValueError("Missing required column 'name' in customer Excel file")
        
        results = []
        for _, row in df.iterrows():
            try:
                # Convert is_eu to boolean if present
                is_eu = False
                if 'is_eu' in df.columns:
                    is_eu_val = row['is_eu']
                    if isinstance(is_eu_val, bool):
                        is_eu = is_eu_val
                    elif isinstance(is_eu_val, (int, float)):
                        is_eu = bool(is_eu_val)
                    elif isinstance(is_eu_val, str):
                        is_eu = is_eu_val.lower() in ('true', '1', 't', 'yes')

                customer = Customer(
                    name=row['name'],
                    name_index=row.get('name_index', ''),
                    street=row.get('street', ''),
                    city=row.get('city', ''),
                    country=row.get('country', ''),
                    email1=row.get('email1', ''),
                    email2=row.get('email2', ''),
                    email3=row.get('email3', ''),
                    atest_email=row.get('atest_email', ''),
                    invoice_email=row.get('invoice_email', ''),
                    ico_vat=row.get('ico_vat', ''),
                    ic_dph=row.get('ic_dph', ''),
                    currency=row.get('currency', 'EUR'),
                    is_eu=is_eu,
                    delivery_address=row.get('delivery_address', '')
                )
                session.add(customer)
                results.append({
                    'name': customer.name,
                    'status': 'imported'
                })
            except Exception as e:
                results.append({
                    'name': row.get('name', 'Unknown'),
                    'status': 'error',
                    'message': str(e)
                })
        
        session.commit()
        return results

    @staticmethod
    def import_products(session: Session, file_path: str) -> List[Dict[str, Any]]:
        """
        Import products from Excel file
        Required columns:
        - name: Product name
        Optional columns:
        - description: Product description
        - weight_per_unit: Weight per unit in kg
        """
        df = ExcelHandler.read_excel(file_path)
        required_columns = ['name']
        
        if not all(col in df.columns for col in required_columns):
            raise ValueError("Missing required column 'name' in product Excel file")
        
        results = []
        for _, row in df.iterrows():
            try:
                product = Product(
                    name=row['name'],
                    description=row.get('description', ''),
                    weight_per_unit=float(row['weight_per_unit']) if pd.notna(row.get('weight_per_unit')) else None
                )
                session.add(product)
                results.append({
                    'name': product.name,
                    'status': 'imported'
                })
            except Exception as e:
                results.append({
                    'name': row.get('name', 'Unknown'),
                    'status': 'error',
                    'message': str(e)
                })
        
        session.commit()
        return results

    @staticmethod
    def import_items(session: Session, file_path: str) -> List[Dict[str, Any]]:
        """
        Import items from Excel file
        Required columns:
        - customer_index: Customer's name index
        - product_name: Product name
        - customer_code: Customer's code for the item
        Optional columns:
        - customer_item_name: Customer's name for the item
        - type: Item type
        - similar_item: Similar item reference
        """
        df = ExcelHandler.read_excel(file_path)
        required_columns = ['customer_index', 'product_name', 'customer_code']
        
        if not all(col in df.columns for col in required_columns):
            raise ValueError("Missing required columns in item Excel file")
        
        results = []
        for _, row in df.iterrows():
            try:
                customer = session.query(Customer).filter_by(name_index=row['customer_index']).first()
                product = session.query(Product).filter_by(name=row['product_name']).first()
                
                if customer and product:
                    item = Item(
                        customer_id=customer.id,
                        product_id=product.id,
                        customer_code=row['customer_code'],
                        customer_item_name=row.get('customer_item_name', ''),
                        item_type=row.get('type', ''),
                        similar_item=row.get('similar_item', '')
                    )
                    session.add(item)
                    results.append({
                        'customer_code': item.customer_code,
                        'status': 'imported'
                    })
                else:
                    results.append({
                        'customer_code': row['customer_code'],
                        'status': 'error',
                        'message': 'Customer or product not found'
                    })
            except Exception as e:
                results.append({
                    'customer_code': row.get('customer_code', 'Unknown'),
                    'status': 'error',
                    'message': str(e)
                })
        
        session.commit()
        return results

    @staticmethod
    def import_orders(session: Session, file_path: str) -> List[Dict[str, Any]]:
        """
        Import orders from Excel file
        Required columns:
        - customer_index: Customer's name index
        - order_number: Order number/reference
        - order_date: Order date (YYYY-MM-DD)
        Optional columns:
        - delivery_date: Expected delivery date (YYYY-MM-DD)
        - status: Order status
        - notes: Additional notes
        """
        df = ExcelHandler.read_excel(file_path)
        required_columns = ['customer_index', 'order_number', 'order_date']
        
        if not all(col in df.columns for col in required_columns):
            raise ValueError("Missing required columns in order Excel file")
        
        results = []
        for _, row in df.iterrows():
            try:
                customer = session.query(Customer).filter_by(name_index=row['customer_index']).first()
                
                if customer:
                    # Convert dates
                    order_date = pd.to_datetime(row['order_date']).date() if pd.notna(row['order_date']) else None
                    delivery_date = pd.to_datetime(row['delivery_date']).date() if pd.notna(row.get('delivery_date')) else None
                    
                    order = Order(
                        customer_id=customer.id,
                        order_number=row['order_number'],
                        order_date=order_date,
                        delivery_date=delivery_date,
                        status=row.get('status', ''),
                        notes=row.get('notes', '')
                    )
                    session.add(order)
                    results.append({
                        'order_number': order.order_number,
                        'status': 'imported'
                    })
                else:
                    results.append({
                        'order_number': row['order_number'],
                        'status': 'error',
                        'message': 'Customer not found'
                    })
            except Exception as e:
                results.append({
                    'order_number': row.get('order_number', 'Unknown'),
                    'status': 'error',
                    'message': str(e)
                })
        
        session.commit()
        return results

    @staticmethod
    def import_order_items(session: Session, file_path: str) -> List[Dict[str, Any]]:
        """
        Import order items from Excel file
        Required columns:
        - order_number: Order number/reference
        - item_code: Customer's item code
        - quantity: Quantity ordered
        Optional columns:
        - price: Price per unit
        - notes: Additional notes
        """
        df = ExcelHandler.read_excel(file_path)
        required_columns = ['order_number', 'item_code', 'quantity']
        
        if not all(col in df.columns for col in required_columns):
            raise ValueError("Missing required columns in order items Excel file")
        
        results = []
        for _, row in df.iterrows():
            try:
                order = session.query(Order).filter_by(order_number=row['order_number']).first()
                item = session.query(Item).filter_by(customer_code=row['item_code']).first()
                
                if order and item:
                    order_item = OrderItem(
                        order_id=order.id,
                        item_id=item.id,
                        quantity=float(row['quantity']),
                        price=float(row['price']) if pd.notna(row.get('price')) else None,
                        notes=row.get('notes', '')
                    )
                    session.add(order_item)
                    results.append({
                        'item_code': row['item_code'],
                        'status': 'imported'
                    })
                else:
                    results.append({
                        'item_code': row['item_code'],
                        'status': 'error',
                        'message': 'Order or item not found'
                    })
            except Exception as e:
                results.append({
                    'item_code': row.get('item_code', 'Unknown'),
                    'status': 'error',
                    'message': str(e)
                })
        
        session.commit()
        return results

    @staticmethod
    def import_employees(session: Session, file_path: str) -> List[Dict[str, Any]]:
        """
        Import employees from Excel file
        Required columns:
        - name: Employee name
        Optional columns:
        - email: Email address
        - phone: Phone number
        - address: Physical address
        - birthday: Birth date (YYYY-MM-DD)
        - name_day: Name day (YYYY-MM-DD)
        - is_active: Active status (True/False or 1/0)
        """
        df = ExcelHandler.read_excel(file_path)
        required_columns = ['name']
        
        if not all(col in df.columns for col in required_columns):
            raise ValueError("Missing required column 'name' in employee Excel file")
        
        results = []
        for _, row in df.iterrows():
            try:
                # Convert birthday and name_day to proper date objects if present
                birthday = None
                if 'birthday' in df.columns and pd.notna(row['birthday']):
                    try:
                        birthday = pd.to_datetime(row['birthday']).date()
                    except:
                        pass
                
                name_day = None
                if 'name_day' in df.columns and pd.notna(row['name_day']):
                    try:
                        name_day = pd.to_datetime(row['name_day']).date()
                    except:
                        pass
                
                # Convert is_active to boolean if present
                is_active = True
                if 'is_active' in df.columns:
                    is_active_val = row['is_active']
                    if isinstance(is_active_val, bool):
                        is_active = is_active_val
                    elif isinstance(is_active_val, (int, float)):
                        is_active = bool(is_active_val)
                    elif isinstance(is_active_val, str):
                        is_active = is_active_val.lower() in ('true', '1', 'yes', 'y')
                
                employee = Employee(
                    name=row['name'],
                    address=row.get('address', ''),
                    phone=row.get('phone', ''),
                    email=row.get('email', ''),
                    birthday=birthday,
                    name_day=name_day,
                    is_active=is_active
                )
                session.add(employee)
                results.append({
                    'name': employee.name,
                    'status': 'imported'
                })
            except Exception as e:
                results.append({
                    'name': row.get('name', 'Unknown'),
                    'status': 'error',
                    'message': str(e)
                })
        
        session.commit()
        return results

    @staticmethod
    def import_components(session: Session, file_path: str) -> List[Dict[str, Any]]:
        """
        Import components from Excel file
        Required columns:
        - name: Component name
        Optional columns:
        - description: Component description
        """
        df = ExcelHandler.read_excel(file_path)
        required_columns = ['name']
        
        if not all(col in df.columns for col in required_columns):
            raise ValueError("Missing required columns in components Excel file")
        
        results = []
        for _, row in df.iterrows():
            try:
                component = Component(
                    name=row['name'],
                    description=row.get('description', '')
                )
                session.add(component)
                results.append({
                    'name': component.name,
                    'status': 'imported'
                })
            except Exception as e:
                results.append({
                    'name': row.get('name', 'Unknown'),
                    'status': 'error',
                    'message': str(e)
                })
        
        session.commit()
        return results 