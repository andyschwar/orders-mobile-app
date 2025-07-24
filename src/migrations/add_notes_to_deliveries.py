from sqlalchemy import create_engine, text
import os
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Add notes column to deliveries table"""
    from src.models.database import get_database_path
    
    # Get database path
    db_path = get_database_path()
    engine = create_engine(f'sqlite:///{db_path}')
    
    # Add the column
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE deliveries ADD COLUMN notes TEXT"))
            conn.commit()
            logger.info("Added notes column to deliveries table")
        except Exception as e:
            logger.warning(f"Column might already exist: {e}")

def downgrade():
    """Remove notes column from deliveries table"""
    from src.models.database import get_database_path
    
    db_path = get_database_path()
    engine = create_engine(f'sqlite:///{db_path}')
    
    # SQLite doesn't support DROP COLUMN, so we'd need to recreate the table
    # For now, just log that this would need manual intervention
    logger.warning("Manual intervention required to remove notes column") 