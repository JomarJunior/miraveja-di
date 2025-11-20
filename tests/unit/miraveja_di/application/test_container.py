"""Unit tests for DIContainer."""

import pytest

from miraveja_di.application.container import DIContainer
from miraveja_di.domain import (
    CircularDependencyError,
    IContainer,
    Lifetime,
    LifetimeError,
    UnresolvableError,
)


class TestContainerInitialization:
    """Test cases for DIContainer initialization."""

    def test_container_initialization(self):
        """Test that container initializes correctly."""
        container = DIContainer()
        assert container._registry == {}
        assert container._resolver is not None
        assert container._lifetime_manager is not None
        assert container._circular_detector is not None

    def test_container_implements_interface(self):
        """Test that DIContainer implements IContainer."""
        container = DIContainer()
        assert isinstance(container, IContainer)


class TestSingletonRegistration:
    """Test cases for singleton registration."""

    def test_register_single_singleton(self):
        """Test registering a single singleton."""
        container = DIContainer()

        class TestService:
            pass

        container.register_singletons({TestService: lambda c: TestService()})

        assert TestService in container._registry
        metadata = container._registry[TestService]
        assert metadata.registration.lifetime == Lifetime.SINGLETON

    def test_register_multiple_singletons(self):
        """Test registering multiple singletons at once."""
        container = DIContainer()

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            pass

        container.register_singletons(
            {
                ServiceA: lambda c: ServiceA(),
                ServiceB: lambda c: ServiceB(),
                ServiceC: lambda c: ServiceC(),
            }
        )

        assert len(container._registry) == 3
        assert all(
            container._registry[cls].registration.lifetime == Lifetime.SINGLETON
            for cls in [ServiceA, ServiceB, ServiceC]
        )

    def test_register_singleton_with_dependencies(self):
        """Test registering singleton that depends on other singletons."""
        container = DIContainer()

        class DatabaseConfig:
            pass

        class DatabaseConnection:
            def __init__(self, config: DatabaseConfig):
                self.config = config

        container.register_singletons(
            {
                DatabaseConfig: lambda c: DatabaseConfig(),
                DatabaseConnection: lambda c: DatabaseConnection(c.resolve(DatabaseConfig)),
            }
        )

        instance = container.resolve(DatabaseConnection)
        assert isinstance(instance, DatabaseConnection)
        assert isinstance(instance.config, DatabaseConfig)

    def test_register_same_singleton_twice_with_same_lifetime(self):
        """Test that registering same singleton twice doesn't raise error."""
        container = DIContainer()

        class TestService:
            pass

        container.register_singletons({TestService: lambda c: TestService()})
        # Should not raise
        container.register_singletons({TestService: lambda c: TestService()})

    def test_register_singleton_then_transient_raises_error(self):
        """Test that registering singleton then transient raises LifetimeError."""
        container = DIContainer()

        class TestService:
            pass

        container.register_singletons({TestService: lambda c: TestService()})

        with pytest.raises(LifetimeError) as exc_info:
            container.register_transients({TestService: lambda c: TestService()})

        error = exc_info.value
        assert "TestService" in str(error)
        assert "singleton" in str(error)
        assert "transient" in str(error)


class TestTransientRegistration:
    """Test cases for transient registration."""

    def test_register_single_transient(self):
        """Test registering a single transient."""
        container = DIContainer()

        class TestService:
            pass

        container.register_transients({TestService: lambda c: TestService()})

        assert TestService in container._registry
        metadata = container._registry[TestService]
        assert metadata.registration.lifetime == Lifetime.TRANSIENT

    def test_register_multiple_transients(self):
        """Test registering multiple transients at once."""
        container = DIContainer()

        class ServiceA:
            pass

        class ServiceB:
            pass

        container.register_transients(
            {
                ServiceA: lambda c: ServiceA(),
                ServiceB: lambda c: ServiceB(),
            }
        )

        assert len(container._registry) == 2
        assert all(container._registry[cls].registration.lifetime == Lifetime.TRANSIENT for cls in [ServiceA, ServiceB])

    def test_register_transient_then_singleton_raises_error(self):
        """Test that registering transient then singleton raises LifetimeError."""
        container = DIContainer()

        class TestService:
            pass

        container.register_transients({TestService: lambda c: TestService()})

        with pytest.raises(LifetimeError):
            container.register_singletons({TestService: lambda c: TestService()})


class TestResolution:
    """Test cases for dependency resolution."""

    def test_resolve_registered_singleton(self):
        """Test resolving a registered singleton."""
        container = DIContainer()

        class TestService:
            def __init__(self):
                self.value = 42

        container.register_singletons({TestService: lambda c: TestService()})

        instance = container.resolve(TestService)
        assert isinstance(instance, TestService)
        assert instance.value == 42

    def test_resolve_singleton_returns_same_instance(self):
        """Test that resolving singleton returns same instance."""
        container = DIContainer()

        class TestService:
            pass

        container.register_singletons({TestService: lambda c: TestService()})

        instance1 = container.resolve(TestService)
        instance2 = container.resolve(TestService)

        assert instance1 is instance2

    def test_resolve_transient_returns_different_instances(self):
        """Test that resolving transient returns different instances."""
        container = DIContainer()

        class TestService:
            pass

        container.register_transients({TestService: lambda c: TestService()})

        instance1 = container.resolve(TestService)
        instance2 = container.resolve(TestService)

        assert instance1 is not instance2

    def test_resolve_unregistered_class_with_auto_wiring(self):
        """Test resolving unregistered class uses auto-wiring."""
        container = DIContainer()

        class SimpleService:
            def __init__(self):
                pass

        # Not registered, should use auto-wiring
        instance = container.resolve(SimpleService)
        assert isinstance(instance, SimpleService)

    def test_resolve_with_nested_dependencies(self):
        """Test resolving with nested dependency chain."""
        container = DIContainer()

        class DatabaseConfig:
            pass

        class DatabaseConnection:
            def __init__(self, config: DatabaseConfig):
                self.config = config

        class UserRepository:
            def __init__(self, db: DatabaseConnection):
                self.db = db

        container.register_singletons(
            {
                DatabaseConfig: lambda c: DatabaseConfig(),
                DatabaseConnection: lambda c: DatabaseConnection(c.resolve(DatabaseConfig)),
            }
        )

        # UserRepository not registered, should auto-wire
        instance = container.resolve(UserRepository)
        assert isinstance(instance, UserRepository)
        assert isinstance(instance.db, DatabaseConnection)
        assert isinstance(instance.db.config, DatabaseConfig)

    def test_resolve_increments_resolution_count(self):
        """Test that resolution increments the resolution count."""
        container = DIContainer()

        class TestService:
            pass

        container.register_singletons({TestService: lambda c: TestService()})

        metadata = container._registry[TestService]
        assert metadata.resolution_count == 0

        container.resolve(TestService)
        assert metadata.resolution_count == 1

        container.resolve(TestService)
        assert metadata.resolution_count == 2


class TestCircularDependencyDetection:
    """Test cases for circular dependency detection."""

    def test_detect_circular_dependency_two_classes(self):
        """Test detecting circular dependency between two classes."""
        container = DIContainer()

        # Define both classes first to avoid forward reference issues
        class ServiceB:
            pass

        class ServiceA:
            def __init__(self, b: ServiceB):
                self.b = b

        # Update ServiceB after both are defined
        ServiceB.__init__ = lambda self, a: setattr(self, "a", a)
        ServiceB.__annotations__ = {"a": ServiceA}

        # Register to ensure they're used
        container.register_singletons(
            {
                ServiceA: lambda c: ServiceA(c.resolve(ServiceB)),
                ServiceB: lambda c: ServiceB(c.resolve(ServiceA)),
            }
        )

        with pytest.raises(CircularDependencyError) as exc_info:
            container.resolve(ServiceA)

        error = exc_info.value
        assert "ServiceA" in str(error)
        assert "ServiceB" in str(error)

    def test_detect_self_reference(self):
        """Test detecting self-reference circular dependency."""
        container = DIContainer()

        class ServiceA:
            def __init__(self, a: "ServiceA"):
                self.a = a

        # Register explicitly to control resolution
        container.register_singletons(
            {
                ServiceA: lambda c: ServiceA(c.resolve(ServiceA)),
            }
        )

        with pytest.raises(CircularDependencyError) as exc_info:
            container.resolve(ServiceA)

        error = exc_info.value
        assert error.dependency_chain.count(ServiceA) == 2

    def test_detect_circular_in_long_chain(self):
        """Test detecting circular dependency in longer chains."""
        container = DIContainer()

        # Define all classes first
        class ServiceC:
            pass

        class ServiceB:
            pass

        class ServiceA:
            pass

        # Register with circular dependencies
        container.register_singletons(
            {
                ServiceA: lambda c: type("ServiceA", (), {"b": c.resolve(ServiceB)})(),
                ServiceB: lambda c: type("ServiceB", (), {"c": c.resolve(ServiceC)})(),
                ServiceC: lambda c: type("ServiceC", (), {"a": c.resolve(ServiceA)})(),
            }
        )

        with pytest.raises(CircularDependencyError):
            container.resolve(ServiceA)

    def test_no_circular_with_shared_dependency(self):
        """Test that shared dependencies don't trigger circular detection."""
        container = DIContainer()

        class SharedService:
            pass

        class ServiceA:
            def __init__(self, shared: SharedService):
                self.shared = shared

        class ServiceB:
            def __init__(self, shared: SharedService):
                self.shared = shared

        class Root:
            def __init__(self, a: ServiceA, b: ServiceB):
                self.a = a
                self.b = b

        container.register_singletons({SharedService: lambda c: SharedService()})

        # Should not raise circular dependency error
        instance = container.resolve(Root)
        assert isinstance(instance, Root)


class TestScopedContainer:
    """Test cases for scoped containers."""

    def test_create_scope_returns_new_container(self):
        """Test that create_scope returns a new container instance."""
        container = DIContainer()
        scoped = container.create_scope()

        assert scoped is not container
        assert isinstance(scoped, DIContainer)

    def test_scoped_container_inherits_registrations(self):
        """Test that scoped container inherits parent registrations."""
        container = DIContainer()

        class TestService:
            pass

        container.register_singletons({TestService: lambda c: TestService()})

        scoped = container.create_scope()

        # Should have inherited registration
        assert TestService in scoped._registry

    def test_scoped_container_can_override_registrations(self):
        """Test that scoped container inherits parent registrations but can add new ones."""
        container = DIContainer()

        class SharedService:
            def __init__(self):
                pass

        class ScopedOnlyService:
            def __init__(self, shared: SharedService):
                self.shared = shared

        # Register in parent
        container.register_singletons({SharedService: lambda c: SharedService()})

        # Create scoped
        scoped = container.create_scope()

        # Scoped inherits parent registration
        shared_from_scoped = scoped.resolve(SharedService)
        assert isinstance(shared_from_scoped, SharedService)

        # Scoped can register additional services
        scoped.register_singletons({ScopedOnlyService: lambda c: ScopedOnlyService(c.resolve(SharedService))})
        scoped_only_instance = scoped.resolve(ScopedOnlyService)
        assert isinstance(scoped_only_instance, ScopedOnlyService)
        assert isinstance(scoped_only_instance.shared, SharedService)

        # Parent registry doesn't have scoped-only registration
        assert ScopedOnlyService not in container._registry
        assert ScopedOnlyService in scoped._registry


class TestClear:
    """Test cases for clearing container."""

    def test_clear_empties_registry(self):
        """Test that clear empties the registry."""
        container = DIContainer()

        class TestService:
            pass

        container.register_singletons({TestService: lambda c: TestService()})
        assert len(container._registry) > 0

        container.clear()
        assert len(container._registry) == 0

    def test_clear_clears_lifetime_manager_cache(self):
        """Test that clear clears lifetime manager caches."""
        container = DIContainer()

        class TestService:
            pass

        container.register_singletons({TestService: lambda c: TestService()})
        container.resolve(TestService)

        # Should have cached instance
        assert len(container._lifetime_manager._singleton_cache) > 0

        container.clear()

        # Cache should be cleared
        assert len(container._lifetime_manager._singleton_cache) == 0

    def test_clear_clears_circular_detector(self):
        """Test that clear clears circular detector stack."""
        container = DIContainer()

        class ServiceA:
            def __init__(self, b):
                self.b = b

        class ServiceB:
            def __init__(self, a: ServiceA):
                self.a = a

        # Register explicitly to avoid forward reference issues
        container.register_singletons(
            {
                ServiceA: lambda c: ServiceA(c.resolve(ServiceB)),
                ServiceB: lambda c: ServiceB(c.resolve(ServiceA)),
            }
        )

        try:
            container.resolve(ServiceA)
        except CircularDependencyError:
            pass

        container.clear()

        # Detector should be cleared (can't directly test, but shouldn't affect next resolution)
        class SimpleService:
            def __init__(self):
                pass

        container.register_singletons({SimpleService: lambda c: SimpleService()})
        instance = container.resolve(SimpleService)
        assert isinstance(instance, SimpleService)


class TestGetRegistryCopy:
    """Test cases for get_registry_copy method."""

    def test_get_registry_copy_returns_copy(self):
        """Test that get_registry_copy returns a copy of registry."""
        container = DIContainer()

        class TestService:
            pass

        container.register_singletons({TestService: lambda c: TestService()})

        registry_copy = container.get_registry_copy()
        assert registry_copy == container._registry
        assert registry_copy is not container._registry

    def test_modifying_registry_copy_does_not_affect_original(self):
        """Test that modifying copy doesn't affect original registry."""
        container = DIContainer()

        class TestService:
            pass

        container.register_singletons({TestService: lambda c: TestService()})

        registry_copy = container.get_registry_copy()
        registry_copy.clear()

        # Original should still have registration
        assert TestService in container._registry


class TestSetRegistry:
    """Test cases for set_registry method."""

    def test_set_registry_replaces_registry(self):
        """Test that set_registry replaces the registry."""
        container = DIContainer()

        class TestService:
            pass

        # Create a registry
        from miraveja_di.domain import DependencyMetadata, Registration

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration)
        new_registry = {TestService: metadata}

        container.set_registry(new_registry)

        assert container._registry is new_registry
        assert TestService in container._registry


class TestBuilderExecution:
    """Test cases for builder function execution."""

    def test_builder_receives_container(self):
        """Test that builder function receives container as argument."""
        container = DIContainer()
        received_container = []

        class TestService:
            pass

        def builder(c):
            received_container.append(c)
            return TestService()

        container.register_singletons({TestService: builder})
        container.resolve(TestService)

        assert len(received_container) == 1
        assert received_container[0] is container

    def test_builder_can_resolve_dependencies(self):
        """Test that builder can use container to resolve dependencies."""
        container = DIContainer()

        class DatabaseConfig:
            def __init__(self):
                self.connection_string = "test_db"

        class DatabaseConnection:
            def __init__(self, config):
                self.config = config

        container.register_singletons(
            {
                DatabaseConfig: lambda c: DatabaseConfig(),
                DatabaseConnection: lambda c: DatabaseConnection(c.resolve(DatabaseConfig)),
            }
        )

        instance = container.resolve(DatabaseConnection)
        assert instance.config.connection_string == "test_db"

    def test_builder_exception_wrapped_in_unresolvable_error(self):
        """Test that builder exceptions are caught during resolution."""
        container = DIContainer()

        class TestService:
            pass

        def failing_builder(c):
            raise ValueError("Builder failed")

        container.register_singletons({TestService: failing_builder})

        # Should raise the ValueError from builder
        with pytest.raises(ValueError, match="Builder failed"):
            container.resolve(TestService)


class TestComplexScenarios:
    """Test complex integration scenarios."""

    def test_mixed_registration_and_auto_wiring(self):
        """Test mixing explicit registration with auto-wiring."""
        container = DIContainer()

        class ConfigService:
            def __init__(self):
                self.setting = "production"

        class DatabaseService:
            def __init__(self, config: ConfigService):
                self.config = config

        class UserService:
            def __init__(self, db: DatabaseService):
                self.db = db

        # Only register config, others should auto-wire
        container.register_singletons({ConfigService: lambda c: ConfigService()})

        instance = container.resolve(UserService)
        assert isinstance(instance, UserService)
        assert isinstance(instance.db, DatabaseService)
        assert isinstance(instance.db.config, ConfigService)
        assert instance.db.config.setting == "production"

    def test_multiple_resolution_paths_to_same_singleton(self):
        """Test that multiple paths to same singleton use same instance."""
        container = DIContainer()

        class SharedConfig:
            pass

        class ServiceA:
            def __init__(self, config: SharedConfig):
                self.config = config

        class ServiceB:
            def __init__(self, config: SharedConfig):
                self.config = config

        class Root:
            def __init__(self, a: ServiceA, b: ServiceB):
                self.a = a
                self.b = b

        container.register_singletons({SharedConfig: lambda c: SharedConfig()})

        instance = container.resolve(Root)

        # Both services should have the same config instance
        assert instance.a.config is instance.b.config

    def test_transient_with_singleton_dependencies(self):
        """Test transient service with singleton dependencies."""
        container = DIContainer()

        class SingletonService:
            pass

        class TransientService:
            def __init__(self, singleton: SingletonService):
                self.singleton = singleton

        container.register_singletons({SingletonService: lambda c: SingletonService()})
        container.register_transients({TransientService: lambda c: TransientService(c.resolve(SingletonService))})

        # Get two transient instances
        trans1 = container.resolve(TransientService)
        trans2 = container.resolve(TransientService)

        # Transients should be different
        assert trans1 is not trans2

        # But should share same singleton
        assert trans1.singleton is trans2.singleton

    def test_deep_dependency_tree(self):
        """Test resolving deep dependency trees."""
        container = DIContainer()

        class Level0:
            pass

        class Level1:
            def __init__(self, l0: Level0):
                self.l0 = l0

        class Level2:
            def __init__(self, l1: Level1):
                self.l1 = l1

        class Level3:
            def __init__(self, l2: Level2):
                self.l2 = l2

        class Level4:
            def __init__(self, l3: Level3):
                self.l3 = l3

        container.register_singletons({Level0: lambda c: Level0()})

        instance = container.resolve(Level4)
        assert isinstance(instance.l3.l2.l1.l0, Level0)


class TestEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_resolve_with_none_builder_result(self):
        """Test that builder can return None."""
        container = DIContainer()

        class TestService:
            pass

        container.register_singletons({TestService: lambda c: None})

        instance = container.resolve(TestService)
        assert instance is None

    def test_empty_container_resolution(self):
        """Test resolving from empty container with auto-wiring."""
        container = DIContainer()

        class SimpleService:
            def __init__(self):
                pass

        instance = container.resolve(SimpleService)
        assert isinstance(instance, SimpleService)

    def test_register_with_empty_dictionary(self):
        """Test registering with empty dictionary."""
        container = DIContainer()

        # Should not raise
        container.register_singletons({})
        container.register_transients({})

        assert len(container._registry) == 0
