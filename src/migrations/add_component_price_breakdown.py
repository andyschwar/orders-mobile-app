import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from models.database import get_database_path
import logging

logger = logging.getLogger(__name__)

def migrate():
    """Add price breakdown fields to components table"""
    try:
        # Get database path
        db_path = get_database_path()
        engine = create_engine(f'sqlite:///{db_path}')
        
        with engine.connect() as conn:
            # Add new price breakdown columns
            conn.execute(text("""
                ALTER TABLE components 
                ADD COLUMN buy_price REAL DEFAULT 0.0
            """))
            
            conn.execute(text("""
                ALTER TABLE components 
                ADD COLUMN material_price REAL DEFAULT 0.0
            """))
            
            conn.execute(text("""
                ALTER TABLE components 
                ADD COLUMN manufacturing_price REAL DEFAULT 0.0
            """))
            
            conn.execute(text("""
                ALTER TABLE components 
                ADD COLUMN surface_treatment_price REAL DEFAULT 0.0
            """))
            
            # Update existing components to set buy_price = unit_cost for backward compatibility
            conn.execute(text("""
                UPDATE components 
                SET buy_price = unit_cost 
                WHERE buy_price IS NULL OR buy_price = 0.0
            """))
            
            conn.commit()
            
        logger.info("Successfully added price breakdown fields to components table")
        return True
        
    except Exception as e:
        logger.error(f"Error adding price breakdown fields: {str(e)}")
        return False

if __name__ == "__main__":
    migrate() 