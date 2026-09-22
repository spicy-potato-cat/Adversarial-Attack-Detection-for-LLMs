from abc import ABC, abstractmethod

from detection_service.app.contracts.detection_request import DetectionRequest
from detection_service.app.contracts.detector_result import DetectorResult


class BaseDetector(ABC):
    """Common interface for independently versioned detector channels."""

    @abstractmethod
    def detect(self, request: DetectionRequest) -> DetectorResult:
        raise NotImplementedError

