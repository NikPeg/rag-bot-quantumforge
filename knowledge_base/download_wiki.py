#!/usr/bin/env python3
"""
Скрипт для скачивания статей из вики Hazbin Hotel с fandom.com.
Скачивает страницы, очищает от HTML и сохраняет в папку raw.
"""

import requests
from bs4 import BeautifulSoup
from pathlib import Path
import time
import re
from urllib.parse import urljoin, urlparse
import json


class WikiDownloader:
    def __init__(self, base_url: str = "https://hazbinhotel.fandom.com", output_dir: str = "raw"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.downloaded_pages = set()
        
    def clean_text(self, text: str) -> str:
        """Очищает текст от лишних символов и форматирования."""
        # Удаляем множественные пробелы и переносы строк
        text = re.sub(r'\s+', ' ', text)
        # Удаляем пробелы в начале и конце
        text = text.strip()
        return text
    
    def extract_main_content(self, soup: BeautifulSoup) -> str:
        """Извлекает основной контент статьи из HTML."""
        # Ищем основной контент статьи
        content_divs = [
            soup.find('div', {'class': 'mw-parser-output'}),
            soup.find('div', {'id': 'content'}),
            soup.find('article'),
            soup.find('main')
        ]
        
        content = None
        for div in content_divs:
            if div:
                content = div
                break
        
        if not content:
            # Если не нашли специальный контейнер, берем body
            content = soup.find('body')
        
        if not content:
            return ""
        
        # Удаляем ненужные элементы
        for element in content.find_all(['script', 'style', 'nav', 'header', 'footer', 
                                        'aside', 'div', 'span'], 
                                       class_=re.compile(r'nav|menu|sidebar|footer|header|ad')):
            element.decompose()
        
        # Удаляем все ссылки, но сохраняем текст
        for link in content.find_all('a'):
            if link.string:
                link.replace_with(link.string)
            else:
                link.decompose()
        
        # Извлекаем текст
        text = content.get_text(separator='\n', strip=True)
        
        # Очищаем текст
        lines = []
        for line in text.split('\n'):
            line = self.clean_text(line)
            if line and len(line) > 10:  # Пропускаем очень короткие строки
                lines.append(line)
        
        return '\n\n'.join(lines)
    
    def get_page_title(self, soup: BeautifulSoup, url: str) -> str:
        """Извлекает заголовок страницы."""
        title_elem = soup.find('h1', class_='page-header__title')
        if not title_elem:
            title_elem = soup.find('h1')
        if not title_elem:
            # Пытаемся извлечь из URL
            parsed = urlparse(url)
            title = parsed.path.split('/')[-1].replace('_', ' ')
            return title
        return title_elem.get_text(strip=True)
    
    def download_page(self, page_url: str) -> bool:
        """Скачивает одну страницу вики."""
        if page_url in self.downloaded_pages:
            return False
        
        try:
            print(f"Скачиваю: {page_url}")
            response = self.session.get(page_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Извлекаем заголовок
            title = self.get_page_title(soup, page_url)
            title = re.sub(r'[^\w\s-]', '', title).strip()
            title = re.sub(r'[-\s]+', '_', title)
            
            if not title:
                title = "untitled"
            
            # Извлекаем контент
            content = self.extract_main_content(soup)
            
            if not content or len(content) < 100:
                print(f"  ⚠ Пропущено: слишком мало контента ({len(content)} символов)")
                return False
            
            # Сохраняем в файл
            filename = f"{len(self.downloaded_pages):02d}_{title}.md"
            filepath = self.output_dir / filename
            
            # Создаем markdown документ
            markdown = f"# {title}\n\n{content}\n"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            self.downloaded_pages.add(page_url)
            print(f"  ✓ Сохранено: {filename} ({len(content)} символов)")
            return True
            
        except Exception as e:
            print(f"  ✗ Ошибка при скачивании {page_url}: {e}")
            return False
    
    def get_category_pages(self, category_name: str, limit: int = 50) -> list:
        """Получает список страниц из категории вики."""
        pages = []
        api_url = f"{self.base_url}/api.php"
        
        params = {
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': f'Category:{category_name}',
            'cmlimit': limit,
            'format': 'json'
        }
        
        try:
            response = self.session.get(api_url, params=params, timeout=10)
            data = response.json()
            
            if 'query' in data and 'categorymembers' in data['query']:
                for member in data['query']['categorymembers']:
                    title = member['title']
                    page_url = f"{self.base_url}/wiki/{title.replace(' ', '_')}"
                    pages.append(page_url)
            
        except Exception as e:
            print(f"Ошибка при получении категории {category_name}: {e}")
        
        return pages
    
    def get_all_pages_from_categories(self, categories: list, max_pages: int = 50) -> list:
        """Получает страницы из нескольких категорий."""
        all_pages = []
        
        for category in categories:
            print(f"\nПолучаю страницы из категории: {category}")
            pages = self.get_category_pages(category, limit=max_pages)
            all_pages.extend(pages)
            print(f"  Найдено {len(pages)} страниц")
        
        # Удаляем дубликаты
        return list(set(all_pages))
    
    def download_from_list(self, page_urls: list, delay: float = 1.0):
        """Скачивает список страниц с задержкой между запросами."""
        print(f"\nНачинаю скачивание {len(page_urls)} страниц...\n")
        
        for i, url in enumerate(page_urls, 1):
            self.download_page(url)
            if i < len(page_urls):
                time.sleep(delay)  # Задержка между запросами
        
        print(f"\n✓ Скачано {len(self.downloaded_pages)} страниц")


def main():
    """Основная функция."""
    downloader = WikiDownloader(output_dir="raw")
    
    # Категории для скачивания
    categories = [
        "Characters",
        "Locations",
        "Episodes",
        "Objects",
        "Organizations",
        "Events",
        "Concepts"
    ]
    
    # Получаем список страниц
    print("Получаю список страниц из вики...")
    page_urls = downloader.get_all_pages_from_categories(categories, max_pages=50)
    
    if not page_urls:
        print("\n⚠ Не удалось получить страницы через API. Пробую альтернативный метод...")
        # Альтернативный список ключевых страниц
        key_pages = [
            "https://hazbinhotel.fandom.com/wiki/Charlie_Morningstar",
            "https://hazbinhotel.fandom.com/wiki/Vaggie",
            "https://hazbinhotel.fandom.com/wiki/Alastor",
            "https://hazbinhotel.fandom.com/wiki/Angel_Dust",
            "https://hazbinhotel.fandom.com/wiki/Husk",
            "https://hazbinhotel.fandom.com/wiki/Niffty",
            "https://hazbinhotel.fandom.com/wiki/Sir_Pentious",
            "https://hazbinhotel.fandom.com/wiki/Cherri_Bomb",
            "https://hazbinhotel.fandom.com/wiki/Lucifer_Morningstar",
            "https://hazbinhotel.fandom.com/wiki/Lilith",
            "https://hazbinhotel.fandom.com/wiki/Adam",
            "https://hazbinhotel.fandom.com/wiki/Lute",
            "https://hazbinhotel.fandom.com/wiki/Vox",
            "https://hazbinhotel.fandom.com/wiki/Velvette",
            "https://hazbinhotel.fandom.com/wiki/Valentino",
            "https://hazbinhotel.fandom.com/wiki/Carmilla_Carmine",
            "https://hazbinhotel.fandom.com/wiki/Zestial",
            "https://hazbinhotel.fandom.com/wiki/Rosie",
            "https://hazbinhotel.fandom.com/wiki/Emily",
            "https://hazbinhotel.fandom.com/wiki/Sera",
            "https://hazbinhotel.fandom.com/wiki/Hazbin_Hotel",
            "https://hazbinhotel.fandom.com/wiki/Pentagram_City",
            "https://hazbinhotel.fandom.com/wiki/Cannibal_Town",
            "https://hazbinhotel.fandom.com/wiki/Hell",
            "https://hazbinhotel.fandom.com/wiki/Heaven",
            "https://hazbinhotel.fandom.com/wiki/Extermination",
            "https://hazbinhotel.fandom.com/wiki/Overlords",
            "https://hazbinhotel.fandom.com/wiki/Sinners",
            "https://hazbinhotel.fandom.com/wiki/Soul_Contracts",
            "https://hazbinhotel.fandom.com/wiki/The_Seven_Deadly_Sins",
            "https://hazbinhotel.fandom.com/wiki/Redemption_Program",
            "https://hazbinhotel.fandom.com/wiki/Pilot",
            "https://hazbinhotel.fandom.com/wiki/Season_1"
        ]
        page_urls = key_pages
    
    # Скачиваем страницы
    downloader.download_from_list(page_urls, delay=1.5)
    
    print(f"\n✓ Готово! Скачано {len(downloader.downloaded_pages)} страниц в папку {downloader.output_dir}")


if __name__ == '__main__':
    main()

