from __future__ import annotations

import re
from bs4 import BeautifulSoup


def extract_page_text(raw_html: str, max_chars: int) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")
    for t in soup(["script", "style", "noscript", "iframe"]):
        t.extract()
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:max_chars]


def extract_evidence_snippet(text: str, max_sentences: int = 2) -> str:
    if not text:
        return ""
    sentence_split = re.split(r"(?<=[.!?])\s+", text)
    sentence_split = [s.strip() for s in sentence_split if s.strip()]
    return " ".join(sentence_split[:max_sentences])[:500]
