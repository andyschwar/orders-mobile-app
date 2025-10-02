#!/usr/bin/env python3
"""
Migration: Add delivery_date field to label_logs table
Date: 2025-01-27
Description: Adds delivery_date column to label_logs table to track delivery dates in label logs
"""

import os
import sys
from sqlalchemy import create_engine, text
from datetime import datetime

# Add the src directory to the path so we can import the database module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.database import get_database_path

def run_migration():
    """Add delivery_date column to label_logs table"""
    try:
        # Get database path
        db_path = get_database_path()
        print(f"Running migration on database: {db_path}")
        
        # Create engine
        engine = create_engine(f'sqlite:///{db_path}')
        
        with engine.connect() as conn:
            # Check if the column already exists
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM pragma_table_info('label_logs') 
                WHERE name = 'delivery_date'
            """))
            
            column_exists = result.fetchone()[0] > 0
            
            if column_exists:
                print("delivery_date column already exists in label_logs table")
                return True
            
            # Add the delivery_date column
            print("Adding delivery_date column to label_logs table...")
            conn.execute(text("""
                ALTER TABLE label_logs 
                ADD COLUMN delivery_date DATE
            """))
            
            conn.commit()
            print("✅ Successfully added delivery_date column to label_logs table")
            return True
            
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1)
