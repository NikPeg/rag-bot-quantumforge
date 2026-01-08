#!/usr/bin/env python3
"""
Демонстрация работы RAG-бота.

Показывает примеры успешных ответов и ответов "Я не знаю".
"""

from rag_bot import RAGBot


def main():
    print('='*60)
    print('ДЕМОНСТРАЦИЯ РАБОТЫ RAG-БОТА')
    print('='*60)
    
    try:
        bot = RAGBot()
        
        # Пример 1: Успешный ответ
        print('\n' + '='*60)
        print('Пример 1: Успешный ответ на вопрос из базы знаний')
        print('='*60)
        query = 'Что такое Twilight Manor?'
        print(f'\nЗапрос: {query}')
        print('-'*60)
        
        result = bot.answer(query, use_cot=True)
        if result['success']:
            print(f'\nОтвет:\n{result["answer"][:500]}...')
            print(f'\nНайдено чанков: {result["chunks_found"]}')
            print(f'Источники: {", ".join(result["sources"][:3])}')
            if result.get('total_tokens'):
                print(f'Использовано токенов: {result["total_tokens"]}')
        
        # Пример 2: Ответ "Я не знаю"
        print('\n' + '='*60)
        print('Пример 2: Ответ "Я не знаю" на вопрос вне базы знаний')
        print('='*60)
        query = 'Кто такой Гарри Поттер?'
        print(f'\nЗапрос: {query}')
        print('-'*60)
        
        result = bot.answer(query, use_cot=True)
        if result['success']:
            print(f'\nОтвет: {result["answer"]}')
            print(f'Найдено чанков: {result["chunks_found"]}')
        
        # Пример 3: Еще один успешный ответ
        print('\n' + '='*60)
        print('Пример 3: Еще один успешный ответ')
        print('='*60)
        query = 'Кто такой Korax?'
        print(f'\nЗапрос: {query}')
        print('-'*60)
        
        result = bot.answer(query, use_cot=True)
        if result['success']:
            print(f'\nОтвет (первые 400 символов):\n{result["answer"][:400]}...')
            print(f'\nНайдено чанков: {result["chunks_found"]}')
            print(f'Источники: {", ".join(result["sources"][:2])}')
        
        print('\n' + '='*60)
        print('Демонстрация завершена')
        print('='*60)
        
    except Exception as e:
        print(f'\n❌ Ошибка: {e}')
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

