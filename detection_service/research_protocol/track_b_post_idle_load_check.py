"""Future isolated load-only gate. No inference calls or dataset access."""
import argparse,gc,json
from pathlib import Path

def load_only(gate_id):
    if not gate_id or gate_id=='PREPARATION':
        raise ValueError('POST_TRACK_A_IDLE_AUTHORIZATION_REQUIRED')
    # Deliberately lazy: these imports and all model loading are forbidden during preparation.
    from detection_service.research_protocol.adapters import DetectorAdapter,FrozenDetectorContracts
    from detection_service.research_protocol.ds_runtime import accepted_ds_adapter
    contracts=FrozenDetectorContracts()
    results=[]
    for label in ('D_S','D_M-B','D_G'):
        adapter=accepted_ds_adapter() if label=='D_S' else DetectorAdapter(label,contracts)
        adapter.validate_frozen_identity()
        model=adapter._load_live()
        results.append(dict(detector=label,status='EXACT_FROZEN_LOAD_PASS'))
        del model,adapter
        gc.collect()
    return dict(gate_id=gate_id,status='LOAD_ONLY_PASS',results=results,inference_calls=0,
                protected_data_accessed=False,scientific_runtime_equivalence_claim=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--post-idle-authorized-gate-id',required=True)
    args=p.parse_args()
    print(json.dumps(load_only(args.post_idle_authorized_gate_id),indent=2))
