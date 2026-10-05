"""Read-only post-run verification; leave frozen STAT-004 run code untouched."""

from detection_service.analysis.statistical_oof import digest_ids, require
from detection_service.scripts import statistical_feature_ablation_resume as resume


def check():
    # The historical checker references this helper through the wrong module.
    # Bind the existing canonical implementation only while verifying results.
    previous = getattr(resume.baseline, "digest_ids", None)
    require(previous is None or previous is digest_ids, "conflicting membership digest implementation")
    resume.baseline.digest_ids = digest_ids
    try:
        resume.check()
    finally:
        if previous is None:
            del resume.baseline.digest_ids
        else:
            resume.baseline.digest_ids = previous


if __name__ == "__main__":
    check()
