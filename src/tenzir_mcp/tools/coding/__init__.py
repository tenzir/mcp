"""Code generation tools for TQL programs and packages."""

from .make_ocsf_mapping import make_ocsf_mapping
from .make_parser import make_parser

__all__ = [
    "make_parser",
    "make_ocsf_mapping",
]
