#!/usr/bin/env python3
"""
Скрипт для создания векторного индекса базы знаний.

Этот скрипт:
1. Загружает все документы из knowledge_base/
2. Разбивает их на чанки (100-300 слов или 500-1000 токенов)
3. Генерирует эмбеддинги с помощью sentence-transformers/all-MiniLM-L6-v2
4. Сохраняет индекс в ChromaDB с метаданными
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    # Fallback для старых версий
    from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document


# Конфигурация
KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent / "knowledge_base"
INDEX_DIR = Path(__file__).parent / "chroma_db"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 500  # токенов
CHUNK_OVERLAP = 100  # токенов


def load_documents() -> List[Document]:
    """Загружает все .md документы из knowledge_base, исключая папку raw."""
    print(f"Загрузка документов из {KNOWLEDGE_BASE_DIR}...")
    
    documents = []
    excluded_files = {"README.md", "terms_map.json"}
    excluded_dirs = {"raw", "__pycache__"}
    
    # Проходим по всем файлам в knowledge_base
    for file_path in KNOWLEDGE_BASE_DIR.rglob("*.md"):
        # Пропускаем файлы из исключённых директорий
        if any(excluded_dir in file_path.parts for excluded_dir in excluded_dirs):
            continue
        
        # Пропускаем исключённые файлы
        if file_path.name in excluded_files:
            continue
        
        try:
            loader = TextLoader(str(file_path), encoding="utf-8")
            docs = loader.load()
            # Обновляем метаданные с правильным путём
            for doc in docs:
                doc.metadata["source"] = str(file_path)
            documents.extend(docs)
        except Exception as e:
            print(f"Ошибка при загрузке {file_path}: {e}")
            continue
    
    print(f"Загружено {len(documents)} документов")
    return documents


def split_documents(documents: List[Document]) -> List[Document]:
    """Разбивает документы на чанки с сохранением метаданных."""
    print(f"Разбиение документов на чанки (размер: {CHUNK_SIZE} токенов, overlap: {CHUNK_OVERLAP})...")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    
    chunks = []
    for doc in documents:
        # Извлекаем имя файла из source
        source_path = doc.metadata.get("source", "")
        file_name = os.path.basename(source_path) if source_path else "unknown"
        
        # Разбиваем документ на чанки
        doc_chunks = text_splitter.split_documents([doc])
        
        # Добавляем метаданные к каждому чанку
        for idx, chunk in enumerate(doc_chunks):
            chunk.metadata.update({
                "source": source_path,
                "file_name": file_name,
                "chunk_index": idx,
                "total_chunks": len(doc_chunks),
            })
            chunks.append(chunk)
    
    print(f"Создано {len(chunks)} чанков из {len(documents)} документов")
    return chunks


def create_embeddings():
    """Создаёт модель эмбеддингов."""
    print(f"Инициализация модели эмбеддингов: {EMBEDDING_MODEL}...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},  # Используем CPU по умолчанию
        encode_kwargs={"normalize_embeddings": True},  # Нормализация для косинусного расстояния
    )
    # Тестируем размерность на примере
    test_embedding = embeddings.embed_query("test")
    print(f"Размерность эмбеддингов: {len(test_embedding)}")
    return embeddings


def build_index(chunks: List[Document], embeddings) -> Chroma:
    """Создаёт векторный индекс в ChromaDB."""
    print(f"Создание векторного индекса в {INDEX_DIR}...")
    
    # Удаляем старый индекс, если существует
    if INDEX_DIR.exists():
        import shutil
        shutil.rmtree(INDEX_DIR)
        print("Удалён старый индекс")
    
    # Создаём новый индекс
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(INDEX_DIR),
    )
    
    # Индекс автоматически сохраняется на диск в Chroma 0.4.x+
    # vectorstore.persist() больше не нужен
    print(f"Индекс сохранён в {INDEX_DIR}")
    
    return vectorstore


def test_index(vectorstore: Chroma):
    """Тестирует индекс на примере запроса."""
    print("\n" + "="*60)
    print("Тестирование индекса")
    print("="*60)
    
    test_queries = [
        "Что такое Eclipse Manor?",
        "Кто такой Korax?",
        "Опиши Netherrealm",
    ]
    
    for query in test_queries:
        print(f"\nЗапрос: {query}")
        print("-" * 60)
        
        # Ищем топ-3 наиболее релевантных чанка
        results = vectorstore.similarity_search_with_score(query, k=3)
        
        for i, (doc, score) in enumerate(results, 1):
            print(f"\nРезультат {i} (score: {score:.4f}):")
            print(f"  Файл: {doc.metadata.get('file_name', 'unknown')}")
            print(f"  Чанк: {doc.metadata.get('chunk_index', 'unknown')}")
            print(f"  Текст: {doc.page_content[:200]}...")


def main():
    """Основная функция."""
    start_time = time.time()
    
    print("="*60)
    print("Создание векторного индекса базы знаний")
    print("="*60)
    print(f"Модель эмбеддингов: {EMBEDDING_MODEL}")
    print(f"Размер чанка: {CHUNK_SIZE} токенов")
    print(f"Overlap: {CHUNK_OVERLAP} токенов")
    print(f"Векторная БД: ChromaDB")
    print("="*60 + "\n")
    
    # Шаг 1: Загрузка документов
    documents = load_documents()
    
    if not documents:
        print("Ошибка: не найдено документов для индексации")
        return
    
    # Шаг 2: Разбиение на чанки
    chunks = split_documents(documents)
    
    # Шаг 3: Создание модели эмбеддингов
    embeddings = create_embeddings()
    
    # Шаг 4: Построение индекса
    vectorstore = build_index(chunks, embeddings)
    
    # Шаг 5: Тестирование
    test_index(vectorstore)
    
    # Статистика
    elapsed_time = time.time() - start_time
    print("\n" + "="*60)
    print("Статистика индексации")
    print("="*60)
    print(f"Документов обработано: {len(documents)}")
    print(f"Чанков создано: {len(chunks)}")
    print(f"Время индексации: {elapsed_time:.2f} секунд")
    print(f"Средняя скорость: {len(chunks)/elapsed_time:.2f} чанков/сек")
    print(f"Индекс сохранён в: {INDEX_DIR}")
    print("="*60)


if __name__ == "__main__":
    main()

