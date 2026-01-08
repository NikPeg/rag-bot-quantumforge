# Настройка переменных окружения для запуска на сервере

## Быстрый старт

### Шаг 1: Получение credentials

**Вариант A: Использование API ключа (рекомендуется для продакшена)**

1. Получите API ключ в [Yandex Cloud Console](https://console.cloud.yandex.ru/)
2. Получите folder-id:
   - Через yc CLI: `yc config get folder-id`
   - Или в консоли Yandex Cloud

**Вариант B: Использование IAM токена (для разработки)**

На локальной машине с установленным `yc` CLI:
```bash
cd task_8
python get_yandex_credentials.py
```

Скрипт выведет значения для добавления в `.env`.

### Шаг 2: Создание .env файла

Создайте файл `.env` в корне проекта со следующим содержимым:

```env
# Telegram Bot Token (обязательно)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# YandexGPT - выберите ОДИН вариант:

# ВАРИАНТ 1: API ключ (рекомендуется)
YANDEX_GPT_API_KEY=your_api_key_here
YANDEX_GPT_FOLDER_ID=your_folder_id_here

# ВАРИАНТ 2: IAM токен (истекает через 12 часов)
# YANDEX_GPT_FOLDER_ID=your_folder_id_here
# YANDEX_GPT_IAM_TOKEN=your_iam_token_here

# Модель (опционально)
YANDEX_GPT_MODEL=yandexgpt
```

### Шаг 3: Запуск

```bash
cd task_8
docker-compose up -d
```

## Полный список переменных окружения

### Обязательные:
- `TELEGRAM_BOT_TOKEN` или `TG_TOKEN` - токен Telegram бота

### Для YandexGPT (выберите один вариант):

**Вариант 1: API ключ**
- `YANDEX_GPT_API_KEY` - API ключ YandexGPT
- `YANDEX_GPT_FOLDER_ID` - ID каталога Yandex Cloud

**Вариант 2: IAM токен**
- `YANDEX_GPT_FOLDER_ID` - ID каталога Yandex Cloud  
- `YANDEX_GPT_IAM_TOKEN` - IAM токен (получить через `get_yandex_credentials.py`)

### Опциональные:
- `YANDEX_GPT_MODEL` - модель YandexGPT (по умолчанию: `yandexgpt`)

## Важные замечания

1. **IAM токен истекает через 12 часов** - для продакшена рекомендуется использовать API ключ
2. **Не коммитьте .env файл** в git - он содержит секретные данные
3. **Для Docker**: все переменные из `.env` автоматически загружаются через `env_file` в `docker-compose.yml`

## Проверка настроек

После настройки `.env` проверьте, что все переменные загружены:

```bash
# Локально
source .env
echo $TELEGRAM_BOT_TOKEN
echo $YANDEX_GPT_FOLDER_ID

# В Docker
docker-compose config | grep YANDEX_GPT
```

