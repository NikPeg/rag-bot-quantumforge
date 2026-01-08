FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов зависимостей
COPY task_8/requirements.txt /app/requirements.txt
COPY task_4/requirements.txt /app/task_4_requirements.txt

# Установка Python зависимостей с использованием BuildKit cache mount
# Это ускоряет повторные сборки, кешируя pip пакеты
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /app/requirements.txt

# Копирование кода приложения
COPY task_4/ /app/task_4/
COPY task_3/ /app/task_3/
COPY task_8/ /app/task_8/
COPY knowledge_base/ /app/knowledge_base/

# Создание директории для логов
RUN mkdir -p /app/logs

# Установка рабочей директории для бота
WORKDIR /app/task_8

# Запуск бота
CMD ["python", "bot.py"]

