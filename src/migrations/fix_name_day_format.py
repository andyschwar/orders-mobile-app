import sqlite3
import os
from datetime import datetime

def migrate():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'orders.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # First check if the column exists and get its type
        cursor.execute("PRAGMA table_info(employees)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        if 'name_day' not in columns:
            print("name_day column does not exist, creating it...")
            cursor.execute("ALTER TABLE employees ADD COLUMN name_day VARCHAR(5)")
        elif columns['name_day'].upper() != 'VARCHAR(5)':
            print("Converting name_day column to VARCHAR(5)...")
            # Get all name_day values
            cursor.execute("SELECT id, name_day FROM employees")
            rows = cursor.fetchall()
            
            # Create temporary column
            cursor.execute("ALTER TABLE employees ADD COLUMN name_day_new VARCHAR(5)")
            
            # Convert and copy data
            for row in rows:
                id_, name_day = row
                if name_day:
                    try:
                        # Try parsing as date string
                        if isinstance(name_day, str):
                            try:
                                # Try parsing as YYYY-MM-DD
                                date_obj = datetime.strptime(name_day, "%Y-%m-%d").date()
                            except ValueError:
                                try:
                                    # Try parsing as MM-DD
                                    month, day = map(int, name_day.split('-'))
                                    date_obj = datetime(2000, month, day).date()
                                except:
                                    continue
                        else:
                            date_obj = name_day
                        
                        # Convert to MM-DD format
                        new_format = f"{date_obj.month:02d}-{date_obj.day:02d}"
                        cursor.execute(
                            "UPDATE employees SET name_day_new = ? WHERE id = ?",
                            (new_format, id_)
                        )
                    except Exception as e:
                        print(f"Error converting name_day for id {id_}: {str(e)}")
            
            # Drop old column and rename new one
            cursor.execute("CREATE TABLE employees_new AS SELECT id, name, address, phone, email, birthday, name_day_new as name_day, is_active, created_at, updated_at FROM employees")
            cursor.execute("DROP TABLE employees")
            cursor.execute("ALTER TABLE employees_new RENAME TO employees")
            
        conn.commit()
        print("Name day format migration completed successfully")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        conn.rollback()
    finally:
        conn.close() 