#!/usr/bin/env python3
import argparse
from sqlalchemy.orm import sessionmaker
from models.database import init_db
from utils.excel_import import (
    import_customers, import_products, import_items,
    import_employees, import_orders_and_items
)

def main():
    parser = argparse.ArgumentParser(description='Import data from Excel files')
    parser.add_argument('file_path', help='Path to the Excel file')
    parser.add_argument('--type', choices=['customers', 'products', 'items', 'employees', 'orders'],
                      required=True, help='Type of data to import')
    parser.add_argument('--sheet', help='Sheet name in Excel file (optional)')
    
    args = parser.parse_args()
    
    # Initialize database
    engine = init_db()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        if args.type == 'customers':
            count = import_customers(session, args.file_path, args.sheet or "Customers")
            print(f"\nSuccessfully imported {count} customers")
            
        elif args.type == 'products':
            count = import_products(session, args.file_path, args.sheet or "Products")
            print(f"\nSuccessfully imported {count} products")
            
        elif args.type == 'items':
            count = import_items(session, args.file_path, args.sheet or "Items")
            print(f"\nSuccessfully imported {count} items")
            
        elif args.type == 'employees':
            count = import_employees(session, args.file_path, args.sheet or "Employees")
            print(f"\nSuccessfully imported {count} employees")
            
        elif args.type == 'orders':
            orders_count, items_count = import_orders_and_items(session, args.file_path, args.sheet or "Orders")
            print(f"\nSuccessfully imported {orders_count} orders with {items_count} order items")
            
    except Exception as e:
        print(f"\nError: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 