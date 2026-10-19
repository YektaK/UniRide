"""The ``archive`` tree is quarantined historical material, not a Python package.

Importing it, or anything below it, always fails. See QUARANTINE.md in the
archived subtree (for example archive/academic_benchmark/yaem2026_legacy/QUARANTINE.md)
and archive/README.md for the rules. Audit M17, Gate C item C-01.
"""

raise ImportError(
    "archive/ is quarantined historical material and must not be imported; "
    "see QUARANTINE.md in the archived subtree (archive/README.md for the rules)."
)
