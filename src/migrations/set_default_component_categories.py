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
        
        # Check if category column exists
        cursor.execute("PRAGMA table_info(components)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'category' not in columns:
            logger.error("Category column does not exist in components table")
            conn.close()
            return False
        
        # Count components without category
        cursor.execute("SELECT COUNT(*) FROM components WHERE category IS NULL OR category = ''")
        count = cursor.fetchone()[0]
        logger.info(f"Found {count} components without category")
        
        if count > 0:
            # Update all components that don't have a category
            cursor.execute("""
                UPDATE components 
                SET category = 'Body' 
                WHERE category IS NULL OR category = ''
            """)
            
            updated_count = cursor.rowcount
            conn.commit()
            logger.info(f"Updated {updated_count} components with category 'Body'")
        else:
            logger.info("No components need category update")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    migrate() 