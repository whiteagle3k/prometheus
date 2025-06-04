"""
Core LLM module for Prometheus Framework

Provides intelligent routing between local and external models,
with a fast classification model for utility tasks.
"""

from .fast_llm import FastLLM
from .local_llm import LocalLLM
from .router import LLMRouter, RouteDecision, TaskContext

__all__ = ["LLMRouter", "RouteDecision", "TaskContext", "LocalLLM", "FastLLM"]
