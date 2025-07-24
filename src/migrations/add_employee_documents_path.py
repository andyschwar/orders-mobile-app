#!/usr/bin/env python3
"""
Migration script to add documents_path column to employees table.
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
    """Add documents_path column to employees table"""
    try:
        db_path = get_database_path()
        engine = create_engine(f'sqlite:///{db_path}')
        
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("PRAGMA table_info(employees)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'documents_path' not in columns:
                logger.info("Adding documents_path column to employees table...")
                conn.execute(text("ALTER TABLE employees ADD COLUMN documents_path VARCHAR(500)"))
                conn.commit()
                logger.info("Successfully added documents_path column")
            else:
                logger.info("documents_path column already exists")
                
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise

if __name__ == "__main__":
    migrate() 