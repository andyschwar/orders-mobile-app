import os
import stat
import sys

def fix_database_permissions():
    """Fix permissions on the database file to ensure it's writable."""
    if getattr(sys, 'frozen', False):
        # Running in a bundle
        db_path = os.path.join(os.path.dirname(sys.executable), 'orders.db')
    else:
        # Running in normal Python environment
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'orders.db')
    
    if os.path.exists(db_path):
        try:
            # Set read/write permissions for owner and group
            os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)
            print(f"Successfully set permissions on {db_path}")
        except Exception as e:
            print(f"Error setting permissions on {db_path}: {e}")
    else:
        print(f"Database file not found at {db_path}") 