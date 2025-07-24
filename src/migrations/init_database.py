import os
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models.database import Base

def init_database():
    """Initialize the database with all required tables and run migrations"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'orders.db')
    
    # Create SQLAlchemy engine
    engine = create_engine(f'sqlite:///{db_path}')
    
    try:
        # Create all tables defined in SQLAlchemy models
        Base.metadata.create_all(engine)
        print("Base tables created successfully")
        
        # Create a session to test the connection
        Session = sessionmaker(bind=engine)
        session = Session()
        session.execute(text("SELECT 1"))
        session.close()
        
        # Now run migrations to ensure all columns are present
        run_migrations(db_path)
        
        return True
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        return False

def run_migrations(db_path):
    """Run all database migrations in the correct order"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add any missing columns to existing tables
        add_missing_columns(cursor)
        
        conn.commit()
        print("All migrations completed successfully")
        
    except Exception as e:
        print(f"Error during migrations: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def add_missing_columns(cursor):
    """Add any missing columns to existing tables"""
    try:
        # Check customers table columns
        cursor.execute("PRAGMA table_info(customers)")
        customer_columns = {col[1] for col in cursor.fetchall()}
        
        # Add missing columns to customers table
        customer_missing = {
            'name_index': 'VARCHAR(20)',
            'name': 'VARCHAR(100) NOT NULL',
            'street': 'VARCHAR(100)',
            'city': 'VARCHAR(100)',
            'country': 'VARCHAR(100)',
            'email1': 'VARCHAR(100)',
            'email2': 'VARCHAR(100)',
            'email3': 'VARCHAR(100)',
            'atest_email': 'VARCHAR(100)',
            'invoice_email': 'VARCHAR(100)',
            'ico_vat': 'VARCHAR(20)',
            'ic_dph': 'VARCHAR(20)',
            'currency': 'VARCHAR(3)',
            'is_eu': 'BOOLEAN DEFAULT 0',
            'delivery_address': 'TEXT',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        
        for col, type_ in customer_missing.items():
            if col not in customer_columns:
                try:
                    cursor.execute(f"ALTER TABLE customers ADD COLUMN {col} {type_}")
                    print(f"Added column {col} to customers table")
                except Exception as e:
                    print(f"Error adding column {col}: {str(e)}")
        
        # Check products table columns
        cursor.execute("PRAGMA table_info(products)")
        product_columns = {col[1] for col in cursor.fetchall()}
        
        # Add missing columns to products table
        product_missing = {
            'name': 'VARCHAR(100) NOT NULL',
            'description': 'TEXT',
            'weight_per_unit': 'FLOAT',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        
        for col, type_ in product_missing.items():
            if col not in product_columns:
                try:
                    cursor.execute(f"ALTER TABLE products ADD COLUMN {col} {type_}")
                    print(f"Added column {col} to products table")
                except Exception as e:
                    print(f"Error adding column {col}: {str(e)}")
        
        # Check employees table columns
        cursor.execute("PRAGMA table_info(employees)")
        employee_columns = {col[1] for col in cursor.fetchall()}
        
        # Add missing columns to employees table
        employee_missing = {
            'name': 'VARCHAR(100) NOT NULL',
            'name_day': 'DATE',
            'is_active': 'BOOLEAN DEFAULT 1',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        
        for col, type_ in employee_missing.items():
            if col not in employee_columns:
                try:
                    cursor.execute(f"ALTER TABLE employees ADD COLUMN {col} {type_}")
                    print(f"Added column {col} to employees table")
                except Exception as e:
                    print(f"Error adding column {col}: {str(e)}")
        
        print("All missing columns added successfully")
        
    except Exception as e:
        print(f"Error adding missing columns: {str(e)}")
        raise

def get_table_names(cursor):
    """Get list of all tables in the database"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cursor.fetchall()]

if __name__ == "__main__":
    init_database() 