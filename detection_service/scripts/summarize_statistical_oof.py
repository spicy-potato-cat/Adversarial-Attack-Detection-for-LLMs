"""Post-run descriptive caveats only; never refit models or alter OOF outputs."""

import csv
import json

from detection_service.quality.development_fixture import ROOT, file_hash, json_bytes


def main():
    output = ROOT / "artifacts/statistical_v2/oof"
    destination = output / "ds_v1_diagnostic_caveats_v1.json"
    if destination.exists():
        raise RuntimeError("diagnostic caveats already recorded; refuse overwrite")
    with (output / "ds_v1_recipe_oof_predictions.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    errors = [r for r in rows if r["error_type"] in ("FN", "FP")]
    diagnostics = json.loads((output / "ds_v1_error_characterization.json").read_text(encoding="utf-8"))
    payload = {
        "scope": "POST_OOF_DESCRIPTIVE_INTERPRETATION_ONLY; original pipeline and outputs remain frozen",
        "source_predictions_sha256": file_hash(output / "ds_v1_recipe_oof_predictions.csv"),
        "source_characterization_sha256": file_hash(output / "ds_v1_error_characterization.json"),
        "all_errors_single_window": all(int(r["window_count"]) == 1 for r in errors),
        "error_count": len(errors),
        "all_errors_zero_window_variation": all(float(r["std_window_perplexity"]) == 0 for r in errors),
        "all_negatives_single_window": all(int(r["window_count"]) == 1 for r in rows if r["label"] == "0"),
        "positive_reference_window_std_q25": diagnostics["class_reference_quantiles"]["1"]["std_window_perplexity"]["q25"],
        "negative_reference_window_std_q75": diagnostics["class_reference_quantiles"]["0"]["std_window_perplexity"]["q75"],
        "high_window_variation_pattern": "The preregistered >=negative q75 rule has cutoff zero and matches all FP and TN. It is not evidence of high variance or error enrichment.",
        "weak_window_variation_pattern": "All 60 FN and 105/123 TP have zero variation; mainly a single-window coverage/representation limit, not a proven causal explanation.",
        "window_family_rank_interpretation": "Mechanical support-count rank 1 reflects degeneracy. Adding median-window PPL/variance/max-median ratios alone cannot add information when there is only one window. Later authorized design must address this limit, not count redundant aggregates as improvement.",
        "low_mean_PPL_pattern": "Low-PPL FN fraction is 15/60 versus 31/123 TP: no enrichment. FN median PPL 168.9998 versus TP 165.3204 does not support a dominant low-mean-surprise explanation.",
        "FP_variance_pattern": "High surprisal variation is 45/203 FP versus 193/749 TN: no enrichment. Do not call high variance a dominant FP driver.",
        "short_FP_pattern": "158/203 FP are short, but 734/749 TN are also short. Short-input counts alone do not show higher FP risk; 32-127-token negatives have 45/60 FP, with small/source-confounded support.",
        "supported_FN_associations": "51/60 FN have <32 tokens versus 34/123 TP. Low max surprisal occurs in 40/60 FN versus 6/123 TP. Associations only, not causal mechanisms.",
        "supported_FP_associations": "High max surprisal occurs in 52/203 FP versus 44/749 TN. Aggregate-spike proxy occurs in 50/203 FP versus 18/749 TN; no token-run/position evidence retained.",
        "long_or_tail_claims": "No inputs >=512 tokens, no truncation, and no retained anomaly-position diagnostics. Long-prompt dilution/tail effects cannot be evaluated on this cohort.",
        "max_input_tokens": max(int(r["input_tokens"]) for r in rows),
        "truncated_rows": sum(r["truncated"] == "True" for r in rows),
        "hypothesis_rank_limit": "The original deterministic rank is a coverage count, not validated feature importance, candidate benefit, or promotion evidence. Proposed features are unimplemented.",
        "fits_performed": 0, "predictions_changed": False, "thresholds_changed": False, "new_features": False,
    }
    with destination.open("xb") as handle:
        handle.write(json_bytes(payload))
    print(json.dumps({"status": "PASS", "sha256": file_hash(destination), "error_count": len(errors)}, indent=2))


if __name__ == "__main__":
    main()
