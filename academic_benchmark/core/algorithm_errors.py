"""Stable selection failures for academic algorithm boundaries."""

from __future__ import annotations


class AlgorithmSelectionError(ValueError):
    """Base class for expected algorithm selection and execution failures."""

    def __init__(
        self,
        code: str,
        message: str,
        replacement_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.replacement_id = replacement_id


class UnknownAlgorithmError(AlgorithmSelectionError):
    def __init__(self, requested_id: object) -> None:
        super().__init__(
            "unknown_algorithm",
            f"Unknown algorithm identifier '{requested_id}'.",
        )


class PlannedAlgorithmError(AlgorithmSelectionError):
    def __init__(self, canonical_id: str) -> None:
        super().__init__(
            "planned_algorithm",
            f"Algorithm '{canonical_id}' is planned and cannot be selected.",
        )


class CandidateAlgorithmError(AlgorithmSelectionError):
    def __init__(self, canonical_id: str) -> None:
        super().__init__(
            "candidate_algorithm",
            f"Algorithm '{canonical_id}' is a candidate and cannot be selected.",
        )


class DeprecatedManifestIdentifierError(AlgorithmSelectionError):
    def __init__(self, requested_id: str, replacement_id: str) -> None:
        super().__init__(
            "deprecated_manifest_identifier",
            f"Manifest algorithm identifier '{requested_id}' is not canonical; use "
            f"'{replacement_id}' instead.",
            replacement_id,
        )


class ForbiddenAliasError(AlgorithmSelectionError):
    def __init__(self, requested_id: str, replacement_id: str | None = None) -> None:
        message = f"Algorithm identifier '{requested_id}' is forbidden."
        if replacement_id:
            message = f"{message} Use '{replacement_id}' instead."
        super().__init__("forbidden_alias", message, replacement_id)


class UnsupportedProblemContractError(AlgorithmSelectionError):
    def __init__(self, detail: str) -> None:
        super().__init__("unsupported_problem_contract", detail)


class UnsupportedProtocolError(AlgorithmSelectionError):
    def __init__(self, detail: str) -> None:
        super().__init__("unsupported_protocol", detail)


class BackendUnavailableError(AlgorithmSelectionError):
    def __init__(self, detail: str) -> None:
        super().__init__("backend_unavailable", detail)


class CapabilityEvidenceError(AlgorithmSelectionError):
    def __init__(self, detail: str) -> None:
        super().__init__("capability_evidence_error", detail)


class ExecutorUnavailableError(AlgorithmSelectionError):
    def __init__(self, detail: str) -> None:
        super().__init__("executor_unavailable", detail)


class ResultContractViolation(AlgorithmSelectionError):
    def __init__(self, detail: str) -> None:
        super().__init__("result_contract_violation", detail)
