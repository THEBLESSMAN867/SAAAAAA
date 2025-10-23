"""Golden Rule enforcement utilities."""

from __future__ import annotations

import hashlib
from typing import Iterable, List, Optional, Set


class GoldenRuleViolation(Exception):
    """Raised when a Golden Rule assertion is violated."""


class GoldenRuleValidator:
    """Enforces the Golden Rules across orchestrated execution phases."""

    def __init__(self, questionnaire_hash: str, step_catalog: Iterable[str]):
        self._baseline_questionnaire_hash = questionnaire_hash
        self._baseline_step_signature = self._hash_sequence(step_catalog)
        self._baseline_step_catalog = list(step_catalog)
        self._state_ids: Set[int] = set()
        self._predicate_signature: Optional[Set[str]] = None

    @staticmethod
    def _hash_sequence(sequence: Iterable[str]) -> str:
        canonical = "|".join(str(item) for item in sequence)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def assert_immutable_metadata(
        self,
        questionnaire_hash: str,
        step_catalog: Iterable[str]
    ) -> None:
        """Ensure canonical questionnaire and step catalog remain unchanged."""

        if self._baseline_questionnaire_hash:
            if questionnaire_hash and questionnaire_hash != self._baseline_questionnaire_hash:
                raise GoldenRuleViolation("Questionnaire metadata hash mismatch")

        if self._hash_sequence(step_catalog) != self._baseline_step_signature:
            raise GoldenRuleViolation("Execution step catalog mutated")

    def reset_atomic_state(self) -> None:
        """Reset atomic state tracking between phases."""

        self._state_ids.clear()

    def assert_atomic_context(self, state_obj: object) -> None:
        """Ensure copy-on-write semantics for per-step state."""

        obj_id = id(state_obj)
        if obj_id in self._state_ids:
            raise GoldenRuleViolation("State object reused across steps")

        self._state_ids.add(obj_id)

    def assert_deterministic_dag(self, step_ids: List[str]) -> None:
        """Validate deterministic ordering and absence of cycles."""

        if len(step_ids) != len(set(step_ids)):
            raise GoldenRuleViolation("Duplicate step identifiers detected")

        if sorted(step_ids) != step_ids:
            raise GoldenRuleViolation("Execution chain deviates from canonical order")

    def assert_homogeneous_treatment(self, predicate_set: Iterable[str]) -> None:
        """Ensure identical predicate set is applied across all questions."""

        fingerprint = {str(item) for item in predicate_set}

        if self._predicate_signature is None:
            self._predicate_signature = fingerprint
            return

        if fingerprint != self._predicate_signature:
            raise GoldenRuleViolation("Predicate set mismatch detected")

    @property
    def baseline_step_catalog(self) -> List[str]:
        """Expose the baseline step catalog for downstream validation."""

        return list(self._baseline_step_catalog)
