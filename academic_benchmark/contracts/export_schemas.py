from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dataset import DatasetManifestV1
from .run import RunManifestV1
from .study import StudyManifestV1


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
MODELS = {
    "study-v1.schema.json": StudyManifestV1,
    "dataset-v1.schema.json": DatasetManifestV1,
    "run-v1.schema.json": RunManifestV1,
}


def render_schemas() -> dict[str, str]:
    rendered: dict[str, str] = {}
    for filename, model in MODELS.items():
        schema = model.model_json_schema(mode="validation")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        rendered[filename] = json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return rendered


def write_schemas(root: Path = SCHEMA_DIR) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for filename, content in render_schemas().items():
        (root / filename).write_text(content, encoding="utf-8", newline="\n")


def check_schemas(root: Path = SCHEMA_DIR) -> list[str]:
    stale: list[str] = []
    for filename, content in render_schemas().items():
        path = root / filename
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            stale.append(filename)
    return stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write or verify UniRide manifest schemas")
    parser.add_argument("action", choices=("write", "check"))
    args = parser.parse_args(argv)
    if args.action == "write":
        write_schemas()
        return 0
    stale = check_schemas()
    if stale:
        parser.error("stale schema snapshots: " + ", ".join(stale))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
