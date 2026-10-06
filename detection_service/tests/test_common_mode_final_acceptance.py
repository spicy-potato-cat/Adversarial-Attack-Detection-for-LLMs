import pytest

from detection_service.scripts.common_mode_final_acceptance import classifications, long_agreement


def test_long_agreement_counts_existing_patterns_without_fusion():
    subgroup = {"count": 5, "patterns": [
        {"pattern": "D_S_v1=0|D_S_B2_LR=1|D_M-B_v1=1|D_G_v1=1", "count": 2},
        {"pattern": "D_S_v1=1|D_S_B2_LR=1|D_M-B_v1=0|D_G_v1=0", "count": 1},
        {"pattern": "D_S_v1=0|D_S_B2_LR=0|D_M-B_v1=1|D_G_v1=1", "count": 2},
    ]}
    assert long_agreement(subgroup) == {"all_three_fp": 2, "ds_only_fp": 1,
        "ds_dm_overlap": 2, "ds_dg_overlap": 2, "dm_dg_overlap": 4}
    subgroup["count"] = 6
    with pytest.raises(ValueError, match="accounting"):
        long_agreement(subgroup)


@pytest.mark.parametrize("shared_delta,unique_delta,catches,expected", [
    (-1, 1, 2, ["REDUCED_SHARED_FAILURE", "PRESERVED_COMPLEMENTARITY"]),
    (0, 0, 1, ["PRESERVED_COMPLEMENTARITY"]),
    (1, -1, 0, ["REDUCED_COMPLEMENTARITY"]),
    (0, 0, 0, ["NO_CLEAR_CHANGE"]),
])
def test_descriptive_classification_does_not_imply_causal_diversity(shared_delta, unique_delta, catches, expected):
    budget = {"effect": [
        {"metric": "all_detector_fn_count", "other": "primary_stack", "delta": shared_delta},
        {"metric": "unique_catch_count", "other": "primary_stack", "delta": unique_delta, "candidate": catches},
    ]}
    assert classifications(budget) == expected
