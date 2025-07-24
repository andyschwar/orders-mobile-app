import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'orders.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all employees with their name_days
        cursor.execute("SELECT id, name_day FROM employees WHERE name_day IS NOT NULL")
        employees = cursor.fetchall()
        
        # Create temporary column
        cursor.execute("ALTER TABLE employees ADD COLUMN name_day_new VARCHAR(5)")
        
        # Convert and update data
        for emp_id, name_day in employees:
            if name_day:  # Convert from YYYY-MM-DD to MM-DD
                month_day = name_day[5:]  # Get MM-DD part
                cursor.execute(
                    "UPDATE employees SET name_day_new = ? WHERE id = ?",
                    (month_day, emp_id)
                )
        
        # Drop old column and rename new one
        cursor.execute("CREATE TABLE employees_new AS SELECT id, name, address, phone, email, birthday, name_day_new as name_day, is_active, created_at, updated_at FROM employees")
        cursor.execute("DROP TABLE employees")
        cursor.execute("ALTER TABLE employees_new RENAME TO employees")
        
        conn.commit()
        print("Successfully converted name_day column to MM-DD format")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate() 