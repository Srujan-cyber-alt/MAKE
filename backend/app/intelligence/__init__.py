"""MAKE Intelligence Core V1.

Persistent reasoning and orchestration layer sitting above MAKE's existing
Video and Image subsystems.

Architecture:
    Intent Engine -> World Memory -> Reality Graph -> Reasoning Engine ->
    Consistency Engine -> Self-Critique -> Creative Director ->
    Visual Planning Engine -> Tool Router -> Persistent Job Manager ->
    Execution -> Artifact Manager -> Provenance

This subsystem is CPU-first: no GPU dependencies, no third-party AI-generation
APIs. Local model integration is supported through pluggable ToolAdapter
interfaces so the core never needs to be redesigned.

The frozen Video and Image subsystems are accessed ONLY through clean,
read-only integration interfaces defined in ``app.intelligence.jobs.tool_router``.
Their files, training, inference, datasets, checkpoints and tests are not
modified.
"""

from app.intelligence.config import intelligence_settings

__all__ = ["intelligence_settings"]
__version__ = "1.0.0"
