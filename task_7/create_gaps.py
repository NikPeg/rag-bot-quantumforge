#!/usr/bin/env python3
"""
Скрипт для создания искусственных пробелов в базе знаний.

Удаляет 2-3 ключевые сущности из базы знаний для тестирования
поведения бота при отсутствии информации.
"""

import shutil
from pathlib import Path

# Путь к базе знаний
KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent / "knowledge_base"
BACKUP_DIR = Path(__file__).parent / "backup_removed_files"

# Файлы для удаления (ключевые сущности)
FILES_TO_REMOVE = [
    "39_Charlie_Morningstar.md",  # Zara Morningstar - главный персонаж
    "88_Alastor.md",  # Korax - важный персонаж
    "138_Hazbin_Hotel.md",  # Twilight Manor - ключевая локация
]

def create_backup():
    """Создаёт резервную копию файлов перед удалением."""
    BACKUP_DIR.mkdir(exist_ok=True)
    print(f"Создание резервной копии в {BACKUP_DIR}...")
    
    for filename in FILES_TO_REMOVE:
        source = KNOWLEDGE_BASE_DIR / filename
        if source.exists():
            dest = BACKUP_DIR / filename
            shutil.copy2(source, dest)
            print(f"  ✓ Скопирован {filename}")
    
    print(f"Резервная копия создана в {BACKUP_DIR}")

def remove_files():
    """Удаляет указанные файлы из базы знаний."""
    print("\nУдаление файлов из базы знаний...")
    
    removed_count = 0
    for filename in FILES_TO_REMOVE:
        file_path = KNOWLEDGE_BASE_DIR / filename
        if file_path.exists():
            file_path.unlink()
            print(f"  ✓ Удалён {filename}")
            removed_count += 1
        else:
            print(f"  ⚠ Файл {filename} не найден")
    
    print(f"\nУдалено файлов: {removed_count}/{len(FILES_TO_REMOVE)}")
    return removed_count

def main():
    """Основная функция."""
    print("=" * 60)
    print("Создание искусственных пробелов в базе знаний")
    print("=" * 60)
    print("\nУдаляемые сущности:")
    print("  1. Zara Morningstar (главный персонаж)")
    print("  2. Korax (важный персонаж)")
    print("  3. Twilight Manor (ключевая локация)")
    print("=" * 60)
    
    # Создаём резервную копию
    create_backup()
    
    # Удаляем файлы
    removed = remove_files()
    
    if removed > 0:
        print("\n" + "=" * 60)
        print("✅ Пробелы в базе знаний созданы успешно!")
        print("=" * 60)
        print("\n⚠ ВАЖНО: После тестирования восстановите файлы командой:")
        print(f"  python restore_gaps.py")
        print("=" * 60)
    else:
        print("\n⚠ Ошибка: файлы не были удалены")

if __name__ == "__main__":
    main()

