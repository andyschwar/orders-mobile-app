import pandas as pd
from sqlalchemy.orm import Session
from models.database import Customer, Item, Product, OrderItem, Employee, Order, Delivery, Component, ProductComponent, Material, ComponentMaterial
from datetime import datetime
import numpy as np
from PyQt6.QtWidgets import QMessageBox
import logging

logger = logging.getLogger(__name__)

def determine_component_type(name, row):
    """Determine component type based on price logic"""
    
    # Get price values, defaulting to 0 if not present or NaN
    buy_price = float(row.get('buy_price', 0)) if pd.notna(row.get('buy_price', 0)) else 0.0
    manufacturing_price = float(row.get('manufacturing_price', 0)) if pd.notna(row.get('manufacturing_price', 0)) else 0.0
    material_price = float(row.get('material_price', 0)) if pd.notna(row.get('material_price', 0)) else 0.0
    surface_treatment_price = float(row.get('surface_treatment_price', 0)) if pd.notna(row.get('surface_treatment_price', 0)) else 0.0
    
    # Calculate total cost
    total_cost = buy_price + material_price + manufacturing_price + surface_treatment_price
    
    # Your logic:
    # 1. If total cost is 0, then "to review"
    if total_cost == 0:
        return 'to review'
    
    # 2. If buy price is 0, then "manufactured"
    if buy_price == 0:
        return 'manufactured'
    
    # 3. If buy price is more than 0, look at manufacturing price
    if buy_price > 0:
        if manufacturing_price == 0:
            return 'bought'
        else:
            return 'outsourced'
    
    # Fallback (shouldn't reach here with the above logic)
    return 'to review'

def clean_string(value):
    """Clean string values from Excel"""
    if pd.isna(value) or value is None:
        return None
    
    # Convert to string first
    str_value = str(value).strip()
    
    # Handle numeric values that might have .0 suffix
    if str_value.endswith('.0') and str_value.replace('.0', '').replace('-', '').replace('.', '').isdigit():
        # Remove .0 suffix for what appears to be an integer
        str_value = str_value[:-2]
    
    # Return empty string instead of None for empty strings
    return str_value if str_value else ""

def clean_date(value):
    """Convert Excel date to Python date"""
    if pd.isna(value) or value is None:
        return None
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            try:
                return datetime.strptime(value, "%d.%m.%Y").date()
            except ValueError:
                return None
    return value.date() if isinstance(value, datetime) else None

def clean_boolean(value):
    """Convert Excel boolean values"""
    if pd.isna(value) or value is None:
        return False
    if isinstance(value, str):
        return value.lower() in ['yes', 'true', '1', 'ano']
    return bool(value)

def clean_number(value):
    """Convert Excel numeric values"""
    if pd.isna(value) or value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def clean_name_day(value):
    """Convert Excel date to MM-DD string format"""
    if pd.isna(value) or value is None:
        return None
    if isinstance(value, str):
        try:
            # Try to parse as D.M. format with trailing dots (e.g., "1.1.")
            value = value.rstrip('.')  # Remove trailing dot only
            day, month = map(int, value.split('.'))  # Split by dots
            return f"{month:02d}-{day:02d}"
        except (ValueError, IndexError):
            try:
                # Try to parse as date string
                date_obj = datetime.strptime(value, "%Y-%m-%d").date()
                return f"{date_obj.month:02d}-{date_obj.day:02d}"
            except ValueError:
                try:
                    # Try to parse as DD.MM.YYYY format
                    date_obj = datetime.strptime(value, "%d.%m.%Y").date()
                    return f"{date_obj.month:02d}-{date_obj.day:02d}"
                except ValueError:
                    try:
                        # Try to parse as DD-MM format
                        month, day = map(int, value.split('-')[::-1])  # Split and reverse for DD-MM format
                        return f"{month:02d}-{day:02d}"
                    except (ValueError, IndexError):
                        return None
    if isinstance(value, datetime):
        return f"{value.month:02d}-{value.day:02d}"
    return None

def import_customers(session: Session, file_path: str, sheet_name: str = "Customers"):
    """Import customers from Excel - import new customers and update existing ones with new data"""
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        updated_customers = []
        
        for _, row in df.iterrows():
            name_index = clean_string(row.get('name_index'))
            name = clean_string(row.get('name'))
            
            if not name_index or not name:  # Skip customers without required fields
                skipped_count += 1
                continue
                
            # Check if customer already exists
            existing_customer = session.query(Customer).filter(
                Customer.name_index == name_index
            ).first()
            
            if existing_customer:
                # Update existing customer with new data
                has_changes = False
                
                # Check and update each field if new data is provided
                new_fields = {
                    'name': clean_string(row.get('name')),
                    'street': clean_string(row.get('street')),
                    'city': clean_string(row.get('city')),
                    'country': clean_string(row.get('country')),
                    'email1': clean_string(row.get('email1')),
                    'email2': clean_string(row.get('email2')),
                    'email3': clean_string(row.get('email3')),
                    'atest_email': clean_string(row.get('atest_email')),
                    'invoice_email': clean_string(row.get('invoice_email')),
                    'ico_vat': clean_string(row.get('ico_vat')),
                    'ic_dph': clean_string(row.get('ic_dph')),
                    'currency': clean_string(row.get('currency')),
                    'is_eu': clean_boolean(row.get('is_eu')),
                    'delivery_address': clean_string(row.get('delivery_address'))
                }
                
                # Update fields that have new data
                for field, new_value in new_fields.items():
                    if new_value is not None and new_value != getattr(existing_customer, field):
                        setattr(existing_customer, field, new_value)
                        has_changes = True
                
                if has_changes:
                    updated_customers.append({
                        'Name Index': name_index,
                        'Name': name,
                        'Status': 'Updated'
                    })
                    updated_count += 1
                else:
                    updated_customers.append({
                        'Name Index': name_index,
                        'Name': name,
                        'Status': 'No changes needed'
                    })
            else:
                # Create new customer
                customer = Customer(
                    name_index=name_index,
                    name=name,
                    street=clean_string(row.get('street')),
                    city=clean_string(row.get('city')),
                    country=clean_string(row.get('country')),
                    email1=clean_string(row.get('email1')),
                    email2=clean_string(row.get('email2')),
                    email3=clean_string(row.get('email3')),
                    atest_email=clean_string(row.get('atest_email')),
                    invoice_email=clean_string(row.get('invoice_email')),
                    ico_vat=clean_string(row.get('ico_vat')),
                    ic_dph=clean_string(row.get('ic_dph')),
                    currency=clean_string(row.get('currency')),
                    is_eu=clean_boolean(row.get('is_eu')),
                    delivery_address=clean_string(row.get('delivery_address'))
                )
                session.add(customer)
                imported_count += 1
            
        session.commit()
        
        # Print summary
        print(f"\n=== Customers Import Summary ===")
        print(f"✅ Imported: {imported_count} new customers")
        print(f"🔄 Updated: {updated_count} existing customers")
        print(f"⏭️  Skipped: {skipped_count} customers (invalid)")
        
        if updated_customers:
            print(f"\n📋 Customers processing details:")
            for customer in updated_customers[:5]:  # Show first 5
                if customer['Status'] == 'Updated':
                    print(f"   🔄 {customer['Name Index']} - {customer['Name']} - Updated")
                else:
                    print(f"   ✓ {customer['Name Index']} - {customer['Name']} - No changes needed")
            if len(updated_customers) > 5:
                print(f"   ... and {len(updated_customers) - 5} more customers")
            
            # Export updated customers to Excel for reference
            output_file = "customers_import_summary.xlsx"
            df_updated = pd.DataFrame(updated_customers)
            df_updated.to_excel(output_file, index=False)
            print(f"📄 Exported {len(updated_customers)} customers summary to {output_file}")
        
        return imported_count + updated_count
    except Exception as e:
        session.rollback()
        raise Exception(f"Error importing customers: {str(e)}")

def import_products(session: Session, file_path: str, sheet_name: str = "Products"):
    """Import products from Excel - import new products and update existing ones with new data"""
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        updated_products = []
        
        for _, row in df.iterrows():
            name = clean_string(row.get('name'))
            if not name:  # Skip products without a name
                skipped_count += 1
                continue
                
            # Always check for existing product with exact match first
            existing_product = session.query(Product).filter(Product.name == name).first()
            
            if existing_product:
                # Update existing product with new data
                new_description = clean_string(row.get('description'))
                new_weight = clean_number(row.get('weight_per_unit'))
                
                # Only update if there's new data
                has_changes = False
                if new_description and new_description != existing_product.description:
                    existing_product.description = new_description
                    has_changes = True
                if new_weight is not None and new_weight != existing_product.weight_per_unit:
                    existing_product.weight_per_unit = new_weight
                    has_changes = True
                
                if has_changes:
                    updated_products.append({
                        'Name': name,
                        'Status': 'Updated'
                    })
                    updated_count += 1
                else:
                    updated_products.append({
                        'Name': name,
                        'Status': 'No changes needed'
                    })
            else:
                # Create new product
                product = Product(
                    name=name,
                    description=clean_string(row.get('description')),
                    weight_per_unit=clean_number(row.get('weight_per_unit'))
                )
                session.add(product)
                imported_count += 1
            
        session.commit()
        
        # Print summary
        print(f"\n=== Products Import Summary ===")
        print(f"✅ Imported: {imported_count} new products")
        print(f"🔄 Updated: {updated_count} existing products")
        print(f"⏭️  Skipped: {skipped_count} products (invalid)")
        
        if updated_products:
            print(f"\n📋 Products processing details:")
            for product in updated_products[:5]:  # Show first 5
                if product['Status'] == 'Updated':
                    print(f"   🔄 {product['Name']} - Updated")
                else:
                    print(f"   ✓ {product['Name']} - No changes needed")
            if len(updated_products) > 5:
                print(f"   ... and {len(updated_products) - 5} more products")
            
            # Export updated products to Excel for reference
            output_file = "products_import_summary.xlsx"
            df_updated = pd.DataFrame(updated_products)
            df_updated.to_excel(output_file, index=False)
            print(f"📄 Exported {len(updated_products)} products summary to {output_file}")
        
        return imported_count + updated_count
    except Exception as e:
        session.rollback()
        raise Exception(f"Error importing products: {str(e)}")

def import_items(session: Session, file_path: str, sheet_name: str = "Items"):
    """Import items from Excel - only import new items, skip existing ones"""
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        imported_count = 0
        skipped_count = 0
        errors = []
        skipped_items = []
        existing_items = []
        
        for _, row in df.iterrows():
            customer_index = clean_string(row.get('customer_index'))
            product_name = clean_string(row.get('product_name'))
            customer_code = clean_string(row.get('customer_code'))
            customer_item_name = clean_string(row.get('customer_item_name'))
            item_type = clean_string(row.get('item_type'))
            similar_item = clean_string(row.get('similar_item'))
            
            # Check required fields
            if not customer_code:
                errors.append(f"Missing required customer_code for product: {product_name}")
                skipped_count += 1
                continue
                
            if not customer_index:
                errors.append(f"Missing required customer_index for item: {customer_code}")
                skipped_count += 1
                continue
                
            if not product_name:
                errors.append(f"Missing required product_name for item: {customer_code}")
                skipped_count += 1
                continue
            
            # Find related customer and product
            customer = session.query(Customer).filter(
                Customer.name_index == customer_index
            ).first()
            
            product = session.query(Product).filter(
                Product.name == product_name
            ).first()
            
            if not customer or not product:
                error_msg = ""
                if not customer:
                    error_msg = f"Customer not found with index: {customer_index}"
                if not product:
                    error_msg = f"Product not found with name: {product_name}"
                    
                errors.append(error_msg)
                skipped_items.append({
                    'Customer Index': customer_index,
                    'Product Name': product_name,
                    'Customer Code': customer_code,
                    'Customer Item Name': customer_item_name,
                    'Item Type': item_type,
                    'Similar Item': similar_item,
                    'Error': error_msg
                })
                skipped_count += 1
                continue
            
            # Check if item already exists
            existing_item = session.query(Item).filter(
                Item.customer_id == customer.id,
                Item.customer_code == customer_code
            ).first()
            
            if existing_item:
                # Update existing item with new data
                has_changes = False
                
                # Check and update each field if new data is provided
                new_product_id = product.id
                new_customer_item_name = customer_item_name
                new_item_type = item_type
                new_similar_item = similar_item
                
                if new_product_id != existing_item.product_id:
                    existing_item.product_id = new_product_id
                    has_changes = True
                if new_customer_item_name and new_customer_item_name != existing_item.customer_item_name:
                    existing_item.customer_item_name = new_customer_item_name
                    has_changes = True
                if new_item_type and new_item_type != existing_item.item_type:
                    existing_item.item_type = new_item_type
                    has_changes = True
                if new_similar_item and new_similar_item != existing_item.similar_item:
                    existing_item.similar_item = new_similar_item
                    has_changes = True
                
                if has_changes:
                    existing_items.append({
                        'Customer Index': customer_index,
                        'Product Name': product_name,
                        'Customer Code': customer_code,
                        'Customer Item Name': customer_item_name,
                        'Item Type': item_type,
                        'Similar Item': similar_item,
                        'Status': 'Updated'
                    })
                    imported_count += 1  # Count as imported since it was updated
                else:
                    existing_items.append({
                        'Customer Index': customer_index,
                        'Product Name': product_name,
                        'Customer Code': customer_code,
                        'Customer Item Name': customer_item_name,
                        'Item Type': item_type,
                        'Similar Item': similar_item,
                        'Status': 'No changes needed'
                    })
            else:
                # Create new item
                item = Item(
                    customer_id=customer.id,
                    product_id=product.id,
                    customer_code=customer_code,
                    customer_item_name=customer_item_name,
                    item_type=item_type,
                    similar_item=similar_item
                )
                session.add(item)
                imported_count += 1
            
        session.commit()
        
        # Print summary
        print(f"\n=== Items Import Summary ===")
        print(f"✅ Imported: {imported_count} items (new + updated)")
        print(f"⏭️  Skipped: {skipped_count} items (invalid)")
        
        if existing_items:
            print(f"\n📋 Items processing details:")
            updated_count = sum(1 for item in existing_items if item['Status'] == 'Updated')
            no_changes_count = sum(1 for item in existing_items if item['Status'] == 'No changes needed')
            
            if updated_count > 0:
                print(f"   🔄 {updated_count} items updated")
            if no_changes_count > 0:
                print(f"   ✓ {no_changes_count} items - no changes needed")
            
            # Show first few examples
            for item in existing_items[:5]:
                if item['Status'] == 'Updated':
                    print(f"   🔄 {item['Customer Index']} - {item['Customer Code']} ({item['Product Name']}) - Updated")
                else:
                    print(f"   ✓ {item['Customer Index']} - {item['Customer Code']} ({item['Product Name']}) - No changes")
            if len(existing_items) > 5:
                print(f"   ... and {len(existing_items) - 5} more items")
        
        if errors:
            print(f"\n❌ Errors encountered:")
            for error in errors[:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(errors) > 5:
                print(f"   ... and {len(errors) - 5} more errors")
            
            # Export skipped items to Excel
            if skipped_items:
                output_file = "skipped_items.xlsx"
                df_skipped = pd.DataFrame(skipped_items)
                df_skipped.to_excel(output_file, index=False)
                print(f"\n📄 Exported {len(skipped_items)} skipped items to {output_file}")
        
        # Export items summary to Excel for reference
        if existing_items:
            output_file = "items_import_summary.xlsx"
            df_existing = pd.DataFrame(existing_items)
            df_existing.to_excel(output_file, index=False)
            print(f"📄 Exported {len(existing_items)} items summary to {output_file}")
                
        return imported_count
    except Exception as e:
        session.rollback()
        raise Exception(f"Error importing items: {str(e)}")

def import_employees(session: Session, file_path: str, sheet_name: str = "Employees"):
    """Import employees from Excel - import new employees and update existing ones with new data"""
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        updated_employees = []
        
        for _, row in df.iterrows():
            name = clean_string(row.get('name'))
            if not name:  # Skip employees without a name
                skipped_count += 1
                continue
                
            # Check if employee already exists
            existing_employee = session.query(Employee).filter(
                Employee.name == name
            ).first()
            
            if existing_employee:
                # Update existing employee with new data
                has_changes = False
                
                # Check and update each field if new data is provided
                new_fields = {
                    'address': clean_string(row.get('address')),
                    'phone': clean_string(row.get('phone')),
                    'email': clean_string(row.get('email')),
                    'birthday': clean_date(row.get('birthday')),
                    'name_day': clean_name_day(row.get('name_day')),
                    'is_active': clean_boolean(row.get('is_active', True))
                }
                
                # Update fields that have new data
                for field, new_value in new_fields.items():
                    if new_value is not None and new_value != getattr(existing_employee, field):
                        setattr(existing_employee, field, new_value)
                        has_changes = True
                
                if has_changes:
                    updated_employees.append({
                        'Name': name,
                        'Status': 'Updated'
                    })
                    updated_count += 1
                else:
                    updated_employees.append({
                        'Name': name,
                        'Status': 'No changes needed'
                    })
            else:
                # Create new employee
                employee = Employee(
                    name=name,
                    address=clean_string(row.get('address')),
                    phone=clean_string(row.get('phone')),
                    email=clean_string(row.get('email')),
                    birthday=clean_date(row.get('birthday')),
                    name_day=clean_name_day(row.get('name_day')),
                    is_active=clean_boolean(row.get('is_active', True))
                )
                session.add(employee)
                imported_count += 1
            
        session.commit()
        
        # Print summary
        print(f"\n=== Employees Import Summary ===")
        print(f"✅ Imported: {imported_count} new employees")
        print(f"🔄 Updated: {updated_count} existing employees")
        print(f"⏭️  Skipped: {skipped_count} employees (invalid)")
        
        if updated_employees:
            print(f"\n📋 Employees processing details:")
            for employee in updated_employees[:5]:  # Show first 5
                if employee['Status'] == 'Updated':
                    print(f"   🔄 {employee['Name']} - Updated")
                else:
                    print(f"   ✓ {employee['Name']} - No changes needed")
            if len(updated_employees) > 5:
                print(f"   ... and {len(updated_employees) - 5} more employees")
            
            # Export updated employees to Excel for reference
            output_file = "employees_import_summary.xlsx"
            df_updated = pd.DataFrame(updated_employees)
            df_updated.to_excel(output_file, index=False)
            print(f"📄 Exported {len(updated_employees)} employees summary to {output_file}")
        
        return imported_count + updated_count
    except Exception as e:
        session.rollback()
        raise Exception(f"Error importing employees: {str(e)}")

def import_orders_and_items(session: Session, file_path: str, sheet_name: str = "Orders"):
    """Import orders and order items from Excel with delivery tracking"""
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        orders_count = 0
        items_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        # Group by order_number to process orders
        order_groups = df.groupby('order_number')
        
        for order_number, order_data in order_groups:
            order_number = clean_string(order_number)
            if not order_number:
                errors.append(f"Missing order number in row")
                skipped_count += 1
                continue
            
            # Check if order already exists
            existing_order = session.query(Order).filter(
                Order.order_number == order_number
            ).first()
            
            if existing_order:
                print(f"🔄 Updating existing order: {order_number}")
                # Update existing order
                customer_index = clean_string(order_data.iloc[0].get('customer_index'))
                order_date = clean_date(order_data.iloc[0].get('order_date'))
                
                if customer_index:
                    customer = session.query(Customer).filter(
                        Customer.name_index == customer_index
                    ).first()
                    if customer and customer.id != existing_order.customer_id:
                        existing_order.customer_id = customer.id
                
                if order_date and order_date != existing_order.order_date:
                    existing_order.order_date = order_date
                
                # Process order items for existing order
                for _, row in order_data.iterrows():
                    item_code = clean_string(row.get('item_code'))
                    if not item_code:
                        continue
                    
                    # Find the item
                    item = session.query(Item).filter(
                        Item.customer_code == item_code
                    ).first()
                    
                    if not item:
                        errors.append(f"Item not found: {item_code} for order {order_number}")
                        continue
                    
                    # Check if order item already exists
                    existing_order_item = session.query(OrderItem).filter(
                        OrderItem.order_id == existing_order.id,
                        OrderItem.item_id == item.id
                    ).first()
                    
                    if existing_order_item:
                        # Update existing order item
                        quantity = clean_number(row.get('quantity'))
                        price = clean_number(row.get('price'))
                        delivery_date = clean_date(row.get('delivery_date'))
                        delivered_quantity = clean_number(row.get('delivered_quantity', 0))
                        last_delivery_date = clean_date(row.get('last_delivery_date'))
                        surface_treatment = clean_string(row.get('surface_treatment'))
                        
                        if quantity is not None:
                            existing_order_item.quantity = quantity
                        if price is not None:
                            existing_order_item.price = price
                        if delivery_date:
                            existing_order_item.delivery_date = delivery_date
                        if delivered_quantity is not None:
                            existing_order_item.delivered_quantity = delivered_quantity
                        if last_delivery_date:
                            existing_order_item.last_delivery_date = last_delivery_date
                        
                        # Always update surface_treatment (can be empty string)
                        existing_order_item.surface_treatment = surface_treatment
                        
                        updated_count += 1
                    else:
                        # Create new order item
                        surface_treatment = clean_string(row.get('surface_treatment'))
                        order_item = OrderItem(
                            order_id=existing_order.id,
                            item_id=item.id,
                            quantity=clean_number(row.get('quantity')),
                            price=clean_number(row.get('price')),
                            delivery_date=clean_date(row.get('delivery_date')),
                            delivered_quantity=clean_number(row.get('delivered_quantity', 0)),
                            surface_treatment=surface_treatment
                        )
                        
                        session.add(order_item)
                        items_count += 1
            else:
                # Create new order
                customer_index = clean_string(order_data.iloc[0].get('customer_index'))
                order_date = clean_date(order_data.iloc[0].get('order_date'))
                
                if not customer_index:
                    errors.append(f"Missing customer index for order {order_number}")
                    skipped_count += 1
                    continue
                
                if not order_date:
                    errors.append(f"Missing order date for order {order_number}")
                    skipped_count += 1
                    continue
                
                customer = session.query(Customer).filter(
                    Customer.name_index == customer_index
                ).first()
                
                if not customer:
                    errors.append(f"Customer not found: {customer_index} for order {order_number}")
                    skipped_count += 1
                    continue
                
                new_order = Order(
                    customer_id=customer.id,
                    order_number=order_number,
                    order_date=order_date
                )
                session.add(new_order)
                session.flush()  # Get the order ID
                orders_count += 1
                
                print(f"✅ Created new order: {order_number} for {customer.name}")
                
                # Process order items for new order
                for _, row in order_data.iterrows():
                    item_code = clean_string(row.get('item_code'))
                    if not item_code:
                        continue
                    
                    # Find the item
                    item = session.query(Item).filter(
                        Item.customer_code == item_code
                    ).first()
                    
                    if not item:
                        errors.append(f"Item not found: {item_code} for order {order_number}")
                        continue
                    
                    # Create new order item
                    surface_treatment = clean_string(row.get('surface_treatment'))
                    order_item = OrderItem(
                        order_id=new_order.id,
                        item_id=item.id,
                        quantity=clean_number(row.get('quantity')),
                        price=clean_number(row.get('price')),
                        delivery_date=clean_date(row.get('delivery_date')),
                        delivered_quantity=clean_number(row.get('delivered_quantity', 0)),
                        surface_treatment=surface_treatment
                    )
                    
                    session.add(order_item)
                    items_count += 1
        
        session.commit()
        
        # Print summary
        print(f"\n=== Orders & Order Items Import Summary ===")
        print(f"✅ New orders: {orders_count}")
        print(f"✅ New order items: {items_count}")
        print(f"🔄 Updated order items: {updated_count}")
        print(f"⏭️  Skipped: {skipped_count}")
        
        if errors:
            print(f"\n❌ Errors encountered:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"   - {error}")
            if len(errors) > 10:
                print(f"   ... and {len(errors) - 10} more errors")
            
            # Export errors to Excel
            if errors:
                output_file = "order_import_errors.xlsx"
                df_errors = pd.DataFrame({'Error': errors})
                df_errors.to_excel(output_file, index=False)
                print(f"\n📄 Exported {len(errors)} errors to {output_file}")
        
        return orders_count, items_count + updated_count
    except Exception as e:
        session.rollback()
        raise Exception(f"Error importing orders and items: {str(e)}")

def import_new_orders_only(session: Session, file_path: str, sheet_name: str = "Orders"):
    """Import only new orders from Excel - skip existing orders completely"""
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        orders_count = 0
        items_count = 0
        skipped_count = 0
        errors = []
        
        # Group by order_number to process orders
        order_groups = df.groupby('order_number')
        
        for order_number, order_data in order_groups:
            order_number = clean_string(order_number)
            if not order_number:
                errors.append(f"Missing order number in row")
                skipped_count += 1
                continue
            
            # Check if order already exists - SKIP if it does
            existing_order = session.query(Order).filter(
                Order.order_number == order_number
            ).first()
            
            if existing_order:
                print(f"⏭️  Skipping existing order: {order_number}")
                skipped_count += 1
                continue
            
            # Create new order only
            customer_index = clean_string(order_data.iloc[0].get('customer_index'))
            order_date = clean_date(order_data.iloc[0].get('order_date'))
            
            if not customer_index:
                errors.append(f"Missing customer index for order {order_number}")
                skipped_count += 1
                continue
            
            if not order_date:
                errors.append(f"Missing order date for order {order_number}")
                skipped_count += 1
                continue
            
            customer = session.query(Customer).filter(
                Customer.name_index == customer_index
            ).first()
            
            if not customer:
                errors.append(f"Customer not found: {customer_index} for order {order_number}")
                skipped_count += 1
                continue
            
            new_order = Order(
                customer_id=customer.id,
                order_number=order_number,
                order_date=order_date
            )
            session.add(new_order)
            session.flush()  # Get the order ID
            orders_count += 1
            
            print(f"✅ Created new order: {order_number} for {customer.name}")
            
            # Process order items for new order
            for _, row in order_data.iterrows():
                item_code = clean_string(row.get('item_code'))
                if not item_code:
                    continue
                
                # Find the item
                item = session.query(Item).filter(
                    Item.customer_code == item_code
                ).first()
                
                if not item:
                    errors.append(f"Item not found: {item_code} for order {order_number}")
                    continue
                
                # Create new order item
                surface_treatment = clean_string(row.get('surface_treatment'))
                order_item = OrderItem(
                    order_id=new_order.id,
                    item_id=item.id,
                    quantity=clean_number(row.get('quantity')),
                    price=clean_number(row.get('price')),
                    delivery_date=clean_date(row.get('delivery_date')),
                    delivered_quantity=clean_number(row.get('delivered_quantity', 0)),
                    surface_treatment=surface_treatment
                )
                
                session.add(order_item)
                items_count += 1
        
        session.commit()
        
        # Print summary
        print(f"\n=== New Orders Import Summary ===")
        print(f"✅ New orders created: {orders_count}")
        print(f"✅ New order items created: {items_count}")
        print(f"⏭️  Skipped (existing orders): {skipped_count}")
        
        if errors:
            print(f"\n❌ Errors encountered:")
            for error in errors:
                print(f"   - {error}")
        
        return orders_count, items_count
        
    except Exception as e:
        session.rollback()
        raise Exception(f"Error importing new orders: {str(e)}")

def import_deliveries(session: Session, file_path: str, sheet_name: str = "Deliveries"):
    """
    Import deliveries from Excel file.
    
    Expected columns:
    - order_number: Order number
    - customer_code: Customer item code
    - planned_delivery_date: Planned delivery date from order (YYYY-MM-DD)
    - actual_delivery_date: Actual delivery date (YYYY-MM-DD)
    - quantity: Quantity delivered
    - notes: Optional notes about the delivery
    """
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        # Validate required columns
        required_columns = ['order_number', 'customer_code', 'planned_delivery_date', 'actual_delivery_date', 'quantity']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return {
                'success': False,
                'message': f"Missing required columns: {', '.join(missing_columns)}",
                'imported': 0,
                'skipped': 0,
                'errors': []
            }
        
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                order_number = clean_string(row['order_number'])
                customer_code = clean_string(row['customer_code'])
                planned_delivery_date_str = clean_string(row['planned_delivery_date'])
                actual_delivery_date_str = clean_string(row['actual_delivery_date'])
                quantity = clean_number(row['quantity'])
                
                # Handle optional notes field
                notes = None
                if 'notes' in df.columns:
                    notes_value = row.get('notes')
                    if pd.notna(notes_value) and str(notes_value).strip():
                        notes = clean_string(notes_value)
                
                if not order_number or not customer_code or quantity is None:
                    errors.append(f"Row {index + 2}: Missing required data")
                    continue
                
                # Parse planned delivery date
                try:
                    if pd.isna(planned_delivery_date_str) or planned_delivery_date_str == 'nan':
                        errors.append(f"Row {index + 2}: Missing planned delivery date")
                        continue
                    else:
                        planned_delivery_date = pd.to_datetime(planned_delivery_date_str).date()
                except:
                    errors.append(f"Row {index + 2}: Invalid planned delivery date format")
                    continue
                
                # Parse actual delivery date
                try:
                    if pd.isna(actual_delivery_date_str) or actual_delivery_date_str == 'nan':
                        actual_delivery_date = planned_delivery_date  # Use planned date if actual is empty
                    else:
                        actual_delivery_date = pd.to_datetime(actual_delivery_date_str).date()
                except:
                    actual_delivery_date = planned_delivery_date  # Use planned date if parsing fails
                
                # Find order
                order = session.query(Order).filter(Order.order_number == order_number).first()
                if not order:
                    errors.append(f"Row {index + 2}: Order '{order_number}' not found")
                    continue
                
                # Find order item by customer code and planned delivery date
                order_item = session.query(OrderItem).join(Item).filter(
                    OrderItem.order_id == order.id,
                    Item.customer_code == customer_code,
                    OrderItem.delivery_date == planned_delivery_date
                ).first()
                
                if not order_item:
                    errors.append(f"Row {index + 2}: Item '{customer_code}' with planned delivery date '{planned_delivery_date}' not found in order '{order_number}'")
                    continue
                
                # Check if delivery would exceed order quantity
                if order_item.delivered_quantity + quantity > order_item.quantity:
                    errors.append(f"Row {index + 2}: Delivery quantity {quantity} would exceed remaining quantity {order_item.quantity - order_item.delivered_quantity}")
                    continue
                
                # Check if delivery already exists (same order item, actual date, and quantity)
                existing_delivery = session.query(Delivery).filter(
                    Delivery.order_item_id == order_item.id,
                    Delivery.delivery_date == actual_delivery_date,
                    Delivery.quantity == quantity
                ).first()
                
                if existing_delivery:
                    skipped_count += 1
                    continue
                
                # Create delivery
                delivery = Delivery(
                    order_item_id=order_item.id,
                    quantity=quantity,
                    delivery_date=actual_delivery_date,
                    notes=notes
                )
                
                # Update order item
                order_item.delivered_quantity += quantity
                order_item.last_delivery_date = actual_delivery_date
                
                session.add(delivery)
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
                continue
        
        if imported_count > 0:
            session.commit()
        
        return {
            'success': True,
            'message': f"Successfully imported {imported_count} deliveries, skipped {skipped_count} duplicates",
            'imported': imported_count,
            'skipped': skipped_count,
            'errors': errors
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f"Error reading file: {str(e)}",
            'imported': 0,
            'skipped': 0,
            'errors': [str(e)]
        }

def export_current_deliveries(session: Session, file_path: str):
    """
    Export current deliveries from database to Excel file.
    
    This function exports all existing deliveries in the database so users can see
    what's already there and add only missing deliveries.
    """
    try:
        from models.database import Delivery, OrderItem, Order, Item
        
        # Query all deliveries with related data
        deliveries = session.query(Delivery).join(OrderItem).join(Order).join(Item).all()
        
        if not deliveries:
            return {
                'success': False,
                'message': "No deliveries found in database",
                'exported': 0
            }
        
        # Prepare data for export
        export_data = []
        for delivery in deliveries:
            order_item = delivery.order_item
            order = order_item.order
            item = order_item.item
            
            export_data.append({
                'order_number': order.order_number,
                'customer_code': item.customer_code,
                'planned_delivery_date': order_item.delivery_date.strftime('%Y-%m-%d'),
                'actual_delivery_date': delivery.delivery_date.strftime('%Y-%m-%d'),
                'quantity': delivery.quantity,
                'notes': delivery.notes or ''
            })
        
        # Create DataFrame and export
        df = pd.DataFrame(export_data)
        
        # Create Excel file with multiple sheets
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Main deliveries sheet
            df.to_excel(writer, sheet_name='Current Deliveries', index=False)
            
            # Instructions sheet
            instructions_data = {
                'Column': [
                    'order_number',
                    'customer_code', 
                    'planned_delivery_date',
                    'actual_delivery_date',
                    'quantity',
                    'notes'
                ],
                'Required': [
                    'Yes',
                    'Yes',
                    'Yes', 
                    'Yes',
                    'Yes',
                    'No'
                ],
                'Description': [
                    'Order number (must exist in database)',
                    'Customer item code (must exist in database)',
                    'Planned delivery date from order (YYYY-MM-DD format)',
                    'Actual delivery date (YYYY-MM-DD format)',
                    'Quantity delivered (number)',
                    'Optional notes about the delivery'
                ],
                'Example': [
                    'ORD-001',
                    '074-0103-32',
                    '2025-01-15',
                    '2025-01-15',
                    '50',
                    'First delivery'
                ]
            }
            
            instructions_df = pd.DataFrame(instructions_data)
            instructions_df.to_excel(writer, sheet_name='Instructions', index=False)
            
            # Notes sheet
            notes_data = {
                'Important Notes': [
                    'This file contains ALL current deliveries from the database',
                    'You can add new deliveries by adding rows to the Current Deliveries sheet',
                    'The system will automatically skip duplicate deliveries (same order, item, planned date, actual date, and quantity)',
                    'Delivery quantities cannot exceed the remaining order quantity',
                    'Dates should be in YYYY-MM-DD format',
                    'The system will update the delivered_quantity and last_delivery_date for order items automatically',
                    'If actual_delivery_date is empty, it will use the planned_delivery_date',
                    'To add missing deliveries: Add new rows with your delivery data',
                    'To update existing deliveries: Delete the old row and add a new one with updated data'
                ]
            }
            
            notes_df = pd.DataFrame(notes_data)
            notes_df.to_excel(writer, sheet_name='Notes', index=False)
            
            # Summary sheet
            summary_data = {
                'Summary': [
                    f'Total deliveries exported: {len(export_data)}',
                    f'Export date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                    f'Database: {session.bind.url}',
                    '',
                    'How to use this file:',
                    '1. Review the Current Deliveries sheet to see existing deliveries',
                    '2. Add new rows for missing deliveries',
                    '3. Save the file',
                    '4. Import using the Import tab in the application'
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        return {
            'success': True,
            'message': f"Successfully exported {len(export_data)} current deliveries to {file_path}",
            'exported': len(export_data)
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f"Error exporting current deliveries: {str(e)}",
            'exported': 0
        }

def import_components_from_excel(session: Session, file_path: str, parent_widget=None):
    """Import components from Excel file"""
    try:
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Validate required columns
        required_columns = ['name', 'description', 'supplier', 'cost_currency']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            error_msg = f"Missing required columns: {', '.join(missing_columns)}\n\nRequired columns: {', '.join(required_columns)}"
            if parent_widget:
                QMessageBox.critical(parent_widget, "Import Error", error_msg)
            return False, error_msg
        
        # Process each row
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Clean and validate the name field
                name = clean_string(row.get('name'))
                if not name or pd.isna(name):
                    errors.append(f"Row {index + 2}: Missing or invalid component name")
                    skipped_count += 1
                    continue
                
                # Check if component already exists by name (unique identifier)
                existing = session.query(Component).filter(Component.name == name).first()
                if existing:
                    skipped_count += 1
                    continue
                
                # Determine component type based on name and characteristics
                component_type = determine_component_type(name, row)
                
                # Create new component (always in CZK)
                component = Component(
                    name=name,
                    description=clean_string(row.get('description', '')),
                    supplier=clean_string(row.get('supplier', '')),
                    buy_price=float(row.get('buy_price', 0)) if pd.notna(row.get('buy_price', 0)) else 0.0,
                    material_price=float(row.get('material_price', 0)) if pd.notna(row.get('material_price', 0)) else 0.0,
                    manufacturing_price=float(row.get('manufacturing_price', 0)) if pd.notna(row.get('manufacturing_price', 0)) else 0.0,
                    surface_treatment_price=float(row.get('surface_treatment_price', 0)) if pd.notna(row.get('surface_treatment_price', 0)) else 0.0,
                    cost_currency='CZK',  # Always import in CZK
                    component_type=component_type
                )
                
                # Calculate total unit cost and EUR conversion
                component.update_unit_cost()
                
                session.add(component)
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
                session.rollback()  # Rollback on individual row errors
                continue
        
        # Commit changes
        try:
            session.commit()
        except Exception as e:
            session.rollback()
            raise Exception(f"Error committing components: {str(e)}")
        
        # Show results
        result_msg = f"Import completed!\n\nImported: {imported_count}\nSkipped (already exists): {skipped_count}"
        if errors:
            result_msg += f"\n\nErrors:\n" + "\n".join(errors[:5])  # Show first 5 errors
            if len(errors) > 5:
                result_msg += f"\n... and {len(errors) - 5} more errors"
        
        if parent_widget:
            QMessageBox.information(parent_widget, "Import Results", result_msg)
        
        return True, result_msg
        
    except Exception as e:
        error_msg = f"Error importing components: {str(e)}"
        logger.error(error_msg)
        if parent_widget:
            QMessageBox.critical(parent_widget, "Import Error", error_msg)
        return False, error_msg

def import_product_components_from_excel(session: Session, file_path: str, parent_widget=None):
    """Import product-component assignments from Excel file"""
    try:
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Validate required columns
        required_columns = ['product_name', 'component_name', 'quantity']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            error_msg = f"Missing required columns: {', '.join(missing_columns)}\n\nRequired columns: {', '.join(required_columns)}"
            if parent_widget:
                QMessageBox.critical(parent_widget, "Import Error", error_msg)
            return False, error_msg
        
        # Process each row
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Clean and validate required fields
                product_name = clean_string(row.get('product_name'))
                component_name = clean_string(row.get('component_name'))
                quantity = row.get('quantity')
                
                if not product_name or pd.isna(product_name):
                    errors.append(f"Row {index + 2}: Missing or invalid product name")
                    continue
                
                if not component_name or pd.isna(component_name):
                    errors.append(f"Row {index + 2}: Missing or invalid component name")
                    continue
                
                if pd.isna(quantity) or quantity <= 0:
                    errors.append(f"Row {index + 2}: Missing or invalid quantity")
                    continue
                
                # Find product and component
                product = session.query(Product).filter(Product.name == product_name).first()
                component = session.query(Component).filter(Component.name == component_name).first()
                
                if not product:
                    errors.append(f"Row {index + 2}: Product '{product_name}' not found")
                    continue
                
                if not component:
                    errors.append(f"Row {index + 2}: Component '{component_name}' not found")
                    continue
                
                # Check if assignment already exists (unique combination of product and component)
                existing = session.query(ProductComponent).filter(
                    ProductComponent.product_id == product.id,
                    ProductComponent.component_id == component.id
                ).first()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Create new product-component assignment
                product_component = ProductComponent(
                    product_id=product.id,
                    component_id=component.id,
                    quantity=float(quantity)
                )
                
                session.add(product_component)
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
                session.rollback()  # Rollback on individual row errors
                continue
        
        # Commit changes
        try:
            session.commit()
        except Exception as e:
            session.rollback()
            raise Exception(f"Error committing product components: {str(e)}")
        
        # Show results
        result_msg = f"Import completed!\n\nImported: {imported_count}\nSkipped (already exists): {skipped_count}"
        if errors:
            result_msg += f"\n\nErrors:\n" + "\n".join(errors[:5])  # Show first 5 errors
            if len(errors) > 5:
                result_msg += f"\n... and {len(errors) - 5} more errors"
        
        if parent_widget:
            QMessageBox.information(parent_widget, "Import Results", result_msg)
        
        return True, result_msg
        
    except Exception as e:
        error_msg = f"Error importing product components: {str(e)}"
        logger.error(error_msg)
        if parent_widget:
            QMessageBox.critical(parent_widget, "Import Error", error_msg)
        return False, error_msg

def import_component_materials_from_excel(session: Session, file_path: str, parent_widget=None):
    """Import component materials from Excel file - bulk upload material type and required length for components"""
    try:
        df = pd.read_excel(file_path, sheet_name="Component Materials")
        
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Clean and validate required fields
                component_name = clean_string(row.get('component_name'))
                material_name = clean_string(row.get('material_name'))
                required_length = row.get('required_length')
                
                if not component_name or pd.isna(component_name):
                    errors.append(f"Row {index + 2}: Missing or invalid component name")
                    continue
                
                if not material_name or pd.isna(material_name):
                    errors.append(f"Row {index + 2}: Missing or invalid material name")
                    continue
                
                if pd.isna(required_length) or required_length <= 0:
                    errors.append(f"Row {index + 2}: Missing or invalid required length")
                    continue
                
                # Find component and material
                component = session.query(Component).filter(Component.name == component_name).first()
                material = session.query(Material).filter(Material.name == material_name).first()
                
                if not component:
                    errors.append(f"Row {index + 2}: Component '{component_name}' not found")
                    continue
                
                if not material:
                    errors.append(f"Row {index + 2}: Material '{material_name}' not found")
                    continue
                
                # Check if component-material relationship already exists
                existing = session.query(ComponentMaterial).filter(
                    ComponentMaterial.component_id == component.id,
                    ComponentMaterial.material_id == material.id
                ).first()
                
                # Get optional fields with defaults
                cutting_allowance = float(row.get('cutting_allowance', 5.0)) if pd.notna(row.get('cutting_allowance', 5.0)) else 5.0
                waste_percentage = float(row.get('waste_percentage', 0.0)) if pd.notna(row.get('waste_percentage', 0.0)) else 0.0
                notes = clean_string(row.get('notes'))
                
                if existing:
                    # Update existing component material
                    existing.required_length = float(required_length)
                    existing.cutting_allowance = cutting_allowance
                    existing.waste_percentage = waste_percentage
                    if notes:
                        existing.notes = notes
                    existing.updated_at = datetime.now()
                    updated_count += 1
                else:
                    # Create new component material
                    component_material = ComponentMaterial(
                        component_id=component.id,
                        material_id=material.id,
                        required_length=float(required_length),
                        cutting_allowance=cutting_allowance,
                        waste_percentage=waste_percentage,
                        notes=notes
                    )
                    session.add(component_material)
                    imported_count += 1
                
            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
                continue
        
        # Commit all changes
        session.commit()
        
        # Update material costs for affected components
        updated_components = set()
        for index, row in df.iterrows():
            component_name = clean_string(row.get('component_name'))
            if component_name:
                component = session.query(Component).filter(Component.name == component_name).first()
                if component:
                    updated_components.add(component)
        
        for component in updated_components:
            component.update_material_cost_from_materials()
        
        session.commit()
        
        # Prepare result message
        result_msg = f"Component Materials Import Results:\n"
        result_msg += f"✅ Imported: {imported_count} new material assignments\n"
        result_msg += f"🔄 Updated: {updated_count} existing material assignments\n"
        result_msg += f"⏭️ Skipped: {skipped_count} rows\n"
        
        if errors:
            result_msg += f"\n❌ Errors ({len(errors)}):\n"
            for error in errors[:10]:  # Show first 10 errors
                result_msg += f"  • {error}\n"
            if len(errors) > 10:
                result_msg += f"  • ... and {len(errors) - 10} more errors\n"
        
        logger.info(f"Component materials import completed: {imported_count} imported, {updated_count} updated, {len(errors)} errors")
        
        if parent_widget:
            QMessageBox.information(parent_widget, "Import Complete", result_msg)
        
        return True, result_msg
        
    except Exception as e:
        error_msg = f"Error importing component materials: {str(e)}"
        logger.error(error_msg)
        if parent_widget:
            QMessageBox.critical(parent_widget, "Import Error", error_msg)
        return False, error_msg 