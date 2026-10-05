"""Opt-in frozen B2 statistical candidate; ds_v1 service defaults are unchanged."""

from .detector import B2StatisticalDetector
from .model import B2Model, load_calibration

__all__ = ["B2StatisticalDetector", "B2Model", "load_calibration"]
