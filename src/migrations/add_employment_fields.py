#!/usr/bin/env python3
"""
Migration script to add employment-related columns to employees table.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_database_path
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Add employment-related columns to employees table"""
    try:
        db_path = get_database_path()
        engine = create_engine(f'sqlite:///{db_path}')
        
        with engine.connect() as conn:
            # Check if columns already exist
            result = conn.execute(text("PRAGMA table_info(employees)"))
            columns = [row[1] for row in result.fetchall()]
            
            # Add employment_start column
            if 'employment_start' not in columns:
                logger.info("Adding employment_start column to employees table...")
                conn.execute(text("ALTER TABLE employees ADD COLUMN employment_start DATE"))
                logger.info("Successfully added employment_start column")
            else:
                logger.info("employment_start column already exists")
            
            # Add employment_end column
            if 'employment_end' not in columns:
                logger.info("Adding employment_end column to employees table...")
                conn.execute(text("ALTER TABLE employees ADD COLUMN employment_end DATE"))
                logger.info("Successfully added employment_end column")
            else:
                logger.info("employment_end column already exists")
            
            # Add employment_type column
            if 'employment_type' not in columns:
                logger.info("Adding employment_type column to employees table...")
                conn.execute(text("ALTER TABLE employees ADD COLUMN employment_type VARCHAR(50)"))
                logger.info("Successfully added employment_type column")
            else:
                logger.info("employment_type column already exists")
                
            conn.commit()
                
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise

if __name__ == "__main__":
    migrate() 