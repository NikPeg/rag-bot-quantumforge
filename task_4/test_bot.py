#!/usr/bin/env python3
"""
Скрипт для тестирования RAG-бота.

Проверяет:
1. Успешные ответы на вопросы из базы знаний
2. Корректные ответы "Я не знаю" на вопросы вне базы знаний
3. Работу Few-shot и Chain-of-Thought
"""

from rag_bot import RAGBot
import sys


def test_successful_queries(bot: RAGBot):
    """Тестирует запросы, на которые бот должен дать ответ."""
    print("\n" + "="*60)
    print("ТЕСТ 1: Запросы с ответами в базе знаний")
    print("="*60)
    
    test_queries = [
        "Что такое Twilight Manor?",
        "Кто такой Korax?",
        "Опиши Netherrealm",
        "Что происходит во время Purge?"
    ]
    
    success_count = 0
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Запрос: {query}")
        print("-" * 60)
        
        result = bot.answer(query, use_cot=True)
        
        if result['success']:
            answer = result['answer']
            print(f"✅ Ответ получен ({len(answer)} символов)")
            print(f"Найдено чанков: {result['chunks_found']}")
            print(f"Источники: {', '.join(result['sources'][:2])}")
            
            # Проверяем, что ответ содержит информацию (не "не знаю")
            if 'не знаю' not in answer.lower() and 'нет информации' not in answer.lower():
                print("✅ Бот дал информативный ответ")
                success_count += 1
            else:
                print("⚠️ Бот ответил 'не знаю', хотя информация должна быть в базе")
        else:
            print(f"❌ Ошибка: {result.get('error')}")
    
    print(f"\n✅ Успешно обработано: {success_count}/{len(test_queries)}")
    return success_count == len(test_queries)


def test_unknown_queries(bot: RAGBot):
    """Тестирует запросы, на которые бот должен ответить 'Я не знаю'."""
    print("\n" + "="*60)
    print("ТЕСТ 2: Запросы без ответов в базе знаний")
    print("="*60)
    
    test_queries = [
        "Как называется столица Марса?",
        "Кто такой Гарри Поттер?",
        "Что такое квантовая физика?",
        "Когда была основана компания Apple?"
    ]
    
    success_count = 0
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Запрос: {query}")
        print("-" * 60)
        
        result = bot.answer(query, use_cot=True)
        
        if result['success']:
            answer = result['answer']
            print(f"Ответ (первые 200 символов): {answer[:200]}...")
            print(f"Найдено чанков: {result['chunks_found']}")
            
            # Проверяем, что бот честно сказал "не знаю"
            if 'не знаю' in answer.lower() or 'нет информации' in answer.lower() or result['chunks_found'] == 0:
                print("✅ Бот корректно ответил 'Я не знаю'")
                success_count += 1
            else:
                print("⚠️ Бот не сказал 'Я не знаю', хотя должен был")
        else:
            print(f"❌ Ошибка: {result.get('error')}")
    
    print(f"\n✅ Корректно обработано: {success_count}/{len(test_queries)}")
    return success_count == len(test_queries)


def test_cot_functionality(bot: RAGBot):
    """Тестирует работу Chain-of-Thought."""
    print("\n" + "="*60)
    print("ТЕСТ 3: Проверка Chain-of-Thought")
    print("="*60)
    
    query = "Кто такой Korax?"
    
    print(f"\nЗапрос: {query}")
    print("-" * 60)
    
    # Тест с CoT
    result_cot = bot.answer(query, use_cot=True)
    
    if result_cot['success']:
        answer_cot = result_cot['answer']
        has_cot = 'рассуждение' in answer_cot.lower() or 'ищу' in answer_cot.lower() or 'шаг' in answer_cot.lower()
        
        if has_cot:
            print("✅ Chain-of-Thought работает (найдены признаки рассуждения)")
            print(f"Ответ с CoT (первые 300 символов):\n{answer_cot[:300]}...")
        else:
            print("⚠️ Chain-of-Thought не обнаружен в ответе")
            return False
    else:
        print(f"❌ Ошибка: {result_cot.get('error')}")
        return False
    
    return True


def test_few_shot_examples(bot: RAGBot):
    """Проверяет, что few-shot примеры загружены."""
    print("\n" + "="*60)
    print("ТЕСТ 4: Проверка Few-shot примеров")
    print("="*60)
    
    examples = bot.few_shot_examples
    
    if examples:
        print(f"✅ Загружено few-shot примеров: {len(examples)}")
        for i, example in enumerate(examples, 1):
            print(f"\nПример {i}:")
            print(f"  Q: {example['question']}")
            print(f"  A: {example['answer'][:100]}...")
        return True
    else:
        print("⚠️ Few-shot примеры не загружены")
        return False


def main():
    """Основная функция тестирования."""
    print("="*60)
    print("ТЕСТИРОВАНИЕ RAG-БОТА")
    print("="*60)
    
    try:
        print("\nИнициализация бота...")
        bot = RAGBot()
        print("✅ Бот успешно инициализирован")
        
        # Запускаем тесты
        test1 = test_successful_queries(bot)
        test2 = test_unknown_queries(bot)
        test3 = test_cot_functionality(bot)
        test4 = test_few_shot_examples(bot)
        
        # Итоги
        print("\n" + "="*60)
        print("ИТОГИ ТЕСТИРОВАНИЯ")
        print("="*60)
        print(f"Тест 1 (Успешные ответы): {'✅ ПРОЙДЕН' if test1 else '❌ ПРОВАЛЕН'}")
        print(f"Тест 2 (Ответы 'Я не знаю'): {'✅ ПРОЙДЕН' if test2 else '❌ ПРОВАЛЕН'}")
        print(f"Тест 3 (Chain-of-Thought): {'✅ ПРОЙДЕН' if test3 else '❌ ПРОВАЛЕН'}")
        print(f"Тест 4 (Few-shot примеры): {'✅ ПРОЙДЕН' if test4 else '❌ ПРОВАЛЕН'}")
        
        all_passed = test1 and test2 and test3 and test4
        
        if all_passed:
            print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            return 0
        else:
            print("\n⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
            return 1
            
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

