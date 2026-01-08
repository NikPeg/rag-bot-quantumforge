#!/usr/bin/env python3
"""
Скрипт для тестирования YandexGPT через HTTP API
Демонстрирует работу с YandexGPT API через прямые HTTP запросы
Использует yc CLI для получения IAM токена и folder-id
"""

import subprocess
import json
import sys
import time
import requests
from typing import Optional, Dict, Any, List


def run_yc_command(command: list) -> tuple[bool, str]:
    """
    Выполняет команду yc и возвращает результат
    
    Args:
        command: список аргументов для yc
        
    Returns:
        tuple: (успех, вывод или ошибка)
    """
    try:
        result = subprocess.run(
            ['yc'] + command,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr
    except FileNotFoundError:
        return False, "yc CLI не найден. Установите Yandex Cloud CLI."


def check_yc_auth() -> bool:
    """Проверяет, авторизован ли пользователь в yc"""
    success, output = run_yc_command(['config', 'list'])
    return success and ('token' in output.lower() or 'iam-token' in output.lower())


def get_folder_id() -> Optional[str]:
    """Получает ID текущего каталога"""
    success, output = run_yc_command(['config', 'get', 'folder-id'])
    if success:
        return output.strip()
    return None


def get_iam_token() -> Optional[str]:
    """Получает IAM токен через yc"""
    success, output = run_yc_command(['iam', 'create-token'])
    if success:
        return output.strip()
    return None


def test_yandex_gpt(
    prompt: str, 
    model: str = "yandexgpt-lite",
    iam_token: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Тестирует YandexGPT с заданным промптом
    
    Args:
        prompt: текст запроса
        model: модель для использования (yandexgpt, yandexgpt-lite, yandexgpt-pro)
        iam_token: IAM токен для авторизации (если не указан, будет получен через yc)
        api_key: API ключ для авторизации (альтернатива IAM токену)
        
    Returns:
        словарь с результатом запроса
    """
    if not check_yc_auth():
        return {
            "success": False,
            "error": "Не авторизован в yc. Выполните: yc init"
        }
    
    folder_id = get_folder_id()
    if not folder_id:
        return {
            "success": False,
            "error": "Не удалось получить folder-id. Проверьте конфигурацию yc."
        }
    
    # Получаем IAM токен, если не указан
    if not iam_token and not api_key:
        iam_token = get_iam_token()
        if not iam_token:
            return {
                "success": False,
                "error": "Не удалось получить IAM токен. Проверьте авторизацию в yc."
            }
    
    # Формируем modelUri - если model уже содержит полный URI, используем его, иначе формируем стандартный
    if model.startswith("gpt://"):
        model_uri = model
    else:
        model_uri = f"gpt://{folder_id}/{model}"
    
    # Формируем JSON для запроса
    request_data = {
        "modelUri": model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": "2000"
        },
        "messages": [
            {
                "role": "user",
                "text": prompt
            }
        ]
    }
    
    # Формируем заголовки авторизации
    headers = {
        "Content-Type": "application/json"
    }
    
    if api_key:
        headers["Authorization"] = f"Api-Key {api_key}"
    elif iam_token:
        headers["Authorization"] = f"Bearer {iam_token}"
    else:
        return {
            "success": False,
            "error": "Не указан ни IAM токен, ни API ключ"
        }
    
    # Выполняем HTTP запрос к API
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    start_time = time.time()
    
    try:
        response = requests.post(url, headers=headers, json=request_data, timeout=60)
        response.raise_for_status()
        
        elapsed_time = time.time() - start_time
        result = response.json()
        
        # Извлекаем текст ответа
        text = ""
        if "result" in result and "alternatives" in result["result"]:
            if len(result["result"]["alternatives"]) > 0:
                text = result["result"]["alternatives"][0].get("message", {}).get("text", "")
        
        # Извлекаем информацию об использовании токенов
        usage = result.get("result", {}).get("usage", {})
        input_tokens = int(usage.get("inputTextTokens", 0) or 0)
        output_tokens = int(usage.get("completionTokens", 0) or 0)
        total_tokens = int(usage.get("totalTokens", 0) or 0)
        
        return {
            "success": True,
            "response": result,
            "text": text,
            "response_time": elapsed_time,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens
        }
    except requests.exceptions.HTTPError as e:
        error_text = ""
        try:
            error_data = e.response.json()
            error_text = error_data.get("message", str(e))
        except:
            error_text = str(e)
        
        return {
            "success": False,
            "error": f"HTTP ошибка: {error_text}",
            "status_code": e.response.status_code
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Ошибка выполнения запроса: {str(e)}"
        }
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "Не удалось распарсить ответ от API"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Неожиданная ошибка: {str(e)}"
        }


def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Рассчитывает стоимость запроса для YandexGPT моделей"""
    # Тарифы YandexGPT (примерные, нужно уточнить актуальные)
    costs = {
        "yandexgpt-lite": {"input": 0.05, "output": 0.10},  # ₽ за 1K токенов
        "yandexgpt": {"input": 0.10, "output": 0.20},
        "yandexgpt-5-pro": {"input": 0.15, "output": 0.30},
        "aliceai-llm": {"input": 0.10, "output": 0.20}  # Предположительно
    }
    
    # Определяем модель для расчета стоимости
    model_key = model
    if "aliceai-llm" in model:
        model_key = "aliceai-llm"
    elif model not in costs:
        return 0.0  # Неизвестная модель
    
    cost_info = costs.get(model_key, {"input": 0.0, "output": 0.0})
    input_cost = (input_tokens / 1000) * cost_info["input"]
    output_cost = (output_tokens / 1000) * cost_info["output"]
    
    return input_cost + output_cost


def compare_models(test_prompt: str = None) -> List[Dict[str, Any]]:
    """Сравнивает разные модели YandexGPT"""
    if test_prompt is None:
        test_prompt = "Объясни, что такое RAG (Retrieval-Augmented Generation) и как это работает. Ответь на русском языке, кратко (2-3 предложения)."
    
    # Получаем folder_id для формирования полного URI для aliceai-llm
    folder_id = get_folder_id()
    alice_uri = f"gpt://{folder_id}/aliceai-llm/latest" if folder_id else None
    
    # Модели для тестирования (убрали те, что возвращают 500)
    models_config = [
        {
            "id": "yandexgpt-lite",
            "name": "YandexGPT Lite",
            "uri": None  # Будет сформирован автоматически
        },
        {
            "id": "yandexgpt",
            "name": "YandexGPT",
            "uri": None
        },
        {
            "id": "yandexgpt-5-pro",
            "name": "YandexGPT 5 Pro",
            "uri": None
        }
    ]
    
    # Добавляем Alice AI только если folder_id доступен
    if alice_uri:
        models_config.append({
            "id": "aliceai-llm",
            "name": "Alice AI",
            "uri": alice_uri
        })
    
    results = []
    
    print("=" * 80)
    print("Сравнение моделей YandexGPT")
    print("=" * 80)
    print(f"\nТестовый промпт: {test_prompt[:100]}...\n")
    
    for model_config in models_config:
        model_id = model_config["id"]
        model_name = model_config["name"]
        model_uri = model_config.get("uri")
        
        # Используем URI если указан, иначе стандартный формат
        model_to_test = model_uri if model_uri else model_id
        
        print(f"\n{'='*80}")
        print(f"Тестирование: {model_name}")
        print(f"{'='*80}")
        
        try:
            result = test_yandex_gpt(test_prompt, model_to_test)
            
            if result["success"]:
                cost = calculate_cost(
                    result.get("input_tokens", 0),
                    result.get("output_tokens", 0),
                    model_id
                )
                
                print(f"✅ Успешно")
                print(f"Время ответа: {result.get('response_time', 0):.2f} сек")
                print(f"Входные токены: {result.get('input_tokens', 0)}")
                print(f"Выходные токены: {result.get('output_tokens', 0)}")
                print(f"Всего токенов: {result.get('total_tokens', 0)}")
                print(f"Стоимость: ₽{cost:.6f}")
                print(f"\nОтвет (первые 200 символов):")
                print(f"{result.get('text', '')[:200]}...")
                
                results.append({
                    "model": model_name,
                    "model_id": model_id,
                    "success": True,
                    "response_time": result.get('response_time', 0),
                    "input_tokens": result.get('input_tokens', 0),
                    "output_tokens": result.get('output_tokens', 0),
                    "total_tokens": result.get('total_tokens', 0),
                    "cost": cost,
                    "content_length": len(result.get('text', '')),
                    "content_preview": result.get('text', '')[:200]
                })
            else:
                print(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
                results.append({
                    "model": model_name,
                    "model_id": model_id,
                    "success": False,
                    "error": result.get('error', 'Неизвестная ошибка')
                })
        except Exception as e:
            print(f"❌ Критическая ошибка при тестировании {model_name}: {str(e)}")
            results.append({
                "model": model_name,
                "model_id": model_id,
                "success": False,
                "error": f"Критическая ошибка: {str(e)}"
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
    print(f"\n{'Модель':<30} {'Время (с)':<12} {'Токены':<15} {'Стоимость (₽)':<18} {'Статус':<10}")
    print("-" * 80)
    
    for result in results:
        if result['success']:
            print(
                f"{result['model']:<30} "
                f"{result['response_time']:<12.2f} "
                f"{result['total_tokens']:<15} "
                f"₽{result['cost']:<17.6f} "
                f"{'✅':<10}"
            )
        else:
            print(
                f"{result['model']:<30} "
                f"{'N/A':<12} "
                f"{'N/A':<15} "
                f"{'N/A':<18} "
                f"{'❌':<10}"
            )


def main():
    """Основная функция"""
    print("Тестирование YandexGPT через HTTP API")
    print("=" * 60)
    
    # Проверка авторизации
    if not check_yc_auth():
        print("❌ Ошибка: не авторизован в yc")
        print("\nДля авторизации выполните:")
        print("  yc init")
        sys.exit(1)
    
    print("✅ Авторизация в yc подтверждена")
    
    # Простой тест
    print("\n" + "=" * 60)
    print("Простой тест YandexGPT")
    print("=" * 60)
    
    test_prompt = "Привет! Как дела?"
    result = test_yandex_gpt(test_prompt)
    
    if result["success"]:
        print(f"✅ Запрос выполнен успешно")
        print(f"\nПромпт: {test_prompt}")
        print(f"Ответ: {result['text']}")
    else:
        print(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
        print("\nВозможные причины:")
        print("1. Не настроен folder-id: yc config set folder-id <ID>")
        print("2. Нет доступа к YandexGPT API")
        print("3. Неверный формат запроса")
    
    # Сравнение моделей
    print("\n")
    test_prompt = "Объясни, что такое RAG (Retrieval-Augmented Generation) и как это работает. Ответь на русском языке, кратко (2-3 предложения)."
    results = compare_models(test_prompt)
    
    # Выводим таблицу
    print_comparison_table(results)
    
    # Сохраняем результаты в JSON
    output_file = "yandex_gpt_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_prompt": test_prompt,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Результаты сохранены в {output_file}")


if __name__ == "__main__":
    main()

