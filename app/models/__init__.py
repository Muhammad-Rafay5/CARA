"""
Model subsystem for CARA.

Exports:
- ModelRegistry & default singleton registry
- ModelProfile
- ModelSelector
- FallbackChain
- HealthMonitor
- UsageTracker & default singleton usage_tracker
"""

from app.models.fallback import FallbackChain
from app.models.health import HealthMonitor
from app.models.registry import ModelProfile, ModelRegistry, registry
from app.models.selector import ModelSelector
from app.models.usage import UsageTracker, usage_tracker

__all__ = [
    "FallbackChain",
    "HealthMonitor",
    "ModelProfile",
    "ModelRegistry",
    "ModelSelector",
    "UsageTracker",
    "registry",
    "usage_tracker",
]
