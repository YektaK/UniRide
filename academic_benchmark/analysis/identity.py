"""STUB for the red-test commit of D-01: every entry point raises ``NotImplementedError``."""
from __future__ import annotations


class ComparisonIdentityError(ValueError):
    pass


SEED_PROTOCOL_VERSION = "sha256-seed-v1"


def comparison_cell_key(row, manifest, *, allow_dirty=False):
    raise NotImplementedError


def assert_single_comparison_family(items, *, vary=(), allow_dirty=False):
    raise NotImplementedError


def configuration_hash(row, manifest):
    raise NotImplementedError


def normalise_termination_policy(text):
    raise NotImplementedError
