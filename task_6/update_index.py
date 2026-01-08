#!/usr/bin/env python3
"""
Скрипт для автоматического обновления векторного индекса базы знаний.

Этот скрипт:
1. Сканирует источник данных (knowledge_base/) и находит новые или изменённые документы
2. Разбивает документы на чанки
3. Генерирует эмбеддинги
4. Обновляет векторную БД (добавляет новые чанки, опционально удаляет устаревшие)
5. Логирует процесс обновления
"""

import os
import json
import hashlib
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Set, Optional
from datetime import datetime

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document


# Конфигурация
KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent / "knowledge_base"
INDEX_DIR = Path(__file__).parent.parent / "task_3" / "chroma_db"
STATE_FILE = Path(__file__).parent / "index_state.json"
LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 500  # токенов
CHUNK_OVERLAP = 100  # токенов

# Настройка логирования
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def compute_file_hash(file_path: Path) -> str:
    """Вычисляет SHA256 хеш файла для отслеживания изменений."""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        logger.error(f"Ошибка при вычислении хеша {file_path}: {e}")
        return ""


def load_state() -> Dict[str, Any]:
    """Загружает состояние индекса из файла."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Ошибка при загрузке состояния: {e}")
            return {}
    return {}


def save_state(state: Dict[str, Any]):
    """Сохраняет состояние индекса в файл."""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Ошибка при сохранении состояния: {e}")


def scan_documents() -> List[Path]:
    """Сканирует knowledge_base и возвращает список всех документов для индексации."""
    logger.info(f"Сканирование документов в {KNOWLEDGE_BASE_DIR}...")
    
    documents = []
    excluded_files = {"README.md", "terms_map.json"}
    excluded_dirs = {"raw", "__pycache__", "logs"}
    
    for file_path in KNOWLEDGE_BASE_DIR.rglob("*.md"):
        # Пропускаем файлы из исключённых директорий
        if any(excluded_dir in file_path.parts for excluded_dir in excluded_dirs):
            continue
        
        # Пропускаем исключённые файлы
        if file_path.name in excluded_files:
            continue
        
        documents.append(file_path)
    
    logger.info(f"Найдено {len(documents)} документов для проверки")
    return documents


def find_changed_files(
    documents: List[Path],
    state: Dict[str, Any]
) -> tuple[List[Path], List[Path], Set[str]]:
    """
    Находит новые и изменённые файлы.
    
    Returns:
        tuple: (новые_файлы, изменённые_файлы, удалённые_файлы_хеши)
    """
    current_hashes = {}
    new_files = []
    changed_files = []
    previous_hashes = state.get("file_hashes", {})
    
    for file_path in documents:
        file_hash = compute_file_hash(file_path)
        file_str = str(file_path)
        current_hashes[file_str] = file_hash
        
        if file_str not in previous_hashes:
            new_files.append(file_path)
            logger.info(f"Новый файл: {file_path}")
        elif previous_hashes[file_str] != file_hash:
            changed_files.append(file_path)
            logger.info(f"Изменённый файл: {file_path}")
    
    # Находим удалённые файлы
    deleted_files = set(previous_hashes.keys()) - set(current_hashes.keys())
    if deleted_files:
        logger.info(f"Удалённые файлы: {len(deleted_files)}")
        for deleted in deleted_files:
            logger.info(f"  - {deleted}")
    
    return new_files, changed_files, deleted_files


def load_documents(file_paths: List[Path]) -> List[Document]:
    """Загружает документы из указанных файлов."""
    documents = []
    
    for file_path in file_paths:
        try:
            loader = TextLoader(str(file_path), encoding="utf-8")
            docs = loader.load()
            for doc in docs:
                doc.metadata["source"] = str(file_path)
            documents.extend(docs)
        except Exception as e:
            logger.error(f"Ошибка при загрузке {file_path}: {e}")
            continue
    
    return documents


def split_documents(documents: List[Document]) -> List[Document]:
    """Разбивает документы на чанки с сохранением метаданных."""
    logger.info(f"Разбиение {len(documents)} документов на чанки...")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    
    chunks = []
    for doc in documents:
        source_path = doc.metadata.get("source", "")
        file_name = os.path.basename(source_path) if source_path else "unknown"
        
        doc_chunks = text_splitter.split_documents([doc])
        
        for idx, chunk in enumerate(doc_chunks):
            chunk.metadata.update({
                "source": source_path,
                "file_name": file_name,
                "chunk_index": idx,
                "total_chunks": len(doc_chunks),
                "indexed_at": datetime.now().isoformat(),
            })
            chunks.append(chunk)
    
    logger.info(f"Создано {len(chunks)} чанков из {len(documents)} документов")
    return chunks


def update_vector_index(
    vectorstore: Chroma,
    chunks: List[Document],
    deleted_files: Set[str]
) -> Dict[str, Any]:
    """
    Обновляет векторный индекс: добавляет новые чанки и удаляет устаревшие.
    
    Args:
        vectorstore: существующий векторный индекс
        chunks: новые чанки для добавления
        deleted_files: множество путей к удалённым файлам
    
    Returns:
        словарь со статистикой обновления
    """
    stats = {
        "added_chunks": 0,
        "deleted_chunks": 0,
        "total_chunks_before": 0,
        "total_chunks_after": 0
    }
    
    # Получаем текущее количество чанков
    try:
        collection = vectorstore._collection
        stats["total_chunks_before"] = collection.count()
    except Exception as e:
        logger.warning(f"Не удалось получить количество чанков: {e}")
    
    # Добавляем новые чанки
    if chunks:
        logger.info(f"Добавление {len(chunks)} новых чанков в индекс...")
        try:
            vectorstore.add_documents(chunks)
            stats["added_chunks"] = len(chunks)
            logger.info(f"✅ Добавлено {len(chunks)} чанков")
        except Exception as e:
            logger.error(f"Ошибка при добавлении чанков: {e}")
            raise
    
    # Удаляем чанки из удалённых файлов
    if deleted_files:
        logger.info(f"Удаление чанков из {len(deleted_files)} удалённых файлов...")
        try:
            # Получаем все документы из индекса
            all_docs = vectorstore.get()
            
            # Находим IDs чанков для удаления
            ids_to_delete = []
            for i, source in enumerate(all_docs.get("metadatas", [])):
                if source and "source" in source:
                    source_path = source["source"]
                    if source_path in deleted_files:
                        ids_to_delete.append(all_docs["ids"][i])
            
            if ids_to_delete:
                logger.info(f"Удаление {len(ids_to_delete)} чанков...")
                vectorstore.delete(ids=ids_to_delete)
                stats["deleted_chunks"] = len(ids_to_delete)
                logger.info(f"✅ Удалено {len(ids_to_delete)} чанков")
        except Exception as e:
            logger.warning(f"Ошибка при удалении чанков: {e}")
            # Не критично, продолжаем работу
    
    # Получаем финальное количество чанков
    try:
        collection = vectorstore._collection
        stats["total_chunks_after"] = collection.count()
    except Exception as e:
        logger.warning(f"Не удалось получить финальное количество чанков: {e}")
    
    return stats


def load_or_create_index() -> Chroma:
    """Загружает существующий индекс или создаёт новый."""
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    
    if INDEX_DIR.exists():
        logger.info(f"Загрузка существующего индекса из {INDEX_DIR}...")
        vectorstore = Chroma(
            persist_directory=str(INDEX_DIR),
            embedding_function=embeddings,
        )
        logger.info("✅ Индекс загружен")
    else:
        logger.info(f"Создание нового индекса в {INDEX_DIR}...")
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        # Создаём пустой индекс
        vectorstore = Chroma(
            persist_directory=str(INDEX_DIR),
            embedding_function=embeddings,
        )
        logger.info("✅ Новый индекс создан")
    
    return vectorstore


def main():
    """Основная функция обновления индекса."""
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("Автоматическое обновление векторного индекса")
    logger.info("=" * 60)
    logger.info(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Источник данных: {KNOWLEDGE_BASE_DIR}")
    logger.info(f"Индекс: {INDEX_DIR}")
    logger.info("=" * 60)
    
    try:
        # Шаг 1: Загрузка состояния
        state = load_state()
        logger.info("Состояние загружено")
        
        # Шаг 2: Сканирование документов
        all_documents = scan_documents()
        
        # Шаг 3: Поиск изменений
        new_files, changed_files, deleted_files = find_changed_files(all_documents, state)
        
        files_to_process = new_files + changed_files
        
        if not files_to_process and not deleted_files:
            logger.info("✅ Нет изменений. Индекс актуален.")
            return {
                "success": True,
                "message": "Нет изменений",
                "new_files": 0,
                "changed_files": 0,
                "deleted_files": 0,
                "added_chunks": 0,
                "deleted_chunks": 0,
                "elapsed_time": time.time() - start_time
            }
        
        logger.info(f"Найдено изменений: {len(new_files)} новых, {len(changed_files)} изменённых, {len(deleted_files)} удалённых")
        
        # Шаг 4: Загрузка и обработка новых/изменённых документов
        chunks = []
        if files_to_process:
            documents = load_documents(files_to_process)
            chunks = split_documents(documents)
        
        # Шаг 5: Загрузка/создание индекса
        vectorstore = load_or_create_index()
        
        # Шаг 6: Обновление индекса
        stats = update_vector_index(vectorstore, chunks, deleted_files)
        
        # Шаг 7: Обновление состояния
        # Вычисляем хеши всех файлов для следующего запуска
        current_hashes = {}
        for file_path in all_documents:
            file_str = str(file_path)
            current_hashes[file_str] = compute_file_hash(file_path)
        
        state["file_hashes"] = current_hashes
        state["last_update"] = datetime.now().isoformat()
        state["last_stats"] = stats
        save_state(state)
        
        # Шаг 8: Итоговая статистика
        elapsed_time = time.time() - start_time
        logger.info("=" * 60)
        logger.info("Статистика обновления")
        logger.info("=" * 60)
        logger.info(f"Новых файлов: {len(new_files)}")
        logger.info(f"Изменённых файлов: {len(changed_files)}")
        logger.info(f"Удалённых файлов: {len(deleted_files)}")
        logger.info(f"Добавлено чанков: {stats['added_chunks']}")
        logger.info(f"Удалено чанков: {stats['deleted_chunks']}")
        logger.info(f"Всего чанков до: {stats['total_chunks_before']}")
        logger.info(f"Всего чанков после: {stats['total_chunks_after']}")
        logger.info(f"Время выполнения: {elapsed_time:.2f} секунд")
        logger.info("=" * 60)
        logger.info("✅ Обновление завершено успешно")
        
        return {
            "success": True,
            "new_files": len(new_files),
            "changed_files": len(changed_files),
            "deleted_files": len(deleted_files),
            "added_chunks": stats["added_chunks"],
            "deleted_chunks": stats["deleted_chunks"],
            "total_chunks_before": stats["total_chunks_before"],
            "total_chunks_after": stats["total_chunks_after"],
            "elapsed_time": elapsed_time
        }
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "elapsed_time": time.time() - start_time
        }


if __name__ == "__main__":
    result = main()
    exit(0 if result.get("success", False) else 1)

