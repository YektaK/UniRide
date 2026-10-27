"""MT6F-03 (audit L3-h): the never-read request field ``use_sota_engine`` is gone.

``OptimizationRequest`` sets no ``extra="forbid"``, so an old client that still
sends the key keeps validating; the value is simply ignored. The core decoder
option ``CVRPTWDecoder(use_sota_engine=...)`` is a different, live parameter.
"""

from models.schemas import LocationNode, OptimizationRequest, StudentNode


def _request_payload(**extra):
    return {
        "algorithm": "ga_split",
        "students": [
            StudentNode(
                id="s1",
                location_code="L1",
                disability_type="Sw",
                coordinates={"lat": 0.0, "lng": 0.0},
                pickup_time="08:30",
                dropoff_time="17:00",
            )
        ],
        "depot": LocationNode(id="DEPOT", lat=0.0, lng=0.0),
        **extra,
    }


def test_use_sota_engine_is_not_a_request_field():
    assert "use_sota_engine" not in OptimizationRequest.model_fields


def test_old_client_sending_use_sota_engine_still_validates():
    request = OptimizationRequest(**_request_payload(use_sota_engine=True))
    assert request.algorithm == "ga_split"


def test_sent_use_sota_engine_value_is_ignored_not_stored():
    request = OptimizationRequest(**_request_payload(use_sota_engine=True))
    assert not hasattr(request, "use_sota_engine")
    assert "use_sota_engine" not in request.model_dump()
