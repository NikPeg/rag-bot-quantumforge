#!/usr/bin/env python3
"""
Скрипт для автоматического тестирования RAG-бота на золотом наборе вопросов.

Оценивает качество ответов бота и сохраняет результаты в лог.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Добавляем путь к task_4 для импорта RAGBot
sys.path.insert(0, str(Path(__file__).parent.parent / "task_4"))

from rag_bot import RAGBot


# Конфигурация
GOLDEN_QUESTIONS_FILE = Path(__file__).parent / "golden_questions.txt"
LOGS_FILE = Path(__file__).parent / "logs.jsonl"
EXPECTED_ANSWERS = {
    # Вопросы, на которые бот должен ответить (известные темы)
    "Кто такой Silk Shadow?": {"should_answer": True},
    "Что такое Starfall City?": {"should_answer": True},
    "Что такое Purge?": {"should_answer": True},
    "Опиши персонажа Grim": {"should_answer": True},
    "Где находится Feast District?": {"should_answer": True},
    "Что такое Reformation?": {"should_answer": True},
    "Кто такой Malachar Morningstar?": {"should_answer": True},
    "Опиши Netherrealm": {"should_answer": True},
    
    # Вопросы, на которые бот должен НЕ ответить (удалённые/отсутствующие темы)
    "Кто такая Zara Morningstar?": {"should_answer": False},
    "Кто такой Korax?": {"should_answer": False},
    "Что такое Twilight Manor?": {"should_answer": False},
    "Кто такой Гарри Поттер?": {"should_answer": False},
    "Что такое квантовая физика?": {"should_answer": False},
    "Где находится Марс?": {"should_answer": False},
    "Опиши персонажа Дарта Вейдера": {"should_answer": False},
}


def load_golden_questions() -> List[str]:
    """Загружает золотой набор вопросов из файла."""
    questions = []
    
    if not GOLDEN_QUESTIONS_FILE.exists():
        print(f"⚠ Файл {GOLDEN_QUESTIONS_FILE} не найден. Используются вопросы по умолчанию.")
        return list(EXPECTED_ANSWERS.keys())
    
    with open(GOLDEN_QUESTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Пропускаем комментарии и пустые строки
            if line and not line.startswith("#"):
                questions.append(line)
    
    return questions


def is_successful_answer(answer: str, chunks_found: int, should_answer: bool) -> bool:
    """
    Определяет, был ли ответ успешным.
    
    Args:
        answer: текст ответа
        chunks_found: количество найденных чанков
        should_answer: должен ли бот ответить на этот вопрос
        
    Returns:
        True, если ответ соответствует ожиданиям
    """
    answer_lower = answer.lower()
    
    # Проверяем, содержит ли ответ фразы "не знаю"
    unknown_phrases = [
        "я не знаю",
        "не знаю",
        "нет информации",
        "не найдено информации",
        "не могу ответить",
    ]
    
    is_unknown = any(phrase in answer_lower for phrase in unknown_phrases)
    
    if should_answer:
        # Бот должен ответить - проверяем, что он не сказал "не знаю"
        # и что нашел чанки
        return not is_unknown and chunks_found > 0
    else:
        # Бот должен НЕ ответить - проверяем, что он сказал "не знаю"
        # или не нашел чанки
        return is_unknown or chunks_found == 0


def evaluate_answer(answer: str, chunks_found: int, should_answer: bool) -> Dict[str, Any]:
    """
    Оценивает качество ответа.
    
    Returns:
        словарь с оценками
    """
    answer_length = len(answer)
    
    # Определяем успешность ответа
    is_successful = is_successful_answer(answer, chunks_found, should_answer)
    
    # Оцениваем полноту ответа (для успешных ответов)
    completeness_score = 0.0
    if is_successful and should_answer:
        # Простая эвристика: чем длиннее ответ, тем полнее (но не слишком)
        if 50 <= answer_length <= 500:
            completeness_score = 1.0
        elif answer_length < 50:
            completeness_score = answer_length / 50.0
        else:
            completeness_score = max(0.5, 1.0 - (answer_length - 500) / 1000.0)
    
    return {
        "is_successful": is_successful,
        "completeness_score": completeness_score,
        "answer_length": answer_length,
    }


def log_query(
    query: str,
    result: Dict[str, Any],
    evaluation: Dict[str, Any],
    should_answer: bool
) -> Dict[str, Any]:
    """
    Формирует запись лога для запроса.
    
    Returns:
        словарь с данными для лога
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "chunks_found": result.get("chunks_found", 0),
        "answer_length": len(result.get("answer", "")),
        "is_successful": evaluation["is_successful"],
        "completeness_score": evaluation["completeness_score"],
        "should_answer": should_answer,
        "sources": result.get("sources", []),
        "answer": result.get("answer", ""),
        "filtered_chunks": result.get("filtered_chunks", 0),
        "input_tokens": result.get("input_tokens", 0),
        "output_tokens": result.get("output_tokens", 0),
        "total_tokens": result.get("total_tokens", 0),
    }
    
    return log_entry


def save_log(log_entry: Dict[str, Any]):
    """Сохраняет запись в лог-файл (JSONL формат)."""
    with open(LOGS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def analyze_logs() -> Dict[str, Any]:
    """Анализирует сохранённые логи и возвращает статистику."""
    if not LOGS_FILE.exists():
        return {}
    
    logs = []
    with open(LOGS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                logs.append(json.loads(line))
    
    if not logs:
        return {}
    
    total = len(logs)
    successful = sum(1 for log in logs if log.get("is_successful", False))
    should_answer_count = sum(1 for log in logs if log.get("should_answer", False))
    should_not_answer_count = total - should_answer_count
    
    # Статистика по вопросам, на которые должны быть ответы
    should_answer_successful = sum(
        1 for log in logs
        if log.get("should_answer", False) and log.get("is_successful", False)
    )
    
    # Статистика по вопросам, на которые НЕ должны быть ответы
    should_not_answer_successful = sum(
        1 for log in logs
        if not log.get("should_answer", True) and log.get("is_successful", False)
    )
    
    # Средняя полнота ответов
    avg_completeness = sum(log.get("completeness_score", 0) for log in logs) / total
    
    # Темы, по которым бот часто не отвечает
    failed_queries = [
        log["query"] for log in logs
        if not log.get("is_successful", False)
    ]
    
    return {
        "total_queries": total,
        "successful_queries": successful,
        "success_rate": successful / total if total > 0 else 0.0,
        "should_answer_count": should_answer_count,
        "should_answer_successful": should_answer_successful,
        "should_answer_success_rate": (
            should_answer_successful / should_answer_count
            if should_answer_count > 0 else 0.0
        ),
        "should_not_answer_count": should_not_answer_count,
        "should_not_answer_successful": should_not_answer_successful,
        "should_not_answer_success_rate": (
            should_not_answer_successful / should_not_answer_count
            if should_not_answer_count > 0 else 0.0
        ),
        "avg_completeness_score": avg_completeness,
        "failed_queries": failed_queries,
    }


def main():
    """Основная функция тестирования."""
    print("=" * 60)
    print("Автоматическое тестирование RAG-бота")
    print("=" * 60)
    
    # Очищаем старый лог
    if LOGS_FILE.exists():
        LOGS_FILE.unlink()
        print(f"Очищен старый лог: {LOGS_FILE}")
    
    # Загружаем золотой набор вопросов
    questions = load_golden_questions()
    print(f"\nЗагружено вопросов: {len(questions)}")
    
    # Инициализируем бота
    print("\nИнициализация RAG-бота...")
    try:
        bot = RAGBot()
    except Exception as e:
        print(f"❌ Ошибка при инициализации бота: {e}")
        return
    
    print("✅ Бот готов к тестированию\n")
    
    # Тестируем каждый вопрос
    print("=" * 60)
    print("Запуск тестирования")
    print("=" * 60)
    
    start_time = time.time()
    
    for i, question in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}] Вопрос: {question}")
        print("-" * 60)
        
        # Определяем ожидаемый результат
        should_answer = EXPECTED_ANSWERS.get(question, {}).get("should_answer", True)
        expected = "должен ответить" if should_answer else "должен НЕ ответить"
        print(f"Ожидание: {expected}")
        
        # Получаем ответ от бота
        try:
            result = bot.answer(question, use_cot=False)  # Отключаем CoT для быстрого тестирования
            
            if not result.get("success", False):
                print(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
                continue
            
            # Оцениваем ответ
            evaluation = evaluate_answer(
                result.get("answer", ""),
                result.get("chunks_found", 0),
                should_answer
            )
            
            # Формируем лог
            log_entry = log_query(question, result, evaluation, should_answer)
            save_log(log_entry)
            
            # Выводим результат
            status = "✅" if evaluation["is_successful"] else "❌"
            print(f"{status} Результат: {'успешно' if evaluation['is_successful'] else 'неуспешно'}")
            print(f"   Найдено чанков: {result.get('chunks_found', 0)}")
            print(f"   Длина ответа: {len(result.get('answer', ''))} символов")
            print(f"   Оценка полноты: {evaluation['completeness_score']:.2f}")
            
            # Показываем краткий ответ
            answer_preview = result.get("answer", "")[:100]
            if len(result.get("answer", "")) > 100:
                answer_preview += "..."
            print(f"   Ответ: {answer_preview}")
            
        except Exception as e:
            print(f"❌ Ошибка при обработке вопроса: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    elapsed_time = time.time() - start_time
    
    # Анализируем результаты
    print("\n" + "=" * 60)
    print("Анализ результатов")
    print("=" * 60)
    
    stats = analyze_logs()
    
    if stats:
        print(f"\nВсего запросов: {stats['total_queries']}")
        print(f"Успешных: {stats['successful_queries']} ({stats['success_rate']*100:.1f}%)")
        print(f"\nВопросы, на которые должен ответить:")
        print(f"  Всего: {stats['should_answer_count']}")
        print(f"  Успешных: {stats['should_answer_successful']} ({stats['should_answer_success_rate']*100:.1f}%)")
        print(f"\nВопросы, на которые должен НЕ ответить:")
        print(f"  Всего: {stats['should_not_answer_count']}")
        print(f"  Успешных: {stats['should_not_answer_successful']} ({stats['should_not_answer_success_rate']*100:.1f}%)")
        print(f"\nСредняя оценка полноты: {stats['avg_completeness_score']:.2f}")
        
        if stats['failed_queries']:
            print(f"\n⚠ Вопросы, на которые бот не ответил корректно:")
            for query in stats['failed_queries']:
                print(f"  - {query}")
    
    print(f"\nВремя выполнения: {elapsed_time:.2f} секунд")
    print(f"Лог сохранён в: {LOGS_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()

