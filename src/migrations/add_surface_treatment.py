from sqlalchemy import create_engine, text
import os
import json

def get_database_path():
    """Get database path from config or use default"""
    config_file = os.path.expanduser('~/Library/Application Support/Orders/config.json')
    
    # Try to read config file
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                if 'database_path' in config:
                    return config['database_path']
        except Exception as e:
            print(f"Could not read config file: {e}")
    
    # Default to local database
    db_dir = os.path.expanduser('~/Library/Application Support/Orders')
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, 'orders.db')

def migrate():
    """Add surface_treatment column to order_items table and calculate values for existing records"""
    try:
        # Get database path from config
        db_path = get_database_path()
        print(f"Using database: {db_path}")
        
        # Create engine
        engine = create_engine(f'sqlite:///{db_path}')
        
        # Check if the column already exists
        with engine.connect() as conn:
            # Check if surface_treatment column exists
            result = conn.execute(text("""
                PRAGMA table_info(order_items)
            """))
            columns = [row[1] for row in result]
            
            if 'surface_treatment' not in columns:
                print("Adding surface_treatment column...")
                conn.execute(text("""
                    ALTER TABLE order_items 
                    ADD COLUMN surface_treatment VARCHAR(20)
                """))
                print("Column added successfully.")
            else:
                print("surface_treatment column already exists.")
            
            # Update existing records with calculated values based on business logic
            # First, get all order items that need surface treatment calculation
            result = conn.execute(text("""
                SELECT oi.id, oi.item_id, i.customer_item_name, c.name_index
                FROM order_items oi
                JOIN items i ON oi.item_id = i.id
                JOIN customers c ON i.customer_id = c.id
                WHERE oi.surface_treatment IS NULL
            """))
            
            rows = result.fetchall()
            print(f"Found {len(rows)} order items that need surface treatment calculation.")
            
            if rows:
                # List of customer indices that use FOSFAT
                fosfat_customers = [
                    "ARAD", "DROBETA", "CARACAL", "POPRAD", 
                    "TREBIŠOV", "TLMAČE", "DAKO"
                ]
                
                updated_count = 0
                for row in rows:
                    order_item_id = row[0]
                    customer_item_name = row[2]
                    customer_index = row[3]
                    
                    # Calculate surface treatment based on business logic
                    surface_treatment = "KATAFOREZA"  # Default
                    
                    # Check if item name contains 'kataf'
                    if customer_item_name and "kataf" in customer_item_name.lower():
                        surface_treatment = "KATAFOREZA"
                    # Check if item name contains 'zinek'
                    elif customer_item_name and "zinek" in customer_item_name.lower():
                        surface_treatment = "ZINEK"
                    # Check if customer index is in fosfat list
                    elif customer_index in fosfat_customers:
                        surface_treatment = "FOSFAT"
                    
                    # Update the order item
                    conn.execute(text("""
                        UPDATE order_items 
                        SET surface_treatment = :surface_treatment
                        WHERE id = :order_item_id
                    """), {
                        "surface_treatment": surface_treatment,
                        "order_item_id": order_item_id
                    })
                    updated_count += 1
                
                print(f"Updated {updated_count} order items with surface treatment.")
            else:
                print("No order items need surface treatment calculation.")
            
            conn.commit()
            
        print("Migration completed successfully!")
        print("Surface treatment calculated for existing order items based on business logic.")
        return True
        
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    migrate() 