#!/usr/bin/env python3
import os
import sqlite3
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def verify_schema():
    try:
        # Get database path
        db_path = os.path.expanduser('~/Library/Application Support/Orders/orders.db')
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check products table schema
        cursor.execute("PRAGMA table_info(products)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        # Required columns and their types
        required_columns = {
            'id': 'INTEGER',
            'name': 'VARCHAR(100)',
            'description': 'TEXT',
            'weight_per_unit': 'FLOAT',
            'created_at': 'DATETIME',
            'updated_at': 'DATETIME'
        }
        
        # Add missing columns
        for col_name, col_type in required_columns.items():
            if col_name not in columns:
                logger.info(f"Adding missing column {col_name} ({col_type}) to products table")
                cursor.execute(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}")
        
        conn.commit()
        logger.info("Schema verification completed")
        
        # Show current schema
        cursor.execute("PRAGMA table_info(products)")
        current_schema = cursor.fetchall()
        logger.info("Current schema:")
        for col in current_schema:
            logger.info(f"  {col[1]}: {col[2]}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == '__main__':
    verify_schema() 