# Задание 8: Telegram RAG-бот

Telegram бот на основе RAG-системы для ответов на вопросы из корпоративной базы знаний.

## Описание

Этот бот использует:
- **aiogram 3.24.0** для работы с Telegram API
- **RAGBot** из task_4 для поиска и генерации ответов
- **ChromaDB** для векторного поиска
- **YandexGPT** для генерации ответов

## Команды бота

- `/start` - приветствие и краткая информация
- `/help` - справка по использованию
- `/forget` - сброс контекста диалога

## Установка и запуск

### Подготовка credentials для YandexGPT

**Вариант 1: Использование API ключа (рекомендуется для продакшена)**

Получите API ключ в Yandex Cloud Console и добавьте в `.env`:
```env
YANDEX_GPT_API_KEY=your_api_key_here
YANDEX_GPT_FOLDER_ID=your_folder_id_here
```

**Вариант 2: Использование IAM токена (для разработки)**

Если у вас установлен `yc` CLI на локальной машине, запустите скрипт для получения токенов:

```bash
cd task_8
python get_yandex_credentials.py
```

Скрипт получит `folder-id` и `IAM токен` и выведет их для добавления в `.env`. 
**Важно:** IAM токен истекает через 12 часов, поэтому для продакшена лучше использовать API ключ.

### Локальный запуск

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` в корне проекта:
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# YandexGPT (выберите один из вариантов)
# Вариант 1: API ключ (рекомендуется)
YANDEX_GPT_API_KEY=your_api_key_here
YANDEX_GPT_FOLDER_ID=your_folder_id_here

# Вариант 2: IAM токен (получить через get_yandex_credentials.py)
# YANDEX_GPT_FOLDER_ID=your_folder_id_here
# YANDEX_GPT_IAM_TOKEN=your_iam_token_here

YANDEX_GPT_MODEL=yandexgpt
```

3. Запустите бота:
```bash
python bot.py
```

### Запуск через Docker

1. Убедитесь, что файл `.env` содержит все необходимые переменные

2. Запустите через docker-compose:
```bash
cd task_8
docker-compose up -d
```

3. Просмотр логов:
```bash
docker-compose logs -f
```

4. Остановка:
```bash
docker-compose down
```

## Переменные окружения

### Обязательные:
- `TELEGRAM_BOT_TOKEN` или `TG_TOKEN` - токен Telegram бота

### Для YandexGPT (выберите один из вариантов):

**Вариант 1: API ключ (рекомендуется для продакшена)**
- `YANDEX_GPT_API_KEY` - API ключ YandexGPT
- `YANDEX_GPT_FOLDER_ID` - ID каталога Yandex Cloud

**Вариант 2: IAM токен (для разработки, истекает через 12 часов)**
- `YANDEX_GPT_FOLDER_ID` - ID каталога Yandex Cloud
- `YANDEX_GPT_IAM_TOKEN` - IAM токен (получить через `get_yandex_credentials.py`)

### Опциональные:
- `YANDEX_GPT_MODEL` - модель YandexGPT (по умолчанию: yandexgpt)

## Структура проекта

```
task_8/
├── bot.py                      # Основной файл Telegram бота
├── get_yandex_credentials.py   # Скрипт для получения Yandex Cloud credentials
├── requirements.txt            # Python зависимости
├── Dockerfile                  # Docker образ
├── docker-compose.yml          # Docker Compose конфигурация
└── README.md                   # Этот файл
```

## Особенности

- Простой и интуитивный интерфейс
- Chain-of-Thought рассуждения в ответах
- Защита от prompt injection
- Честные ответы "Я не знаю" при отсутствии информации
- Указание источников в ответах

## Требования

- Python 3.11+
- Telegram Bot Token (получить у @BotFather)
- YandexGPT credentials (API ключ или IAM токен + folder-id)
- Векторный индекс из task_3 (должен быть создан заранее)

## Получение credentials для сервера

Для запуска на сервере без `yc` CLI:

1. **На локальной машине с установленным `yc` CLI:**
   ```bash
   cd task_8
   python get_yandex_credentials.py
   ```

2. **Скопируйте выведенные значения в `.env` на сервере:**
   ```env
   YANDEX_GPT_FOLDER_ID=ваш_folder_id
   YANDEX_GPT_IAM_TOKEN=ваш_iam_token
   ```

3. **Или используйте API ключ (рекомендуется для продакшена):**
   ```env
   YANDEX_GPT_API_KEY=ваш_api_ключ
   YANDEX_GPT_FOLDER_ID=ваш_folder_id
   ```

**Важно:** IAM токен истекает через 12 часов. Для продакшена рекомендуется использовать API ключ или настроить автоматическое обновление токена.

