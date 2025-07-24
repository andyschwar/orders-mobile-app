import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.expanduser('~/Library/Application Support/Orders'), 'orders.db')
    print(f"Using database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # First check if the column exists and get its type
        cursor.execute("PRAGMA table_info(employees)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        print(f"Current table columns: {columns}")
        
        if 'name_day' not in columns:
            print("name_day column does not exist, creating it...")
            cursor.execute("ALTER TABLE employees ADD COLUMN name_day VARCHAR(5)")
        
        # Add some test name days (in D.M. format, will convert to MM-DD)
        test_data = [
            ('John Doe', '1.1.'),  # New Year
            ('Kalčicová Zdeňka', '23.6.'),  # Zdeňka
            ('Benák Martin', '11.11.'),  # Martin
            ('Kalčic Vlastimil', '27.6.'),  # Vlastimil
            ('Škodák David', '30.12.'),  # David
            ('Benák David', '30.12.'),  # David
            ('Míšek Stanislav', '13.11.'),  # Stanislav
            ('Horáková Iveta', '1.6.'),  # Iveta
            ('Grmela Patrik', '19.3.'),  # Josef
            ('Mrowietz Petr', '29.6.'),  # Petr a Pavel
            ('Schwär Andrea', '26.7.'),  # Anna
            ('Míšek st.', '13.11.'),  # Stanislav
            ('Horák Tomáš', '7.3.'),  # Tomáš
            ('Volný Stanislav', '13.11.'),  # Stanislav
            ('Schwär Petr', '29.6.')  # Petr a Pavel
        ]
        
        # Update name days
        for name, name_day in test_data:
            # Convert from D.M. format to MM-DD format
            if name_day and '.' in name_day:
                # Remove trailing dot and split by dot
                clean_name_day = name_day.rstrip('.')
                day, month = map(int, clean_name_day.split('.'))
                mm_dd_format = f"{month:02d}-{day:02d}"
            else:
                mm_dd_format = name_day
                
            print(f"Updating {name} with name day {name_day} -> {mm_dd_format}")
            cursor.execute(
                "UPDATE employees SET name_day = ? WHERE name = ?",
                (mm_dd_format, name)
            )
            # Check if the update affected any rows
            if cursor.rowcount == 0:
                print(f"Warning: No employee found with name '{name}'")
            else:
                print(f"Updated name day for {name} to {mm_dd_format}")
        
        # Verify the updates
        print("\nVerifying updates:")
        cursor.execute("SELECT name, name_day FROM employees WHERE name_day IS NOT NULL")
        results = cursor.fetchall()
        for name, name_day in results:
            print(f"{name}: {name_day}")
        
        conn.commit()
        print("\nTest name days added successfully")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        conn.rollback()
    finally:
        conn.close() 