from uniride_core.algorithms import sota_common as core_sota_common


def test_core_sota_common_exports_expected_infrastructure():
    expected = {
        "MultiStartInitializer",
        "MultiLayerLS",
        "PenaltyManager",
        "SimulatedAnnealing",
        "LateAcceptanceHC",
        "RecordToRecordTravel",
        "RandomRemoval",
        "WorstRemoval",
        "ShawRemoval",
        "RelatedRemoval",
        "GreedyInsertion",
        "Regret2Insertion",
        "Regret3Insertion",
        "DiversityController",
    }

    assert expected.issubset(set(core_sota_common.__all__))
    for name in expected:
        assert getattr(core_sota_common, name) is not None
