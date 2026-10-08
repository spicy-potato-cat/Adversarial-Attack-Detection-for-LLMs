"""Explicit Commander-approved branch-reference compatibility, not a score change."""

from contextlib import contextmanager
from unittest.mock import patch

from detection_service.research_protocol import r2_ds_predeclare as p
from detection_service.research_protocol import ds_numerical_diagnosis as numerical

RECEIPT = p.OUT / 'r2_ds_track_b_reference_update_v1.json'
ORIGINAL = '0cd2d506380cbb3ec513207e4fa66ad422d2b3f2'
APPROVED = '6c7173b70a10d1506d92360b421eaceb5e56405e'


def verified():
    receipt = p.files.read_json(RECEIPT)
    p.require(receipt['original_task_reference'] == ORIGINAL and
              receipt['approved_untouched_reference'] == APPROVED and
              receipt['commander_authorization'] == 'Accept the updated Track-B reference; finish Track A',
              'TRACK_B_REFERENCE_NOT_AUTHORIZED')
    p.require(p.git('rev-parse', 'prep/r3-verifier-001').decode().strip() == APPROVED,
              'TRACK_B_CHANGED_AFTER_APPROVAL')
    return receipt


@contextmanager
def approved_reference():
    verified()
    with patch.object(numerical, 'TRACK_B', APPROVED):
        yield


def pytest_configure(config):
    """Activate only when explicitly passed as a pytest -p plugin."""
    verified()
    config._r2_ds_original_track_b = numerical.TRACK_B
    numerical.TRACK_B = APPROVED


def pytest_unconfigure(config):
    if hasattr(config, '_r2_ds_original_track_b'):
        numerical.TRACK_B = config._r2_ds_original_track_b
