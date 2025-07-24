#!/usr/bin/env python3
"""
Migration to add EUR conversion fields to Component model
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from models.database import get_database_path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Add EUR conversion fields to components table"""
    try:
        # Get database path
        db_path = get_database_path()
        engine = create_engine(f'sqlite:///{db_path}')
        
        with engine.connect() as conn:
            # Add EUR conversion fields
            conn.execute(text("""
                ALTER TABLE components 
                ADD COLUMN buy_price_eur FLOAT DEFAULT 0.0
            """))
            
            conn.execute(text("""
                ALTER TABLE components 
                ADD COLUMN material_price_eur FLOAT DEFAULT 0.0
            """))
            
            conn.execute(text("""
                ALTER TABLE components 
                ADD COLUMN manufacturing_price_eur FLOAT DEFAULT 0.0
            """))
            
            conn.execute(text("""
                ALTER TABLE components 
                ADD COLUMN surface_treatment_price_eur FLOAT DEFAULT 0.0
            """))
            
            conn.execute(text("""
                ALTER TABLE components 
                ADD COLUMN unit_cost_eur FLOAT DEFAULT 0.0
            """))
            
            conn.commit()
            logger.info("Successfully added EUR conversion fields to components table")
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    run_migration() 