#!/usr/bin/env python3
"""
Скрипт для создания облака слов из базы знаний.
Помогает проверить, что все имена персонажей были заменены.
"""

from pathlib import Path
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
from collections import Counter


def extract_text_from_files(directory: Path) -> str:
    """Извлекает весь текст из всех файлов в директории."""
    all_text = []
    
    # Исключаем папку raw и служебные файлы
    for file_path in sorted(directory.glob('*.md')):
        # Пропускаем файлы в папке raw
        if 'raw' in str(file_path):
            continue
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                all_text.append(content)
        except Exception as e:
            print(f"Ошибка при чтении {file_path.name}: {e}")
    
    return '\n\n'.join(all_text)


def get_original_terms(terms_map_path: Path) -> set:
    """Получает список оригинальных терминов из словаря замен."""
    import json
    
    with open(terms_map_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    original_terms = set()
    for category in data.values():
        if isinstance(category, dict):
            original_terms.update(category.keys())
    
    return original_terms


def check_for_original_terms(text: str, original_terms: set) -> list:
    """Проверяет, остались ли в тексте оригинальные термины."""
    found_terms = []
    
    # Исключаем заголовки файлов (строки, начинающиеся с #) и названия файлов
    lines = text.split('\n')
    content_lines = []
    for line in lines:
        # Пропускаем заголовки markdown (начинающиеся с #) и пустые строки
        stripped = line.strip()
        if not stripped.startswith('#') and stripped and not stripped.startswith('#'):
            content_lines.append(line)
    content_text = '\n'.join(content_lines).lower()
    
    # Также исключаем паттерны типа "Charlie_Morningstar" (с подчеркиванием в заголовках)
    for term in original_terms:
        # Ищем термин как отдельное слово, но не в составе других слов
        pattern = r'\b' + re.escape(term.lower()) + r'\b'
        # Исключаем случаи, где термин является частью имени файла (с подчеркиванием)
        if re.search(pattern, content_text):
            # Дополнительная проверка: не является ли это частью имени файла
            if not re.search(r'[_\s]' + re.escape(term.lower()) + r'[_\s]', content_text):
                found_terms.append(term)
    
    return found_terms


def create_wordcloud(text: str, output_path: Path, width: int = 1200, height: int = 800):
    """Создает облако слов из текста."""
    # Удаляем очень частые слова (стоп-слова)
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
        'these', 'those', 'he', 'she', 'it', 'they', 'we', 'you', 'i', 'his',
        'her', 'its', 'their', 'our', 'your', 'my', 'me', 'him', 'us', 'them',
        'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
        'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some',
        'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
        'very', 'just', 'now', 'then', 'here', 'there', 'when', 'where', 'why',
        'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
        'too', 'very', 'can', 'will', 'just', 'don', 'should', 'now'
    }
    
    # Создаем WordCloud
    wordcloud = WordCloud(
        width=width,
        height=height,
        background_color='white',
        max_words=200,
        colormap='viridis',
        stopwords=stopwords,
        relative_scaling=0.5,
        min_font_size=10
    ).generate(text)
    
    # Сохраняем изображение
    plt.figure(figsize=(width/100, height/100), facecolor='white', edgecolor='none')
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.tight_layout(pad=0)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✓ Облако слов сохранено: {output_path}")


def main():
    """Основная функция."""
    script_dir = Path(__file__).parent
    knowledge_base_dir = script_dir
    terms_map_path = script_dir / 'terms_map.json'
    output_path = script_dir / 'wordcloud.png'
    
    print("Создание облака слов из базы знаний...\n")
    
    # Извлекаем текст из всех файлов
    print("Извлекаю текст из файлов...")
    text = extract_text_from_files(knowledge_base_dir)
    
    if not text:
        print("✗ Не найдено файлов для анализа.")
        return
    
    print(f"✓ Извлечено {len(text)} символов текста\n")
    
    # Проверяем на наличие оригинальных терминов
    if terms_map_path.exists():
        print("Проверяю на наличие оригинальных терминов...")
        original_terms = get_original_terms(terms_map_path)
        found_terms = check_for_original_terms(text, original_terms)
        
        if found_terms:
            print(f"⚠ ВНИМАНИЕ! Найдены оригинальные термины, которые не были заменены:")
            for term in found_terms[:20]:  # Показываем первые 20
                print(f"  - {term}")
            if len(found_terms) > 20:
                print(f"  ... и ещё {len(found_terms) - 20} терминов")
        else:
            print("✓ Все оригинальные термины успешно заменены!")
        print()
    
    # Создаем облако слов
    print("Создаю облако слов...")
    create_wordcloud(text, output_path)
    
    print(f"\n✓ Готово! Облако слов сохранено в: {output_path}")


if __name__ == '__main__':
    main()

