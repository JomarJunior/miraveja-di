from typing import Any, Callable, Dict, Type, TypeVar

from miraveja_di.application.circular_detector import CircularDependencyDetector
from miraveja_di.application.lifetime_manager import LifetimeManager
from miraveja_di.application.resolver import DependencyResolver
from miraveja_di.domain import (
    DependencyMetadata,
    IContainer,
    ILifetimeManager,
    IResolver,
    Lifetime,
    LifetimeError,
    Registration,
)

T = TypeVar("T")


class DIContainer(IContainer):
    """Main dependency injection container.

    Orchestrates registration and resolution of dependencies using domain objects.
    Supports singleton, transient, and scoped lifetimes with auto-wiring.

    Attributes:
        _registry: Dictionary mapping dependency types to their metadata.
        _resolver: Component responsible for auto-wiring dependencies.
        _lifetime_manager: Component managing instance lifetimes.
        _circular_detector: Component detecting circular dependencies.
    """

    def __init__(self) -> None:
        """Initialize the DI container with empty registry and domain components."""
        self._registry: Dict[Type, DependencyMetadata] = {}
        self._resolver: IResolver = DependencyResolver()
        self._lifetime_manager: ILifetimeManager = LifetimeManager()
        self._circular_detector = CircularDependencyDetector()

    def _register(
        self,
        dependency_type: Type,
        builder: Callable[[IContainer], Any],
        lifetime: Lifetime,
    ) -> None:
        """Internal registration method with validation.

        Args:
            dependency_type: The type to register.
            builder: Factory function to create the instance.
            lifetime: How long the instance should live.

        Raises:
            LifetimeError: If already registered with a different lifetime.
        """
        # Check for conflicting registrations
        if dependency_type in self._registry:
            existing = self._registry[dependency_type]
            if existing.registration.lifetime != lifetime:
                raise LifetimeError(
                    f"Dependency {dependency_type.__name__} is already registered "
                    f"with lifetime {existing.registration.lifetime.value}, "
                    f"cannot re-register with {lifetime.value}"
                )
            return  # Skip if already registered with same lifetime

        # Create registration
        registration = Registration(
            dependency_type=dependency_type,
            builder=builder,
            lifetime=lifetime,
        )

        # Store metadata
        self._registry[dependency_type] = DependencyMetadata(
            registration=registration,
        )

    def register_singletons(self, dependencies: Dict[Type, Callable[[IContainer], Any]]) -> None:
        """Register multiple singleton dependencies at once.

        Singleton dependencies are created once and shared across the entire application.

        Args:
            dependencies: Dictionary mapping dependency types to builder functions.
                         Each builder receives the container and returns an instance.

        Raises:
            LifetimeError: If a dependency is already registered with a different lifetime.

        Example:
            >>> container.register_singletons({
            ...     DatabaseConfig: lambda c: DatabaseConfig.from_env(),
            ...     DatabaseConnection: lambda c: DatabaseConnection(c.resolve(DatabaseConfig)),
            ... })
        """
        for dependency_type, builder in dependencies.items():
            self._register(dependency_type, builder, Lifetime.SINGLETON)

    def register_transients(self, dependencies: Dict[Type, Callable[[IContainer], Any]]) -> None:
        """Register multiple transient dependencies at once.

        Transient dependencies are created fresh on each resolution.

        Args:
            dependencies: Dictionary mapping dependency types to builder functions.
                         Each builder receives the container and returns an instance.

        Raises:
            LifetimeError: If a dependency is already registered with a different lifetime.

        Example:
            >>> container.register_transients({
            ...     RequestHandler: lambda c: RequestHandler(c.resolve(DatabaseConnection)),
            ...     EventProcessor: lambda c: EventProcessor(),
            ... })
        """
        for dependency_type, builder in dependencies.items():
            self._register(dependency_type, builder, Lifetime.TRANSIENT)

    def resolve(self, dependency_type: type[T]) -> T:
        """Resolve and return an instance of the specified type.

        Uses auto-wiring if no explicit registration exists. Delegates to resolver
        for dependency graph construction and lifetime manager for instance creation.

        Args:
            dependency_type: The type to resolve.

        Returns:
            Instance of the requested type with all dependencies injected.

        Raises:
            UnresolvableError: If the dependency cannot be resolved.
            CircularDependencyError: If a circular dependency is detected.

        Example:
            >>> user_service = container.resolve(UserService)
        """
        # Check for circular dependencies
        self._circular_detector.push(dependency_type)

        try:
            # Check if explicitly registered
            if dependency_type in self._registry:
                metadata = self._registry[dependency_type]
                instance = self._lifetime_manager.get_or_create(
                    metadata,
                    lambda: metadata.registration.builder(self),
                )
                metadata.resolution_count += 1
                return instance

            # Auto-wire if not registered
            instance = self._resolver.resolve_dependencies(dependency_type, self)
            return instance

        finally:
            self._circular_detector.pop()

    def get_registry_copy(self) -> Dict[Type, DependencyMetadata]:
        """Get a copy of the registry for scope inheritance.

        Returns:
            Copy of the current registry.
        """
        return self._registry.copy()

    def set_registry(self, registry: Dict[Type, DependencyMetadata]) -> None:
        """Set the registry from a parent container.

        Args:
            registry: Registry to inherit.
        """
        self._registry = registry

    def create_scope(self) -> "IContainer":
        """Create a child container for scoped lifetime.

        Scoped containers inherit parent registrations but maintain separate
        instance caches for scoped dependencies. Useful for per-request state
        in web applications.

        Returns:
            New container that inherits parent registrations.

        Example:
            >>> with container.create_scope() as scoped:
            ...     # Same instance within this scope
            ...     ctx1 = scoped.resolve(RequestContext)
            ...     ctx2 = scoped.resolve(RequestContext)
            ...     assert ctx1 is ctx2
        """
        scoped_container = DIContainer()
        # Inherit parent registrations
        scoped_container.set_registry(self.get_registry_copy())
        return scoped_container

    def clear(self) -> None:
        """Clear all registrations and cached instances.

        Useful for testing or resetting the container state.
        """
        self._registry.clear()
        self._lifetime_manager.clear_cache()
        self._circular_detector.clear()
