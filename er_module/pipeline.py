"""
Pipeline Orchestrator
Responsibility: Tie all modules together into a single callable interface.
This is the main entry point for the ER generation module.

Integration point for the Hybrid AI Database Engine:
  - Call ERPipeline.run(user_text) from your existing FastAPI / Streamlit routes.
  - Returns: {"er_model": {...}, "sql": "...", "diagram_path": "..."}
"""

import os
import logging
from typing import Optional

from .input_processor      import InputProcessor
from .nlp_extractor        import NLPExtractor
from .relationship_extractor import RelationshipExtractor
from .er_model_builder     import ERModelBuilder
from .er_diagram_generator import ERDiagramGenerator
from .sql_schema_generator import SQLSchemaGenerator

logger = logging.getLogger(__name__)


class ERPipeline:
    """
    End-to-end pipeline: natural language → ER diagram + JSON + SQL.

    Example
    -------
    >>> pipeline = ERPipeline()
    >>> result   = pipeline.run(
    ...     "Student has ID, Name, Email. Course has CID and Title. "
    ...     "One Student can enroll in many Courses."
    ... )
    >>> print(result["sql"])
    >>> print(result["diagram_path"])
    """

    def __init__(
        self,
        spacy_model: str = "en_core_web_sm",
        output_dir: str  = "./er_outputs",
    ):
        self.output_dir  = output_dir
        os.makedirs(output_dir, exist_ok=True)

        logger.info("Initialising ER Pipeline components …")
        self.processor    = InputProcessor()
        self.nlp          = NLPExtractor(model=spacy_model)
        self.rel_extractor = RelationshipExtractor()
        self.model_builder = ERModelBuilder()
        self.diagram_gen   = ERDiagramGenerator()
        self.sql_gen       = SQLSchemaGenerator()
        logger.info("Pipeline ready.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        user_text: str,
        output_name: str = "er_diagram",
        diagram_format: str = "png",
        generate_sql: bool = True,
        view_diagram: bool = False,
        notation: str = "chen",
    ) -> dict:
        """
        Execute the full pipeline.

        Parameters
        ----------
        user_text      : str  — raw natural language input
        output_name    : str  — base filename for the diagram
        diagram_format : str  — 'png', 'pdf', or 'svg'
        generate_sql   : bool — whether to generate SQL DDL
        view_diagram   : bool — open diagram in system viewer
        notation       : str  — 'chen' or 'crow'

        Returns
        -------
        dict:
            {
              "er_model"     : dict,
              "er_json"      : str,
              "sql"          : str or None,
              "diagram_path" : str,
              "warnings"     : list[str]
            }
        """
        warnings = []

        # ── Stage 1: Input Processing ──────────────────────────────────
        logger.info("[1/5] Processing input …")
        try:
            processed = self.processor.process(user_text)
        except ValueError as e:
            raise ValueError(f"Input processing failed: {e}") from e

        # ── Stage 2: NLP Extraction ────────────────────────────────────
        logger.info("[2/5] Extracting entities and attributes …")
        nlp_result = self.nlp.extract(processed)

        if not nlp_result["entities"]:
            warnings.append(
                "No entities were detected. Make sure entity names are "
                "capitalised (e.g., 'Student', 'Course')."
            )

        # ── Stage 3: Relationship Extraction ──────────────────────────
        logger.info("[3/5] Extracting relationships …")
        known_entities = list(nlp_result["entities"].keys())
        rel_result = self.rel_extractor.extract(processed, known_entities)

        if not rel_result["relationships"]:
            warnings.append(
                "No relationships detected. Try phrases like "
                "'one X can have many Y' or 'X belongs to Y'."
            )

        # ── Stage 4: ER Model Building ─────────────────────────────────
        logger.info("[4/5] Building ER model …")
        er_model = self.model_builder.build(nlp_result, rel_result)
        er_json  = self.model_builder.to_json(er_model)

        # ── Stage 5a: Diagram Generation ──────────────────────────────
        logger.info("[5/5] Generating ER diagram …")
        diagram_path_base = os.path.join(self.output_dir, output_name)
        try:
            diagram_path = self.diagram_gen.generate(
                er_model,
                output_path=diagram_path_base,
                fmt=diagram_format,
                view=view_diagram,
                notation=notation,
            )
        except Exception as e:
            diagram_path = None
            warnings.append(f"Diagram generation failed: {e}. Is Graphviz installed?")
            logger.warning("Diagram generation error: %s", e)

        # ── Stage 5b: SQL Generation (optional) ───────────────────────
        sql_output = None
        if generate_sql:
            sql_output = self.sql_gen.generate(er_model)

        logger.info("Pipeline complete.")
        return {
            "er_model"    : er_model,
            "er_json"     : er_json,
            "sql"         : sql_output,
            "diagram_path": diagram_path,
            "warnings"    : warnings,
        }
