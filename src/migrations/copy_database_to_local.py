#!/usr/bin/env python3
import os
import shutil
import logging
import sys

# Add the src directory to the path so we can import the database module
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from models.database import get_database_path

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def copy_database_to_local():
    try:
        # Get the current database path (Google Drive)
        current_db_path = get_database_path()
        logger.info(f"Current database path: {current_db_path}")
        
        # Define local database path
        local_db_dir = os.path.expanduser('~/Library/Application Support/Orders')
        os.makedirs(local_db_dir, exist_ok=True)
        local_db_path = os.path.join(local_db_dir, 'orders.db')
        
        logger.info(f"Local database path: {local_db_path}")
        
        # Check if current database exists
        if not os.path.exists(current_db_path):
            logger.error(f"Current database not found at: {current_db_path}")
            return False
        
        # Copy database to local
        logger.info("Copying database to local directory...")
        shutil.copy2(current_db_path, local_db_path)
        
        # Verify the copy was successful
        if os.path.exists(local_db_path):
            logger.info("✅ Database successfully copied to local directory")
            
            # Get file sizes for comparison
            current_size = os.path.getsize(current_db_path)
            local_size = os.path.getsize(local_db_path)
            
            logger.info(f"Google Drive database size: {current_size:,} bytes")
            logger.info(f"Local database size: {local_size:,} bytes")
            
            if current_size == local_size:
                logger.info("✅ File sizes match - copy was successful")
            else:
                logger.warning("⚠️ File sizes don't match - copy may be incomplete")
            
            return True
        else:
            logger.error("❌ Failed to copy database to local directory")
            return False
            
    except Exception as e:
        logger.error(f"Error copying database: {e}")
        return False

if __name__ == "__main__":
    copy_database_to_local() 