"""
Module 2: NLP Extraction Module
Responsibility: Extract entities and their attributes from cleaned text
using spaCy NLP + rule-based heuristics.
"""

import re
from typing import Optional
import spacy
from spacy.matcher import Matcher


# ---------------------------------------------------------------------------
# Primary Key heuristics — column names that almost certainly are PKs
# ---------------------------------------------------------------------------
PK_PATTERNS = re.compile(
    r'^(id|.*_id|.*id)$',
    re.IGNORECASE
)

# Keywords that precede attribute lists
ATTRIBUTE_TRIGGERS = {
    "has", "have", "contains", "contain", "includes", "include",
    "with", "consisting of", "comprised of", "possesses", "stores",
}

# Keywords that introduce a new entity definition
ENTITY_TRIGGERS = {
    "entity", "table", "model", "class", "object", "record",
}


class NLPExtractor:
    """
    Extracts:
      - Entity names  : capitalised nouns / noun phrases explicitly named
      - Attributes    : fields following "has/contains/with ..."
      - Primary Keys  : attributes matching PK_PATTERNS (ID, EntityID, etc.)

    Uses spaCy's dependency parser and a custom Matcher to identify
    entity-attribute pairings without any ML training.
    """

    def __init__(self, model: str = "en_core_web_sm"):
        try:
            self.nlp = spacy.load(model)
        except OSError:
            raise RuntimeError(
                f"spaCy model '{model}' not found. "
                f"Run: python -m spacy download {model}"
            )
        self._setup_matcher()

    # ------------------------------------------------------------------
    # Matcher setup
    # ------------------------------------------------------------------

    def _setup_matcher(self):
        """Register phrase patterns for entity triggers inside spaCy Matcher."""
        self.matcher = Matcher(self.nlp.vocab)

        # Pattern: <Entity-like proper noun> "has" <list of nouns>
        # We use token-level patterns for robustness.
        self.matcher.add("ENTITY_HAS_ATTRS", [
            [{"POS": "PROPN"}, {"LOWER": "has"}],
            [{"POS": "NOUN", "IS_TITLE": True}, {"LOWER": "has"}],
        ])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, processed_input: dict) -> dict:
        """
        Parameters
        ----------
        processed_input : dict
            Output from InputProcessor.process()

        Returns
        -------
        dict:
            {
              "entities": {
                "EntityName": {
                  "attributes": ["attr1", "attr2", ...],
                  "primary_key": "attr_name_or_None"
                }
              }
            }
        """
        cleaned_text = processed_input["cleaned"]
        sentences = processed_input["sentences"]

        entities: dict = {}

        # Pass 1 — sentence-level extraction (most reliable)
        for sent_text in sentences:
            self._extract_from_sentence(sent_text, entities)

        # Pass 2 — whole-document pass to catch anything missed
        doc = self.nlp(cleaned_text)
        self._extract_from_doc(doc, entities)

        # Post-process: identify primary keys
        for ent_name, ent_data in entities.items():
            ent_data["primary_key"] = self._infer_primary_key(
                ent_name, ent_data["attributes"]
            )

        return {"entities": entities}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_from_sentence(self, sent_text: str, entities: dict):
        """
        Handle patterns like:
          'Student has ID, Name, Email'
          'Course contains CID, Title'
          'Student entity with attributes ID, Name'
        """
        doc = self.nlp(sent_text)

        # Walk tokens looking for an entity name followed by a trigger word
        i = 0
        while i < len(doc):
            token = doc[i]

            # Identify potential entity names: proper nouns or title-case nouns
            # that are NOT trigger words themselves.
            if self._is_entity_candidate(token):
                entity_name = token.text

                # Look ahead for an attribute trigger
                trigger_idx = self._find_trigger(doc, i + 1)
                if trigger_idx is not None:
                    attrs = self._collect_attributes(doc, trigger_idx + 1)
                    if attrs:
                        if entity_name not in entities:
                            entities[entity_name] = {"attributes": [], "primary_key": None}
                        # Merge (avoid duplicates)
                        existing = set(entities[entity_name]["attributes"])
                        for a in attrs:
                            if a not in existing:
                                entities[entity_name]["attributes"].append(a)
                        i = len(doc)  # consumed sentence
                        continue
            i += 1

    def _extract_from_doc(self, doc, entities: dict):
        """
        Fallback: use spaCy NER + noun chunks to pick up any entities
        not caught by sentence-level patterns.
        """
        # Capitalised standalone nouns that could be entity names
        for chunk in doc.noun_chunks:
            head = chunk.root
            if head.is_alpha and head.text[0].isupper() and len(head.text) > 2:
                name = head.text
                if name not in entities and name.lower() not in ATTRIBUTE_TRIGGERS:
                    entities[name] = {"attributes": [], "primary_key": None}

    def _is_entity_candidate(self, token) -> bool:
        """True if the token looks like an entity name."""
        return (
            token.is_alpha
            and token.text[0].isupper()
            and token.pos_ in {"PROPN", "NOUN"}
            and token.text.lower() not in ATTRIBUTE_TRIGGERS
            and token.text.lower() not in ENTITY_TRIGGERS
            and len(token.text) > 1
        )

    def _find_trigger(self, doc, start_idx: int) -> Optional[int]:
        """
        Scan from start_idx forward (up to 4 tokens) for an attribute trigger word.
        Returns the index of the trigger token or None.
        """
        for j in range(start_idx, min(start_idx + 4, len(doc))):
            if doc[j].lower_ in ATTRIBUTE_TRIGGERS:
                return j
            # Handle multi-word triggers like "consisting of"
            if j + 1 < len(doc):
                bigram = f"{doc[j].lower_} {doc[j+1].lower_}"
                if bigram in ATTRIBUTE_TRIGGERS:
                    return j + 1
        return None

    def _collect_attributes(self, doc, start_idx: int) -> list:
        """
        Collect comma/and-separated attribute names starting at start_idx.
        Stop at sentence boundary or a conjunction that starts a new clause.
        """
        attrs = []
        stop_lower = {"and", "but", "or", "where", "which", "that", "with", "also"}

        i = start_idx
        while i < len(doc):
            tok = doc[i]

            # Stop conditions
            if tok.is_punct and tok.text in {'.', ';', ':'}:
                break
            if tok.lower_ in stop_lower and i > start_idx + 1:
                # "and" between attributes is ok; "and" starting new clause — check
                if i + 1 < len(doc) and doc[i + 1].pos_ not in {"NOUN", "PROPN"}:
                    break

            # Collect nouns, proper nouns, and adjectives (covers "EmailAddress" etc.)
            if tok.pos_ in {"NOUN", "PROPN", "X"} and tok.is_alpha:
                attrs.append(tok.text)
            elif tok.pos_ == "ADJ" and tok.is_alpha and tok.text[0].isupper():
                attrs.append(tok.text)

            i += 1

        return attrs

    def _infer_primary_key(self, entity_name: str, attributes: list) -> Optional[str]:
        """
        Heuristic PK detection (in priority order):
        1. Attribute literally named 'ID'
        2. Attribute matching pattern .*ID (e.g., StudentID, CID)
        3. First attribute ending with 'Id' or 'id'
        Returns None if no PK can be determined.
        """
        # Priority 1: exact "ID"
        for attr in attributes:
            if attr == "ID":
                return attr

        # Priority 2: entityName + ID  e.g., StudentID, CourseID
        entity_id_pattern = re.compile(
            rf'^{re.escape(entity_name[:3])}.*id$', re.IGNORECASE
        )
        for attr in attributes:
            if entity_id_pattern.match(attr):
                return attr

        # Priority 3: any attribute matching PK_PATTERNS
        for attr in attributes:
            if PK_PATTERNS.match(attr):
                return attr

        # Priority 4: first attribute (common convention)
        if attributes:
            return attributes[0]

        return None
