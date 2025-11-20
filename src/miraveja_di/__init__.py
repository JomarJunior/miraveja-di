"""
miraveja-di: Lightweight type-hint based Dependency Injection container with auto-wiring.

Public API exports for the miraveja-di package.
"""

# Application exports
from miraveja_di.application.container import DIContainer

# Domain exports
from miraveja_di.domain.enums import Lifetime
from miraveja_di.domain.exceptions import (
    CircularDependencyError,
    DIException,
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
