"""Gate D, D-10: the paper-scale run-plan template stays consistent with the manifest contracts.

``docs/designs/PAPER_SCALE_RUN_PLAN_TEMPLATE.md`` lists every field a paper-scale run plan states and, for each, the
field a reviewer reads after the run. This test checks (1) that every required field heading and checklist item is
present, (2) that every contract field the template cites (``manifest.*`` = ``RunManifestV1``, ``index.*`` =
``RunIndexV2``, ``study.*`` = ``StudyManifestV1``, ``plan.*`` = ``AnalysisPlanV1``) exists in that contract, (3) that a
field without a manifest counterpart says so explicitly and names a gap listed in the template, and (4) that every row cites
``file:line`` evidence (informative, named against a base commit; the line numbers themselves are not checked). It does not check any scientific value.
"""
from __future__ import annotations

import re
import typing
from pathlib import Path

import pytest
from pydantic import BaseModel

from academic_benchmark.contracts import RunIndexV2, RunManifestV1, StudyManifestV1
from academic_benchmark.contracts.analysis_plan import AnalysisPlanV1

REPO = Path(__file__).resolve().parents[2]
TEMPLATE = REPO / "docs" / "designs" / "PAPER_SCALE_RUN_PLAN_TEMPLATE.md"

REQUIRED_FIELDS = (
    "Study and profile commit",
    "Profile hash",
    "Algorithm parameters",
    "Algorithms",
    "Instances",
    "Budget levels",
    "Run count",
    "Base seed and seed protocol",
    "Native limits",
    "Analysis plan ID and hash",
    "Machine",
    "Estimate",
    "Output location",
    "Failure policy",
)
REQUIRED_CHECKLIST = (
    "Fixed-budget hygiene merged",
    "MT6 merged",
    "Owner decision 4 merged",
    "Profile status active",
    "Analysis plan not draft",
    "Clean tree",
    "Analysis environment pinned",
    "Full-suite run on the stronger computer recorded",
)
REQUIRED_APPROVAL_PHRASES = (
    "approves the run plan in chat",
    "sha256",
    "DECISION_LOG",
    "status: active",
    "same lead-merged commit",
    "is not paper evidence",
    "differ from the base commit only by the approval commit",
    "git diff <base commit> <index.git.commit> --",
    "git diff --name-status <base commit> <index.git.commit>",
)
CONTRACTS: dict[str, type[BaseModel]] = {
    "manifest": RunManifestV1,
    "index": RunIndexV2,
    "study": StudyManifestV1,
    "plan": AnalysisPlanV1,
}
TOKEN = re.compile(r"`((?:manifest|index|study|plan)\.[A-Za-z0-9_.\[\]<>]+)`")
GAP_REF = re.compile(r"\bG\d+\b")
CITATION = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|json|md)):(\d+)`")


def _template_text() -> str:
    assert TEMPLATE.is_file(), f"missing {TEMPLATE.relative_to(REPO)}"
    return TEMPLATE.read_text(encoding="utf-8")


def _section(text: str, title: str) -> str:
    match = re.search(rf"^## {re.escape(title)}\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert match, f"template has no '## {title}' section"
    return match.group(1)


def _table_rows(section: str) -> list[list[str]]:
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line.replace("|", "").strip()) <= {"-", ":", " "}:
            continue
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows[1:]  # header


def _unwrap(annotation: typing.Any) -> list[typing.Any]:
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        return _unwrap(typing.get_args(annotation)[0])
    if origin in (typing.Union, getattr(__import__("types"), "UnionType", None)):
        found: list[typing.Any] = []
        for arg in typing.get_args(annotation):
            found.extend(_unwrap(arg))
        return found
    if origin is list:
        return _unwrap(typing.get_args(annotation)[0])
    if origin is dict:
        return [dict]
    return [annotation]


def _resolves(model: type[BaseModel], parts: list[str]) -> bool:
    """True when ``parts`` names a field path of ``model`` (free-key dict, TypedDict and JSON values end the check)."""
    if not parts:
        return True
    name, rest = parts[0], parts[1:]
    if name not in model.model_fields:
        return False
    if not rest:
        return True
    for candidate in _unwrap(model.model_fields[name].annotation):
        if isinstance(candidate, type) and issubclass(candidate, BaseModel):
            if _resolves(candidate, rest):
                return True
        elif candidate is dict:
            return True  # free keys (configuration, derived seeds, stage allocation, capabilities)
        elif typing.is_typeddict(candidate):
            if rest[0] in candidate.__annotations__:
                return True
        elif "JsonValue" in repr(candidate) or candidate is typing.Any:
            return True
    return False


def _token_parts(token: str) -> tuple[str, list[str]]:
    namespace, _, path = token.partition(".")
    parts = [re.sub(r"\[\]$", "", piece) for piece in path.split(".")]
    return namespace, [piece for piece in parts if not (piece.startswith("<") and piece.endswith(">"))]


def _field_rows(text: str) -> list[list[str]]:
    rows = _table_rows(_section(text, "Field table"))
    assert rows, "the field table is empty"
    for row in rows:
        assert len(row) == 5, f"field table row needs 5 cells (field, source, check, gap, evidence): {row}"
    return rows


def test_every_required_field_has_a_row() -> None:
    first_cells = [row[0] for row in _field_rows(_template_text())]
    for name in REQUIRED_FIELDS:
        assert any(cell.startswith(name) for cell in first_cells), f"no field row starts with {name!r}"


def test_every_checklist_item_is_listed() -> None:
    rows = _table_rows(_section(_template_text(), "Checklist"))
    first_cells = [row[0] for row in rows]
    for item in REQUIRED_CHECKLIST:
        assert any(cell.startswith(item) for cell in first_cells), f"no checklist row starts with {item!r}"


def test_approval_procedure_states_every_rule() -> None:
    approval = _section(_template_text(), "Approval")
    for phrase in REQUIRED_APPROVAL_PHRASES:
        assert phrase in approval, f"the Approval section does not say {phrase!r}"


def test_every_cited_contract_field_exists() -> None:
    text = _template_text()
    cited = 0
    for section in ("Field table", "Checklist"):
        for row in _table_rows(_section(text, section)):
            for cell in row[1:4]:
                for token in TOKEN.findall(cell):
                    namespace, parts = _token_parts(token)
                    cited += 1
                    assert _resolves(CONTRACTS[namespace], parts), f"{token} is not a field of {CONTRACTS[namespace].__name__}"
    assert cited >= 20, f"the template cites only {cited} contract fields"


def test_a_field_without_a_manifest_counterpart_names_a_listed_gap() -> None:
    text = _template_text()
    gaps_section = _section(text, "Gaps for the lead")
    listed = {row[0] for row in _table_rows(gaps_section)}
    assert listed, "the gap table is empty"
    referenced: set[str] = set()
    for section in ("Field table", "Checklist"):
        for row in _table_rows(_section(text, section)):
            check = row[2]
            has_manifest_field = any(
                TOKEN.match(f"`{t}`") and _token_parts(t)[0] in ("manifest", "index") for t in TOKEN.findall(check)
            )
            gap_cell = row[3] if section == "Field table" else check
            refs = set(GAP_REF.findall(gap_cell))
            referenced |= refs
            if section == "Field table" and "NO MANIFEST FIELD" in check:
                assert refs, f"row {row[0]!r}: 'NO MANIFEST FIELD' needs a gap number in the gap column"
            if not has_manifest_field:
                assert "NO MANIFEST FIELD" in check, f"row {row[0]!r}: no manifest/index field and no explicit 'NO MANIFEST FIELD'"
                assert refs, f"row {row[0]!r}: 'NO MANIFEST FIELD' must name a gap (G1, G2, ...)"
    assert referenced <= listed, f"gaps referenced but not listed: {sorted(referenced - listed)}"
    assert listed <= referenced, f"gaps listed but never referenced: {sorted(listed - referenced)}"


def test_evidence_column_cites_files_informatively() -> None:
    """Line numbers move with the code, so they are not checked; each row still cites something and names the base commit."""
    text = _template_text()
    assert "a75cdde1" in text, "the template must name the commit its file:line citations refer to"
    for row in _field_rows(text):
        assert CITATION.findall(row[4]), f"row {row[0]!r}: no `file:line` evidence"


def test_placeholders_do_not_decide_a_scientific_value() -> None:
    """Run counts, levels and limits stay placeholders that name the owner question (OQ-n), never a number."""
    rows = {row[0]: row for row in _field_rows(_template_text())}
    for name in ("Run count", "Budget levels", "Native limits"):
        key = next(k for k in rows if k.startswith(name))
        assert "OQ-" in rows[key][1], f"{name!r}: the source cell must refer to the owner question"
        assert "<" in rows[key][1], f"{name!r}: the source cell must hold a <placeholder>"


@pytest.mark.parametrize("gap_prefix", ["G1", "G2"])
def test_gap_table_rows_have_a_recommendation(gap_prefix: str) -> None:
    rows = _table_rows(_section(_template_text(), "Gaps for the lead"))
    row = next((r for r in rows if r[0] == gap_prefix), None)
    assert row is not None, f"gap {gap_prefix} missing"
    assert len(row) == 4 and row[2] and row[3], f"gap {gap_prefix} needs what is missing, a way to check it meanwhile and a follow-up"
