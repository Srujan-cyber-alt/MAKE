"""
Failure Intelligence for MAKE AI Video Phase 16.

Structured provider error classification with retry/fallback decisions.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FailureType(str, Enum):
    AUTH_ERROR = "auth_error"
    RATE_LIMIT = "rate_limit"
    TEMPORARY_PROVIDER_FAILURE = "temporary_provider_failure"
    INVALID_REQUEST = "invalid_request"
    MODEL_UNAVAILABLE = "model_unavailable"
    CONTENT_POLICY_REJECTION = "content_policy_rejection"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    OUTPUT_INVALID = "output_invalid"
    UNKNOWN = "unknown"


@dataclass
class FailurePolicy:
    failure_type: FailureType
    retryable: bool
    fallback_allowed: bool
    user_action_required: bool
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    description: str = ""


class FailureIntelligence:
    DEFAULT_POLICIES = {
        FailureType.AUTH_ERROR: FailurePolicy(
            failure_type=FailureType.AUTH_ERROR,
            retryable=False,
            fallback_allowed=True,
            user_action_required=True,
            max_retries=0,
            description="Authentication failed. Check API credentials.",
        ),
        FailureType.RATE_LIMIT: FailurePolicy(
            failure_type=FailureType.RATE_LIMIT,
            retryable=True,
            fallback_allowed=True,
            user_action_required=False,
            max_retries=3,
            retry_delay_seconds=2.0,
            backoff_multiplier=2.0,
            jitter=True,
            description="Rate limited. Retrying with exponential backoff.",
        ),
        FailureType.TEMPORARY_PROVIDER_FAILURE: FailurePolicy(
            failure_type=FailureType.TEMPORARY_PROVIDER_FAILURE,
            retryable=True,
            fallback_allowed=True,
            user_action_required=False,
            max_retries=2,
            retry_delay_seconds=1.0,
            backoff_multiplier=2.0,
            jitter=True,
            description="Temporary provider failure. Retrying.",
        ),
        FailureType.INVALID_REQUEST: FailurePolicy(
            failure_type=FailureType.INVALID_REQUEST,
            retryable=False,
            fallback_allowed=False,
            user_action_required=True,
            max_retries=0,
            description="Invalid request parameters. User must correct input.",
        ),
        FailureType.MODEL_UNAVAILABLE: FailurePolicy(
            failure_type=FailureType.MODEL_UNAVAILABLE,
            retryable=False,
            fallback_allowed=True,
            user_action_required=False,
            max_retries=0,
            description="Model unavailable. Falling back to alternative.",
        ),
        FailureType.CONTENT_POLICY_REJECTION: FailurePolicy(
            failure_type=FailureType.CONTENT_POLICY_REJECTION,
            retryable=False,
            fallback_allowed=False,
            user_action_required=True,
            max_retries=0,
            description="Content rejected by provider policy. User must modify request.",
        ),
        FailureType.TIMEOUT: FailurePolicy(
            failure_type=FailureType.TIMEOUT,
            retryable=True,
            fallback_allowed=True,
            user_action_required=False,
            max_retries=2,
            retry_delay_seconds=5.0,
            backoff_multiplier=2.0,
            jitter=True,
            description="Request timed out. Retrying or falling back.",
        ),
        FailureType.NETWORK_ERROR: FailurePolicy(
            failure_type=FailureType.NETWORK_ERROR,
            retryable=True,
            fallback_allowed=True,
            user_action_required=False,
            max_retries=3,
            retry_delay_seconds=1.0,
            backoff_multiplier=2.0,
            jitter=True,
            description="Network error. Retrying.",
        ),
        FailureType.OUTPUT_INVALID: FailurePolicy(
            failure_type=FailureType.OUTPUT_INVALID,
            retryable=False,
            fallback_allowed=True,
            user_action_required=False,
            max_retries=0,
            description="Output failed validation. Falling back.",
        ),
        FailureType.UNKNOWN: FailurePolicy(
            failure_type=FailureType.UNKNOWN,
            retryable=True,
            fallback_allowed=True,
            user_action_required=False,
            max_retries=1,
            retry_delay_seconds=2.0,
            backoff_multiplier=2.0,
            jitter=True,
            description="Unknown error. Retrying once then falling back.",
        ),
    }

    def __init__(self):
        self._policies: Dict[FailureType, FailurePolicy] = dict(self.DEFAULT_POLICIES)

    def classify_error(self, error: Exception, context: Dict[str, Any] = None) -> FailureType:
        error_str = str(error).lower()
        context = context or {}

        if "auth" in error_str or "401" in error_str or "403" in error_str:
            return FailureType.AUTH_ERROR
        if "rate limit" in error_str or "429" in error_str:
            return FailureType.RATE_LIMIT
        if "timeout" in error_str or "timed out" in error_str:
            return FailureType.TIMEOUT
        if "network" in error_str or "connection" in error_str or "dns" in error_str:
            return FailureType.NETWORK_ERROR
        if "content policy" in error_str or "rejected" in error_str or "policy" in error_str:
            return FailureType.CONTENT_POLICY_REJECTION
        if "invalid" in error_str or "bad request" in error_str or "400" in error_str:
            return FailureType.INVALID_REQUEST
        if "unavailable" in error_str or "503" in error_str or "502" in error_str:
            if context.get("retry_count", 0) < 2:
                return FailureType.TEMPORARY_PROVIDER_FAILURE
            return FailureType.MODEL_UNAVAILABLE
        if "validation" in error_str or "invalid output" in error_str or "corrupt" in error_str:
            return FailureType.OUTPUT_INVALID
        if "model" in error_str and ("not found" in error_str or "unavailable" in error_str):
            return FailureType.MODEL_UNAVAILABLE

        return FailureType.UNKNOWN

    def get_policy(self, failure_type: FailureType) -> FailurePolicy:
        return self._policies.get(failure_type, self._policies[FailureType.UNKNOWN])

    def should_retry(self, failure_type: FailureType, retry_count: int) -> bool:
        policy = self.get_policy(failure_type)
        return retry_count < policy.max_retries and policy.retryable

    def should_fallback(self, failure_type: FailureType) -> bool:
        policy = self.get_policy(failure_type)
        return policy.fallback_allowed

    def requires_user_action(self, failure_type: FailureType) -> bool:
        policy = self.get_policy(failure_type)
        return policy.user_action_required

    def get_retry_delay(self, failure_type: FailureType, retry_count: int) -> float:
        policy = self.get_policy(failure_type)
        delay = policy.retry_delay_seconds * (policy.backoff_multiplier ** retry_count)
        if policy.jitter:
            import random
            delay = delay * (0.5 + random.random())
        return delay

    def add_custom_policy(self, policy: FailurePolicy):
        self._policies[policy.failure_type] = policy

    def get_failure_description(self, failure_type: FailureType) -> str:
        policy = self.get_policy(failure_type)
        return policy.description


failure_intelligence = FailureIntelligence()
