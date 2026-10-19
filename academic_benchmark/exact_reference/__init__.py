"""Exact reference protocol (design docs/designs/EXACT_SOLVER_AMPL_DESIGN.md sections 2, 4, 5; DECISION_LOG A04, E09, E12).

Modules (nothing is imported here on purpose: ``contracts.export_schemas`` imports ``rows``, and importing the package must
stay light):

* ``protocol`` (WP-E2, WP-E7): the single definition of ``exact_reference_v1``: status labels, stop reasons, manifest
  validators for wave campaigns, ``union_day_v1`` and the TSP/ATSP reference, ``assert_not_pooled``.
* ``inputs`` (WP-E8 companion task): manifest-governed, sha256-checked readers of the 16 TSP instances, ft53 and the published
  optimal tours; archive locations and manifest paths that leave their folder are refused.
* ``rows`` (WP-E8): ``ExactReferenceRowV1``, the typed row (no ``algorithm_id``, ``evaluation_budget`` or ``gap_*`` field).
* ``reader`` (WP-E8): ``load_exact_reference``, ``discover_exact_references`` (``results_index.json``, no glob),
  ``validate_hamiltonian_rows`` and ``cross_check_published_tours`` (the independent validator in
  ``academic_benchmark.validation.hamiltonian_cycle``).

Exact rows are references: they are never pooled, ranked, averaged or tested with fixed-budget or native-termination rows
(``academic_benchmark.protocol_registry``). Gap columns belong to the analysis layer (Package D), not to this package.
"""
