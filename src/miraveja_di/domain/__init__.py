"""
Domain layer - Core business logic and models.

This layer contains the fundamental business rules and models for dependency injection.
It has no dependencies on other layers.
"""

from .enums import Lifetime
from .exceptions import (
    CircularDependencyError,
    DIException,
    LifetimeError,
    ScopeError,
    UnresolvableError,
)
from .interfaces import IContainer, ILifetimeManager, IResolver
from .models import DependencyMetadata, Registration, ResolutionContext

# Rebuild Pydantic models to resolve forward references
Registration.model_rebuild()

__all__ = [
    # Enums
    "Lifetime",
    # Exceptions
    "DIException",
    "CircularDependencyError",
    "UnresolvableError",
    "LifetimeError",
    "ScopeError",
    # Interfaces
    "IContainer",
    "IResolver",
    "ILifetimeManager",
    # Models
    "Registration",
    "DependencyMetadata",
    "ResolutionContext",
]
