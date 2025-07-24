from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import sessionmaker
import enum
from datetime import datetime
import os

class UserRole(enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"

def add_users_table():
    """Add users table to the database"""
    
    # Get database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'orders.db')
    
    # Create engine
    engine = create_engine(f'sqlite:///{db_path}')
    
    # Create metadata
    metadata = MetaData()
    
    # Define users table
    users_table = Table('users', metadata,
        Column('id', Integer, primary_key=True),
        Column('username', String(50), unique=True, nullable=False),
        Column('password_hash', String(255), nullable=False),
        Column('email', String(100), unique=True, nullable=True),
        Column('role', Enum(UserRole), default=UserRole.VIEWER, nullable=False),
        Column('is_active', Boolean, default=True, nullable=False),
        Column('created_at', DateTime, default=datetime.utcnow, nullable=False),
        Column('last_login', DateTime, nullable=True)
    )
    
    # Create table
    metadata.create_all(engine)
    
    print("Users table created successfully!")
    
    # Create session and add default users
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Import auth utilities
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from utils.auth import create_default_users, hash_password
    
    # Create default users
    create_default_users(session)
    
    session.close()
    print("Default users created successfully!")

if __name__ == "__main__":
    add_users_table() 