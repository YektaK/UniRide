"""Active, manifest-governed TSPLIB inputs of the exact reference runner (WP-E8 companion task; DECISION_LOG E12).

Three tracked collections hold the instance data and the published optima that GOAL 2 verifies against:

* ``academic_benchmark/tsplib_data/tsp/``: the 16 TSP instances with n <= 100 (E09), ``MANIFEST.json`` schema
  ``uniride-tsp-collection/v1``; per file sha256, canonical coordinate-text sha256, provenance and published optimum;
* ``academic_benchmark/tsplib_data/opt_tours/``: the published optimal tours, ``MANIFEST.json`` schema
  ``uniride-opt-tour-collection/v1``; a tour that is not published is listed with ``source: none``;
* ``academic_benchmark/tsplib_data/atsp/``: ATSP collection (``uniride-atsp-collection/v1``, existing); ft53 is read here.

Every read verifies the file bytes against the manifest sha256 first; a missing or altered file is an error, never a
silent skip. Standard library only; no database is opened; nothing is written. Any path inside the archive directory is
refused (:func:`archive_refusal`): archived material is evidence to be quarantined, not an input
(``ACADEMIC_STUDY_UNIFICATION_DESIGN.md``, archive and default-input rule).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TSPLIB_DATA_DIR = REPO_ROOT / "academic_benchmark" / "tsplib_data"
TSP_DIR = TSPLIB_DATA_DIR / "tsp"
OPT_TOUR_DIR = TSPLIB_DATA_DIR / "opt_tours"
ATSP_MANIFEST = TSPLIB_DATA_DIR / "atsp" / "MANIFEST.json"
MANIFEST_NAME = "MANIFEST.json"
TSP_SCHEMA = "uniride-tsp-collection/v1"
TOUR_SCHEMA = "uniride-opt-tour-collection/v1"
ATSP_SCHEMA = "uniride-atsp-collection/v1"
_REFUSED_PART = "archive"


class InputRefused(ValueError):
    """An input is missing, altered (sha256 differs from its manifest) or comes from a refused location."""


def archive_refusal(path) -> str:
    """Refusal message when ``path`` lies in the archive directory (relative, absolute, ``..`` and case variants
    included), else ''."""
    raw = Path(path)
    candidates = [Path(os.path.normpath(raw))]
    try:
        candidates.append(raw.resolve())
    except OSError:
        pass
    for cand in candidates:
        try:
            parts = cand.relative_to(REPO_ROOT).parts  # inside the checkout: only the part below the root counts
        except ValueError:
            parts = cand.parts
        if any(p.lower() == _REFUSED_PART for p in parts):
            return (f"{raw} lies in the archive directory; archived files are never read as input, use the active "
                    f"dataset folders (academic_benchmark/tsplib_data/tsp and opt_tours)")
    return ""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def coordinate_text_sha256(coords) -> str:
    """sha256 of the canonical coordinate text: one line ``{i} {x!r} {y!r}`` + LF per node, ASCII, 0-based."""
    canonical = "".join(f"{i} {x!r} {y!r}\n" for i, (x, y) in enumerate(coords)).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()


def _load_manifest(manifest_path: Path, schema: str) -> dict:
    if not manifest_path.is_file():
        raise InputRefused(f"manifest not found: {manifest_path.name} (collection folder {manifest_path.parent.name})")
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    if doc.get("schema_version") != schema:
        raise InputRefused(f"{manifest_path.name}: schema_version {doc.get('schema_version')!r}, expected {schema!r}")
    return doc


def _entry(doc: dict, name: str):
    want = name.lower()
    for inst in doc.get("instances", ()):
        if str(inst.get("name", "")).lower() == want:
            return inst
    return None


def _verified_bytes(path: Path, entry: dict, what: str) -> bytes:
    if not path.is_file():
        raise InputRefused(f"{entry['name']}: {what} {path.name} is missing")
    data = path.read_bytes()
    digest = sha256_bytes(data)
    if digest != entry.get("sha256"):
        raise InputRefused(f"{entry['name']}: {what} {path.name} has sha256 {digest}, the manifest says {entry.get('sha256')}")
    return data


# ---------------------------------------------------------------- the 16 TSP instances
def tsp_entries(tsp_dir=TSP_DIR) -> list:
    """Manifest entries of the TSP collection, in manifest order."""
    return list(_load_manifest(Path(tsp_dir) / MANIFEST_NAME, TSP_SCHEMA)["instances"])


def read_tsp_file(name: str, tsp_dir=TSP_DIR):
    """(file text, manifest entry) of a committed instance after the sha256 check, or None when the collection does not
    list ``name``."""
    tsp_dir = Path(tsp_dir)
    entry = _entry(_load_manifest(tsp_dir / MANIFEST_NAME, TSP_SCHEMA), name)
    if entry is None:
        return None
    return _verified_bytes(tsp_dir / entry["file_name"], entry, "instance file").decode("utf-8"), entry


# ---------------------------------------------------------------- ATSP (ft53)
def atsp_entries(manifest_path=ATSP_MANIFEST) -> list:
    return list(_load_manifest(Path(manifest_path), ATSP_SCHEMA)["instances"])


def read_atsp_file(name: str, manifest_path=ATSP_MANIFEST):
    """(file text, manifest entry) of an ATSP instance listed in the ATSP collection manifest (sha256 verified), or
    None. ``artifact_path`` of the entry is relative to the repository root."""
    entry = _entry(_load_manifest(Path(manifest_path), ATSP_SCHEMA), name)
    if entry is None:
        return None
    path = REPO_ROOT / entry["artifact_path"]
    return _verified_bytes(path, entry, "instance file").decode("utf-8"), entry


# ---------------------------------------------------------------- published optimal tours
def parse_tour_text(text: str) -> list:
    """1-based node ids of a TSPLIB ``TOUR_SECTION``. Several ids may share a line; ``-1`` or ``EOF`` ends the section."""
    nodes, in_section = [], False
    for line in text.splitlines():
        token = line.strip()
        if token.upper().startswith("TOUR_SECTION"):
            in_section = True
        elif in_section:
            for part in token.split():
                if part in ("-1", "EOF"):
                    return nodes
                nodes.append(int(part))
    return nodes


def read_collection_tour(name: str, tour_dir=OPT_TOUR_DIR):
    """(1-based node list, ``"opt_tour_file"``) of the published tour of ``name`` after the sha256 check, or None when
    the collection lists no tour for it (``source: none``) or does not list it at all."""
    tour_dir = Path(tour_dir)
    entry = _entry(_load_manifest(tour_dir / MANIFEST_NAME, TOUR_SCHEMA), name)
    if entry is None or entry.get("source") == "none":
        return None
    text = _verified_bytes(tour_dir / entry["file_name"], entry, "tour file").decode("utf-8")
    return parse_tour_text(text), "opt_tour_file"
