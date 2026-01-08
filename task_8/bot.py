#!/usr/bin/env python3
"""
Telegram бот на основе RAG-системы.

Использует aiogram 3.24.0 для создания Telegram бота с командами:
- /start - приветствие
- /help - справка
- /forget - сброс контекста диалога
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Загружаем переменные окружения из .env
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# Добавляем пути для импорта RAGBot
sys.path.insert(0, str(project_root / "task_4"))
sys.path.insert(0, str(project_root))

from rag_bot import RAGBot


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация из переменных окружения
# Поддерживаем оба варианта имени переменной для совместимости
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TG_TOKEN")
# YANDEX_GPT_API_KEY опционален - если не указан или пустой, используется IAM токен через yc
YANDEX_GPT_API_KEY = os.getenv("YANDEX_GPT_API_KEY") or None
if YANDEX_GPT_API_KEY == "":
    YANDEX_GPT_API_KEY = None
YANDEX_GPT_MODEL = os.getenv("YANDEX_GPT_MODEL", "yandexgpt")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError(
        "TELEGRAM_BOT_TOKEN или TG_TOKEN не установлен в переменных окружения. "
        "Получите токен у @BotFather в Telegram."
    )

# Инициализация бота и диспетчера
bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Инициализация RAG-бота
# YANDEX_GPT_API_KEY опционален - если не указан, используется YANDEX_GPT_IAM_TOKEN из .env
try:
    rag_bot = RAGBot(
        api_key=YANDEX_GPT_API_KEY if YANDEX_GPT_API_KEY else None,
        enable_security=True
    )
    logger.info("RAG-бот успешно инициализирован")
except Exception as e:
    logger.error(f"Ошибка инициализации RAG-бота: {e}")
    raise

# Хранилище контекста диалогов (в продакшене лучше использовать Redis или БД)
user_contexts: Dict[int, list] = {}


@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    welcome_text = """
🤖 <b>Добро пожаловать в RAG-бот QuantumForge!</b>

Я умный помощник, который отвечает на вопросы на основе корпоративной базы знаний.

<b>Доступные команды:</b>
/start - показать это приветствие
/help - справка по использованию
/forget - сбросить контекст диалога

<b>Как использовать:</b>
Просто задайте мне вопрос, и я найду ответ в базе знаний!

Примеры вопросов:
• Кто такой Silk Shadow?
• Что такое Starfall City?
• Опиши Netherrealm
"""
    await message.answer(welcome_text)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
📚 <b>Справка по использованию бота</b>

<b>Команды:</b>
• /start - приветствие и краткая информация
• /help - эта справка
• /forget - сбросить контекст диалога

<b>Как задавать вопросы:</b>
Просто напишите ваш вопрос обычным текстом. Бот автоматически:
1. Найдёт релевантную информацию в базе знаний
2. Сформирует ответ на основе найденных данных
3. Укажет источники информации

<b>Особенности:</b>
• Бот использует Chain-of-Thought - показывает свои рассуждения
• Бот честно говорит "Я не знаю", если информации нет в базе
• Бот защищён от prompt injection атак

<b>Примеры вопросов:</b>
• Кто такой Silk Shadow?
• Что такое Starfall City?
• Опиши персонажа Grim
• Где находится Feast District?
"""
    await message.answer(help_text)


@dp.message(Command("forget"))
async def cmd_forget(message: Message):
    """Обработчик команды /forget - сброс контекста"""
    user_id = message.from_user.id
    if user_id in user_contexts:
        del user_contexts[user_id]
    await message.answer("✅ Контекст диалога сброшен. Начинаем с чистого листа!")


@dp.message(F.text)
async def handle_message(message: Message):
    """Обработчик текстовых сообщений"""
    user_id = message.from_user.id
    query = message.text.strip()
    
    if not query:
        await message.answer("Пожалуйста, задайте вопрос.")
        return
    
    # Отправляем сообщение о том, что бот думает
    thinking_msg = await message.answer("🔍 Ищу информацию в базе знаний...")
    
    try:
        # Получаем ответ от RAG-бота
        result = rag_bot.answer(query, use_cot=True)
        
        if result["success"]:
            answer = result["answer"]
            
            # Формируем ответ с источниками
            response_text = answer
            
            # Добавляем информацию об источниках, если они есть
            if result.get("sources"):
                sources = result["sources"][:3]  # Показываем до 3 источников
                response_text += f"\n\n📚 <i>Источники: {', '.join(sources)}</i>"
            
            # Добавляем информацию о фильтрации, если была
            if result.get("filtered_chunks", 0) > 0:
                response_text += f"\n\n🛡️ <i>Отфильтровано {result['filtered_chunks']} потенциально опасных чанков</i>"
            
            # Удаляем сообщение "думаю" и отправляем ответ
            await thinking_msg.delete()
            await message.answer(response_text)
            
        else:
            # Ошибка при генерации ответа
            error_msg = result.get("error", "Неизвестная ошибка")
            await thinking_msg.delete()
            await message.answer(
                f"❌ Произошла ошибка при обработке запроса:\n\n<code>{error_msg}</code>"
            )
            logger.error(f"Ошибка для пользователя {user_id}: {error_msg}")
    
    except Exception as e:
        logger.exception(f"Исключение при обработке сообщения от {user_id}: {e}")
        await thinking_msg.delete()
        await message.answer(
            "❌ Произошла внутренняя ошибка. Пожалуйста, попробуйте позже."
        )


async def main():
    """Основная функция запуска бота"""
    logger.info("Запуск Telegram бота...")
    
    try:
        # Удаляем вебхук, если он был установлен
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Запускаем polling
        logger.info("Бот запущен и готов к работе!")
        await dp.start_polling(bot)
    
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.exception(f"Критическая ошибка при запуске: {e}")
        sys.exit(1)

