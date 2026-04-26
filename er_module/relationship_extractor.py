"""
Module 3: Relationship Extraction Module
Responsibility: Detect and classify relationships between entities
using deterministic rule-based pattern matching.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Relationship:
    """Represents a single relationship between two entities."""
    entity_a: str
    entity_b: str
    rel_type: str          # ONE_TO_ONE | ONE_TO_MANY | MANY_TO_MANY
    label: str
    direction: str = "A→B"
    junction_table: Optional[str] = None


class RelationshipPatterns:
    """Ordered regex pattern library for relationship classification."""

    PATTERNS = [
        # ONE-TO-ONE
        (re.compile(r'(\w+)\s+has\s+exactly\s+one\s+(\w+)', re.IGNORECASE),
         "ONE_TO_ONE", "has one"),
        (re.compile(r'(\w+)\s+one.?to.?one\s+(\w+)', re.IGNORECASE),
         "ONE_TO_ONE", "one-to-one"),
        (re.compile(r'each\s+(\w+)\s+(?:has|is\s+assigned)\s+(?:exactly\s+)?one\s+(\w+)', re.IGNORECASE),
         "ONE_TO_ONE", "is assigned one"),

        # ONE-TO-MANY
        (re.compile(r'one\s+(\w+)\s+can\s+(?:have|enroll\s+in|take|own|teach|contain|hold)\s+(?:many|multiple|several)\s+(\w+)', re.IGNORECASE),
         "ONE_TO_MANY", "can have many"),
        (re.compile(r'(\w+)\s+can\s+(?:have|take|own|teach|contain)\s+(?:many|multiple|several)\s+(\w+)', re.IGNORECASE),
         "ONE_TO_MANY", "can have many"),
        (re.compile(r'(\w+)\s+has\s+(?:many|multiple|several)\s+(\w+)', re.IGNORECASE),
         "ONE_TO_MANY", "has many"),
        (re.compile(r'(\w+)\s+one.?to.?many\s+(\w+)', re.IGNORECASE),
         "ONE_TO_MANY", "one-to-many"),
        (re.compile(r'(\w+)\s+(?:manages|teaches|owns|supervises|controls)\s+(?:many\s+)?(\w+)', re.IGNORECASE),
         "ONE_TO_MANY", "manages"),
        (re.compile(r'(\w+)\s+belongs\s+to\s+(?:a\s+|one\s+)?(\w+)', re.IGNORECASE),
         "ONE_TO_MANY", "belongs to"),
        (re.compile(r'(\w+)\s+is\s+assigned\s+to\s+(?:a\s+|one\s+)?(\w+)', re.IGNORECASE),
         "ONE_TO_MANY", "assigned to"),
        (re.compile(r'each\s+(\w+)\s+has\s+(?:many|multiple)\s+(\w+)', re.IGNORECASE),
         "ONE_TO_MANY", "has many"),

        # MANY-TO-MANY
        (re.compile(r'(\w+)\s+can\s+(?:enroll\s+in|take|attend|register\s+for)\s+(?:many|multiple)\s+(\w+)', re.IGNORECASE),
         "MANY_TO_MANY", "enrolls in"),
        (re.compile(r'(\w+)\s+many.?to.?many\s+(\w+)', re.IGNORECASE),
         "MANY_TO_MANY", "many-to-many"),
        (re.compile(r'many\s+(\w+)\s+can\s+(?:be\s+)?(?:linked|associated|related)\s+to\s+many\s+(\w+)', re.IGNORECASE),
         "MANY_TO_MANY", "associated with"),
        (re.compile(r'(\w+)\s+(?:and|&)\s+(\w+)\s+(?:share|collaborate)', re.IGNORECASE),
         "MANY_TO_MANY", "shares"),
    ]


class RelationshipExtractor:
    """Applies pattern library to sentences and resolves entity names."""

    def __init__(self):
        self.patterns = RelationshipPatterns.PATTERNS

    def extract(self, processed_input: dict, known_entities: list) -> dict:
        sentences = processed_input["sentences"]
        relationships = []
        seen_pairs: set = set()

        for sentence in sentences:
            for pattern, rel_type, label in self.patterns:
                for match in pattern.finditer(sentence):
                    entity_a_raw = match.group(1)
                    entity_b_raw = match.group(2)

                    entity_a = self._resolve_entity(entity_a_raw, known_entities)
                    entity_b = self._resolve_entity(entity_b_raw, known_entities)

                    if entity_a is None or entity_b is None or entity_a == entity_b:
                        continue

                    pair_key = frozenset([entity_a, entity_b, rel_type])
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    direction = "A→B"
                    if "belongs to" in label or "assigned to" in label:
                        entity_a, entity_b = entity_b, entity_a
                        direction = "B→A (reversed)"

                    junction = f"{entity_a}_{entity_b}" if rel_type == "MANY_TO_MANY" else None

                    relationships.append(Relationship(
                        entity_a=entity_a,
                        entity_b=entity_b,
                        rel_type=rel_type,
                        label=label,
                        direction=direction,
                        junction_table=junction,
                    ))

        return {"relationships": relationships}

    def _resolve_entity(self, raw_name: str, known_entities: list) -> Optional[str]:
        """Match raw extracted name to a known entity (case-insensitive + prefix)."""
        if not raw_name:
            return None
        raw_lower = raw_name.lower()
        for name in known_entities:
            if name.lower() == raw_lower:
                return name
        for name in known_entities:
            if name.lower().startswith(raw_lower[:4]) or raw_lower.startswith(name.lower()[:4]):
                return name
        return raw_name.capitalize() if raw_name[0].isupper() else None
