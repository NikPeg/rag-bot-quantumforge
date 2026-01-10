#!/usr/bin/env python3
"""
Скрипт для тестирования различных LLM моделей через OpenRouter API
Сравнивает качество и скорость ответов разных моделей
"""

import os
import json
import time
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from pathlib import Path

# Загружаем переменные окружения из .env в корне проекта
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Пробуем разные варианты имени переменной
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY') or os.getenv('AI_OPENROUTER_API_KEY')
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


# Модели для тестирования
MODELS_TO_TEST = [
    {
        "id": "xiaomi/mimo-v2-flash:free",
        "name": "Xiaomi MiMo-V2-Flash",
        "provider": "OpenRouter",
        "cost_input": 0,
        "cost_output": 0,
        "context": 256000,
        "description": "Бесплатная open-source модель, топ #1 на SWE-bench"
    },
    {
        "id": "anthropic/claude-sonnet-4.5",
        "name": "Claude Sonnet 4.5",
        "provider": "OpenRouter",
        "cost_input": 3.0,
        "cost_output": 15.0,
        "context": 1000000,
        "description": "Топовая модель от Anthropic для агентов и кодирования"
    },
    {
        "id": "google/gemini-2.5-flash",
        "name": "Google Gemini 2.5 Flash",
        "provider": "OpenRouter",
        "cost_input": 0.30,
        "cost_output": 2.50,
        "context": 1050000,
        "description": "State-of-the-art для reasoning и кодирования"
    },
    {
        "id": "google/gemini-3-flash-preview",
        "name": "Google Gemini 3 Flash Preview",
        "provider": "OpenRouter",
        "cost_input": 0.50,
        "cost_output": 3.0,
        "context": 1050000,
        "description": "Preview версия с мультимодальностью"
    },
    {
        "id": "deepseek/deepseek-v3.2",
        "name": "DeepSeek V3.2",
        "provider": "OpenRouter",
        "cost_input": 0.25,
        "cost_output": 0.38,
        "context": 164000,
        "description": "Эффективная модель с reasoning, очень дешёвая"
    },
]


def test_model(
    model_id: str,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 500
) -> Dict[str, Any]:
    """
    Тестирует модель через OpenRouter API
    
    Args:
        model_id: ID модели в OpenRouter
        prompt: текст запроса
        temperature: температура генерации
        max_tokens: максимальное количество токенов в ответе
        
    Returns:
        словарь с результатами теста
    """
    if not OPENROUTER_API_KEY:
        return {
            "success": False,
            "error": "OPENROUTER_API_KEY не найден в .env файле"
        }
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/rag-bot-quantumforge",
        "X-Title": "RAG Bot QuantumForge"
    }
    
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "")
                
                # Получаем информацию об использовании токенов
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                
                return {
                    "success": True,
                    "content": content,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": usage.get("total_tokens", 0),
                    "response_time": elapsed_time,
                    "model_info": data.get("model", model_id)
                }
            else:
                return {
                    "success": False,
                    "error": "Пустой ответ от API",
                    "response": data
                }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "response_time": elapsed_time
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Таймаут запроса (>60 сек)"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Ошибка: {str(e)}"
        }


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    cost_per_m_input: float,
    cost_per_m_output: float
) -> float:
    """Рассчитывает стоимость запроса"""
    input_cost = (input_tokens / 1_000_000) * cost_per_m_input
    output_cost = (output_tokens / 1_000_000) * cost_per_m_output
    return input_cost + output_cost


def compare_models(test_prompt: str) -> List[Dict[str, Any]]:
    """
    Сравнивает все модели на одном промпте
    
    Args:
        test_prompt: промпт для тестирования
        
    Returns:
        список результатов для каждой модели
    """
    results = []
    
    print("=" * 80)
    print("Сравнение LLM моделей через OpenRouter")
    print("=" * 80)
    print(f"\nТестовый промпт: {test_prompt[:100]}...\n")
    
    for model in MODELS_TO_TEST:
        print(f"\n{'='*80}")
        print(f"Тестирование: {model['name']}")
        print(f"Описание: {model['description']}")
        print(f"{'='*80}")
        
        result = test_model(model['id'], test_prompt)
        
        if result['success']:
            cost = calculate_cost(
                result['input_tokens'],
                result['output_tokens'],
                model['cost_input'],
                model['cost_output']
            )
            
            print(f"✅ Успешно")
            print(f"Время ответа: {result['response_time']:.2f} сек")
            print(f"Входные токены: {result['input_tokens']}")
            print(f"Выходные токены: {result['output_tokens']}")
            print(f"Стоимость: ${cost:.6f}")
            print(f"\nОтвет (первые 200 символов):")
            print(f"{result['content'][:200]}...")
            
            results.append({
                "model": model['name'],
                "model_id": model['id'],
                "success": True,
                "response_time": result['response_time'],
                "input_tokens": result['input_tokens'],
                "output_tokens": result['output_tokens'],
                "total_tokens": result['total_tokens'],
                "cost": cost,
                "content_length": len(result['content']),
                "content_preview": result['content'][:200]
            })
        else:
            print(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
            results.append({
                "model": model['name'],
                "model_id": model['id'],
                "success": False,
                "error": result.get('error', 'Неизвестная ошибка')
            })
        
        # Небольшая пауза между запросами
        time.sleep(1)
    
    return results


def print_comparison_table(results: List[Dict[str, Any]]):
    """Выводит таблицу сравнения результатов"""
    print("\n" + "=" * 80)
    print("Сводная таблица сравнения")
    print("=" * 80)
    
    # Заголовок таблицы
    print(f"\n{'Модель':<30} {'Время (с)':<12} {'Токены':<15} {'Стоимость':<15} {'Статус':<10}")
    print("-" * 80)
    
    for result in results:
        if result['success']:
            print(
                f"{result['model']:<30} "
                f"{result['response_time']:<12.2f} "
                f"{result['total_tokens']:<15} "
                f"${result['cost']:<14.6f} "
                f"{'✅':<10}"
            )
        else:
            print(
                f"{result['model']:<30} "
                f"{'N/A':<12} "
                f"{'N/A':<15} "
                f"{'N/A':<15} "
                f"{'❌':<10}"
            )


def main():
    """Основная функция"""
    if not OPENROUTER_API_KEY:
        print("❌ Ошибка: OPENROUTER_API_KEY не найден")
        print("\nДобавьте в .env файл в корне проекта:")
        print("OPENROUTER_API_KEY=your_api_key_here")
        print("\nПолучить ключ можно на: https://openrouter.ai/keys")
        return
    
    # Тестовый промпт для RAG-бота
    test_prompt = """Объясни, что такое RAG (Retrieval-Augmented Generation) и как это работает. 
Ответь на русском языке, кратко (2-3 предложения)."""
    
    # Альтернативный промпт для более сложного теста
    complex_prompt = """Ты — корпоративный ассистент. Пользователь спрашивает: 
"Как настроить CI/CD pipeline для Python проекта?"

Напиши краткий, структурированный ответ с конкретными шагами. 
Используй профессиональный, но понятный язык."""
    
    print("Выберите тип теста:")
    print("1. Простой тест (объяснение RAG)")
    print("2. Сложный тест (корпоративный вопрос)")
    
    choice = input("\nВведите номер (1 или 2, по умолчанию 1): ").strip()
    
    if choice == "2":
        prompt = complex_prompt
    else:
        prompt = test_prompt
    
    # Запускаем сравнение
    results = compare_models(prompt)
    
    # Выводим таблицу
    print_comparison_table(results)
    
    # Сохраняем результаты в JSON
    output_file = "openrouter_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_prompt": prompt,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Результаты сохранены в {output_file}")


if __name__ == "__main__":
    main()

