"""Predeclared CALIBRATION benign-only selector; not an evaluation-time tuner."""

from fractions import Fraction
import math
from typing import Annotated, Literal

from pydantic import Field, model_validator

from detection_service.research_protocol.prediction import Binary, Count, Probability
from detection_service.research_protocol.regime import FrozenMetadata, SampleID, require

ALPHA = Fraction(3, 100)
ALGORITHM = "benign_empirical_fpr_budget_v1"
TIE_POLICY = "binary64_nextafter_boundary_toward_positive_infinity"


class SelectionScore(FrozenMetadata):
    sample_id: SampleID
    truth_label: Binary
    partition: Literal["CALIBRATION"]
    score: Probability


class SelectedThreshold(FrozenMetadata):
    algorithm_id: Literal["benign_empirical_fpr_budget_v1"] = ALGORITHM
    benign_count: Annotated[Count, Field(ge=1)]
    max_allowed_fp: Count
    boundary_score: Probability
    boundary_ties: Annotated[Count, Field(ge=1)]
    threshold: Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
    attained_fp: Count
    attained_fpr: Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)]

    @model_validator(mode="after")
    def relations(self):
        require(self.max_allowed_fp == (3 * self.benign_count) // 100, "K_MUST_USE_EXACT_FLOOR")
        require(self.threshold == math.nextafter(self.boundary_score, math.inf), "THRESHOLD_NOT_BOUNDARY_SUCCESSOR")
        require(self.attained_fp <= self.max_allowed_fp and self.attained_fpr == self.attained_fp / self.benign_count,
                "BENIGN_FPR_BUDGET_VIOLATION")
        return self


def select_threshold(rows):
    """Validate every row, then use only benign scores with fixed alpha=3/100."""
    values = tuple(SelectionScore.model_validate(r) for r in rows)
    require(len({r.sample_id for r in values}) == len(values), "DUPLICATE_SELECTION_SAMPLE")
    benign = sorted((r.score for r in values if r.truth_label == 0), reverse=True)
    require(bool(benign), "ZERO_BENIGN_CALIBRATION_SCORES")
    k = (ALPHA.numerator * len(benign)) // ALPHA.denominator
    require(k < len(benign), "INVALID_FPR_POLICY_CONFIGURATION")
    boundary = benign[k]
    threshold = math.nextafter(boundary, math.inf)
    require(math.isfinite(threshold) and threshold > boundary, "UNREPRESENTABLE_THRESHOLD")
    fp = sum(score >= threshold for score in benign)
    return SelectedThreshold(benign_count=len(benign), max_allowed_fp=k, boundary_score=boundary,
        boundary_ties=benign.count(boundary), threshold=threshold, attained_fp=fp, attained_fpr=fp / len(benign))
