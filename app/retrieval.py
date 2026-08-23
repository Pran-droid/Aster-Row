import json
import re
from pathlib import Path

from app.config import KNOWLEDGE_BASE_DIR


INTERNAL_DOCS = {"14-internal-content-migration-notes.md"}
ACTIVE_PRIORITY = {"01-returns-policy-current.md", "03-final-sale-and-promotions.md", "04-damaged-or-wrong-items.md", "05-domestic-shipping.md", "06-international-shipping.md", "07-warranty.md", "08-order-changes-and-cancellations.md", "09-trailplus-membership.md", "10-gift-cards-and-price-adjustments.md", "11-product-care.md", "12-breeze-tumbler-product-card.md", "13-support-escalation.md"}


class KnowledgeBase:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.documents = []

    def _parse_front_matter(self, text: str):
        if text.startswith("---\n"):
            _, front_matter, body = text.split("---\n", 2)
            metadata = {}
            for line in front_matter.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip()
            return metadata, body.strip()
        return {}, text.strip()

    def build(self):
        self.documents = []
        for path in sorted(self.base_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            metadata, body = self._parse_front_matter(text)
            chunks = self._chunk_text(body)
            for idx, chunk in enumerate(chunks):
                self.documents.append(
                    {
                        "filename": path.name,
                        "title": metadata.get("title", path.stem),
                        "status": metadata.get("status", "unknown"),
                        "effective_date": metadata.get("effective_date", ""),
                        "policy_authority": metadata.get("policy_authority", "unknown"),
                        "supersedes": metadata.get("supersedes", ""),
                        "chunk_index": idx,
                        "text": chunk,
                    }
                )

    def _chunk_text(self, text: str, max_chars: int = 800):
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
        chunks = []
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 1 <= max_chars:
                current = (current + "\n\n" + paragraph).strip()
            else:
                if current:
                    chunks.append(current)
                current = paragraph
        if current:
            chunks.append(current)
        return chunks or [text.strip()]

    def search(self, query: str, limit: int = 5):
        q = query.lower()
        scored = []
        for doc in self.documents:
            filename = doc["filename"]
            if filename in INTERNAL_DOCS:
                continue
            text = doc["text"].lower()
            score = 0
            score += 3 if filename in ACTIVE_PRIORITY else 0
            score += 2 if doc["status"] == "active" else 0
            score += 2 if doc["policy_authority"] == "official" else 0
            score += sum(1 for token in ["return", "delivery", "shipping", "warranty", "canada", "trailplus", "damaged", "dishwasher", "final sale"] if token in q and token in text)
            if q in text:
                score += 5
            scored.append({**doc, "score": score})

        scored.sort(key=lambda item: item["score"], reverse=True)
        return [{
            "filename": item["filename"],
            "title": item["title"],
            "status": item["status"],
            "score": item["score"],
            "text": item["text"],
        } for item in scored[:limit] if item["score"] > 0]
