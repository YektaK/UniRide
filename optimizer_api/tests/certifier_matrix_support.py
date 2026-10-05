"""Test support for suites that exercise the *non-matrix* certificate checks.

Since audit C2 the production certificate re-costs every step on the
authoritative ``time_matrix``. Many older boundary tests build stub responses
with arbitrary step durations and assert capacity, coverage, chain or count
violations; the matrix is not what they test. For them the "matrix" is the
set of arcs the stub response reports (the pre-C2 behaviour), supplied through
the same injectable ``arc_lookup`` the production boundary uses.

This must never be used where matrix fidelity is under test: that is covered by
``test_certifier_authoritative_matrix.py``.
"""

from __future__ import annotations

import pytest

from uniride_core.adapters.demand_builder import student_occurrence_keys
from verification import response_certifier
from verification.response_certifier import certify_optimization_response


def echo_arc_lookup(request, response):
    """Lookup over physical codes whose arcs are the response's own steps."""
    keys = student_occurrence_keys(request.students)
    code_of = {request.depot.id: request.depot.id}
    for student, key in zip(request.students, keys):
        code_of[key] = student.location_code
    arcs = {}
    for route in getattr(response, "routes", None) or []:
        for step in getattr(route, "route_details", None) or []:
            origin = code_of.get(str(step.location1))
            destination = code_of.get(str(step.location2))
            if origin is None or destination is None:
                continue
            arcs.setdefault((origin, destination), float(step.duration))

    def lookup(origin, destination):
        if origin == destination:
            return 0.0
        return arcs[(origin, destination)]

    return lookup


def certify_on_reported(request, response):
    """Certify with the response's own arcs standing in for the matrix."""
    return certify_optimization_response(
        request, response, arc_lookup=echo_arc_lookup(request, response)
    )


def certify_on_loader_matrix(monkeypatch, loader):
    """Make the router's certificate re-cost on the arcs of ``loader``.

    For tests that run real strategies against an injected fake loader: the
    certificate then judges the response on the very matrix the solve used.
    """
    from routers import optimization
    from verification.authoritative_arcs import arc_lookup_from_submatrix

    def certify(request, response, arc_lookup=None):
        return response_certifier.certify_optimization_response(
            request, response, arc_lookup=arc_lookup_from_submatrix(loader, request)
        )

    monkeypatch.setattr(optimization, "certify_optimization_response", certify)


def _skip_arc_capture(monkeypatch):
    """Stub strategies run without a stored matrix: skip the pre-solve capture.

    The router captures the authoritative arcs BEFORE solving (a missing matrix
    is a 503 without a solve). Suites that exercise the certificate with stub
    strategies and a stubbed/echoed certificate give the router a dummy lookup.
    """
    from routers import optimization

    monkeypatch.setattr(
        optimization,
        "authoritative_arc_lookup",
        lambda *args, **kwargs: (lambda origin, destination: 0.0),
    )


@pytest.fixture
def stub_arc_capture(monkeypatch):
    _skip_arc_capture(monkeypatch)


@pytest.fixture
def echo_certifier_matrix(monkeypatch):
    """Make the router's certificate use the stub response's own arcs."""
    _skip_arc_capture(monkeypatch)
    from routers import optimization

    def certify(request, response, arc_lookup=None):
        return response_certifier.certify_optimization_response(
            request, response, arc_lookup=echo_arc_lookup(request, response)
        )

    monkeypatch.setattr(optimization, "certify_optimization_response", certify)
