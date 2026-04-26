"""
Module 4: ER Model Builder
Responsibility: Combine extracted entities and relationships into a
structured, validated ER model (JSON-serializable dict).

Also assigns:
- Primary keys (confirmed/refined)
- Foreign keys (derived from relationships)
- Junction table definitions for M:N
"""

import json
from typing import Optional
from .relationship_extractor import Relationship


class ERModelBuilder:
    """
    Constructs the canonical ER model data structure.

    Output schema:
    {
      "entities": {
        "EntityName": {
          "attributes": ["attr1", "attr2"],
          "primary_key": "attr_name",
          "foreign_keys": [
            {"column": "fk_col", "references": "OtherEntity.pk_col"}
          ]
        }
      },
      "relationships": [
        {
          "entity_a": "...",
          "entity_b": "...",
          "rel_type": "ONE_TO_MANY",
          "label": "...",
          "junction_table": null
        }
      ],
      "junction_tables": {
        "TableName": {
          "columns": ["fk_a", "fk_b"],
          "primary_key": ["fk_a", "fk_b"]
        }
      }
    }
    """

    def build(self, nlp_result: dict, rel_result: dict) -> dict:
        """
        Parameters
        ----------
        nlp_result : dict
            Output of NLPExtractor.extract()  → {"entities": {...}}
        rel_result : dict
            Output of RelationshipExtractor.extract() → {"relationships": [...]}

        Returns
        -------
        dict : The complete ER model
        """
        entities = {}
        for name, data in nlp_result["entities"].items():
            entities[name] = {
                "attributes": list(data["attributes"]),
                "primary_key": data.get("primary_key"),
                "foreign_keys": [],
            }

        relationships = []
        junction_tables = {}

        for rel in rel_result["relationships"]:
            # Ensure both entities exist in the model
            if rel.entity_a not in entities:
                entities[rel.entity_a] = {
                    "attributes": [], "primary_key": None, "foreign_keys": []
                }
            if rel.entity_b not in entities:
                entities[rel.entity_b] = {
                    "attributes": [], "primary_key": None, "foreign_keys": []
                }

            rel_dict = {
                "entity_a": rel.entity_a,
                "entity_b": rel.entity_b,
                "rel_type": rel.rel_type,
                "label": rel.label,
                "direction": rel.direction,
                "junction_table": rel.junction_table,
            }
            relationships.append(rel_dict)

            # ── Assign foreign keys ──────────────────────────────────────
            if rel.rel_type == "ONE_TO_ONE":
                # FK goes on entity_b (convention: weaker side)
                self._add_fk(
                    entities, rel.entity_b,
                    fk_col=f"{rel.entity_a.lower()}_id",
                    references=rel.entity_a,
                    pk_col=entities[rel.entity_a]["primary_key"] or "id",
                )

            elif rel.rel_type == "ONE_TO_MANY":
                # FK goes on the "many" side → entity_b
                self._add_fk(
                    entities, rel.entity_b,
                    fk_col=f"{rel.entity_a.lower()}_id",
                    references=rel.entity_a,
                    pk_col=entities[rel.entity_a]["primary_key"] or "id",
                )

            elif rel.rel_type == "MANY_TO_MANY":
                # Create a junction table
                jt_name = rel.junction_table or f"{rel.entity_a}_{rel.entity_b}"
                fk_a = f"{rel.entity_a.lower()}_id"
                fk_b = f"{rel.entity_b.lower()}_id"
                junction_tables[jt_name] = {
                    "columns": [fk_a, fk_b],
                    "primary_key": [fk_a, fk_b],
                    "foreign_keys": [
                        {"column": fk_a, "references": f"{rel.entity_a}.{entities[rel.entity_a]['primary_key'] or 'id'}"},
                        {"column": fk_b, "references": f"{rel.entity_b}.{entities[rel.entity_b]['primary_key'] or 'id'}"},
                    ]
                }

        return {
            "entities": entities,
            "relationships": relationships,
            "junction_tables": junction_tables,
        }

    # ------------------------------------------------------------------

    def _add_fk(self, entities: dict, target_entity: str,
                fk_col: str, references: str, pk_col: str):
        """Add a foreign key to target_entity if not already present."""
        fk_def = {"column": fk_col, "references": f"{references}.{pk_col}"}
        existing = [f["column"] for f in entities[target_entity]["foreign_keys"]]
        if fk_col not in existing:
            entities[target_entity]["foreign_keys"].append(fk_def)
            # Also register FK column in attributes if missing
            if fk_col not in entities[target_entity]["attributes"]:
                entities[target_entity]["attributes"].append(fk_col)

    def to_json(self, er_model: dict, indent: int = 2) -> str:
        """Serialize the ER model to a pretty-printed JSON string."""
        return json.dumps(er_model, indent=indent, ensure_ascii=False)
