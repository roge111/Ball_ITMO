
from pathlib import Path
import sys
import re


ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from managers.ReadInfo import ReadInfo
read_info = ReadInfo()

print(re.sub(r'\b[A-Za-z]+\d+\b', '', read_info.read_pdf_info('info/Дресс-код_для_кавалеров.pdf').replace(' ', '').replace('\n', '')))
