"""
miraveja-di: Lightweight type-hint based Dependency Injection container with auto-wiring.

Public API exports for the miraveja-di package.
"""

# Application exports
from miraveja_di.application import DIContainer

# Domain exports
from miraveja_di.domain import (
    CircularDependencyError,
    DIException,
    Lifetime,
    LifetimeError,
    ScopeError,
    UnresolvableError,
)

__version__ = "0.1.0"

__all__ = [
    # Container
    "DIContainer",
    # Enums
    "Lifetime",
    # Exceptions
    "DIException",
    "CircularDependencyError",
    "UnresolvableError",
    "LifetimeError",
    "ScopeError",
]
