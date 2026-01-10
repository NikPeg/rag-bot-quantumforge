# Задание 1: Исследование моделей и инфраструктуры

## Описание

Это задание содержит исследование различных компонентов для построения RAG-бота:
- Сравнение LLM моделей (локальные vs облачные)
- Сравнение моделей эмбеддингов
- Сравнение векторных БД (FAISS vs ChromaDB)
- Рекомендации по конфигурации сервера

## Файлы

- `research_report.md` - подробный отчёт с анализом и рекомендациями
- `test_yandex_gpt.py` - скрипт для тестирования YandexGPT через yc CLI
- `requirements.txt` - зависимости Python

## Быстрый старт

### 1. Установка зависимостей

```bash
python -m venv .venv
source .venv/bin/activate  # на Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Настройка Yandex Cloud CLI

Убедитесь, что `yc` установлен и настроен:

```bash
# Проверка версии
yc --version

# Инициализация (если ещё не сделано)
yc init

# Проверка авторизации
yc config list
```

### 3. Тестирование YandexGPT

```bash
python test_yandex_gpt.py
```

## Основные выводы

**Рекомендуемое решение:**
- **LLM**: Xiaomi MiMo-V2-Flash (через OpenRouter) — **БЕСПЛАТНО**
- **Эмбеддинги**: sentence-transformers/all-MiniLM-L6-v2 (локально)
- **Векторная БД**: ChromaDB
- **Сервер**: Yandex Cloud Compute (8 vCPU, 32 GB RAM)

**Альтернативы:**
- **YandexGPT Pro**: если критична поддержка русского языка и обработка данных в России
- **DeepSeek V3.2**: максимальная экономия (~$2/мес)
- **Gemini 2.5 Flash**: большой контекст (1M токенов) и reasoning

**Обоснование:**
- Бесплатная LLM с высоким качеством (сравнимо с Claude Sonnet 4.5)
- Экономия ~$100-150/мес по сравнению с платными моделями
- Встроенная поддержка метаданных в ChromaDB
- Простота развёртывания

Подробности см. в `research_report.md`.

## Тестирование моделей

### Тестирование YandexGPT

```bash
python test_yandex_gpt.py
```

### Тестирование моделей через OpenRouter

Перед запуском убедитесь, что в `.env` файле в корне проекта есть ключ:

```bash
OPENROUTER_API_KEY=your_api_key_here
```

Получить ключ можно на: https://openrouter.ai/keys

Запуск тестирования:

```bash
python test_openrouter_models.py
```

Скрипт протестирует 5 моделей:
- Xiaomi MiMo-V2-Flash (бесплатно)
- Anthropic Claude Sonnet 4.5
- Google Gemini 2.5 Flash
- Google Gemini 3 Flash Preview
- DeepSeek V3.2

Результаты сохраняются в `openrouter_test_results.json`.

