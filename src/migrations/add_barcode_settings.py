#!/usr/bin/env python3
"""
Migration to add barcode settings to customers table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import init_db, Customer
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, inspect

def migrate():
    """Add barcode settings to customers table"""
    print("Adding barcode settings to customers table...")
    
    try:
        # Initialize database
        engine = init_db()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if columns already exist
        inspector = inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('customers')]
        
        # Add barcode settings columns if they don't exist
        if 'barcodes_enabled' not in existing_columns:
            session.execute(text("ALTER TABLE customers ADD COLUMN barcodes_enabled BOOLEAN DEFAULT 0"))
            print("✅ Added barcodes_enabled column")
        
        if 'order_barcode_prefix' not in existing_columns:
            session.execute(text("ALTER TABLE customers ADD COLUMN order_barcode_prefix VARCHAR(10) DEFAULT 'N'"))
            print("✅ Added order_barcode_prefix column")
        
        if 'item_barcode_prefix' not in existing_columns:
            session.execute(text("ALTER TABLE customers ADD COLUMN item_barcode_prefix VARCHAR(10) DEFAULT 'P'"))
            print("✅ Added item_barcode_prefix column")
        
        if 'quantity_barcode_prefix' not in existing_columns:
            session.execute(text("ALTER TABLE customers ADD COLUMN quantity_barcode_prefix VARCHAR(10) DEFAULT 'U'"))
            print("✅ Added quantity_barcode_prefix column")
        
        # Set default barcode settings for existing customers that should have barcodes
        # Based on the hardcoded list in the original label generator
        barcode_customers = ["POPRAD", "TREBISOV", "TLMACE", "ZAHREB"]
        
        for customer_name in barcode_customers:
            customer = session.query(Customer).filter(Customer.name_index == customer_name).first()
            if customer:
                customer.barcodes_enabled = True
                customer.order_barcode_prefix = 'N'
                customer.item_barcode_prefix = 'P'
                customer.quantity_barcode_prefix = 'U'
                print(f"✅ Enabled barcodes for customer: {customer_name}")
        
        session.commit()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate() 