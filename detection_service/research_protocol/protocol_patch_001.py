"""Prospective metric-domain correction; parent release remains immutable."""

from detection_service.research_protocol import protocol_lock as parent
from detection_service.research_protocol.alignment import PRIMARY
from detection_service.research_protocol.regime import FrozenMetadata, require

PATCH_ID = "exp_protocol_001_patch_001"
ARTIFACT = "artifacts/research_protocol/protocol_patches/exp_protocol_001_patch_001.json"


class MetricDomains(FrozenMetadata):
    attack_target_domain: tuple[str, ...]
    attack_target_uncertainty_domain: tuple[str, ...]
    transfer_evaluation_domain: tuple[str, ...] = PRIMARY
    common_mode_domain: tuple[str, ...] = PRIMARY


def validate_domains(manifest, domains=None):
    if manifest.threat_regime == "R2_SINGLE_DETECTOR_TARGETED":
        targets = {s.target_detector for s in manifest.samples}
        require(len(targets) == 1 and targets <= set(PRIMARY), "SINGLE_DECLARED_R2_TARGET_REQUIRED")
        expected = (next(iter(targets)),)
    elif manifest.threat_regime == "R3_ENSEMBLE_TARGETED":
        require(all(s.target_detector == "ALL" for s in manifest.samples), "R3_ALL_TARGET_REQUIRED")
        expected = PRIMARY
    else:
        expected = ()
    value = MetricDomains(attack_target_domain=expected, attack_target_uncertainty_domain=expected) if domains is None else MetricDomains.model_validate(domains)
    require(value.attack_target_domain == expected, "ATTACK_TARGET_DOMAIN_CONFLICT")
    require(value.attack_target_uncertainty_domain == expected, "TARGET_UNCERTAINTY_DOMAIN_CONFLICT")
    require(value.transfer_evaluation_domain == PRIMARY, "TRANSFER_STACK_DOMAIN_CONFLICT")
    require(value.common_mode_domain == PRIMARY, "COMMON_MODE_STACK_DOMAIN_CONFLICT")
    return value


def target_metric_names(names, target, detector_ids):
    require(target in PRIMARY, "SINGLE_DECLARED_R2_TARGET_REQUIRED")
    detector_id = detector_ids[PRIMARY.index(target)]
    return tuple(k for k in names if k.startswith(("target/" + detector_id + "/", "transfer/" + detector_id + "/")))


def verify_patch(*, require_committed=True):
    value = parent.files.read_json(parent.files.ROOT / ARTIFACT)
    require(value["patch_id"] == PATCH_ID and value["parent_protocol"] == parent.RELEASE_ID, "PATCH_IDENTITY_CONFLICT")
    require(value["manifest_hash"] == parent.digest({k: v for k, v in value.items() if k != "manifest_hash"}), "PATCH_SELF_HASH_CONFLICT")
    for path, expected in value["sha256"].items():
        require(parent.files.sha(parent.files.ROOT / path) == expected, "PATCH_PRESERVATION_FAILURE:" + path)
    if require_committed:
        commit = patch_commit()
        require((parent.files.ROOT / ARTIFACT).read_bytes() == parent.git("show", commit + ":" + ARTIFACT), "COMMITTED_PATCH_BYTES_REQUIRED:" + ARTIFACT)
        for path in value["patch_code_paths"]:
            require((parent.files.ROOT / path).read_bytes() == parent.git("show", commit + ":" + path), "COMMITTED_PATCH_BYTES_REQUIRED:" + path)
    return value


def patch_commit():
    commits = parent.git("log", "-1", "--format=%H", "--", ARTIFACT).decode().splitlines()
    require(len(commits) == 1, "COMMITTED_PATCH_REQUIRED")
    return commits[0]


def verify_experiment_preflight(request):
    request = parent.ExperimentRequest.model_validate(request.model_dump() if isinstance(request, parent.ExperimentRequest) else request)
    verify_patch()
    receipt = parent.verify_experiment_preflight(request)
    domains = validate_domains(request.manifest)
    return dict(receipt, protocol_patch_id=PATCH_ID, metric_domains=domains.model_dump(mode="json"))


def evaluate_official(request, predictions):
    request = parent.ExperimentRequest.model_validate(request.model_dump() if isinstance(request, parent.ExperimentRequest) else request)
    require(request.purpose == "OFFICIAL_EVALUATION", "TEST_FIXTURE_CANNOT_PUBLISH_REAL_RESULT")
    verify_experiment_preflight(request)
    policy = parent.operational.verified_policy()
    projected = tuple(parent.apply_operating_policy(p, policy) for p in predictions)
    table = parent.align_evaluation(request.manifest, projected, binding=parent.bind_predictions(request.manifest),
        decision_view="OPERATIONAL", contracts=policy.contracts, operating_policy=policy)
    core = parent.evaluate_core(table)
    names = parent.metric_catalog(core)
    attack = tuple(k for k in names if k.startswith(("pair/", "pattern/", "recovery/", "all_three/")) or k.endswith("/fnr"))
    benign = tuple(k for k in names if k.endswith("/fpr"))
    intervals = [parent.bootstrap_metrics(table, attack, parent.BootstrapConfig(unit=request.bootstrap_unit, domain="ATTACK_ONLY"))]
    if core.individual.benign_count:
        intervals.append(parent.bootstrap_metrics(table, benign, parent.BootstrapConfig(unit=request.bootstrap_unit, domain="BENIGN_ONLY")))
    if request.manifest.threat_regime == "R2_SINGLE_DETECTOR_TARGETED":
        target = request.manifest.samples[0].target_detector
        selected = target_metric_names(names, target, table.provenance.primary_detector_ids)
        intervals.append(parent.bootstrap_metrics(table, selected, parent.BootstrapConfig(unit="LINEAGE_CLUSTERED", domain="VALID_TARGET_ATTEMPTS", target_detector=target)))
    return parent.result_bundle(table, request.manifest, "OPERATIONAL_FIXED_V1", uncertainty=tuple(intervals))
