#!/usr/bin/env python3
"""
RAG-бот с техниками промптинга (Few-shot и Chain-of-Thought).

Этот модуль реализует полный RAG-пайплайн:
1. Загрузка векторного индекса из ChromaDB
2. Поиск релевантных чанков по запросу пользователя
3. Формирование промпта с Few-shot примерами и Chain-of-Thought
4. Генерация ответа через YandexGPT
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
import requests


# Конфигурация
INDEX_DIR = Path(__file__).parent.parent / "task_3" / "chroma_db"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
YANDEX_GPT_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
DEFAULT_MODEL = "yandexgpt"
TOP_K_CHUNKS = 5  # Количество чанков для поиска


class YandexGPTClient:
    """Клиент для работы с YandexGPT API."""
    
    def __init__(self, model: str = DEFAULT_MODEL, api_key: Optional[str] = None):
        """
        Инициализирует клиент YandexGPT.
        
        Args:
            model: название модели (yandexgpt, yandexgpt-lite, yandexgpt-pro)
            api_key: API ключ (если не указан, используется IAM токен через yc)
        """
        self.model = model
        self.api_key = api_key
        self.folder_id = self._get_folder_id()
        self.iam_token = None if api_key else self._get_iam_token()
    
    def _run_yc_command(self, command: list) -> Tuple[bool, str]:
        """Выполняет команду yc и возвращает результат."""
        try:
            result = subprocess.run(
                ['yc'] + command,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False, ""
    
    def _get_folder_id(self) -> Optional[str]:
        """Получает ID текущего каталога."""
        success, output = self._run_yc_command(['config', 'get', 'folder-id'])
        return output if success else None
    
    def _get_iam_token(self) -> Optional[str]:
        """Получает IAM токен через yc."""
        success, output = self._run_yc_command(['iam', 'create-token'])
        return output if success else None
    
    def _get_model_uri(self) -> str:
        """Формирует URI модели."""
        if self.model.startswith("gpt://"):
            return self.model
        if not self.folder_id:
            raise ValueError("Не удалось получить folder-id. Проверьте конфигурацию yc.")
        return f"gpt://{self.folder_id}/{self.model}"
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.6,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Генерирует ответ через YandexGPT API.
        
        Args:
            messages: список сообщений в формате [{"role": "user", "text": "..."}]
            temperature: температура генерации
            max_tokens: максимальное количество токенов в ответе
            
        Returns:
            словарь с результатом генерации
        """
        model_uri = self._get_model_uri()
        
        request_data = {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": str(max_tokens)
            },
            "messages": messages
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Api-Key {self.api_key}"
        elif self.iam_token:
            headers["Authorization"] = f"Bearer {self.iam_token}"
        else:
            return {
                "success": False,
                "error": "Не указан ни IAM токен, ни API ключ"
            }
        
        try:
            response = requests.post(
                YANDEX_GPT_API_URL,
                headers=headers,
                json=request_data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            # Извлекаем текст ответа
            text = ""
            if "result" in result and "alternatives" in result["result"]:
                if len(result["result"]["alternatives"]) > 0:
                    text = result["result"]["alternatives"][0].get("message", {}).get("text", "")
            
            usage = result.get("result", {}).get("usage", {})
            
            return {
                "success": True,
                "text": text,
                "input_tokens": int(usage.get("inputTextTokens", 0) or 0),
                "output_tokens": int(usage.get("completionTokens", 0) or 0),
                "total_tokens": int(usage.get("totalTokens", 0) or 0)
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
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка выполнения запроса: {str(e)}"
            }


class RAGBot:
    """RAG-бот с техниками промптинга."""
    
    def __init__(
        self,
        index_dir: Path = INDEX_DIR,
        embedding_model: str = EMBEDDING_MODEL,
        llm_model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None
    ):
        """
        Инициализирует RAG-бота.
        
        Args:
            index_dir: путь к директории с индексом ChromaDB
            embedding_model: название модели эмбеддингов
            llm_model: название LLM модели
            api_key: API ключ для YandexGPT (опционально)
        """
        self.index_dir = index_dir
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        
        # Загружаем векторный индекс
        print("Загрузка векторного индекса...")
        self.vectorstore = self._load_index()
        
        # Инициализируем LLM клиент
        print("Инициализация LLM клиента...")
        self.llm_client = YandexGPTClient(model=llm_model, api_key=api_key)
        
        # Загружаем few-shot примеры
        self.few_shot_examples = self._load_few_shot_examples()
        
        print("✅ RAG-бот готов к работе!")
    
    def _load_index(self) -> Chroma:
        """Загружает векторный индекс из ChromaDB."""
        if not self.index_dir.exists():
            raise FileNotFoundError(
                f"Индекс не найден в {self.index_dir}. "
                f"Сначала запустите task_3/build_index.py для создания индекса."
            )
        
        embeddings = HuggingFaceEmbeddings(
            model_name=self.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        
        vectorstore = Chroma(
            persist_directory=str(self.index_dir),
            embedding_function=embeddings,
        )
        
        return vectorstore
    
    def _load_few_shot_examples(self) -> List[Dict[str, str]]:
        """
        Загружает few-shot примеры из базы знаний.
        
        Возвращает список примеров в формате [{"question": "...", "answer": "..."}]
        """
        # Попробуем найти реальные примеры из базы знаний
        try:
            # Ищем примеры вопросов-ответов из базы
            test_queries = [
                "Что такое Twilight Manor?",
                "Кто такой Korax?"
            ]
            
            found_examples = []
            for query in test_queries:
                results = self.vectorstore.similarity_search_with_score(query, k=2)
                if results:
                    # Берем лучший результат
                    doc, score = results[0]
                    if score < 1.5:  # Хорошая релевантность
                        # Формируем краткий ответ на основе найденного чанка
                        # Берем первые 2-3 предложения для краткости
                        content = doc.page_content
                        sentences = content.split('. ')
                        if len(sentences) > 3:
                            answer = '. '.join(sentences[:3]) + '.'
                        else:
                            answer = content[:250] + "..." if len(content) > 250 else content
                        
                        found_examples.append({
                            "question": query,
                            "answer": answer
                        })
            
            # Используем найденные примеры, если они есть
            if found_examples:
                return found_examples[:2]  # Максимум 2 примера
        except Exception as e:
            print(f"Предупреждение: не удалось загрузить few-shot примеры из базы: {e}")
        
        # Fallback примеры, если не удалось извлечь из базы
        examples = [
            {
                "question": "Что такое Twilight Manor?",
                "answer": "Twilight Manor — это отель, которым управляет Zara Morningstar. В нём проходят реабилитацию гости из Netherrealm."
            },
            {
                "question": "Кто такой Korax?",
                "answer": "Korax — это могущественный персонаж из Netherrealm, известный своими способностями и влиянием."
            }
        ]
        
        return examples
    
    def _format_few_shot_examples(self) -> str:
        """Форматирует few-shot примеры для промпта."""
        if not self.few_shot_examples:
            return ""
        
        formatted = "\nПримеры правильных ответов:\n\n"
        for i, example in enumerate(self.few_shot_examples, 1):
            formatted += f"Пример {i}:\n"
            formatted += f"Q: {example['question']}\n"
            formatted += f"A: {example['answer']}\n\n"
        
        return formatted
    
    def _format_context(self, chunks: List[Document]) -> str:
        """Форматирует найденные чанки для контекста."""
        if not chunks:
            return "Контекст не найден."
        
        context = "Контекст из базы знаний:\n\n"
        for i, chunk in enumerate(chunks, 1):
            source = chunk.metadata.get('file_name', 'unknown')
            context += f"[{i}] Источник: {source}\n"
            context += f"{chunk.page_content}\n\n"
        
        return context
    
    def _build_prompt(
        self,
        query: str,
        chunks: List[Document],
        use_cot: bool = True
    ) -> str:
        """
        Строит промпт с Few-shot и Chain-of-Thought.
        
        Args:
            query: запрос пользователя
            chunks: найденные релевантные чанки
            use_cot: использовать ли Chain-of-Thought
            
        Returns:
            сформированный промпт
        """
        # System prompt с инструкциями
        system_prompt = """Ты — корпоративный бот-ассистент, который отвечает на вопросы на основе базы знаний.

Твоя задача — аккуратно ответить на вопрос пользователя, используя ТОЛЬКО информацию из предоставленного контекста.

Важные правила:
1. Отвечай ТОЛЬКО на основе информации из контекста
2. Если в контексте нет нужной информации, честно скажи "Я не знаю" или "В предоставленном контексте нет информации об этом"
3. Избегай домыслов и галлюцинаций
4. Отвечай на русском языке
5. Будь кратким, но информативным
"""
        
        # Добавляем Chain-of-Thought инструкции
        if use_cot:
            system_prompt += """
6. ВСЕГДА показывай свои рассуждения перед ответом:
   - Сначала объясни, что ты ищешь в контексте
   - Затем укажи, какие фрагменты из контекста релевантны
   - После этого сформулируй ответ на основе найденной информации
   
Формат ответа:
[Рассуждение]
1. Ищу в контексте информацию о...
2. В документе [номер] найдено...
3. Следовательно, ответ...

[Ответ]
Твой ответ здесь
"""
        
        # Few-shot примеры
        few_shot = self._format_few_shot_examples()
        
        # Контекст
        context = self._format_context(chunks)
        
        # Формируем полный промпт
        prompt = f"""{system_prompt}

{few_shot}

{context}

Вопрос пользователя: {query}

Твой ответ (следуй формату выше):"""
        
        return prompt
    
    def search(self, query: str, k: int = TOP_K_CHUNKS) -> List[Document]:
        """
        Ищет релевантные чанки по запросу.
        
        Args:
            query: текстовый запрос
            k: количество чанков для возврата
            
        Returns:
            список найденных документов
        """
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        
        # Фильтруем по релевантности (score < 1.5 для косинусного расстояния)
        filtered_results = [
            doc for doc, score in results
            if score < 1.5  # Порог релевантности
        ]
        
        return filtered_results[:k]
    
    def answer(
        self,
        query: str,
        use_cot: bool = True,
        temperature: float = 0.6,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Отвечает на вопрос пользователя.
        
        Args:
            query: вопрос пользователя
            use_cot: использовать ли Chain-of-Thought
            temperature: температура генерации
            max_tokens: максимальное количество токенов
            
        Returns:
            словарь с ответом и метаданными
        """
        # Шаг 1: Поиск релевантных чанков
        chunks = self.search(query)
        
        if not chunks:
            return {
                "success": True,
                "answer": "Я не знаю. В базе знаний не найдено информации по вашему запросу.",
                "sources": [],
                "chunks_found": 0
            }
        
        # Шаг 2: Формирование промпта
        prompt = self._build_prompt(query, chunks, use_cot=use_cot)
        
        # Шаг 3: Генерация ответа через LLM
        messages = [
            {
                "role": "user",
                "text": prompt
            }
        ]
        
        result = self.llm_client.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        if not result["success"]:
            return {
                "success": False,
                "error": result.get("error", "Неизвестная ошибка"),
                "sources": [chunk.metadata.get('file_name', 'unknown') for chunk in chunks]
            }
        
        # Формируем ответ
        return {
            "success": True,
            "answer": result["text"],
            "sources": [chunk.metadata.get('file_name', 'unknown') for chunk in chunks],
            "chunks_found": len(chunks),
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
            "total_tokens": result.get("total_tokens", 0)
        }


def main():
    """Основная функция для запуска бота в REPL режиме."""
    print("=" * 60)
    print("RAG-бот с техниками промптинга")
    print("=" * 60)
    print()
    
    try:
        # Инициализируем бота
        bot = RAGBot()
        
        print("\n" + "=" * 60)
        print("Интерактивный режим")
        print("=" * 60)
        print("Введите ваш вопрос (или 'exit' для выхода)")
        print("Команды:")
        print("  'exit' или 'quit' - выход")
        print("  'nocot' - отключить Chain-of-Thought")
        print("  'cot' - включить Chain-of-Thought (по умолчанию)")
        print("=" * 60 + "\n")
        
        use_cot = True
        
        while True:
            try:
                query = input("\nВопрос: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['exit', 'quit', 'выход']:
                    print("\nДо свидания!")
                    break
                
                if query.lower() == 'nocot':
                    use_cot = False
                    print("Chain-of-Thought отключен")
                    continue
                
                if query.lower() == 'cot':
                    use_cot = True
                    print("Chain-of-Thought включен")
                    continue
                
                # Получаем ответ
                print("\n🔍 Ищу информацию в базе знаний...")
                result = bot.answer(query, use_cot=use_cot)
                
                if result["success"]:
                    print("\n" + "=" * 60)
                    print("Ответ:")
                    print("=" * 60)
                    print(result["answer"])
                    print("\n" + "-" * 60)
                    print(f"Найдено чанков: {result['chunks_found']}")
                    print(f"Источники: {', '.join(result['sources'][:3])}")
                    if result.get('total_tokens'):
                        print(f"Использовано токенов: {result['total_tokens']}")
                    print("=" * 60)
                else:
                    print(f"\n❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
                    
            except KeyboardInterrupt:
                print("\n\nВыход...")
                break
            except Exception as e:
                print(f"\n❌ Ошибка: {str(e)}")
                import traceback
                traceback.print_exc()
    
    except Exception as e:
        print(f"\n❌ Критическая ошибка при инициализации бота: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

