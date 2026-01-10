#!/usr/bin/env python3
"""
Скрипт для замены терминов в текстах базы знаний.
Заменяет все упоминания оригинальных терминов на вымышленные.
"""

import json
import re
from pathlib import Path
from typing import Dict, List


def load_terms_map(terms_map_path: str) -> Dict[str, str]:
    """Загружает словарь замен из JSON файла."""
    with open(terms_map_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Объединяем все категории в один словарь
    terms_map = {}
    for category in data.values():
        if isinstance(category, dict):
            terms_map.update(category)
    
    return terms_map


def create_replacement_patterns(terms_map: Dict[str, str]) -> List[tuple]:
    """
    Создает список паттернов для замены.
    Сортирует по длине (от длинных к коротким), чтобы избежать частичных замен.
    Обрабатывает также формы с апострофами и в разных регистрах.
    """
    patterns = []
    for original, replacement in terms_map.items():
        # Создаем паттерн с границами слов для точного совпадения
        # Также обрабатываем формы с апострофами (Hell's -> Netherrealm's)
        escaped = re.escape(original)
        # Паттерн для обычного слова
        pattern1 = r'\b' + escaped + r'\b'
        patterns.append((pattern1, replacement, len(original)))
        
        # Паттерн для формы с апострофом (Hell's, Charlie's и т.д.)
        pattern2 = r'\b' + escaped + r"'s\b"
        patterns.append((pattern2, replacement + "'s", len(original) + 2))
        
        # Паттерн для формы с апострофом в конце (Hell' -> Netherrealm')
        pattern3 = r'\b' + escaped + r"'\b"
        patterns.append((pattern3, replacement + "'", len(original) + 1))
    
    # Сортируем по длине (от длинных к коротким)
    patterns.sort(key=lambda x: x[2], reverse=True)
    
    return [(pattern, replacement) for pattern, replacement, _ in patterns]


def replace_terms_in_text(text: str, patterns: List[tuple]) -> str:
    """Заменяет все термины в тексте согласно словарю."""
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def process_file(input_path: Path, output_path: Path, patterns: List[tuple]):
    """Обрабатывает один файл: читает, заменяет термины, сохраняет."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        replaced_content = replace_terms_in_text(content, patterns)
        
        # Создаем директорию для выходного файла, если её нет
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(replaced_content)
        
        print(f"✓ Обработан: {input_path.name}")
    except Exception as e:
        print(f"✗ Ошибка при обработке {input_path.name}: {e}")


def main():
    """Основная функция."""
    script_dir = Path(__file__).parent
    terms_map_path = script_dir / 'terms_map.json'
    input_dir = script_dir / 'raw'
    output_dir = script_dir
    
    # Загружаем словарь замен
    terms_map = load_terms_map(str(terms_map_path))
    patterns = create_replacement_patterns(terms_map)
    
    print(f"Загружено {len(terms_map)} терминов для замены")
    print(f"Создано {len(patterns)} паттернов для замены\n")
    
    # Обрабатываем все файлы в директории raw
    if not input_dir.exists():
        print(f"✗ Директория {input_dir} не найдена.")
        print(f"  Сначала запустите download_wiki.py для скачивания страниц вики.")
        return
    
    processed_count = 0
    files_to_process = list(input_dir.glob('*.txt')) + list(input_dir.glob('*.md'))
    
    if not files_to_process:
        print(f"✗ В директории {input_dir} не найдено файлов для обработки.")
        return
    
    print(f"Найдено {len(files_to_process)} файлов для обработки...\n")
    
    for file_path in files_to_process:
        output_path = output_dir / file_path.name
        process_file(file_path, output_path, patterns)
        processed_count += 1
    
    print(f"\n✓ Обработано {processed_count} файлов")
    print(f"  Результаты сохранены в: {output_dir}")


if __name__ == '__main__':
    main()

