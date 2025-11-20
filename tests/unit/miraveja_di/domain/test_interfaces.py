"""Unit tests for domain interfaces."""

from abc import ABC

import pytest

from miraveja_di.domain.enums import Lifetime
from miraveja_di.domain.interfaces import IContainer, ILifetimeManager, IResolver
from miraveja_di.domain.models import DependencyMetadata


class TestIContainerInterface:
    """Test cases for the IContainer interface."""

    def test_icontainer_is_abstract(self):
        """Test that IContainer is an abstract base class."""
        assert issubclass(IContainer, ABC)

    def test_icontainer_cannot_be_instantiated(self):
        """Test that IContainer cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IContainer()

    def test_icontainer_has_register_method(self):
        """Test that IContainer defines register abstract method."""
        assert hasattr(IContainer, "register")
        assert callable(getattr(IContainer, "register"))

    def test_icontainer_has_resolve_method(self):
        """Test that IContainer defines resolve abstract method."""
        assert hasattr(IContainer, "resolve")
        assert callable(getattr(IContainer, "resolve"))

    def test_icontainer_has_clear_method(self):
        """Test that IContainer defines clear abstract method."""
        assert hasattr(IContainer, "clear")
        assert callable(getattr(IContainer, "clear"))

    def test_icontainer_implementation_requires_all_methods(self):
        """Test that implementing IContainer requires all abstract methods."""

        # Missing all methods
        class IncompleteContainer(IContainer):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteContainer()

        # Missing some methods
        class PartialContainer(IContainer):
            def register(self, dependency_type, builder, lifetime):
                pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            PartialContainer()

    def test_icontainer_can_be_implemented(self):
        """Test that IContainer can be properly implemented."""

        class ConcreteContainer(IContainer):
            def register_singletons(self, dependencies):
                pass

            def register_transients(self, dependencies):
                pass

            def resolve(self, dependency_type):
                return None

            def create_scope(self):
                return self

            def clear(self):
                pass

            def get_registry_copy(self):
                return {}

        # Should not raise
        container = ConcreteContainer()
        assert isinstance(container, IContainer)

    def test_icontainer_implementation_can_call_methods(self):
        """Test that implemented IContainer methods can be called."""

        class WorkingContainer(IContainer):
            def __init__(self):
                self.registry = {}
                self.cleared = False

            def register_singletons(self, dependencies):
                for dep_type, builder in dependencies.items():
                    self.registry[dep_type] = (builder, Lifetime.SINGLETON)

            def register_transients(self, dependencies):
                for dep_type, builder in dependencies.items():
                    self.registry[dep_type] = (builder, Lifetime.TRANSIENT)

            def resolve(self, dependency_type):
                if dependency_type in self.registry:
                    builder, _ = self.registry[dependency_type]
                    return builder(self)
                return None

            def create_scope(self):
                return self

            def clear(self):
                self.registry.clear()
                self.cleared = True

            def get_registry_copy(self):
                return self.registry.copy()

        container = WorkingContainer()

        # Test register_singletons
        container.register_singletons({str: lambda c: "test"})
        assert str in container.registry

        # Test resolve
        result = container.resolve(str)
        assert result == "test"

        # Test clear
        container.clear()
        assert container.cleared
        assert len(container.registry) == 0

    def test_icontainer_type_checking(self):
        """Test that type checking works for IContainer implementations."""

        class MyContainer(IContainer):
            def register_singletons(self, dependencies):
                pass

            def register_transients(self, dependencies):
                pass

            def resolve(self, dependency_type):
                return None

            def create_scope(self):
                return self

            def clear(self):
                pass

            def get_registry_copy(self):
                return {}

        container = MyContainer()
        assert isinstance(container, IContainer)
        assert issubclass(MyContainer, IContainer)


class TestIResolverInterface:
    """Test cases for the IResolver interface."""

    def test_iresolver_is_abstract(self):
        """Test that IResolver is an abstract base class."""
        assert issubclass(IResolver, ABC)

    def test_iresolver_cannot_be_instantiated(self):
        """Test that IResolver cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IResolver()

    def test_iresolver_has_resolve_dependencies_method(self):
        """Test that IResolver defines resolve_dependencies abstract method."""
        assert hasattr(IResolver, "resolve_dependencies")
        assert callable(getattr(IResolver, "resolve_dependencies"))

    def test_iresolver_implementation_requires_resolve_dependencies(self):
        """Test that implementing IResolver requires resolve_dependencies method."""

        class IncompleteResolver(IResolver):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteResolver()

    def test_iresolver_can_be_implemented(self):
        """Test that IResolver can be properly implemented."""

        class ConcreteResolver(IResolver):
            def resolve_dependencies(self, dependency_type, container):
                return dependency_type()

        # Should not raise
        resolver = ConcreteResolver()
        assert isinstance(resolver, IResolver)

    def test_iresolver_implementation_can_resolve(self):
        """Test that implemented IResolver can resolve dependencies."""

        class MockContainer:
            pass

        class SimpleResolver(IResolver):
            def resolve_dependencies(self, dependency_type, container):
                return dependency_type()

        class TestService:
            def __init__(self):
                self.initialized = True

        resolver = SimpleResolver()
        result = resolver.resolve_dependencies(TestService, MockContainer())

        assert isinstance(result, TestService)
        assert result.initialized

    def test_iresolver_type_checking(self):
        """Test that type checking works for IResolver implementations."""

        class MyResolver(IResolver):
            def resolve_dependencies(self, dependency_type, container):
                return None

        resolver = MyResolver()
        assert isinstance(resolver, IResolver)
        assert issubclass(MyResolver, IResolver)


class TestILifetimeManagerInterface:
    """Test cases for the ILifetimeManager interface."""

    def test_ilifetime_manager_is_abstract(self):
        """Test that ILifetimeManager is an abstract base class."""
        assert issubclass(ILifetimeManager, ABC)

    def test_ilifetime_manager_cannot_be_instantiated(self):
        """Test that ILifetimeManager cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            ILifetimeManager()

    def test_ilifetime_manager_has_get_or_create_method(self):
        """Test that ILifetimeManager defines get_or_create abstract method."""
        assert hasattr(ILifetimeManager, "get_or_create")
        assert callable(getattr(ILifetimeManager, "get_or_create"))

    def test_ilifetime_manager_has_clear_cache_method(self):
        """Test that ILifetimeManager defines clear_cache abstract method."""
        assert hasattr(ILifetimeManager, "clear_cache")
        assert callable(getattr(ILifetimeManager, "clear_cache"))

    def test_ilifetime_manager_implementation_requires_all_methods(self):
        """Test that implementing ILifetimeManager requires all abstract methods."""

        class IncompleteManager(ILifetimeManager):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteManager()

        class PartialManager(ILifetimeManager):
            def get_or_create(self, metadata, factory):
                pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            PartialManager()

    def test_ilifetime_manager_can_be_implemented(self):
        """Test that ILifetimeManager can be properly implemented."""

        class ConcreteManager(ILifetimeManager):
            def get_or_create(self, metadata, factory):
                return factory()

            def clear_cache(self):
                pass

            def clear_scoped_cache(self):
                pass

        # Should not raise
        manager = ConcreteManager()
        assert isinstance(manager, ILifetimeManager)

    def test_ilifetime_manager_implementation_can_manage_lifetime(self):
        """Test that implemented ILifetimeManager can manage instance lifetimes."""

        class SimpleManager(ILifetimeManager):
            def __init__(self):
                self.cache = {}
                self.cache_cleared = False

            def get_or_create(self, metadata, factory):
                dep_type = metadata.registration.dependency_type
                if dep_type not in self.cache:
                    self.cache[dep_type] = factory()
                return self.cache[dep_type]

            def clear_cache(self):
                self.cache.clear()
                self.cache_cleared = True

            def clear_scoped_cache(self):
                pass

        class TestService:
            pass

        from miraveja_di.domain.models import Registration

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration)

        manager = SimpleManager()

        # Test get_or_create
        instance1 = manager.get_or_create(metadata, lambda: TestService())
        instance2 = manager.get_or_create(metadata, lambda: TestService())

        assert instance1 is instance2  # Same instance from cache

        # Test clear_cache
        manager.clear_cache()
        assert manager.cache_cleared
        assert len(manager.cache) == 0

    def test_ilifetime_manager_type_checking(self):
        """Test that type checking works for ILifetimeManager implementations."""

        class MyManager(ILifetimeManager):
            def get_or_create(self, metadata, factory):
                return None

            def clear_cache(self):
                pass

            def clear_scoped_cache(self):
                pass

        manager = MyManager()
        assert isinstance(manager, ILifetimeManager)
        assert issubclass(MyManager, ILifetimeManager)
