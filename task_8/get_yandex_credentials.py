#!/usr/bin/env python3
"""
Скрипт для получения Yandex Cloud credentials через yc CLI.

Этот скрипт должен запускаться на машине с установленным yc CLI.
Он получает folder-id и IAM токен и выводит их для добавления в .env файл.
"""

import subprocess
import sys
from pathlib import Path


def run_yc_command(command: list) -> tuple[bool, str]:
    """Выполняет команду yc и возвращает результат."""
    try:
        result = subprocess.run(
            ['yc'] + command,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return False, str(e)


def get_folder_id() -> str | None:
    """Получает ID текущего каталога."""
    success, output = run_yc_command(['config', 'get', 'folder-id'])
    return output if success else None


def get_iam_token() -> str | None:
    """Получает IAM токен через yc."""
    success, output = run_yc_command(['iam', 'create-token'])
    return output if success else None


def update_env_file(env_path: Path, folder_id: str, iam_token: str):
    """Обновляет .env файл с полученными credentials."""
    env_content = env_path.read_text(encoding='utf-8') if env_path.exists() else ""
    
    # Удаляем старые значения
    lines = env_path.read_text(encoding='utf-8').split('\n') if env_path.exists() else []
    new_lines = []
    skip_next = False
    
    for line in lines:
        if line.startswith('YANDEX_GPT_FOLDER_ID='):
            continue
        if line.startswith('YANDEX_GPT_IAM_TOKEN='):
            continue
        if line.startswith('# YandexGPT'):
            skip_next = True
            continue
        if skip_next and (line.strip() == '' or line.startswith('#')):
            skip_next = False
            continue
        skip_next = False
        new_lines.append(line)
    
    # Добавляем новые значения
    if not any('YANDEX_GPT_FOLDER_ID' in line for line in new_lines):
        new_lines.append('')
        new_lines.append('# YandexGPT credentials (получены через get_yandex_credentials.py)')
        new_lines.append(f'YANDEX_GPT_FOLDER_ID={folder_id}')
        new_lines.append(f'YANDEX_GPT_IAM_TOKEN={iam_token}')
    
    env_path.write_text('\n'.join(new_lines), encoding='utf-8')


def main():
    """Основная функция."""
    print("=" * 60)
    print("Получение Yandex Cloud credentials")
    print("=" * 60)
    print()
    
    # Проверяем наличие yc
    success, _ = run_yc_command(['--version'])
    if not success:
        print("❌ Ошибка: yc CLI не установлен или не найден в PATH")
        print("Установите yc CLI: https://cloud.yandex.ru/docs/cli/quickstart")
        sys.exit(1)
    
    print("✅ yc CLI найден")
    print()
    
    # Получаем folder-id
    print("Получение folder-id...")
    folder_id = get_folder_id()
    if not folder_id:
        print("❌ Ошибка: не удалось получить folder-id")
        print("Убедитесь, что вы авторизованы в yc: yc init")
        sys.exit(1)
    print(f"✅ Folder ID: {folder_id}")
    print()
    
    # Получаем IAM токен
    print("Получение IAM токена...")
    iam_token = get_iam_token()
    if not iam_token:
        print("❌ Ошибка: не удалось получить IAM токен")
        sys.exit(1)
    print(f"✅ IAM токен получен (длина: {len(iam_token)} символов)")
    print()
    
    # Выводим для ручного добавления
    print("=" * 60)
    print("Добавьте следующие строки в ваш .env файл:")
    print("=" * 60)
    print()
    print("# YandexGPT credentials (получены через get_yandex_credentials.py)")
    print(f"YANDEX_GPT_FOLDER_ID={folder_id}")
    print(f"YANDEX_GPT_IAM_TOKEN={iam_token}")
    print()
    print("=" * 60)
    print()
    
    # Предлагаем автоматически обновить .env
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    
    if env_path.exists():
        response = input(f"Обновить файл {env_path} автоматически? (y/n): ").strip().lower()
        if response == 'y':
            update_env_file(env_path, folder_id, iam_token)
            print(f"✅ Файл {env_path} обновлён")
        else:
            print("Скопируйте строки выше в ваш .env файл вручную")
    else:
        print(f"⚠️  Файл {env_path} не найден")
        print("Создайте .env файл и добавьте строки выше")
    
    print()
    print("⚠️  ВАЖНО: IAM токен истекает через 12 часов!")
    print("Для продакшена рекомендуется использовать YANDEX_GPT_API_KEY")
    print("или настроить автоматическое обновление токена.")


if __name__ == "__main__":
    main()

