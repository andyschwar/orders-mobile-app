from sqlalchemy import create_engine, text
import os
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Add cost tracking fields to components table"""
    from src.models.database import get_database_path
    
    # Get database path
    db_path = get_database_path()
    engine = create_engine(f'sqlite:///{db_path}')
    
    # Add cost fields to components table
    with engine.connect() as conn:
        try:
            # Add unit cost field
            conn.execute(text("ALTER TABLE components ADD COLUMN unit_cost FLOAT DEFAULT 0.0"))
            logger.info("Added unit_cost column to components table")
        except Exception as e:
            logger.warning(f"unit_cost column might already exist: {e}")
        
        try:
            # Add cost currency field
            conn.execute(text("ALTER TABLE components ADD COLUMN cost_currency VARCHAR(3) DEFAULT 'EUR'"))
            logger.info("Added cost_currency column to components table")
        except Exception as e:
            logger.warning(f"cost_currency column might already exist: {e}")
        
        try:
            # Add supplier field
            conn.execute(text("ALTER TABLE components ADD COLUMN supplier VARCHAR(100)"))
            logger.info("Added supplier column to components table")
        except Exception as e:
            logger.warning(f"supplier column might already exist: {e}")
        
        try:
            # Add component type field (manufactured, bought, outsourced)
            conn.execute(text("ALTER TABLE components ADD COLUMN component_type VARCHAR(20) DEFAULT 'bought'"))
            logger.info("Added component_type column to components table")
        except Exception as e:
            logger.warning(f"component_type column might already exist: {e}")
        
        conn.commit()

def downgrade():
    """Remove cost tracking fields from components table"""
    from src.models.database import get_database_path
    
    db_path = get_database_path()
    engine = create_engine(f'sqlite:///{db_path}')
    
    # SQLite doesn't support DROP COLUMN, so we'd need to recreate the table
    # For now, just log that this would need manual intervention
    logger.warning("Manual intervention required to remove cost columns") 