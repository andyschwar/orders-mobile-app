#!/usr/bin/env python3
"""
Migration script to fix Czech characters in customer name_index fields.
This script will replace Czech characters with ASCII equivalents for better font compatibility.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def replace_czech_chars(text):
    """Replace Czech characters with ASCII equivalents for better font compatibility"""
    if not text:
        return text
        
    replacements = {
        'Á': 'A', 'á': 'a',
        'Č': 'C', 'č': 'c',
        'Ď': 'D', 'ď': 'd',
        'É': 'E', 'é': 'e',
        'Ě': 'E', 'ě': 'e',
        'Í': 'I', 'í': 'i',
        'Ň': 'N', 'ň': 'n',
        'Ó': 'O', 'ó': 'o',
        'Ř': 'R', 'ř': 'r',
        'Š': 'S', 'š': 's',
        'Ť': 'T', 'ť': 't',
        'Ú': 'U', 'ú': 'u',
        'Ů': 'U', 'ů': 'u',
        'Ý': 'Y', 'ý': 'y',
        'Ž': 'Z', 'ž': 'z'
    }
    
    for czech_char, ascii_char in replacements.items():
        text = text.replace(czech_char, ascii_char)
    
    return text

def fix_czech_characters():
    """Fix Czech characters in customer name_index fields"""
    try:
        # Use user's home directory for database
        db_dir = os.path.expanduser('~/Library/Application Support/Orders')
        db_path = os.path.join(db_dir, 'orders.db')
        
        print(f"Connecting to database: {db_path}")
        engine = create_engine(f'sqlite:///{db_path}')
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Find customers with Czech characters in name_index
        result = session.execute(text("""
            SELECT id, name_index 
            FROM customers 
            WHERE name_index LIKE '%Á%' OR name_index LIKE '%Č%' OR name_index LIKE '%Ď%' 
               OR name_index LIKE '%É%' OR name_index LIKE '%Ě%' OR name_index LIKE '%Í%'
               OR name_index LIKE '%Ň%' OR name_index LIKE '%Ó%' OR name_index LIKE '%Ř%'
               OR name_index LIKE '%Š%' OR name_index LIKE '%Ť%' OR name_index LIKE '%Ú%'
               OR name_index LIKE '%Ů%' OR name_index LIKE '%Ý%' OR name_index LIKE '%Ž%'
        """))
        
        customers_to_fix = result.fetchall()
        
        if not customers_to_fix:
            print("No customers found with Czech characters in name_index")
            return
        
        print(f"Found {len(customers_to_fix)} customers with Czech characters:")
        for customer_id, name_index in customers_to_fix:
            print(f"  ID {customer_id}: {name_index}")
        
        # Fix the customer name_index fields
        fixed_count = 0
        for customer_id, name_index in customers_to_fix:
            # Replace Czech characters
            fixed_name_index = replace_czech_chars(name_index)
            
            # Update the database
            session.execute(text("""
                UPDATE customers 
                SET name_index = :fixed_name_index 
                WHERE id = :customer_id
            """), {"fixed_name_index": fixed_name_index, "customer_id": customer_id})
            
            print(f"  Fixed ID {customer_id}: {name_index} -> {fixed_name_index}")
            fixed_count += 1
        
        session.commit()
        print(f"\nSuccessfully fixed {fixed_count} customer name_index fields")
        
    except Exception as e:
        print(f"Error fixing Czech characters: {e}")
        if 'session' in locals():
            session.rollback()
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    fix_czech_characters() 