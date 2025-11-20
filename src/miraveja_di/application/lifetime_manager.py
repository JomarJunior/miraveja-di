from typing import Any, Callable, Dict, Type

from miraveja_di.domain import DependencyMetadata, ILifetimeManager, Lifetime


class LifetimeManager(ILifetimeManager):
    """Manages instance lifetimes for singleton, transient, and scoped dependencies.

    Handles caching of singleton instances and creation of transient instances.

    Attributes:
        _singleton_cache: Cache for singleton instances.
        _scoped_cache: Cache for scoped instances (per scope context).
    """

    def __init__(self) -> None:
        """Initialize the lifetime manager with empty caches."""
        self._singleton_cache: Dict[Type, Any] = {}
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
                self._singleton_cache[dependency_type] = factory()
            return self._singleton_cache[dependency_type]

        if lifetime == Lifetime.SCOPED:
            # Return cached scoped instance or create and cache
            if dependency_type not in self._scoped_cache:
                self._scoped_cache[dependency_type] = factory()
            return self._scoped_cache[dependency_type]

        # Lifetime.TRANSIENT
        # Always create new instance for transient
        return factory()

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
