from fastapi import APIRouter, HTTPException, Request, status

from detection_service.app.contracts.detection_request import DetectionRequest
from detection_service.app.contracts.detector_result import DetectionResponse
from detection_service.app.detectors.semantic.detector import SemanticDetectorError
from detection_service.app.detectors.statistical.perplexity_engine import PerplexityEngineError


router = APIRouter(prefix="/v1/detect", tags=["detection"])


@router.post("/input", response_model=DetectionResponse)
def detect_input(payload: DetectionRequest, request: Request) -> DetectionResponse:
    results = []
    for detector in request.app.state.detectors:
        try:
            results.append(detector.detect(payload))
        except PerplexityEngineError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "STATISTICAL_DETECTOR_UNAVAILABLE", "message": str(exc)},
            ) from None
        except SemanticDetectorError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "SEMANTIC_DETECTOR_UNAVAILABLE", "message": str(exc)},
            ) from None
    return DetectionResponse(
        request_id=payload.request_id,
        pipeline_version=request.app.state.settings.pipeline_version,
        detectors=results,
    )
