"""
Infrastructure layer - External integrations.

This layer contains integrations with external frameworks and tools.
It depends on both Application and Domain layers.
"""

from . import fastapi_integration, testing

__all__ = [
    "fastapi_integration",
    "testing",
]
