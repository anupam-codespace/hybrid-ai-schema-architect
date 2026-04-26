"""
Module 1: Input Processor
Responsibility: Clean, normalize, and prepare raw natural language input
for downstream NLP extraction.
"""

import re
import unicodedata


class InputProcessor:
    """
    Cleans and normalizes user-supplied natural language text.

    Design philosophy:
    - Preserve capitalisation intentionally (entity names are often capitalised).
    - Strip only noise: excess whitespace, special chars, encoding artifacts.
    - Expand common abbreviations so the NLP layer sees consistent vocabulary.
    """

    # Map common shorthand to full words the NLP layer understands
    ABBREV_MAP = {
        r"\bID\b": "ID",               # keep as-is — we match "ID" as PK marker
        r"\bPK\b": "primary key",
        r"\bFK\b": "foreign key",
        r"\b1:N\b": "one to many",
        r"\bN:1\b": "many to one",
        r"\bM:N\b": "many to many",
        r"\bN:M\b": "many to many",
        r"\b1:1\b": "one to one",
    }

    # Sentence boundaries that may be written without spaces
    SENTENCE_SPLITTERS = re.compile(r'(?<=[.!?])\s*')

    def process(self, raw_text: str) -> dict:
        """
        Parameters
        ----------
        raw_text : str
            The raw user input string.

        Returns
        -------
        dict with keys:
            'cleaned'   : str  — normalized text ready for NLP
            'sentences' : list[str] — individual sentences
            'original'  : str  — unmodified original
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("Input text is empty or whitespace only.")

        original = raw_text

        # 1. Unicode normalization (handle fancy quotes, dashes, etc.)
        text = unicodedata.normalize("NFKC", raw_text)

        # 2. Replace curly/smart quotes with straight quotes
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')

        # 3. Expand abbreviations (do this BEFORE lowercasing anything)
        for pattern, replacement in self.ABBREV_MAP.items():
            text = re.sub(pattern, replacement, text)

        # 4. Collapse multiple whitespace (but keep newlines as sentence separators)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n+', '. ', text)

        # 5. Strip leading/trailing whitespace
        text = text.strip()

        # 6. Ensure sentence ends with punctuation for spaCy sentence detection
        if text and text[-1] not in '.!?':
            text += '.'

        # 7. Split into individual sentences for granular processing
        sentences = [s.strip() for s in self.SENTENCE_SPLITTERS.split(text) if s.strip()]

        return {
            "original": original,
            "cleaned": text,
            "sentences": sentences,
        }
