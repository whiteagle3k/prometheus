"""
Prometheus Core Framework

The core framework provides all the foundational components for building
identity-driven AI entities with conversational memory and intelligent routing.
"""

__version__ = "0.5.0"
__author__ = "Prometheus Framework"

from .base_entity import BaseEntity
from .config import config

__all__ = ["BaseEntity", "config"] 