import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'orders.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(products)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Create new table with all required columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products_new (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                weight_per_unit FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Build dynamic SQL for copying data
        existing_columns = []
        new_columns = []
        
        # Map old columns to new columns
        if 'id' in columns:
            existing_columns.append('id')
            new_columns.append('id')
        if 'name' in columns:
            existing_columns.append('name')
            new_columns.append('name')
        if 'description' in columns:
            existing_columns.append('description')
            new_columns.append('description')
        if 'weight' in columns:
            existing_columns.append('weight')
            new_columns.append('weight_per_unit')
        elif 'weight_per_unit' in columns:
            existing_columns.append('weight_per_unit')
            new_columns.append('weight_per_unit')
        if 'created_at' in columns:
            existing_columns.append('created_at')
            new_columns.append('created_at')
        if 'updated_at' in columns:
            existing_columns.append('updated_at')
            new_columns.append('updated_at')
        
        # Copy data from old table to new table
        if existing_columns:
            cursor.execute(f"""
                INSERT INTO products_new ({', '.join(new_columns)})
                SELECT {', '.join(existing_columns)}
                FROM products
            """)
        
        # Drop old table and rename new one
        cursor.execute("DROP TABLE products")
        cursor.execute("ALTER TABLE products_new RENAME TO products")
        
        conn.commit()
        print("Successfully updated products table with weight_per_unit column")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate() 