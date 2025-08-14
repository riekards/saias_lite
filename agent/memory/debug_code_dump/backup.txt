import shutil
import os

def backup_file(filepath):
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, os.path.basename(filepath))
    shutil.copy(filepath, backup_path)
    print(f"Backed up {filepath} to {backup_path}")
