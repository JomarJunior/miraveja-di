from typing import Any, Callable, Dict, Optional, Type

from miraveja_di.domain import (
    CircularDependencyError,
    DependencyMetadata,
    ILifetimeManager,
    Lifetime,
    UnresolvableError,
)


class LifetimeManager(ILifetimeManager):
    """Manages instance lifetimes for singleton, transient, and scoped dependencies.

    Handles caching of singleton instances and creation of transient instances.

    Attributes:
        _singleton_cache: Cache for singleton instances.
        _scoped_cache: Cache for scoped instances (per scope context).
    """

    def __init__(self, parent_singleton_cache: Optional[Dict[Type, Any]] = None) -> None:
        """Initialize the lifetime manager with empty caches.

        Args:
            parent_singleton_cache: Optional parent singleton cache for scoped containers.
        """
        if parent_singleton_cache is not None:
            # Scoped container: share parent's singleton cache
            self._singleton_cache: Dict[Type, Any] = parent_singleton_cache
        else:
            # Root container: create own singleton cache
            self._singleton_cache: Dict[Type, Any] = {}
        # Each scope has its own scoped cache
        self._scoped_cache: Dict[Type, Any] = {}

    def get_or_create(self, metadata: DependencyMetadata, factory: Callable[[], Any]) -> Any:
        """Get existing instance or create new one based on lifetime.

        Args:
            metadata: Registration metadata containing lifetime info.
            factory: Function to create new instance if needed.

        Returns:
            Instance according to lifetime rules:
            - Singleton: Returns cached instance or creates and caches new one
            - Transient: Always creates new instance
            - Scoped: Returns cached instance within scope or creates new one

        Example:
            >>> metadata = DependencyMetadata(
            ...     registration=Registration(
            ...         dependency_type=MyService,
            ...         builder=lambda c: MyService(),
            ...         lifetime=Lifetime.SINGLETON
            ...     )
            ... )
            >>> instance = manager.get_or_create(metadata, lambda: MyService())
        """
        lifetime = metadata.registration.lifetime
        dependency_type = metadata.registration.dependency_type

        if lifetime == Lifetime.SINGLETON:
            # Return cached singleton or create and cache
            if dependency_type not in self._singleton_cache:
                try:
                    self._singleton_cache[dependency_type] = factory()
                except Exception as e:
                    if isinstance(e, (UnresolvableError, CircularDependencyError)):
                        raise
                    raise UnresolvableError(dependency_type, f"Failed to create instance: {str(e)}") from e
            return self._singleton_cache[dependency_type]

        if lifetime == Lifetime.SCOPED:
            # Return cached scoped instance or create and cache
            if dependency_type not in self._scoped_cache:
                try:
                    self._scoped_cache[dependency_type] = factory()
                except (UnresolvableError, CircularDependencyError):
                    raise
                except Exception as e:
                    raise UnresolvableError(dependency_type, f"Failed to create instance: {str(e)}") from e
            return self._scoped_cache[dependency_type]

        # Lifetime.TRANSIENT
        # Always create new instance for transient
        try:
            return factory()
        except (UnresolvableError, CircularDependencyError):
            raise
        except Exception as e:
            raise UnresolvableError(dependency_type, f"Failed to create instance: {str(e)}") from e

    def clear_cache(self) -> None:
        """Clear all cached instances (singletons and scoped).

        Useful for testing or resetting container state.
        """
        self._singleton_cache.clear()
        self._scoped_cache.clear()

    def clear_scoped_cache(self) -> None:
        """Clear only the scoped instance cache.

        Useful when ending a scope (e.g., end of HTTP request).
        """
        self._scoped_cache.clear()

    def get_singleton_cache(self) -> Dict[Type, Any]:
        """Get reference to singleton cache for scope inheritance.

        Returns:
            Reference to the singleton cache.
        """
        return self._singleton_cache
