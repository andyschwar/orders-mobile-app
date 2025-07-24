#!/usr/bin/env python3
import os
import logging
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from models.database import Base, Product, Customer, Item, Employee, Order, OrderItem, Component, ProductComponent

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_fresh_database():
    try:
        # Get database path
        db_path = os.path.expanduser('~/Library/Application Support/Orders/orders.db')
        db_dir = os.path.dirname(db_path)
        os.makedirs(db_dir, exist_ok=True)
        
        # Remove existing database if it exists
        if os.path.exists(db_path):
            logger.info(f"Removing existing database at {db_path}")
            os.remove(db_path)
        
        # Create new database with all tables
        logger.info("Creating new database with fresh schema")
        engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(engine)
        
        # Create a session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Verify tables were created
        inspector = MetaData()
        inspector.reflect(bind=engine)
        tables = inspector.tables.keys()
        logger.info("Created tables:")
        for table in tables:
            logger.info(f"  - {table}")
        
        # Close session
        session.close()
        
        logger.info("Database creation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database creation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    create_fresh_database() 