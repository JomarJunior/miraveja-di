from typing import TYPE_CHECKING, Any, Callable, List, Optional, Type

from pydantic import BaseModel, ConfigDict, Field

from miraveja_di.domain.enums import Lifetime
from miraveja_di.domain.exceptions import CircularDependencyError

if TYPE_CHECKING:
    from miraveja_di.domain.interfaces import IContainer


class Registration(BaseModel):
    """Value object representing a dependency registration.

    Attributes:
        dependency_type: The type being registered.
        builder: Factory function that receives container and returns instance.
        lifetime: How long the instance should live.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    dependency_type: Type = Field(..., description="The dependency type to be registered.")
    builder: Callable[["IContainer"], Any] = Field(
        ..., description="The builder function to create an instance of the class."
    )
    lifetime: Lifetime = Field(..., description="The lifetime of the registered dependency.")


class DependencyMetadata(BaseModel):
    """Tracks registration details and cached instances.

    Attributes:
        registration: The original registration configuration.
        cached_instance: Cached instance for Singleton/Scoped lifetimes.
        resolution_count: Number of times this dependency has been resolved.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    registration: Registration = Field(..., description="The registration details of the dependency.")
    cached_instance: Optional[Any] = Field(
        default=None,
        description="Cached instance for Singleton or Scoped lifetimes.",
    )
    resolution_count: int = Field(
        default=0,
        description="Number of times this dependency has been resolved.",
    )


class ResolutionContext(BaseModel):
    """Tracks the current dependency resolution stack.

    Used for circular dependency detection. Maintains a stack of types
    currently being resolved in thread-local storage.

    Attributes:
        stack: List of dependency types currently being resolved.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    stack: List[Type] = Field(
        default_factory=list,
        description="Stack of dependency types currently being resolved.",
    )

    def push(self, dependency_type: Type) -> None:
        """Add a dependency to the resolution stack.

        Args:
            dependency_type: The type being resolved.

        Raises:
            CircularDependencyError: If the type is already in the stack.
        """
        if dependency_type in self.stack:
            cycle = self.stack[self.stack.index(dependency_type) :] + [dependency_type]
            raise CircularDependencyError(cycle)
        self.stack.append(dependency_type)

    def pop(self) -> None:
        """Remove the last (most recent) dependency from the stack."""
        if self.stack:
            self.stack.pop()

    def clear(self) -> None:
        """Clear the entire resolution stack."""
        self.stack.clear()
