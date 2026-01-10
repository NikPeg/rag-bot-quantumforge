#!/bin/bash
# Скрипт для настройки автоматического запуска обновления индекса через cron

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPDATE_SCRIPT="$SCRIPT_DIR/update_index.py"
PYTHON_ENV="$SCRIPT_DIR/../.venv"

# Проверяем наличие скрипта обновления
if [ ! -f "$UPDATE_SCRIPT" ]; then
    echo "Ошибка: скрипт $UPDATE_SCRIPT не найден"
    exit 1
fi

# Определяем путь к Python
if [ -d "$PYTHON_ENV" ]; then
    PYTHON_BIN="$PYTHON_ENV/bin/python"
    echo "Используется виртуальное окружение: $PYTHON_BIN"
else
    PYTHON_BIN=$(which python3)
    echo "Используется системный Python: $PYTHON_BIN"
fi

# Проверяем наличие Python
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Ошибка: Python не найден"
    exit 1
fi

# Создаём команду для cron
CRON_COMMAND="$PYTHON_BIN $UPDATE_SCRIPT >> $SCRIPT_DIR/logs/cron.log 2>&1"

# Время запуска (по умолчанию: каждый день в 6:00)
CRON_SCHEDULE="0 6 * * *"

# Показываем текущую конфигурацию
echo "=========================================="
echo "Настройка автоматического обновления индекса"
echo "=========================================="
echo "Скрипт: $UPDATE_SCRIPT"
echo "Python: $PYTHON_BIN"
echo "Расписание: $CRON_SCHEDULE (каждый день в 6:00)"
echo "Логи: $SCRIPT_DIR/logs/cron.log"
echo "=========================================="
echo ""

# Спрашиваем подтверждение
read -p "Добавить задачу в crontab? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Отменено"
    exit 0
fi

# Проверяем, не добавлена ли уже задача
CRON_ENTRY="$CRON_SCHEDULE $CRON_COMMAND"
if crontab -l 2>/dev/null | grep -q "$UPDATE_SCRIPT"; then
    echo "Задача уже существует в crontab"
    read -p "Заменить существующую задачу? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Удаляем старую задачу
        crontab -l 2>/dev/null | grep -v "$UPDATE_SCRIPT" | crontab -
        echo "Старая задача удалена"
    else
        echo "Отменено"
        exit 0
    fi
fi

# Добавляем новую задачу
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ Задача успешно добавлена в crontab"
echo ""
echo "Для просмотра задач: crontab -l"
echo "Для удаления задачи: crontab -e (удалите строку с $UPDATE_SCRIPT)"
echo ""
echo "Для тестового запуска: $PYTHON_BIN $UPDATE_SCRIPT"

