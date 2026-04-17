import re
import tempfile
from pathlib import Path

from pypdf import PdfReader


def clean_text(text: str) -> str:
    text = re.sub(r"[/\\|_`~]{2,}", " ", text)
    text = re.sub(r"[^a-zA-Z0-9.,!?;:\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_into_chunks(text: str, max_chars: int = 260):
    sentences = re.split(r"(?<=[.!?])\s+", clean_text(text))
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks


def _extract_from_pdf(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        reader = PdfReader(str(tmp_path))
        text = " ".join(page.extract_text() or "" for page in reader.pages)
        return clean_text(text)
    finally:
        tmp_path.unlink(missing_ok=True)


def extract_text_from_upload(file_name: str, file_bytes: bytes) -> str:
    suffix = file_name.lower().split(".")[-1]
    if suffix == "txt":
        return clean_text(file_bytes.decode("utf-8", errors="ignore"))
    if suffix == "pdf":
        return _extract_from_pdf(file_bytes)
    raise ValueError("Unsupported file type. Use txt or pdf with selectable text.")
