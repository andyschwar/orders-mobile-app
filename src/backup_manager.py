#!/usr/bin/env python3
import argparse
from utils.backup import create_backup, restore_backup, list_backups
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='Database Backup Manager')
    parser.add_argument('action', choices=['create', 'restore', 'list'],
                      help='Action to perform (create/restore/list)')
    parser.add_argument('--backup-path', help='Path to backup file (for restore)')
    parser.add_argument('--max-backups', type=int, default=10,
                      help='Maximum number of backups to keep (default: 10)')
    
    args = parser.parse_args()
    
    if args.action == 'create':
        backup_path = create_backup(max_backups=args.max_backups)
        if backup_path:
            print(f"\nBackup created successfully at: {backup_path}")
        else:
            print("\nBackup creation failed!")
            
    elif args.action == 'restore':
        if not args.backup_path:
            print("\nError: --backup-path is required for restore action")
            return
            
        if restore_backup(args.backup_path):
            print("\nDatabase restored successfully!")
        else:
            print("\nRestore failed!")
            
    elif args.action == 'list':
        backups = list_backups()
        if not backups:
            print("\nNo backups found.")
            return
            
        print("\nAvailable backups:")
        print("-" * 80)
        print(f"{'Created at':25} {'Size':10} {'File':44}")
        print("-" * 80)
        
        for backup in backups:
            created = backup['created'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"{created:25} {backup['size']:10} {backup['path']:44}")

if __name__ == "__main__":
    main() 