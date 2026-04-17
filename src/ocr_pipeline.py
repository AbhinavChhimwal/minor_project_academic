import re

import cv2
import pytesseract


def extract_text_from_image(image_path: str) -> str:
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f'Could not read image: {image_path}')
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)
    return clean_text(text)


def clean_text(text: str) -> str:
    text = re.sub(r'[/\|_`~]{2,}', ' ', text)
    text = re.sub(r'[^a-zA-Z0-9.,!?;:\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
