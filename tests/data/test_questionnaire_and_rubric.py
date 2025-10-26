import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema_validator import SchemaValidator


def _write_payload(path: Path, payload: dict) -> None:
    payload["content_hash"] = SchemaValidator._canonical_hash(payload)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


@pytest.fixture()
def questionnaire_payload():
    with Path("questionnaire.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture()
def rubric_payload():
    with Path("rubric_scoring.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_questionnaire_invalid_policy_area(tmp_path, questionnaire_payload):
    questionnaire = json.loads(json.dumps(questionnaire_payload))
    questionnaire["questions"][0]["policy_area_id"] = "PA99"
    path = tmp_path / "questionnaire.json"
    _write_payload(path, questionnaire)

    validator = SchemaValidator()
    report, _ = validator.validate_questionnaire(path)

    assert not report.is_valid
    assert any("unknown policy_area_id" in error for error in report.errors)


def test_rubric_weight_out_of_bounds(tmp_path, rubric_payload):
    rubric = json.loads(json.dumps(rubric_payload))
    rubric["aggregation"]["dimension_question_weights"]["DIM01"]["Q001"] = 2.0
    path = tmp_path / "rubric.json"
    _write_payload(path, rubric)

    validator = SchemaValidator()
    report = validator.validate_rubric(None, path)

    assert not report.is_valid
    assert any("must sum to 1.0" in error for error in report.errors)


def test_rubric_macro_weights_not_one(tmp_path, rubric_payload):
    rubric = json.loads(json.dumps(rubric_payload))
    rubric["aggregation"]["macro_cluster_weights"]["CL01"] = 0.9
    path = tmp_path / "rubric.json"
    _write_payload(path, rubric)

    validator = SchemaValidator()
    report = validator.validate_rubric(None, path)

    assert not report.is_valid
    assert any("macro_cluster_weights" in error for error in report.errors)


def test_rubric_missing_allowed_modality(tmp_path, questionnaire_payload, rubric_payload):
    rubric = json.loads(json.dumps(rubric_payload))
    rubric["rubric_matrix"]["PA01"]["DIM01"]["allowed_modalities"] = ["TYPE_B"]
    path = tmp_path / "rubric.json"
    _write_payload(path, rubric)

    validator = SchemaValidator()
    report = validator.validate_rubric(questionnaire_payload, path)

    assert not report.is_valid
    assert any("not allowed" in error for error in report.errors)


def test_rubric_missing_na_rule(tmp_path, rubric_payload):
    rubric = json.loads(json.dumps(rubric_payload))
    rubric["na_rules"]["modalities"].pop("TYPE_A", None)
    path = tmp_path / "rubric.json"
    _write_payload(path, rubric)

    validator = SchemaValidator()
    report = validator.validate_rubric(None, path)

    assert not report.is_valid
    assert any("NA rules missing" in error for error in report.errors)


def test_rubric_missing_determinism(tmp_path, rubric_payload):
    rubric = json.loads(json.dumps(rubric_payload))
    rubric["scoring_modalities"]["TYPE_F"].pop("determinism", None)
    path = tmp_path / "rubric.json"
    _write_payload(path, rubric)

    validator = SchemaValidator()
    report = validator.validate_rubric(None, path)

    assert not report.is_valid
    assert any("determinism" in error for error in report.errors)
