"""
FastAPI integration module.

Provides helpers and utilities for integrating miraveja-di with FastAPI.
"""

from .integration import (
    ScopedContainerMiddleware,
    create_fastapi_dependency,
    create_scoped_dependency,
    inject_dependencies,
)

__all__ = [
    "create_fastapi_dependency",
    "create_scoped_dependency",
    "inject_dependencies",
    "ScopedContainerMiddleware",
]
