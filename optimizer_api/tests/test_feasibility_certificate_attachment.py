import json

import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from models import schemas
from routers import optimization


def _certificate_model():
    model = getattr(schemas, "FeasibilityCertificateInfo", None)
    assert model is not None, "typed certificate model is missing"
    return model


def test_certificate_model_enforces_invariants():
    model = _certificate_model()
    valid = model(is_feasible=True, violation_count=0, violations=[])
    assert valid.is_feasible is True

    with pytest.raises(ValidationError):
        model(is_feasible=False, violation_count=2, violations=[])
    with pytest.raises(ValidationError):
        model(
            is_feasible=True,
            violation_count=1,
            violations=[{"type": "x", "severity": "error", "details": "x"}],
        )
    with pytest.raises(ValidationError):
        model(
            is_feasible=True,
            violation_count=0,
            violations=[],
            certify_error="must fail closed",
        )


def test_certificate_field_is_optional_and_typed_in_openapi():
    assert "feasibility_certificate" in schemas.OptimizationResponse.model_fields
    assert "feasibility_certificate" in schemas.AlgorithmResult.model_fields

    app = FastAPI()
    app.include_router(optimization.router)
    components = app.openapi()["components"]["schemas"]
    for response_name in ("OptimizationResponse", "AlgorithmResult"):
        prop = components[response_name]["properties"]["feasibility_certificate"]
        assert "FeasibilityCertificateInfo" in json.dumps(prop)
