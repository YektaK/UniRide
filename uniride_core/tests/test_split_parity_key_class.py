"""MT1-05 key-class test: only ``|tw=on|`` golden entries may change.

``golden/split_parity_pre_mt1_05.json`` is the frozen copy of ``split_parity.json`` as
it stood before MT1-05 (WIP ``4ddd2d36``). The owner narrowed H01 (OQ-MT1-13 a): the
split decoder's time-window branch changes, so the ``|tw=on|`` entries are
regenerated; the ``|tw=off|`` entries (capacity-only path, ``use_time_windows=false``)
must stay exactly as they were.
"""

from __future__ import annotations

import json
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "golden"


def _load(name: str) -> dict:
    return json.loads((GOLDEN_DIR / name).read_text(encoding="utf-8"))


def test_same_key_set_before_and_after():
    assert set(_load("split_parity_pre_mt1_05.json")) == set(_load("split_parity.json"))


def test_every_changed_key_is_a_tw_on_key():
    old, new = _load("split_parity_pre_mt1_05.json"), _load("split_parity.json")
    changed = sorted(k for k in old if old[k] != new[k])
    assert all("|tw=on|" in k for k in changed), [k for k in changed if "|tw=on|" not in k]


def test_no_tw_off_key_changed_and_tw_on_keys_did_change():
    old, new = _load("split_parity_pre_mt1_05.json"), _load("split_parity.json")
    off = [k for k in old if "|tw=off|" in k]
    assert off and all(old[k] == new[k] for k in off)
    # non-vacuous: the regeneration really touched the time-window entries
    assert any(old[k] != new[k] for k in old if "|tw=on|" in k)
