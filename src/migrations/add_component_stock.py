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
        
        # Create component_stock table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS component_stock (
                id INTEGER PRIMARY KEY,
                component_id INTEGER NOT NULL,
                current_stock FLOAT DEFAULT 0.0,
                minimum_stock FLOAT DEFAULT 0.0,
                unit_of_measure VARCHAR(20) DEFAULT 'pcs',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (component_id) REFERENCES components (id)
            )
        """)
        
        conn.commit()
        logger.info("Successfully created component_stock table")
        
        # Create index for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_component_stock_component_id ON component_stock (component_id)")
        conn.commit()
        logger.info("Successfully created index on component_stock table")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    migrate() 