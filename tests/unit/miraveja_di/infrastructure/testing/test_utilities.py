"""Unit tests for testing utilities."""

import pytest

from miraveja_di.application.container import DIContainer
from miraveja_di.domain.enums import Lifetime
from miraveja_di.domain.exceptions import UnresolvableError
from miraveja_di.infrastructure.testing.utilities import (
    MockScope,
    TestContainer,
    create_mock_container,
)


class TestTestContainerInitialization:
    """Test cases for TestContainer initialization."""

    def test_test_container_initialization_without_parent(self):
        """Test TestContainer can be initialized without parent container."""
        test_container = TestContainer()

        assert test_container is not None
        assert isinstance(test_container, DIContainer)
        assert test_container._parent_container is None

    def test_test_container_initialization_with_parent(self):
        """Test TestContainer inherits from parent container."""
        parent = DIContainer()

        class TestService:
            def __init__(self):
                pass

        parent.register_singletons({TestService: lambda c: TestService()})

        test_container = TestContainer(parent)

        assert test_container._parent_container is parent
        # Should inherit parent's registrations
        instance = test_container.resolve(TestService)
        assert isinstance(instance, TestService)

    def test_test_container_has_empty_overrides_initially(self):
        """Test TestContainer starts with no overrides."""
        test_container = TestContainer()

        assert len(test_container._overrides) == 0


class TestMockSingleton:
    """Test cases for mock_singleton method."""

    def test_mock_singleton_replaces_dependency(self):
        """Test that mock_singleton replaces a dependency."""
        parent = DIContainer()

        class RealService:
            def __init__(self):
                self.is_real = True

        class MockService:
            def __init__(self):
                self.is_real = False

        parent.register_singletons({RealService: lambda c: RealService()})

        test_container = TestContainer(parent)
        mock_instance = MockService()
        test_container.mock_singleton(RealService, mock_instance)

        resolved = test_container.resolve(RealService)

        assert resolved is mock_instance
        assert not resolved.is_real

    def test_mock_singleton_returns_same_instance(self):
        """Test that mocked singleton returns same instance."""
        test_container = TestContainer()

        class TestService:
            def __init__(self):
                pass

        mock_instance = TestService()
        test_container.mock_singleton(TestService, mock_instance)

        resolved1 = test_container.resolve(TestService)
        resolved2 = test_container.resolve(TestService)

        assert resolved1 is mock_instance
        assert resolved2 is mock_instance
        assert resolved1 is resolved2

    def test_mock_singleton_adds_to_overrides(self):
        """Test that mock_singleton tracks the override."""
        test_container = TestContainer()

        class TestService:
            def __init__(self):
                pass

        mock_instance = TestService()
        test_container.mock_singleton(TestService, mock_instance)

        assert TestService in test_container._overrides
        assert test_container._overrides[TestService] is mock_instance

    def test_mock_singleton_used_by_dependent_services(self):
        """Test that mocked singleton is used by dependent services."""
        parent = DIContainer()

        class DatabaseConnection:
            def __init__(self):
                self.connection_string = "real_db"

        class UserService:
            def __init__(self, db: DatabaseConnection):
                self.db = db

        parent.register_singletons({DatabaseConnection: lambda c: DatabaseConnection()})

        test_container = TestContainer(parent)

        # Mock the database
        mock_db = DatabaseConnection()
        mock_db.connection_string = "mock_db"
        test_container.mock_singleton(DatabaseConnection, mock_db)

        # Resolve dependent service
        user_service = test_container.resolve(UserService)

        assert user_service.db is mock_db
        assert user_service.db.connection_string == "mock_db"

    def test_mock_singleton_multiple_mocks(self):
        """Test mocking multiple different singletons."""
        test_container = TestContainer()

        class Service1:
            def __init__(self):
                pass

        class Service2:
            def __init__(self):
                pass

        mock1 = Service1()
        mock2 = Service2()

        test_container.mock_singleton(Service1, mock1)
        test_container.mock_singleton(Service2, mock2)

        resolved1 = test_container.resolve(Service1)
        resolved2 = test_container.resolve(Service2)

        assert resolved1 is mock1
        assert resolved2 is mock2

    def test_mock_singleton_with_none_value(self):
        """Test that mock_singleton can mock with None value."""
        test_container = TestContainer()

        class OptionalService:
            pass

        test_container.mock_singleton(OptionalService, None)

        resolved = test_container.resolve(OptionalService)

        assert resolved is None


class TestMockTransient:
    """Test cases for mock_transient method."""

    def test_mock_transient_creates_new_instances(self):
        """Test that mock_transient creates new instances each time."""
        test_container = TestContainer()

        class TransientService:
            def __init__(self):
                pass

        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return TransientService()

        test_container.mock_transient(TransientService, factory)

        instance1 = test_container.resolve(TransientService)
        instance2 = test_container.resolve(TransientService)

        assert instance1 is not instance2
        assert call_count == 2

    def test_mock_transient_uses_factory_function(self):
        """Test that mock_transient calls factory function."""
        test_container = TestContainer()

        class CounterService:
            counter = 0

            def __init__(self):
                CounterService.counter += 1
                self.instance_number = CounterService.counter

        def factory():
            return CounterService()

        test_container.mock_transient(CounterService, factory)

        instance1 = test_container.resolve(CounterService)
        instance2 = test_container.resolve(CounterService)

        assert instance1.instance_number == 1
        assert instance2.instance_number == 2

    def test_mock_transient_with_parameterized_factory(self):
        """Test mock_transient with factory that has different behaviors."""
        test_container = TestContainer()

        class ConfigurableService:
            def __init__(self, value):
                self.value = value

        values = ["first", "second", "third"]
        index = 0

        def factory():
            nonlocal index
            val = values[index % len(values)]
            index += 1
            return ConfigurableService(val)

        test_container.mock_transient(ConfigurableService, factory)

        instance1 = test_container.resolve(ConfigurableService)
        instance2 = test_container.resolve(ConfigurableService)
        instance3 = test_container.resolve(ConfigurableService)

        assert instance1.value == "first"
        assert instance2.value == "second"
        assert instance3.value == "third"


class TestOverrideRegistration:
    """Test cases for override_registration method."""

    def test_override_registration_with_singleton(self):
        """Test overriding a registration with singleton lifetime."""
        parent = DIContainer()

        class OriginalService:
            def __init__(self):
                self.name = "original"

        class OverrideService:
            def __init__(self):
                self.name = "override"

        parent.register_singletons({OriginalService: lambda c: OriginalService()})

        test_container = TestContainer(parent)
        test_container.override_registration(OriginalService, lambda c: OverrideService(), Lifetime.SINGLETON)

        resolved = test_container.resolve(OriginalService)

        # Type is still OriginalService, but instance is OverrideService
        assert resolved.name == "override"

    def test_override_registration_with_transient(self):
        """Test overriding a registration with transient lifetime."""
        test_container = TestContainer()

        class TestService:
            def __init__(self):
                pass

        test_container.override_registration(TestService, lambda c: TestService(), Lifetime.TRANSIENT)

        instance1 = test_container.resolve(TestService)
        instance2 = test_container.resolve(TestService)

        assert instance1 is not instance2

    def test_override_registration_with_invalid_lifetime(self):
        """Test that override_registration raises error for invalid lifetime."""
        test_container = TestContainer()

        class TestService:
            def __init__(self):
                pass

        with pytest.raises(ValueError) as exc_info:
            test_container.override_registration(TestService, lambda c: TestService(), Lifetime.SCOPED)

        assert "Unsupported lifetime" in str(exc_info.value)

    def test_override_registration_replaces_existing(self):
        """Test that override_registration replaces existing registration."""
        parent = DIContainer()

        class TestService:
            def __init__(self):
                self.counter = 0

        counter = 0

        def original_builder(c):
            return TestService()

        def override_builder(c):
            nonlocal counter
            counter += 1
            service = TestService()
            service.counter = counter
            return service

        parent.register_singletons({TestService: original_builder})

        test_container = TestContainer(parent)
        test_container.override_registration(TestService, override_builder, Lifetime.SINGLETON)

        instance = test_container.resolve(TestService)

        assert instance.counter == 1


class TestResetOverrides:
    """Test cases for reset_overrides method."""

    def test_reset_overrides_clears_overrides_dict(self):
        """Test that reset_overrides clears the overrides dictionary."""
        test_container = TestContainer()

        class TestService:
            def __init__(self):
                pass

        mock_instance = TestService()
        test_container.mock_singleton(TestService, mock_instance)

        assert len(test_container._overrides) > 0

        test_container.reset_overrides()

        assert len(test_container._overrides) == 0

    def test_reset_overrides_restores_parent_registrations(self):
        """Test that reset_overrides restores parent registrations."""
        parent = DIContainer()

        class TestService:
            def __init__(self):
                self.source = "parent"

        parent.register_singletons({TestService: lambda c: TestService()})

        test_container = TestContainer(parent)

        # Override with mock
        mock_service = TestService()
        mock_service.source = "mock"
        test_container.mock_singleton(TestService, mock_service)

        # Verify override
        resolved = test_container.resolve(TestService)
        assert resolved.source == "mock"

        # Reset overrides
        test_container.reset_overrides()

        # Should get parent's registration again
        resolved_after_reset = test_container.resolve(TestService)
        assert resolved_after_reset.source == "parent"

    def test_reset_overrides_without_parent(self):
        """Test that reset_overrides works without parent container."""
        test_container = TestContainer()

        class TestService:
            def __init__(self):
                pass

        test_container.mock_singleton(TestService, TestService())

        test_container.reset_overrides()

        # Should clear registry
        assert len(test_container._overrides) == 0

    def test_reset_overrides_multiple_times(self):
        """Test that reset_overrides can be called multiple times."""
        test_container = TestContainer()

        class TestService:
            def __init__(self):
                pass

        test_container.mock_singleton(TestService, TestService())
        test_container.reset_overrides()
        test_container.reset_overrides()  # Should not raise

        assert len(test_container._overrides) == 0


class TestTestContainerContextManager:
    """Test cases for TestContainer context manager."""

    def test_context_manager_enter_returns_self(self):
        """Test that __enter__ returns the container itself."""
        test_container = TestContainer()

        with test_container as container:
            assert container is test_container

    def test_context_manager_exit_resets_overrides(self):
        """Test that __exit__ resets overrides."""
        parent = DIContainer()

        class TestService:
            def __init__(self):
                pass

        parent.register_singletons({TestService: lambda c: TestService()})

        test_container = TestContainer(parent)

        with test_container as container:
            container.mock_singleton(TestService, TestService())
            assert len(container._overrides) > 0

        # After exiting, overrides should be cleared
        assert len(test_container._overrides) == 0

    def test_context_manager_exit_clears_container(self):
        """Test that __exit__ clears the container."""
        test_container = TestContainer()

        class TestService:
            def __init__(self):
                pass

        with test_container as container:
            container.register_singletons({TestService: lambda c: TestService()})

        # Container should be cleared
        # Registry is cleared but auto-wiring still works
        assert len(test_container._registry) == 0

    def test_context_manager_exit_returns_false(self):
        """Test that __exit__ returns False (doesn't suppress exceptions)."""
        test_container = TestContainer()

        result = test_container.__exit__(None, None, None)

        assert result is False

    def test_context_manager_with_exception(self):
        """Test that context manager cleans up even with exception."""
        test_container = TestContainer()

        class TestService:
            def __init__(self):
                pass

        try:
            with test_container as container:
                container.mock_singleton(TestService, TestService())
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should still clean up
        assert len(test_container._overrides) == 0


class TestCreateMockContainer:
    """Test cases for create_mock_container function."""

    def test_create_mock_container_with_no_mocks(self):
        """Test creating mock container with no mocks."""
        container = create_mock_container()

        assert isinstance(container, TestContainer)
        assert len(container._overrides) == 0

    def test_create_mock_container_with_single_mock(self):
        """Test creating mock container with single mock."""

        class TestService:
            def __init__(self):
                self.value = "test"

        mock_service = TestService()

        container = create_mock_container((TestService, mock_service))

        resolved = container.resolve(TestService)
        assert resolved is mock_service

    def test_create_mock_container_with_multiple_mocks(self):
        """Test creating mock container with multiple mocks."""

        class Service1:
            def __init__(self):
                pass

        class Service2:
            def __init__(self):
                pass

        class Service3:
            def __init__(self):
                pass

        mock1 = Service1()
        mock2 = Service2()
        mock3 = Service3()

        container = create_mock_container((Service1, mock1), (Service2, mock2), (Service3, mock3))

        assert container.resolve(Service1) is mock1
        assert container.resolve(Service2) is mock2
        assert container.resolve(Service3) is mock3

    def test_create_mock_container_mocks_are_singletons(self):
        """Test that mocks created are singletons."""

        class TestService:
            def __init__(self):
                pass

        mock_service = TestService()

        container = create_mock_container((TestService, mock_service))

        resolved1 = container.resolve(TestService)
        resolved2 = container.resolve(TestService)

        assert resolved1 is mock_service
        assert resolved2 is mock_service
        assert resolved1 is resolved2

    def test_create_mock_container_with_nested_dependencies(self):
        """Test mock container with mocked dependencies used by other services."""

        class DatabaseConnection:
            def __init__(self):
                self.connected = True

        class UserRepository:
            def __init__(self, db: DatabaseConnection):
                self.db = db

        mock_db = DatabaseConnection()
        mock_db.connected = False

        container = create_mock_container((DatabaseConnection, mock_db))

        # UserRepository should use mocked DB
        repo = container.resolve(UserRepository)
        assert repo.db is mock_db
        assert not repo.db.connected


class TestMockScope:
    """Test cases for MockScope context manager."""

    def test_mock_scope_initialization(self):
        """Test MockScope initialization."""
        parent = DIContainer()
        mock_scope = MockScope(parent)

        assert mock_scope._parent_container is parent
        assert mock_scope._scoped_container is None

    def test_mock_scope_enter_creates_scoped_container(self):
        """Test that __enter__ creates a scoped container."""
        parent = DIContainer()

        class TestService:
            def __init__(self):
                pass

        parent.register_singletons({TestService: lambda c: TestService()})

        mock_scope = MockScope(parent)

        with mock_scope as scoped:
            assert scoped is not None
            assert scoped is not parent
            # Should be able to resolve from scoped container
            instance = scoped.resolve(TestService)
            assert isinstance(instance, TestService)

    def test_mock_scope_exit_cleans_up(self):
        """Test that __exit__ cleans up the scoped container."""
        parent = DIContainer()
        mock_scope = MockScope(parent)

        with mock_scope as scoped:
            # Scoped container exists during context
            assert mock_scope._scoped_container is not None

        # After exiting, scoped container should be None
        assert mock_scope._scoped_container is None

    def test_mock_scope_exit_returns_false(self):
        """Test that __exit__ returns False."""
        parent = DIContainer()
        mock_scope = MockScope(parent)

        result = mock_scope.__exit__(None, None, None)

        assert result is False

    def test_mock_scope_cleans_up_on_exception(self):
        """Test that MockScope cleans up even when exception occurs."""
        parent = DIContainer()
        mock_scope = MockScope(parent)

        try:
            with mock_scope as scoped:
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should still clean up
        assert mock_scope._scoped_container is None

    def test_mock_scope_isolates_scoped_instances(self):
        """Test that MockScope provides isolated scoped instances."""
        parent = DIContainer()

        class ScopedService:
            def __init__(self):
                pass

        parent.register_singletons({ScopedService: lambda c: ScopedService()})

        # Create two separate scopes
        with MockScope(parent) as scope1:
            instance1 = scope1.resolve(ScopedService)

        with MockScope(parent) as scope2:
            instance2 = scope2.resolve(ScopedService)

        # Different scopes should have different instances
        assert instance1 is not instance2

    def test_mock_scope_shares_instances_within_scope(self):
        """Test that instances are shared within the same scope."""
        parent = DIContainer()

        class ScopedService:
            def __init__(self):
                pass

        parent.register_singletons({ScopedService: lambda c: ScopedService()})

        with MockScope(parent) as scoped:
            instance1 = scoped.resolve(ScopedService)
            instance2 = scoped.resolve(ScopedService)

            # Same scope should return same instance for singletons
            assert instance1 is instance2


class TestEdgeCases:
    """Test edge cases for testing utilities."""

    def test_test_container_with_cleared_parent(self):
        """Test TestContainer when parent is cleared."""
        parent = DIContainer()

        class TestService:
            def __init__(self):
                pass

        parent.register_singletons({TestService: lambda c: TestService()})

        test_container = TestContainer(parent)

        # Clear parent
        parent.clear()

        # TestContainer should still have inherited registrations
        instance = test_container.resolve(TestService)
        assert isinstance(instance, TestService)

    def test_multiple_test_containers_from_same_parent(self):
        """Test creating multiple TestContainers from same parent."""
        parent = DIContainer()

        class TestService:
            def __init__(self):
                pass

        parent.register_singletons({TestService: lambda c: TestService()})

        test1 = TestContainer(parent)
        test2 = TestContainer(parent)

        # Both should resolve independently
        instance1 = test1.resolve(TestService)
        instance2 = test2.resolve(TestService)

        assert isinstance(instance1, TestService)
        assert isinstance(instance2, TestService)

    def test_test_container_mock_with_auto_wired_service(self):
        """Test mocking a service that was auto-wired."""
        test_container = TestContainer()

        class AutoWiredService:
            def __init__(self):
                self.auto_wired = True

        # First resolve auto-wires it
        auto_instance = test_container.resolve(AutoWiredService)
        assert auto_instance.auto_wired

        # Now mock it
        mock_service = AutoWiredService()
        mock_service.auto_wired = False
        test_container.mock_singleton(AutoWiredService, mock_service)

        # Should get mock
        resolved = test_container.resolve(AutoWiredService)
        assert not resolved.auto_wired

    def test_create_mock_container_with_none_mock(self):
        """Test create_mock_container can have None as mock value."""

        class OptionalService:
            pass

        container = create_mock_container((OptionalService, None))

        resolved = container.resolve(OptionalService)
        assert resolved is None

    def test_mock_scope_with_empty_parent(self):
        """Test MockScope with empty parent container."""
        parent = DIContainer()

        with MockScope(parent) as scoped:
            # Should be able to auto-wire even with empty parent
            class AutoService:
                def __init__(self):
                    pass

            instance = scoped.resolve(AutoService)
            assert isinstance(instance, AutoService)
