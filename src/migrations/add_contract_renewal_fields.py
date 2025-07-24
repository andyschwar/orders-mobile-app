#!/usr/bin/env python3
"""
Migration script to add contract renewal date columns to employees table.
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
    """Add contract renewal date columns to employees table"""
    try:
        db_path = get_database_path()
        engine = create_engine(f'sqlite:///{db_path}')
        
        with engine.connect() as conn:
            # Check if columns already exist
            result = conn.execute(text("PRAGMA table_info(employees)"))
            columns = [row[1] for row in result.fetchall()]
            
            # Add contract_renewal_1 column
            if 'contract_renewal_1' not in columns:
                logger.info("Adding contract_renewal_1 column to employees table...")
                conn.execute(text("ALTER TABLE employees ADD COLUMN contract_renewal_1 DATE"))
                logger.info("Successfully added contract_renewal_1 column")
            else:
                logger.info("contract_renewal_1 column already exists")
            
            # Add contract_renewal_2 column
            if 'contract_renewal_2' not in columns:
                logger.info("Adding contract_renewal_2 column to employees table...")
                conn.execute(text("ALTER TABLE employees ADD COLUMN contract_renewal_2 DATE"))
                logger.info("Successfully added contract_renewal_2 column")
            else:
                logger.info("contract_renewal_2 column already exists")
            
            # Add contract_renewal_3 column
            if 'contract_renewal_3' not in columns:
                logger.info("Adding contract_renewal_3 column to employees table...")
                conn.execute(text("ALTER TABLE employees ADD COLUMN contract_renewal_3 DATE"))
                logger.info("Successfully added contract_renewal_3 column")
            else:
                logger.info("contract_renewal_3 column already exists")
            
            # Add last_contract_renewal column
            if 'last_contract_renewal' not in columns:
                logger.info("Adding last_contract_renewal column to employees table...")
                conn.execute(text("ALTER TABLE employees ADD COLUMN last_contract_renewal DATE"))
                logger.info("Successfully added last_contract_renewal column")
            else:
                logger.info("last_contract_renewal column already exists")
                
            conn.commit()
                
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise

if __name__ == "__main__":
    migrate() 