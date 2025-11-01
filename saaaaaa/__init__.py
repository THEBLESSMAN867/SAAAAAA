"""Namespace package shim exposing the real implementation under ``src``."""

from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)
_SRC_PACKAGE = Path(__file__).resolve().parent.parent / "src" / "saaaaaa"
if _SRC_PACKAGE.exists():
    __path__.append(str(_SRC_PACKAGE))

__all__ = []
