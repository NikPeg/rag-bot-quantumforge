#!/usr/bin/env python3
"""Тестовый скрипт для проверки инициализации бота"""

import os
import sys
from pathlib import Path

# Добавляем пути
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "task_4"))
sys.path.insert(0, str(project_root))

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Проверяем токен
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TG_TOKEN")
print(f"TELEGRAM_BOT_TOKEN: {'✅ Установлен' if TELEGRAM_BOT_TOKEN else '❌ Не установлен'}")

# Проверяем импорты
try:
    from aiogram import Bot
    print("✅ aiogram импортирован")
except ImportError as e:
    print(f"❌ Ошибка импорта aiogram: {e}")
    sys.exit(1)

try:
    from rag_bot import RAGBot
    print("✅ RAGBot импортирован")
except ImportError as e:
    print(f"❌ Ошибка импорта RAGBot: {e}")
    sys.exit(1)

# Пробуем инициализировать бота
try:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    print("✅ Telegram Bot инициализирован")
except Exception as e:
    print(f"❌ Ошибка инициализации Telegram Bot: {e}")
    sys.exit(1)

# Пробуем инициализировать RAGBot
try:
    rag_bot = RAGBot(api_key=os.getenv("YANDEX_GPT_API_KEY"), enable_security=True)
    print("✅ RAGBot инициализирован")
except Exception as e:
    print(f"❌ Ошибка инициализации RAGBot: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Все проверки пройдены! Бот готов к запуску.")

