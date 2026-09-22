from collections.abc import Callable, Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI

from detection_service.app.api.detect import router as detection_router
from detection_service.app.core.settings import Settings
from detection_service.app.detectors.base import BaseDetector
from detection_service.app.detectors.statistical.perplexity_detector import (
    StatisticalPerplexityDetector,
)
from detection_service.app.detectors.semantic.detector import SemanticBaselineDetector


def create_app(
    settings: Settings | None = None,
    detector_factory: Callable[[], BaseDetector | Sequence[BaseDetector]] | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = resolved_settings
        detector_or_detectors = (
            detector_factory()
            if detector_factory
            else _default_detectors(resolved_settings)
        )
        if isinstance(detector_or_detectors, BaseDetector):
            detectors = [detector_or_detectors]
        else:
            detectors = list(detector_or_detectors)
        app.state.detectors = detectors
        app.state.statistical_detector = detectors[0] if detectors else None
        yield

    application = FastAPI(
        title="Adversarial Attack Detection Service",
        version="dev-v0.1",
        lifespan=lifespan,
    )
    application.include_router(detection_router)
    return application


app = create_app()


def _default_detectors(settings: Settings) -> list[BaseDetector]:
    detectors: list[BaseDetector] = [StatisticalPerplexityDetector(settings.statistical)]
    if settings.enable_semantic_detector:
        if settings.semantic.classifier_artifact_dir is None:
            raise RuntimeError("SEMANTIC_MODEL_DIR is required when semantic detector is enabled")
        detectors.append(
            SemanticBaselineDetector.from_artifact(
                settings.semantic.classifier_artifact_dir,
                device=settings.semantic.device,
            )
        )
    return detectors
