from sqlalchemy import create_engine, MetaData, Table, Column, String, DateTime, inspect, text
from sqlalchemy.orm import sessionmaker
import os

def add_reset_token_fields():
    """Add reset token fields to users table"""
    
    # Get database path from the actual database location
    db_path = "/Users/andyschwar/Google Drive/My drive/_app/orders.db"
    
    # Create engine
    engine = create_engine(f'sqlite:///{db_path}')
    
    # Add columns to existing table
    with engine.connect() as conn:
        # Check if columns already exist
        inspector = inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'reset_token' not in existing_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN reset_token VARCHAR(255)"))
            print("Added reset_token column")
        
        if 'reset_token_expires' not in existing_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN reset_token_expires DATETIME"))
            print("Added reset_token_expires column")
        
        conn.commit()
    
    print("Reset token fields added successfully!")

if __name__ == "__main__":
    add_reset_token_fields() 