"""MT1-07 (R3 end to end): the strategy's ``no_feasible_split`` reason reaches
the HTTP caller of /optimize and /compare.

The routers replace ``error_message`` with the certificate JSON whenever the
final ``success`` is false. The certificate JSON stays exactly as before; the
strategy's own reason is added as the extra key ``strategy_error``.
"""

import json

import pytest

from models.schemas import CompareRequest
from routers import optimization
from certifier_matrix_support import echo_certifier_matrix  # noqa: F401 - fixture
from test_max_ride_time_boundary import _install_loader, _request, _star_arcs

pytestmark = pytest.mark.usefixtures("echo_certifier_matrix")


def _infeasible_request():
    # DEPOT->x 12 and x->DEPOT 10: every singleton trip costs 22 > 15.
    return _request(2, max_travel_time=15)


def _violation_signature(payload):
    return sorted(v["type"] for v in payload["violations"])


def test_optimize_error_message_carries_strategy_reason_and_certificate(monkeypatch):
    _install_loader(monkeypatch, _star_arcs(2))

    result = optimization.optimize_route(_infeasible_request())

    assert result.success is False
    payload = json.loads(result.error_message)
    assert "no_feasible_split" in result.error_message
    assert "no_feasible_split" in payload["strategy_error"]
    # certificate part unchanged: same JSON as the certificate DTO dump
    expected = result.feasibility_certificate.model_dump(exclude_none=True)
    assert {k: v for k, v in payload.items() if k != "strategy_error"} == expected
    assert _violation_signature(payload)  # the violations are still there


def test_compare_error_message_carries_strategy_reason_and_certificate(monkeypatch):
    _install_loader(monkeypatch, _star_arcs(2))
    base = _infeasible_request().model_dump()
    compare = CompareRequest.model_validate(
        {k: v for k, v in base.items() if k in CompareRequest.model_fields}
        | {"algorithms": ["ga_split"]}
    )

    response = optimization.compare_algorithms(compare)
    result = response.results[0]

    assert result.success is False
    payload = json.loads(result.error_message)
    assert "no_feasible_split" in payload["strategy_error"]
    expected = result.feasibility_certificate.model_dump(exclude_none=True)
    assert {k: v for k, v in payload.items() if k != "strategy_error"} == expected
    assert _violation_signature(payload)


def test_certificate_json_error_message_is_not_duplicated_as_strategy_error():
    cert = optimization.FeasibilityCertificateInfo.model_validate(
        {"is_feasible": False, "violation_count": 0, "violations": [], "certify_error": "x"}
    )
    as_certificate_json = json.dumps(cert.model_dump(exclude_none=True))

    assert json.loads(optimization._failure_json(cert, as_certificate_json)) == cert.model_dump(
        exclude_none=True
    )
    assert json.loads(optimization._failure_json(cert, None)) == cert.model_dump(
        exclude_none=True
    )
    assert json.loads(optimization._failure_json(cert, "boom"))["strategy_error"] == "boom"
