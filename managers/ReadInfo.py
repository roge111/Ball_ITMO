import PyPDF2
from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

class ReadInfo:
    def __init__(self):
        pass

    def read_pdf_info(self, path: str):
        # Преобразуем путь в абсолютный используя ROOT
        if not Path(path).is_absolute():
            absolute_path = ROOT / path
        else:
            absolute_path = Path(path)
        
        print(f"Пытаюсь открыть файл: {absolute_path}")  # Отладочная информация
        
        # Проверяем существование файла
        if not absolute_path.exists():
            raise FileNotFoundError(f"Файл не найден: {absolute_path}")
        
        with open(absolute_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            count_pages = len(pdf_reader.pages)
            text = ''

            for page_num in range(count_pages):
                page = pdf_reader.pages[page_num]
                text += page.extract_text().replace('ü', '')
            return text