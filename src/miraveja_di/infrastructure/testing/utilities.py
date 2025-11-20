from typing import Any, Callable, Dict, Optional, Tuple, Type, TypeVar

from miraveja_di.application import DIContainer
from miraveja_di.domain import IContainer, Lifetime

T = TypeVar("T")


class TestContainer(DIContainer):
    """DI container for testing with dependency override capabilities.

    Inherits all registrations from a parent container but allows selective
    override of dependencies for testing purposes. Automatically cleans up
    after test execution.

    This is useful for:
    - Mocking external services (databases, APIs, etc.)
    - Replacing implementations with test doubles
    - Isolating tests from shared state

    Attributes:
        _parent_container: The parent container to inherit registrations from.
        _overrides: Dictionary of overridden dependencies for this test.

    Example:
        >>> # Production container
        >>> container = DIContainer()
        >>> container.register_singletons({
        ...     EmailService: lambda c: RealEmailService(),
        ...     UserRepository: lambda c: DatabaseUserRepository(),
        ... })
        >>>
        >>> # Test container with mocks
        >>> def test_user_service():
        ...     test_container = TestContainer(container)
        ...
        ...     # Override EmailService with mock
        ...     mock_email = MockEmailService()
        ...     test_container.mock_singleton(EmailService, mock_email)
        ...
        ...     # UserService will get mocked EmailService
        ...     service = test_container.resolve(UserService)
        ...     service.send_welcome_email(user)
        ...
        ...     # Verify mock was called
        ...     assert mock_email.send_called
    """

    __test__ = False  # Tell pytest not to collect this class as a test

    def __init__(self, parent_container: Optional[IContainer] = None) -> None:
        """Initialize the test container.

        Args:
            parent_container: Optional parent container to inherit registrations from.
                            If None, creates an empty container.
        """
        super().__init__()
        self._parent_container = parent_container
        self._overrides: Dict[Type, Any] = {}

        # Inherit registrations from parent container
        if parent_container:
            self._registry = parent_container.get_registry_copy()

    def mock_singleton(self, dependency_type: Type[T], mock_instance: T) -> None:
        """Replace a singleton dependency with a mock instance.

        The mock instance will be returned for all subsequent resolutions of
        the dependency type, regardless of the original registration.

        Args:
            dependency_type: The type to mock.
            mock_instance: The mock instance to return.

        Example:
            >>> test_container = TestContainer(container)
            >>> mock_db = MockDatabase()
            >>> test_container.mock_singleton(DatabaseConnection, mock_db)
            >>>
            >>> # All resolutions of DatabaseConnection will get mock_db
            >>> service = test_container.resolve(UserService)
            >>> assert service.db is mock_db
        """
        self._overrides[dependency_type] = mock_instance

        # Clear any existing registration and cache for this dependency
        if dependency_type in self._registry:
            del self._registry[dependency_type]
        self._lifetime_manager.clear_cache()

        # Override registration to return the mock
        self.register_singletons({dependency_type: lambda c: mock_instance})

    def mock_transient(self, dependency_type: Type[T], factory: Callable[[], T]) -> None:
        """Replace a transient dependency with a mock factory.

        The factory will be called each time the dependency is resolved,
        allowing different mock instances per resolution.

        Args:
            dependency_type: The type to mock.
            factory: Factory function that returns a mock instance.

        Example:
            >>> test_container = TestContainer(container)
            >>> test_container.mock_transient(
            ...     RequestHandler,
            ...     lambda: MockRequestHandler()
            ... )
            >>>
            >>> # Each resolution gets a new mock instance
            >>> handler1 = test_container.resolve(RequestHandler)
            >>> handler2 = test_container.resolve(RequestHandler)
            >>> assert handler1 is not handler2
        """
        self.register_transients({dependency_type: lambda c: factory()})

    def override_registration(
        self, dependency_type: Type[T], builder: Callable[[IContainer], T], lifetime: Lifetime
    ) -> None:
        """Override a dependency registration with custom builder and lifetime.

        Args:
            dependency_type: The type to override.
            builder: Factory function to create the instance.
            lifetime: Lifetime for the overridden dependency.

        Example:
            >>> test_container = TestContainer(container)
            >>> test_container.override_registration(
            ...     CacheService,
            ...     lambda c: InMemoryCacheService(),  # Instead of Redis
            ...     Lifetime.SINGLETON
            ... )
        """
        # Clear any existing registration and cache for this dependency
        if dependency_type in self._registry:
            del self._registry[dependency_type]
        self._lifetime_manager.clear_cache()

        if lifetime == Lifetime.SINGLETON:
            self.register_singletons({dependency_type: builder})
        elif lifetime == Lifetime.TRANSIENT:
            self.register_transients({dependency_type: builder})
        else:
            raise ValueError(f"Unsupported lifetime for override: {lifetime}")

    def reset_overrides(self) -> None:
        """Remove all overrides and restore parent registrations.

        Useful for cleaning up between test cases.
        """
        self._overrides.clear()
        self._lifetime_manager.clear_cache()
        if self._parent_container:
            self._registry = self._parent_container.get_registry_copy()
        else:
            self._registry.clear()

    def __enter__(self) -> "TestContainer":
        """Context manager entry - returns self."""
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        """Context manager exit - automatically clean up overrides."""
        self.reset_overrides()
        self.clear()
        return False


def create_mock_container(*singletons: Tuple[Type, Any]) -> TestContainer:
    """Create a test container with pre-configured mock singletons.

    Convenience function for quickly setting up a test container with
    multiple mocked dependencies.

    Args:
        *singletons: Tuples of (dependency_type, mock_instance).

    Returns:
        TestContainer with mocked dependencies.

    Example:
        >>> mock_db = MockDatabase()
        >>> mock_cache = MockCache()
        >>>
        >>> test_container = create_mock_container(
        ...     (DatabaseConnection, mock_db),
        ...     (CacheService, mock_cache),
        ... )
        >>>
        >>> service = test_container.resolve(UserService)
        >>> # Service will have mocked dependencies
    """
    container = TestContainer()

    for dependency_type, mock_instance in singletons:
        container.mock_singleton(dependency_type, mock_instance)

    return container


class MockScope:
    """Context manager for scoped testing with automatic cleanup.

    Provides a scoped container context for testing request-scoped
    dependencies with automatic cleanup after the test.

    Example:
        >>> container = DIContainer()
        >>> container.register_singletons({
        ...     DatabaseConnection: lambda c: DatabaseConnection(),
        ... })
        >>>
        >>> with MockScope(container) as scoped:
        ...     # Test with scoped dependencies
        ...     ctx = scoped.resolve(RequestContext)
        ...     service = scoped.resolve(RequestService)
        ...
        ...     # Scoped instances are shared within this block
        ...     assert service.context is ctx
        ...
        ... # Scoped instances automatically cleaned up here
    """

    def __init__(self, parent_container: IContainer) -> None:
        """Initialize the mock scope.

        Args:
            parent_container: The parent container to create the scope from.
        """
        self._parent_container = parent_container
        self._scoped_container: Optional[IContainer] = None

    def __enter__(self) -> IContainer:
        """Enter the scoped context and create a scoped container.

        Returns:
            The scoped container instance.
        """
        self._scoped_container = self._parent_container.create_scope()
        return self._scoped_container

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        """Exit the scoped context and clean up the scoped container."""
        if self._scoped_container:
            self._scoped_container.clear()
            self._scoped_container = None
        return False
