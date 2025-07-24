#!/usr/bin/env python3
"""
Migration script to fix item codes that have .0 suffix from Excel imports.
This script will remove the .0 suffix from customer_code fields in the items table.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def fix_item_codes():
    """Fix item codes by removing .0 suffix"""
    try:
        # Use user's home directory for database
        db_dir = os.path.expanduser('~/Library/Application Support/Orders')
        db_path = os.path.join(db_dir, 'orders.db')
        
        print(f"Connecting to database: {db_path}")
        engine = create_engine(f'sqlite:///{db_path}')
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Find items with .0 suffix in customer_code
        result = session.execute(text("""
            SELECT id, customer_code 
            FROM items 
            WHERE customer_code LIKE '%.0'
        """))
        
        items_to_fix = result.fetchall()
        
        if not items_to_fix:
            print("No items found with .0 suffix in customer_code")
            return
        
        print(f"Found {len(items_to_fix)} items with .0 suffix:")
        for item_id, customer_code in items_to_fix:
            print(f"  ID {item_id}: {customer_code}")
        
        # Fix the item codes
        fixed_count = 0
        for item_id, customer_code in items_to_fix:
            # Remove .0 suffix
            fixed_code = customer_code[:-2] if customer_code.endswith('.0') else customer_code
            
            # Update the database
            session.execute(text("""
                UPDATE items 
                SET customer_code = :fixed_code 
                WHERE id = :item_id
            """), {"fixed_code": fixed_code, "item_id": item_id})
            
            print(f"  Fixed ID {item_id}: {customer_code} -> {fixed_code}")
            fixed_count += 1
        
        session.commit()
        print(f"\nSuccessfully fixed {fixed_count} item codes")
        
    except Exception as e:
        print(f"Error fixing item codes: {e}")
        if 'session' in locals():
            session.rollback()
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    fix_item_codes() 