from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Type, TypeVar

from miraveja_di.domain.models import DependencyMetadata

T = TypeVar("T")


class IContainer(ABC):
    """Abstract interface for dependency injection container operations."""

    @abstractmethod
    def register_singletons(self, dependencies: Dict[Type, Callable[["IContainer"], Any]]) -> None:
        """Register multiple singleton dependencies at once.

        Args:
            dependencies: A dictionary mapping types to their builder functions.
        """

    @abstractmethod
    def register_transients(self, dependencies: Dict[Type, Callable[["IContainer"], Any]]) -> None:
        """Register multiple transient dependencies at once.

        Args:
            dependencies: A dictionary mapping types to their builder functions.
        """

    @abstractmethod
    def resolve(self, dependency_type: Type[T]) -> T:
        """Resolve and return an instance of the requested class type.

        Args:
            dependency_type: The type to resolve.
        """

    @abstractmethod
    def create_scope(self) -> "IContainer":
        """Create and return a new scoped container instance."""

    @abstractmethod
    def clear(self) -> None:
        """Clear all registrations and instances from the container."""

    @abstractmethod
    def get_registry_copy(self) -> Dict[Type, DependencyMetadata]:
        """Get a copy of the current registry of dependencies."""


class IResolver(ABC):
    """Abstract interface for dependency resolution operations."""

    @abstractmethod
    def resolve_dependencies(
        self,
        dependency_type: Type,
        container: IContainer,
    ) -> Any:
        """Resolve all constructor dependencies and create instance.

        Args:
            dependency_type: The type to resolve.
            container: The DI container to use for resolving dependencies.

        Returns:
            Instance with all dependencies injected.

        Raises:
            UnresolvableError: If a dependency cannot be resolved.
        """


class ILifetimeManager(ABC):
    """Abstract interface for managing dependency lifetimes."""

    @abstractmethod
    def get_or_create(
        self,
        metadata: DependencyMetadata,
        factory: Callable[[], Any],
    ) -> Any:
        """Get existing instance or create a new one based on lifetime.

        Args:
            metadata: The dependency metadata containing registration info.
            factory: A callable to create a new instance if needed.
        """

    @abstractmethod
    def clear_cache(self) -> None:
        """Clear any cached instances managed by this lifetime manager."""

    @abstractmethod
    def clear_scoped_cache(self) -> None:
        """Clear only the scoped instances cache."""
