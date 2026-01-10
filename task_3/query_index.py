#!/usr/bin/env python3
"""
Пример использования векторного индекса для поиска релевантных документов.

Этот скрипт демонстрирует, как загрузить созданный индекс и выполнить поиск.
"""

from pathlib import Path
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    # Fallback для старых версий
    from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma


INDEX_DIR = Path(__file__).parent / "chroma_db"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_index():
    """Загружает векторный индекс из ChromaDB."""
    if not INDEX_DIR.exists():
        print(f"Ошибка: индекс не найден в {INDEX_DIR}")
        print("Сначала запустите build_index.py для создания индекса")
        return None
    
    print(f"Загрузка индекса из {INDEX_DIR}...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    
    vectorstore = Chroma(
        persist_directory=str(INDEX_DIR),
        embedding_function=embeddings,
    )
    
    print("Индекс загружен успешно")
    return vectorstore


def search(vectorstore: Chroma, query: str, k: int = 3):
    """Выполняет поиск по индексу."""
    print(f"\n{'='*60}")
    print(f"Запрос: {query}")
    print(f"{'='*60}")
    
    # Поиск с оценкой релевантности
    results = vectorstore.similarity_search_with_score(query, k=k)
    
    if not results:
        print("Результаты не найдены")
        return
    
    for i, (doc, score) in enumerate(results, 1):
        print(f"\nРезультат {i} (релевантность: {score:.4f}):")
        print(f"  Файл: {doc.metadata.get('file_name', 'unknown')}")
        print(f"  Чанк: {doc.metadata.get('chunk_index', 'unknown')} из {doc.metadata.get('total_chunks', 'unknown')}")
        print(f"  Источник: {doc.metadata.get('source', 'unknown')}")
        print(f"  Текст:")
        # Показываем первые 300 символов
        text_preview = doc.page_content[:300]
        if len(doc.page_content) > 300:
            text_preview += "..."
        print(f"    {text_preview}")


def main():
    """Основная функция."""
    # Загружаем индекс
    vectorstore = load_index()
    if vectorstore is None:
        return
    
    # Примеры запросов
    test_queries = [
        "Что такое Eclipse Manor?",
        "Кто такой Korax?",
        "Опиши Netherrealm",
        "Какие персонажи живут в Eclipse Manor?",
        "Что происходит во время Purge?",
    ]
    
    print("\n" + "="*60)
    print("Примеры поиска по индексу")
    print("="*60)
    
    for query in test_queries:
        search(vectorstore, query, k=3)
        print("\n")
    
    # Интерактивный режим
    print("\n" + "="*60)
    print("Интерактивный режим (введите 'exit' для выхода)")
    print("="*60)
    
    while True:
        try:
            query = input("\nВведите запрос: ").strip()
            if not query:
                continue
            if query.lower() in ['exit', 'quit', 'выход']:
                break
            search(vectorstore, query, k=3)
        except KeyboardInterrupt:
            print("\n\nВыход...")
            break
        except Exception as e:
            print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()

