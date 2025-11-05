"""Execution tools for running TQL pipelines and tests."""

from .run_pipeline import run_pipeline
from .run_test import run_test

__all__ = [
    "run_pipeline",
    "run_test",
]
