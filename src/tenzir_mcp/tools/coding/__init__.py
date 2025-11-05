"""Code generation tools for TQL programs and packages."""

from .ocsf_mapping import make_ocsf_mapping
from .parser import make_parser

__all__ = [
    "make_parser",
    "make_ocsf_mapping",
]
