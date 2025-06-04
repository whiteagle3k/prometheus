"""
Core LLM module for Prometheus Framework

Provides intelligent routing between local and external models,
with a fast classification model for utility tasks.
"""

from .router import LLMRouter, RouteDecision, TaskContext
from .local_llm import LocalLLM
from .fast_llm import FastLLM

__all__ = ["LLMRouter", "RouteDecision", "TaskContext", "LocalLLM", "FastLLM"] 