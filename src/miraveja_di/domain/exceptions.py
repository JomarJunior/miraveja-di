from typing import List, Optional, Type


class DIException(Exception):
    """Base exception for DI-related errors."""


class CircularDependencyError(DIException):
    """Raised when a circular dependency is detected.

    Attributes:
        dependency_chain: List of types involved in the circular dependency.
    """

    def __init__(self, dependency_chain: List[Type]) -> None:
        self.dependency_chain = dependency_chain
        message = f"Circular dependency detected: {' -> '.join([cls.__name__ for cls in dependency_chain])}"
        super().__init__(message)


class UnresolvableError(DIException):
    """Raised when a dependency cannot be resolved.

    This occurs when:
    - No registration exists for the requested type.
    - Constructor parameters lacks type hints.
    - Type hint cannot be resolved.

    Attributes:
        cls: The class type that could not be resolved.
        reason: Optional reason for the failure.
    """

    def __init__(self, cls: Type, reason: Optional[str] = None) -> None:
        self.cls = cls
        self.reason = reason
        message = f"Cannot resolve dependency for type: {cls.__name__}"
        if reason:
            message += f". Reason: {reason}"
        super().__init__(message)


class LifetimeError(DIException):
    """Raised for invalid lifetime configuraitons.

    This occurs when:
    - Registering the same type with conflicting lifetimes.
    - Invalid lifetime value provided.
    """


class ScopeError(DIException):
    """Raised for invalid scope operations.

    This occurs when:
    - Attempting to resolve a scoped dependency from the root container.
    - Creating a scope from a non-root container.
    """
