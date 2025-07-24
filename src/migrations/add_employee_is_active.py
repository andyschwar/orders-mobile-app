import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'orders.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(employees)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_active' not in columns:
            # Add is_active column with default value True
            cursor.execute("ALTER TABLE employees ADD COLUMN is_active BOOLEAN DEFAULT 1")
            conn.commit()
            print("Added is_active column to employees table")
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate() 