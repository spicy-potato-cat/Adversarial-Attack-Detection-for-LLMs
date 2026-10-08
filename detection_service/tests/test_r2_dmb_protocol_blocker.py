"""Diagnostic reproduction of the frozen official R2 target-domain conflict.

This is not an experiment or an acceptance of the incompatible official path.
No model inference, project payload or protocol mutation is involved.
"""

import inspect

import pytest

from detection_service.research_protocol import protocol_lock
from detection_service.research_protocol.adapters import FrozenDetectorContracts
from detection_service.research_protocol.core_metrics_contract import synthetic_r2,align_fixture
from detection_service.research_protocol.core_metrics import evaluate_core
from detection_service.research_protocol.metric_catalog import metric_catalog
from detection_service.research_protocol.regime import RegimeContractError
from detection_service.research_protocol.uncertainty import BootstrapConfig,validate_metric_domain


def test_frozen_r2_official_target_domain_blocker_reproduces():
    contracts=FrozenDetectorContracts()
    table=align_fixture(synthetic_r2(contracts)[0],contracts)
    names=metric_catalog(evaluate_core(table))
    target_names=tuple(k for k in names if k.startswith(('target/','transfer/')))
    source=inspect.getsource(protocol_lock.evaluate_official)
    assert 'target_names = tuple(k for k in names if k.startswith(("target/","transfer/")))' in source
    config=BootstrapConfig(unit='LINEAGE_CLUSTERED',domain='VALID_TARGET_ATTEMPTS',target_detector='D_M-B')
    assert 'target/ds_v2/evasion' in target_names and 'target/dg_v1/evasion' in target_names
    with pytest.raises(RegimeContractError,match='^TARGET_METRIC_DOMAIN_CONFLICT$'):
        validate_metric_domain(target_names,config,table)
    selected=tuple(k for k in target_names if k.startswith(('target/dm_b_v1/','transfer/dm_b_v1/')))
    # The existing validator accepts a single-target request. The official
    # orchestrator does not make that request; it remains intentionally untouched.
    validate_metric_domain(selected,config,table)
