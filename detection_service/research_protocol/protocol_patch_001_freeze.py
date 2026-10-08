"""Create additive patch metadata; never overwrite the parent release."""

from detection_service.research_protocol import protocol_patch_001 as patch
from detection_service.research_protocol import r2_dmb_predeclare as p
from detection_service.research_protocol.r1_corpus import publish

CODE = ("detection_service/research_protocol/protocol_patch_001.py",
        "detection_service/research_protocol/protocol_patch_001_freeze.py",
        "detection_service/research_protocol/protocol_patch_001_accept.py",
        "detection_service/tests/test_protocol_patch_001.py",
        "detection_service/tests/.gitattributes", "reviews/.gitattributes")
REVIEW = "reviews/EXP_PROTOCOL_001_PATCH_001_REVIEW.md"


def freeze():
    p.preserved()
    snapshot = p.files.read_json(p.OUT/'r2_dmb_predeclaration_v1.json')['preservation_sha256'].copy()
    for path in (*CODE, REVIEW, str((p.OUT/'r2_dmb_predeclaration_v1.json').relative_to(p.ROOT)).replace('\\','/'),
                 str((p.OUT/'r2_dmb_seed_manifest_v1.json').relative_to(p.ROOT)).replace('\\','/')):
        snapshot[path] = p.digest(path)
    value = dict(patch_id=patch.PATCH_ID,parent_protocol=patch.parent.RELEASE_ID,
        reason="TARGET_METRIC_DOMAIN_CONFLICT",discovery_phase="R2-DMB-001 pre-generation validation",
        authoritative_R2_queries_before_correction=0,scientific_outcomes_before_correction="NONE",
        scope="metric-domain validation semantics only",status="FROZEN_PENDING_REGRESSION_ACCEPTANCE",
        behavioral_effect="Only declared single-target R2 metric prefixes enter target uncertainty; full-stack transfer/common-mode preserved.",
        original_predeclaration_commit="5c74a379b51360a4b84993beba546948344405ea",
        starting_head="adaa4d22794970bd0f1841101f96e2cafba8f80e",
        attack_target_domain="R2: singleton declared target; R3: ALL maps to full frozen stack",
        transfer_evaluation_domain=list(patch.PRIMARY),common_mode_domain=list(patch.PRIMARY),
        official_entrypoint="detection_service.research_protocol.protocol_patch_001.evaluate_official",
        parent_entrypoint_preserved=True,scientific_algorithms_reused_unchanged=True,
        sha256=dict(sorted(snapshot.items())))
    value['manifest_hash'] = patch.parent.digest(value)
    publish(p.ROOT/patch.ARTIFACT,value)
    print(patch.verify_patch(require_committed=False)['patch_id'])


if __name__ == '__main__':
    freeze()
