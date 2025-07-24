from sqlalchemy import create_engine, text
import os
import logging

logger = logging.getLogger(__name__)

def migrate():
    try:
        # Use user's home directory for database
        db_dir = os.path.expanduser('~/Library/Application Support/Orders')
        db_path = os.path.join(db_dir, 'orders.db')
        
        logger.debug(f"Creating database engine with path: {db_path}")
        engine = create_engine(f'sqlite:///{db_path}')
        
        with engine.connect() as conn:
            # Rename the column
            conn.execute(text("ALTER TABLE order_items RENAME COLUMN price TO unit_price"))
            conn.commit()
            
        logger.debug("Successfully renamed price column to unit_price")
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise

if __name__ == '__main__':
    migrate() 