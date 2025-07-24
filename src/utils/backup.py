import os
import shutil
from datetime import datetime
import glob

def create_backup(db_path=None, backup_dir='backups', max_backups=10):
    """
    Create a backup of the database file.
    
    Args:
        db_path (str): Path to the database file (if None, uses current database path)
        backup_dir (str): Directory to store backups
        max_backups (int): Maximum number of backups to keep
    
    Returns:
        str: Path to the created backup file or None if backup failed
    """
    try:
        # Get the current database path if not provided
        if db_path is None:
            from models.database import get_database_path
            db_path = get_database_path()
        
        # Ensure the backup directory exists
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            print(f"Created backup directory: {backup_dir}")
        
        # Generate timestamp for the backup file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"orders_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Create the backup
        shutil.copy2(db_path, backup_path)
        print(f"Created backup: {backup_path}")
        
        # Clean up old backups if necessary
        existing_backups = sorted(glob.glob(os.path.join(backup_dir, "orders_backup_*.db")))
        if len(existing_backups) > max_backups:
            backups_to_delete = existing_backups[:-max_backups]
            for old_backup in backups_to_delete:
                os.remove(old_backup)
                print(f"Removed old backup: {old_backup}")
        
        return backup_path
    
    except Exception as e:
        print(f"Error creating backup: {str(e)}")
        return None

def restore_backup(backup_path, db_path='orders.db'):
    """
    Restore a database from a backup file.
    
    Args:
        backup_path (str): Path to the backup file
        db_path (str): Path where to restore the database
    
    Returns:
        bool: True if restore was successful, False otherwise
    """
    try:
        # Create a backup of the current database before restoring
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pre_restore_backup = f"orders_pre_restore_{timestamp}.db"
        shutil.copy2(db_path, pre_restore_backup)
        print(f"Created pre-restore backup: {pre_restore_backup}")
        
        # Restore the backup
        shutil.copy2(backup_path, db_path)
        print(f"Successfully restored backup: {backup_path}")
        return True
    
    except Exception as e:
        print(f"Error restoring backup: {str(e)}")
        return False

def list_backups(backup_dir='backups'):
    """
    List all available backups.
    
    Args:
        backup_dir (str): Directory containing backups
    
    Returns:
        list: List of backup files with their creation times
    """
    try:
        if not os.path.exists(backup_dir):
            return []
        
        backups = []
        for backup in glob.glob(os.path.join(backup_dir, "orders_backup_*.db")):
            creation_time = datetime.fromtimestamp(os.path.getctime(backup))
            size = os.path.getsize(backup) / (1024 * 1024)  # Convert to MB
            backups.append({
                'path': backup,
                'created': creation_time,
                'size': f"{size:.2f} MB"
            })
        
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    except Exception as e:
        print(f"Error listing backups: {str(e)}")
        return [] 