#!/usr/bin/env python3
"""
Скрипт для восстановления удалённых файлов из резервной копии.
"""

import shutil
from pathlib import Path

KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent / "knowledge_base"
BACKUP_DIR = Path(__file__).parent / "backup_removed_files"

def restore_files():
    """Восстанавливает файлы из резервной копии."""
    if not BACKUP_DIR.exists():
        print(f"Ошибка: резервная копия не найдена в {BACKUP_DIR}")
        return
    
    print(f"Восстановление файлов из {BACKUP_DIR}...")
    
    restored_count = 0
    for backup_file in BACKUP_DIR.glob("*.md"):
        dest = KNOWLEDGE_BASE_DIR / backup_file.name
        shutil.copy2(backup_file, dest)
        print(f"  ✓ Восстановлен {backup_file.name}")
        restored_count += 1
    
    print(f"\nВосстановлено файлов: {restored_count}")

if __name__ == "__main__":
    restore_files()

