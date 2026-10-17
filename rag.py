"""Simple RAG: apne PDF / TXT / MD files par sawal poochna.

Retrieval TF-IDF (scikit-learn) se hota hai, is liye kisi extra API key ki zaroorat
nahi aur har provider (Gemini, Groq, ...) ke saath kaam karta hai.

Teen tareeqe:
1. Positional sawal ("pehli 3 slides", "page 5") -> seedha wahi pages.
2. Normal sawal -> TF-IDF se sab se milte julte hisse.
3. Kuch na mile (ya "summary do" jaisa sawal) -> har file ki shuruat.
"""

import io
import re
from dataclasses import dataclass

from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
MAX_CONTEXT_CHARS = 9000
OVERVIEW_CHUNKS_PER_FILE = 4

_NUMBER_WORDS = {
    "ek": 1, "one": 1, "do": 2, "two": 2, "teen": 3, "three": 3,
    "char": 4, "chaar": 4, "four": 4, "panch": 5, "paanch": 5, "five": 5,
    "chhe": 6, "six": 6, "saat": 7, "seven": 7, "aath": 8, "eight": 8,
    "nau": 9, "nine": 9, "das": 10, "ten": 10,
}
_NUM = r"(\d+|" + "|".join(_NUMBER_WORDS) + r")"
# "pehli 3 slides", "first three pages", "pehle 5"
_FIRST_N = re.compile(r"(?:pehl[iey]|pehal[iey]|first|top)\s*" + _NUM + r"\b", re.I)
# "slide 5", "page no 7", "5th slide"
_PAGE_AFTER = re.compile(
    r"(?:slides?|silids?|pages?|pg)\s*(?:no\.?|number|#)?\s*(\d+)", re.I
)
_PAGE_BEFORE = re.compile(r"(\d+)(?:st|nd|rd|th|vi|wi|wa|wee)?\s*(?:slides?|silids?|pages?)", re.I)


@dataclass
class Chunk:
    source: str  # dikhane wala label, e.g. "lecture.pdf (page 3)"
    text: str
    file: str = ""
    page: int | None = None


def read_file(name: str, data: bytes) -> list[tuple[int | None, str]]:
    """File se (page number, text) ki list banata hai. TXT/MD ke liye page None."""
    if name.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return [(i, page.extract_text() or "") for i, page in enumerate(reader.pages, 1)]
    return [(None, data.decode("utf-8", errors="ignore"))]


def split_text(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    pieces, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            space = text.rfind(" ", start, end)
            if space > start + CHUNK_SIZE // 2:
                end = space
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return pieces


def _to_int(token: str) -> int:
    return int(token) if token.isdigit() else _NUMBER_WORDS[token.lower()]


class DocIndex:
    def __init__(self, files: list[tuple[str, bytes]]):
        self.chunks: list[Chunk] = []
        self.file_names: list[str] = []
        self.vectorizer = None
        self.matrix = None

        for name, data in files:
            self.file_names.append(name)
            for page, text in read_file(name, data):
                label = f"{name} (page {page})" if page else name
                for piece in split_text(text):
                    self.chunks.append(Chunk(label, piece, name, page))

        if self.chunks:
            try:
                self.vectorizer = TfidfVectorizer(
                    stop_words="english", sublinear_tf=True
                )
                self.matrix = self.vectorizer.fit_transform(
                    [c.text for c in self.chunks]
                )
            except ValueError:  # koi kaam ka lafz nahi mila (e.g. scanned PDF)
                self.chunks = []

    # 1) "pehli 3 slides" / "page 5"
    def positional(self, query: str) -> list[Chunk]:
        pages: set[int] = set()
        match = _FIRST_N.search(query)
        if match:
            pages.update(range(1, _to_int(match.group(1)) + 1))
        for pattern in (_PAGE_AFTER, _PAGE_BEFORE):
            for found in pattern.finditer(query):
                pages.add(int(found.group(1)))
        if not pages:
            return []
        return [c for c in self.chunks if c.page in pages]

    # 2) lafzon ka match
    def search(self, query: str, k: int = 4, min_score: float = 0.05) -> list[Chunk]:
        if not self.chunks or self.vectorizer is None:
            return []
        scores = linear_kernel(self.vectorizer.transform([query]), self.matrix)[0]
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self.chunks[i] for i in ranked[:k] if scores[i] >= min_score]

    # 3) har file ki shuruat
    def overview(self) -> list[Chunk]:
        out: list[Chunk] = []
        for name in self.file_names:
            out.extend([c for c in self.chunks if c.file == name][:OVERVIEW_CHUNKS_PER_FILE])
        return out


def _format(hits: list[Chunk]) -> str:
    parts, total = [], 0
    for c in hits:
        block = f"[{c.source}]\n{c.text}"
        if total + len(block) > MAX_CONTEXT_CHARS:
            break
        parts.append(block)
        total += len(block)
    return "\n\n".join(parts)


def build_context(index: DocIndex, query: str) -> str:
    """System prompt mein jodne wala text (document ho to hamesha kuch na kuch deta hai)."""
    hits = index.positional(query)
    how = "These are the pages the user asked for."
    if not hits:
        hits = index.search(query)
        how = "These are the passages most similar to the question."
    if not hits:
        hits = index.overview()
        how = (
            "No passage matched the question strongly, so these are the "
            "beginnings of each document."
        )
    if not hits:
        return ""

    files = ", ".join(index.file_names)
    return (
        f"The user HAS uploaded these documents: {files}. You can read the excerpts "
        "below, so never say that no document is attached. "
        f"{how} Use them to answer, and mention the source name in brackets. "
        "If the excerpts do not contain the answer, say what you can see and ask "
        "the user to be more specific.\n\n"
        f"--- DOCUMENT EXCERPTS ---\n{_format(hits)}\n--- END EXCERPTS ---"
    )