"""Clasificador de relevancia para licitaciones."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

RELEVANCE_LEVELS = ("alta", "media", "baja", "no_relevante")
RELEVANCE_ORDER = {level: i for i, level in enumerate(RELEVANCE_LEVELS)}


@dataclass
class Classification:
    level: str  # alta, media, baja, no_relevante
    matched_keywords: list[str]

    @property
    def order(self) -> int:
        return RELEVANCE_ORDER.get(self.level, 99)

    def meets_minimum(self, minimum: str) -> bool:
        min_order = RELEVANCE_ORDER.get(minimum, 0)
        return self.order <= min_order


class RelevanceClassifier:
    """Clasifica licitaciones según palabras clave configurables."""

    def __init__(self, keywords_path: str | Path = "keywords.yaml"):
        self.keywords_path = Path(keywords_path)
        self._patterns: dict[str, list[tuple[str, re.Pattern[str]]]] = {}
        self._load_keywords()

    def _load_keywords(self) -> None:
        with open(self.keywords_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        for level in ("alta", "media", "baja"):
            words = data.get(level, [])
            patterns = []
            for kw in words:
                # Usar word boundaries para evitar matches parciales
                escaped = re.escape(kw.lower())
                pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
                patterns.append((kw, pattern))
            self._patterns[level] = patterns

    def classify(self, text: str) -> Classification:
        """Clasifica un texto y retorna el nivel más alto que haga match."""
        text_lower = text.lower()
        matched: list[str] = []
        best_level = "no_relevante"

        for level in ("alta", "media", "baja"):
            for keyword, pattern in self._patterns[level]:
                if pattern.search(text_lower):
                    matched.append(keyword)
                    if best_level == "no_relevante" or RELEVANCE_ORDER[level] < RELEVANCE_ORDER[best_level]:
                        best_level = level

        return Classification(level=best_level, matched_keywords=matched)

    def classify_tender(self, tender) -> Classification:
        """Clasifica una licitación usando su texto buscable."""
        return self.classify(tender.searchable_text)
