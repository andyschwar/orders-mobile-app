#!/usr/bin/env python3
import os
import sqlite3
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def migrate():
    try:
        # Get database path
        db_path = os.path.expanduser('~/Library/Application Support/Orders/orders.db')
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(products)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'description' not in columns:
            logger.info("Adding description column to products table")
            cursor.execute("ALTER TABLE products ADD COLUMN description TEXT")
            conn.commit()
            logger.info("Migration completed successfully")
        else:
            logger.info("Description column already exists")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if conn:
            conn.close()
        return False

if __name__ == '__main__':
    migrate() 