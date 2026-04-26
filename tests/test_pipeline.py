"""
Test Suite for ER Diagram Generation Module
Tests all pipeline stages with realistic academic-project inputs.

Run:  python -m pytest tests/ -v
  or: python tests/test_pipeline.py
"""

import pytest
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from er_module.input_processor      import InputProcessor
from er_module.nlp_extractor        import NLPExtractor
from er_module.relationship_extractor import RelationshipExtractor, Relationship
from er_module.er_model_builder     import ERModelBuilder
from er_module.sql_schema_generator import SQLSchemaGenerator
from er_module.pipeline             import ERPipeline


# ──────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def processor():
    return InputProcessor()

@pytest.fixture(scope="module")
def extractor():
    return NLPExtractor()

@pytest.fixture(scope="module")
def rel_extractor():
    return RelationshipExtractor()

@pytest.fixture(scope="module")
def builder():
    return ERModelBuilder()

@pytest.fixture(scope="module")
def sql_gen():
    return SQLSchemaGenerator()

@pytest.fixture(scope="module")
def pipeline():
    return ERPipeline(output_dir="./test_outputs")


# ──────────────────────────────────────────────────────────────────────────
# Test Cases
# ──────────────────────────────────────────────────────────────────────────

TEST_CASES = [
    {
        "name": "Student-Course 1:N",
        "input": (
            "Student has ID, Name, Email. "
            "Course has CID and Title. "
            "One Student can enroll in many Courses."
        ),
        "expected_entities": ["Student", "Course"],
        "expected_rel_type": "ONE_TO_MANY",
    },
    {
        "name": "Employee-Department belongs to",
        "input": (
            "Employee has EmpID, Name, Salary. "
            "Department has DeptID, DName. "
            "Each Employee belongs to a Department."
        ),
        "expected_entities": ["Employee", "Department"],
        "expected_rel_type": "ONE_TO_MANY",
    },
    {
        "name": "Doctor-Patient M:N",
        "input": (
            "Doctor has DoctorID, Name, Specialization. "
            "Patient has PatientID, Name, Age. "
            "Many Doctors can be associated to many Patients."
        ),
        "expected_entities": ["Doctor", "Patient"],
        "expected_rel_type": "MANY_TO_MANY",
    },
    {
        "name": "Library System Multi-entity",
        "input": (
            "Book has BookID, Title, ISBN. "
            "Author has AuthorID, Name. "
            "Member has MemberID, Name, Email. "
            "One Author can write many Books. "
            "Member can borrow many Books."
        ),
        "expected_entities": ["Book", "Author", "Member"],
        "expected_rel_type": None,  # multiple, just check entities
    },
    {
        "name": "1:1 Relationship",
        "input": (
            "Employee has EmpID, Name. "
            "Passport has PassportID, PassportNumber. "
            "Each Employee has exactly one Passport."
        ),
        "expected_entities": ["Employee", "Passport"],
        "expected_rel_type": "ONE_TO_ONE",
    },
]


# ──────────────────────────────────────────────────────────────────────────
# Unit Tests
# ──────────────────────────────────────────────────────────────────────────

class TestInputProcessor:
    def test_basic_cleaning(self, processor):
        result = processor.process("  Student has ID, Name.  ")
        assert "cleaned" in result
        assert result["cleaned"].strip() != ""

    def test_empty_input_raises(self, processor):
        with pytest.raises(ValueError):
            processor.process("")

    def test_whitespace_only_raises(self, processor):
        with pytest.raises(ValueError):
            processor.process("   ")

    def test_abbreviation_expansion(self, processor):
        result = processor.process("Student PK is ID, FK references Course.")
        assert "primary key" in result["cleaned"].lower()
        assert "foreign key" in result["cleaned"].lower()

    def test_sentence_splitting(self, processor):
        result = processor.process("Student has ID. Course has CID.")
        assert len(result["sentences"]) >= 2


class TestNLPExtractor:
    def test_entity_extraction(self, extractor):
        proc = InputProcessor()
        processed = proc.process("Student has ID, Name, Email.")
        result = extractor.extract(processed)
        assert "Student" in result["entities"]

    def test_attribute_extraction(self, extractor):
        proc = InputProcessor()
        processed = proc.process("Student has ID, Name, Email.")
        result = extractor.extract(processed)
        attrs = result["entities"].get("Student", {}).get("attributes", [])
        assert len(attrs) >= 1

    def test_pk_inference(self, extractor):
        proc = InputProcessor()
        processed = proc.process("Student has ID, Name, Email.")
        result = extractor.extract(processed)
        pk = result["entities"].get("Student", {}).get("primary_key")
        assert pk is not None


class TestRelationshipExtractor:
    def test_one_to_many_detection(self, rel_extractor):
        proc = InputProcessor()
        processed = proc.process("One Student can enroll in many Courses.")
        result = rel_extractor.extract(processed, known_entities=["Student", "Course"])
        types = [r.rel_type for r in result["relationships"]]
        assert "ONE_TO_MANY" in types

    def test_many_to_many_detection(self, rel_extractor):
        proc = InputProcessor()
        processed = proc.process("Many Doctors can be associated to many Patients.")
        result = rel_extractor.extract(processed, known_entities=["Doctor", "Patient"])
        types = [r.rel_type for r in result["relationships"]]
        assert "MANY_TO_MANY" in types

    def test_one_to_one_detection(self, rel_extractor):
        proc = InputProcessor()
        processed = proc.process("Each Employee has exactly one Passport.")
        result = rel_extractor.extract(processed, known_entities=["Employee", "Passport"])
        types = [r.rel_type for r in result["relationships"]]
        assert "ONE_TO_ONE" in types

    def test_no_false_positives(self, rel_extractor):
        proc = InputProcessor()
        processed = proc.process("The sky is blue today.")
        result = rel_extractor.extract(processed, known_entities=[])
        assert result["relationships"] == []


class TestERModelBuilder:
    def test_fk_assignment_one_to_many(self, builder):
        nlp_result = {
            "entities": {
                "Student": {"attributes": ["ID", "Name"], "primary_key": "ID"},
                "Course":  {"attributes": ["CID", "Title"], "primary_key": "CID"},
            }
        }
        from er_module.relationship_extractor import Relationship
        rel_result = {
            "relationships": [
                Relationship("Student", "Course", "ONE_TO_MANY", "enrolls in")
            ]
        }
        model = builder.build(nlp_result, rel_result)
        course_fks = [f["column"] for f in model["entities"]["Course"]["foreign_keys"]]
        assert "student_id" in course_fks

    def test_junction_table_many_to_many(self, builder):
        nlp_result = {
            "entities": {
                "Doctor":  {"attributes": ["DoctorID"], "primary_key": "DoctorID"},
                "Patient": {"attributes": ["PatientID"], "primary_key": "PatientID"},
            }
        }
        from er_module.relationship_extractor import Relationship
        rel_result = {
            "relationships": [
                Relationship("Doctor", "Patient", "MANY_TO_MANY", "treats",
                             junction_table="Doctor_Patient")
            ]
        }
        model = builder.build(nlp_result, rel_result)
        assert "Doctor_Patient" in model["junction_tables"]

    def test_json_serializable(self, builder):
        nlp_result = {"entities": {
            "X": {"attributes": ["XID"], "primary_key": "XID"}
        }}
        rel_result = {"relationships": []}
        model = builder.build(nlp_result, rel_result)
        json_str = builder.to_json(model)
        parsed = json.loads(json_str)
        assert "entities" in parsed


class TestSQLGenerator:
    def test_creates_table_statements(self, sql_gen):
        model = {
            "entities": {
                "Student": {
                    "attributes": ["ID", "Name", "Email"],
                    "primary_key": "ID",
                    "foreign_keys": [],
                }
            },
            "relationships": [],
            "junction_tables": {},
        }
        sql = sql_gen.generate(model)
        assert "CREATE TABLE" in sql
        assert "Student" in sql
        assert "PRIMARY KEY" in sql

    def test_foreign_key_in_sql(self, sql_gen):
        model = {
            "entities": {
                "Course": {
                    "attributes": ["CID", "Title", "student_id"],
                    "primary_key": "CID",
                    "foreign_keys": [{"column": "student_id", "references": "Student.ID"}],
                }
            },
            "relationships": [],
            "junction_tables": {},
        }
        sql = sql_gen.generate(model)
        assert "FOREIGN KEY" in sql
        assert "REFERENCES Student" in sql

    def test_junction_table_in_sql(self, sql_gen):
        model = {
            "entities": {},
            "relationships": [],
            "junction_tables": {
                "Doctor_Patient": {
                    "columns": ["doctor_id", "patient_id"],
                    "primary_key": ["doctor_id", "patient_id"],
                    "foreign_keys": [
                        {"column": "doctor_id",  "references": "Doctor.DoctorID"},
                        {"column": "patient_id", "references": "Patient.PatientID"},
                    ]
                }
            },
        }
        sql = sql_gen.generate(model)
        assert "Doctor_Patient" in sql


# ──────────────────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────────────────

class TestPipelineIntegration:
    @pytest.mark.parametrize("tc", TEST_CASES, ids=[tc["name"] for tc in TEST_CASES])
    def test_full_pipeline(self, pipeline, tc):
        result = pipeline.run(
            user_text=tc["input"],
            output_name="test_er",
            generate_sql=True,
            view_diagram=False,
        )
        # ER model structure
        assert "entities" in result["er_model"]
        assert "relationships" in result["er_model"]
        assert "junction_tables" in result["er_model"]

        # Expected entities present
        for expected_ent in tc["expected_entities"]:
            assert expected_ent in result["er_model"]["entities"], \
                f"Expected entity '{expected_ent}' not found in {list(result['er_model']['entities'].keys())}"

        # Expected relationship type
        if tc["expected_rel_type"]:
            found_types = [r["rel_type"] for r in result["er_model"]["relationships"]]
            assert tc["expected_rel_type"] in found_types, \
                f"Expected rel type '{tc['expected_rel_type']}' not found in {found_types}"

        # JSON output is valid
        parsed = json.loads(result["er_json"])
        assert "entities" in parsed

        # SQL output if requested
        assert result["sql"] is not None
        assert "CREATE TABLE" in result["sql"]

    def test_empty_input_raises(self, pipeline):
        with pytest.raises(ValueError):
            pipeline.run("")

    def test_ambiguous_input_returns_warnings(self, pipeline):
        result = pipeline.run("something happened somewhere somehow.")
        assert len(result["warnings"]) > 0


# ──────────────────────────────────────────────────────────────────────────
# Quick manual runner (no pytest required)
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("ER Pipeline — Manual Test Runner")
    print("=" * 60)

    p = ERPipeline(output_dir="./test_outputs")

    for tc in TEST_CASES:
        print(f"\n📋 Test: {tc['name']}")
        print(f"   Input: {tc['input'][:80]}…")
        result = p.run(tc["input"], generate_sql=True, view_diagram=False)

        print(f"   Entities: {list(result['er_model']['entities'].keys())}")
        print(f"   Relationships: {[r['rel_type'] for r in result['er_model']['relationships']]}")
        print(f"   Warnings: {result['warnings']}")
        if result["diagram_path"]:
            print(f"   Diagram: {result['diagram_path']}")
        print()

    print("✅ All manual tests complete.")
