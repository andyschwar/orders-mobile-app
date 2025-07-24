#!/usr/bin/env python3
import os
import sqlite3
import logging
import sys

# Add the src directory to the path so we can import the database module
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from models.database import get_database_path

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def migrate():
    try:
        # Get database path using the same function as the application
        db_path = get_database_path()
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(components)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'category' not in columns:
            logger.info("Adding category column to components table")
            cursor.execute("ALTER TABLE components ADD COLUMN category VARCHAR(50)")
            conn.commit()
            logger.info("Migration completed successfully")
        else:
            logger.info("Category column already exists")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    migrate() 