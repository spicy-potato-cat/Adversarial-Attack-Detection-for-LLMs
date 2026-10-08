"""D_S calibrated-score objective, declared before any target query."""

from copy import deepcopy
from detection_service.research_protocol import r2_dmb_design as accepted

SOURCE_HEAD='99b012e5b72fbae9273fa73ccc8d84d579a69c83'
PROTOCOL_HEAD=accepted.SOURCE_HEAD
TARGET='D_S'
DETECTOR_ID='ds_v2'
THRESHOLD=0.5585373573968287
THRESHOLD_ID='ds_v2_op3_cal_v1'
OPERATORS=accepted.OPERATORS
PREFIXES=accepted.PREFIXES
SUFFIXES=accepted.SUFFIXES
CONFUSABLES=accepted.CONFUSABLES
DESIGN=deepcopy(accepted.DESIGN)
DESIGN.update(experiment='R2-DS-001',target_detector=TARGET,detector_id=DETECTOR_ID,
    expected_parents='ALL_R1_ATTACKS_CAUGHT_BY_FROZEN_DS',target_score='calibrated_score',
    target_threshold=THRESHOLD,target_threshold_id=THRESHOLD_ID,
    coverage='Complete word spans within the frozen reference-LM first 4096 token prefix; exact fast-tokenizer offsets, no specials.',
    saliency_probe='Single-span ALT_CASE reversible edit; no deletion or x-occlusion. Cached no-ops are allowed.',
    saliency='baseline calibrated D_S score minus reversible probe calibrated D_S score; descending then original offset; top 8.',
    objective_justification='D_S uses token-distribution features over sliding reference-LM windows; reversible case probes measure score changes directly, not D_M-B attention/window saliency.',
    score_replay_tolerance=1e-12,generation_query_counts=dict(D_M_B=0,D_G=0,ensemble=0),
    protocol_patch='exp_protocol_001_patch_001',protocol_patch_commit='7e16bcb828c437d5665b0ebe855b8cb021e0dee2')

# Generic operator priorities are retained; every score comparison is calibrated.
for key in ('greedy_success_tie','greedy_improvement_tie','greedy_accept',
            'padding_success_tie','global_success_tie','global_failure'):
    value=DESIGN[key]
    DESIGN[key]=[v.replace('raw score','calibrated score') for v in value] if isinstance(value,list) else value.replace('raw score','calibrated score').replace('raw-score','calibrated-score')
