"""Stable scalar names shared by uncertainty and comparisons; no new formulas."""

def metric_catalog(bundle):
    values = {}
    for detector in bundle.individual.detectors:
        for name in ("accuracy", "precision", "recall", "specificity", "f1", "fpr", "fnr", "npv"):
            values[f"individual/{detector.detector_id}/{name}"] = getattr(detector, name).value
    for pair in bundle.common_mode.pairs:
        prefix = f"pair/{pair.left_detector}/{pair.right_detector}"
        for name in ("jfn", "independence_reference", "ejf", "fn_jaccard"):
            values[prefix + "/" + name] = getattr(pair, name).value
    values["all_three/jfn"] = bundle.common_mode.all_three_jfn.value
    for pattern in bundle.failure_patterns.patterns:
        values["pattern/" + pattern.pattern_id] = pattern.attack_rate.value
    for detector in bundle.recovery.detectors:
        for name in ("unique_catch_rate", "conditional_recovery"):
            values[f"recovery/{detector.detector_id}/{name}"] = getattr(detector, name).value
    if bundle.evasion_transfer is not None:
        for target in bundle.evasion_transfer.targets:
            values[f"target/{target.target_detector}/evasion"] = target.target_evasion_rate.value
            for transfer in target.transfers:
                values[f"transfer/{target.target_detector}/{transfer.transfer_detector}/etr"] = transfer.etr.value
    return dict(sorted(values.items()))
