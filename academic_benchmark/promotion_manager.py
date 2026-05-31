"""CLI workflow for promoting academic benchmark params to core configs."""

from __future__ import annotations

import argparse
import json
from typing import Dict, List, Optional, Sequence

from academic_benchmark.promoted_configs import (
    DEFAULT_PROMOTED_CONFIG_PATH,
    build_promoted_configs,
    write_promoted_configs,
)
from academic_benchmark.tsplib_manager import DB_PATH


def validate_promoted_document(
    document: Dict[str, object],
    *,
    min_configs: int = 1,
    require_params: bool = True,
) -> List[str]:
    """Return validation errors for a promoted-config document."""
    errors: List[str] = []
    configs = document.get("configs")
    if not isinstance(configs, list):
        return ["configs must be a list"]
    if len(configs) < min_configs:
        errors.append(f"expected at least {min_configs} promoted config(s), found {len(configs)}")

    for idx, config in enumerate(configs):
        if not isinstance(config, dict):
            errors.append(f"configs[{idx}] must be an object")
            continue
        for field in ("algorithm", "problem_type", "matrix_kind", "params"):
            if field not in config:
                errors.append(f"configs[{idx}] missing {field}")
        params = config.get("params")
        if require_params and not params:
            errors.append(f"configs[{idx}] has empty params")
        if params is not None and not isinstance(params, dict):
            errors.append(f"configs[{idx}].params must be an object")
    return errors


def promote_configs(
    *,
    db_path: str = DB_PATH,
    output_path: str = DEFAULT_PROMOTED_CONFIG_PATH,
    limit: int = 5000,
    min_configs: int = 1,
    require_params: bool = True,
    dry_run: bool = False,
) -> Dict[str, object]:
    """Build, validate, and optionally write promoted configs."""
    document = build_promoted_configs(db_path=db_path, limit=limit)
    errors = validate_promoted_document(
        document,
        min_configs=min_configs,
        require_params=require_params,
    )
    if errors:
        raise ValueError("; ".join(errors))
    if not dry_run:
        document = write_promoted_configs(
            db_path=db_path,
            output_path=output_path,
            limit=limit,
            generated_at=str(document["generated_at"]),
        )
    return document


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Promote academic benchmark params to core configs.")
    parser.add_argument("--db-path", default=DB_PATH, help="Academic SQLite database path.")
    parser.add_argument(
        "--output",
        default=DEFAULT_PROMOTED_CONFIG_PATH,
        help="Output promoted_configs.json path.",
    )
    parser.add_argument("--limit", type=int, default=5000, help="Maximum rows to inspect from each source table.")
    parser.add_argument("--min-configs", type=int, default=1, help="Minimum promoted configs required.")
    parser.add_argument(
        "--allow-empty-params",
        action="store_true",
        help="Allow configs without params. Useful for deterministic algorithms.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and print without writing.")
    args = parser.parse_args(argv)

    try:
        document = promote_configs(
            db_path=args.db_path,
            output_path=args.output,
            limit=args.limit,
            min_configs=args.min_configs,
            require_params=not args.allow_empty_params,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        print(f"[PROMOTE] validation failed: {exc}")
        return 2

    print(json.dumps({
        "output": None if args.dry_run else args.output,
        "configs": len(document.get("configs", [])),
        "dry_run": args.dry_run,
    }, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main", "promote_configs", "validate_promoted_document"]
