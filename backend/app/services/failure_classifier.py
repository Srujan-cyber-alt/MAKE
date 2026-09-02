"""
Failure Classifier for MAKE AI Video Phase 19.

Extends Phase 16 Failure Intelligence with generation-quality-specific failure types.
"""

from typing import Optional, Dict, List, Any
from app.services.failure_intelligence import FailureIntelligence, FailureType, FailurePolicy
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class GenerationFailureType(str, Enum):
    PROVIDER_FAILURE = "provider_failure"
    NETWORK_FAILURE = "network_failure"
    INVALID_OUTPUT = "invalid_output"
    TECHNICAL_FAILURE = "technical_failure"
    PROMPT_FAILURE = "prompt_failure"
    REFERENCE_FAILURE = "reference_failure"
    IDENTITY_FAILURE = "identity_failure"
    PRODUCT_FAILURE = "product_failure"
    TEMPORAL_FAILURE = "temporal_failure"
    MOTION_FAILURE = "motion_failure"
    CAMERA_FAILURE = "camera_failure"
    COMPOSITION_FAILURE = "composition_failure"
    QUALITY_FAILURE = "quality_failure"
    CONTINUITY_FAILURE = "continuity_failure"


class FailureClassifier:
    def __init__(self):
        self._base = FailureIntelligence()
        self._generation_policies = {
            GenerationFailureType.IDENTITY_FAILURE: FailurePolicy(
                failure_type=GenerationFailureType.IDENTITY_FAILURE,
                retryable=True,
                fallback_allowed=True,
                user_action_required=False,
                max_retries=2,
                description="Identity consistency failed. Retry with stronger references.",
            ),
            GenerationFailureType.PRODUCT_FAILURE: FailurePolicy(
                failure_type=GenerationFailureType.PRODUCT_FAILURE,
                retryable=True,
                fallback_allowed=True,
                user_action_required=False,
                max_retries=2,
                description="Product consistency failed. Retry with product references.",
            ),
            GenerationFailureType.TEMPORAL_FAILURE: FailurePolicy(
                failure_type=GenerationFailureType.TEMPORAL_FAILURE,
                retryable=True,
                fallback_allowed=True,
                user_action_required=False,
                max_retries=2,
                description="Temporal consistency failed. Retry or apply smoothing.",
            ),
            GenerationFailureType.QUALITY_FAILURE: FailurePolicy(
                failure_type=GenerationFailureType.QUALITY_FAILURE,
                retryable=True,
                fallback_allowed=True,
                user_action_required=False,
                max_retries=1,
                description="Quality below threshold. Try alternate model.",
            ),
        }

    def classify(self, error: Optional[Exception] = None, analysis: Optional[Dict[str, Any]] = None) -> GenerationFailureType:
        analysis = analysis or {}
        if analysis.get("identity_drift") or analysis.get("face_drift"):
            return GenerationFailureType.IDENTITY_FAILURE
        if analysis.get("product_drift"):
            return GenerationFailureType.PRODUCT_FAILURE
        if analysis.get("temporal_flicker") or analysis.get("camera_instability"):
            return GenerationFailureType.TEMPORAL_FAILURE
        if analysis.get("motion_artifacts"):
            return GenerationFailureType.MOTION_FAILURE
        if analysis.get("lighting_jump"):
            return GenerationFailureType.CAMERA_FAILURE
        if analysis.get("overall_score", 1.0) < 0.4:
            return GenerationFailureType.QUALITY_FAILURE
        if error:
            return self._base.classify_error(error, analysis)
        return GenerationFailureType.QUALITY_FAILURE

    def get_policy(self, failure_type: GenerationFailureType) -> FailurePolicy:
        return self._generation_policies.get(failure_type, self._base.get_policy(FailureType.UNKNOWN))

    def should_retry(self, failure_type: GenerationFailureType, retry_count: int) -> bool:
        policy = self.get_policy(failure_type)
        return retry_count < policy.max_retries and policy.retryable

    def should_fallback(self, failure_type: GenerationFailureType) -> bool:
        policy = self.get_policy(failure_type)
        return policy.fallback_allowed


failure_classifier = FailureClassifier()
