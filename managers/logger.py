# -*- coding: utf-8 -*-
"""
Модуль логирования: перенаправляет вывод print в txt-файлы.
Каждый модуль пишет в свой файл: logs/<module_name>.txt
"""
from pathlib import Path
from datetime import datetime

# Корень проекта (managers/logger.py -> ROOT)
ROOT = Path(__file__).parent.parent
LOGS_DIR = ROOT / 'logs'


def log(module_name: str, message) -> None:
    """Записывает сообщение в logs/<module_name>.txt с временной меткой."""
    LOGS_DIR.mkdir(exist_ok=True)
    file_path = LOGS_DIR / f"{module_name}.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")