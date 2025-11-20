"""Unit tests for DependencyResolver."""

import pytest

from miraveja_di.application.resolver import DependencyResolver
from miraveja_di.domain import IContainer, IResolver, UnresolvableError


class MockContainer(IContainer):
    """Mock container for testing resolver."""

    def __init__(self):
        self.resolved = {}
        self.resolver: IResolver | None = None  # For nested resolution support

    def register_singletons(self, dependencies):
        pass

    def register_transients(self, dependencies):
        pass

    def resolve(self, dependency_type):
        if dependency_type in self.resolved:
            return self.resolved[dependency_type]
        # Auto-wire for testing - use resolver if set for recursive resolution
        if self.resolver:
            return self.resolver.resolve_dependencies(dependency_type, self)
        return dependency_type()

    def create_scope(self):
        return self

    def clear(self):
        pass

    def get_registry_copy(self):
        return {}


class TestResolverInitialization:
    """Test cases for DependencyResolver initialization."""

    def test_resolver_initialization(self):
        """Test that resolver initializes correctly."""
        resolver = DependencyResolver()
        assert resolver is not None

    def test_resolver_implements_interface(self):
        """Test that DependencyResolver implements IResolver."""
        resolver = DependencyResolver()
        assert isinstance(resolver, IResolver)


class TestBasicResolution:
    """Test cases for basic dependency resolution."""

    def test_resolve_class_with_no_dependencies(self):
        """Test resolving class with no constructor parameters."""
        resolver = DependencyResolver()
        container = MockContainer()

        class SimpleService:
            def __init__(self):
                pass

        instance = resolver.resolve_dependencies(SimpleService, container)
        assert isinstance(instance, SimpleService)

    def test_resolve_class_with_single_dependency(self):
        """Test resolving class with one dependency."""
        resolver = DependencyResolver()
        container = MockContainer()

        class DatabaseService:
            pass

        class UserService:
            def __init__(self, db: DatabaseService):
                self.db = db

        instance = resolver.resolve_dependencies(UserService, container)
        assert isinstance(instance, UserService)
        assert isinstance(instance.db, DatabaseService)

    def test_resolve_class_with_multiple_dependencies(self):
        """Test resolving class with multiple dependencies."""
        resolver = DependencyResolver()
        container = MockContainer()

        class DatabaseService:
            pass

        class LoggerService:
            pass

        class CacheService:
            pass

        class ComplexService:
            def __init__(self, db: DatabaseService, logger: LoggerService, cache: CacheService):
                self.db = db
                self.logger = logger
                self.cache = cache

        instance = resolver.resolve_dependencies(ComplexService, container)
        assert isinstance(instance, ComplexService)
        assert isinstance(instance.db, DatabaseService)
        assert isinstance(instance.logger, LoggerService)
        assert isinstance(instance.cache, CacheService)

    def test_resolve_nested_dependencies(self):
        """Test resolving classes with nested dependencies."""
        resolver = DependencyResolver()
        container = MockContainer()
        container.resolver = resolver  # Enable recursive resolution

        class ConfigService:
            def __init__(self):
                pass

        class DatabaseService:
            def __init__(self, config: ConfigService):
                self.config = config

        class UserService:
            def __init__(self, db: DatabaseService):
                self.db = db

        instance = resolver.resolve_dependencies(UserService, container)
        assert isinstance(instance, UserService)
        assert isinstance(instance.db, DatabaseService)
        assert isinstance(instance.db.config, ConfigService)


class TestTypeHintHandling:
    """Test cases for type hint handling."""

    def test_resolve_with_missing_type_hint_and_no_default(self):
        """Test that missing type hint without default raises error."""
        resolver = DependencyResolver()
        container = MockContainer()

        class ServiceWithoutHint:
            def __init__(self, dependency):
                self.dependency = dependency

        with pytest.raises(UnresolvableError) as exc_info:
            resolver.resolve_dependencies(ServiceWithoutHint, container)

        error = exc_info.value
        assert error.cls == ServiceWithoutHint
        assert "lacks type hint" in str(error)
        assert "dependency" in str(error)

    def test_resolve_with_missing_type_hint_but_has_default(self):
        """Test that missing type hint with default value is skipped."""
        resolver = DependencyResolver()
        container = MockContainer()

        class ServiceWithDefault:
            def __init__(self, required: str, optional="default"):
                self.required = required
                self.optional = optional

        container.resolved[str] = "test_value"

        instance = resolver.resolve_dependencies(ServiceWithDefault, container)
        assert instance.required == "test_value"
        assert instance.optional == "default"

    def test_resolve_with_default_values(self):
        """Test that parameters with defaults are not required."""
        resolver = DependencyResolver()
        container = MockContainer()

        class DatabaseService:
            pass

        class ServiceWithDefaults:
            def __init__(self, db: DatabaseService, timeout: int = 30, retry: bool = True):
                self.db = db
                self.timeout = timeout
                self.retry = retry

        instance = resolver.resolve_dependencies(ServiceWithDefaults, container)
        assert isinstance(instance.db, DatabaseService)
        assert instance.timeout == 30
        assert instance.retry is True

    def test_resolve_skips_self_parameter(self):
        """Test that 'self' parameter is correctly skipped."""
        resolver = DependencyResolver()
        container = MockContainer()

        class TestService:
            def __init__(self):
                pass

        # Should not try to resolve 'self'
        instance = resolver.resolve_dependencies(TestService, container)
        assert isinstance(instance, TestService)


class TestErrorHandling:
    """Test cases for error scenarios."""

    def test_unresolvable_dependency_raises_error(self):
        """Test that unresolvable dependency raises UnresolvableError."""
        resolver = DependencyResolver()

        class FailingContainer(IContainer):
            def register_singletons(self, dependencies):
                pass

            def register_transients(self, dependencies):
                pass

            def resolve(self, dependency_type):
                raise ValueError("Cannot resolve")

            def create_scope(self):
                return self

            def clear(self):
                pass

            def get_registry_copy(self):
                return {}

        container = FailingContainer()

        class DatabaseService:
            pass

        class UserService:
            def __init__(self, db: DatabaseService):
                self.db = db

        with pytest.raises(UnresolvableError) as exc_info:
            resolver.resolve_dependencies(UserService, container)

        error = exc_info.value
        assert error.cls == UserService
        assert "Failed to resolve dependency" in str(error)

    def test_exception_during_instantiation(self):
        """Test that exceptions during instantiation are wrapped."""
        resolver = DependencyResolver()
        container = MockContainer()

        class DatabaseService:
            pass

        class FailingService:
            def __init__(self, db: DatabaseService):
                raise RuntimeError("Construction failed")

        with pytest.raises(UnresolvableError) as exc_info:
            resolver.resolve_dependencies(FailingService, container)

        error = exc_info.value
        assert error.cls == FailingService

    def test_multiple_missing_type_hints(self):
        """Test error with multiple missing type hints."""
        resolver = DependencyResolver()
        container = MockContainer()

        class ServiceWithMultipleMissing:
            def __init__(self, dep1, dep2):
                pass

        # Should raise for first missing hint
        with pytest.raises(UnresolvableError) as exc_info:
            resolver.resolve_dependencies(ServiceWithMultipleMissing, container)

        error = exc_info.value
        assert "dep1" in str(error) or "dep2" in str(error)


class TestEdgeCases:
    """Test edge cases for DependencyResolver."""

    def test_resolve_class_with_kwargs(self):
        """Test resolving class that accepts kwargs."""
        resolver = DependencyResolver()
        container = MockContainer()

        class FlexibleService:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        # Should work with empty kwargs
        instance = resolver.resolve_dependencies(FlexibleService, container)
        assert isinstance(instance, FlexibleService)
        assert instance.kwargs == {}

    def test_resolve_class_with_args(self):
        """Test resolving class with *args."""
        resolver = DependencyResolver()
        container = MockContainer()

        class ArgsService:
            def __init__(self, *args):
                self.args = args

        # Should work with empty args
        instance = resolver.resolve_dependencies(ArgsService, container)
        assert isinstance(instance, ArgsService)
        assert instance.args == ()

    def test_resolve_class_with_class_method_constructor(self):
        """Test resolving class works with regular __init__."""
        resolver = DependencyResolver()
        container = MockContainer()

        class ServiceWithInit:
            def __init__(self):
                self.initialized = True

        instance = resolver.resolve_dependencies(ServiceWithInit, container)
        assert instance.initialized is True

    def test_resolve_builtin_types(self):
        """Test resolving with builtin type hints."""
        resolver = DependencyResolver()
        container = MockContainer()

        # Setup container to resolve built-in types
        container.resolved[str] = "test_string"
        container.resolved[int] = 42

        class ServiceWithBuiltins:
            def __init__(self, name: str, count: int):
                self.name = name
                self.count = count

        instance = resolver.resolve_dependencies(ServiceWithBuiltins, container)
        assert instance.name == "test_string"
        assert instance.count == 42

    def test_resolve_same_dependency_multiple_times(self):
        """Test resolving same dependency type multiple times."""
        resolver = DependencyResolver()
        container = MockContainer()

        class SharedService:
            pass

        class ServiceWithDuplicates:
            def __init__(self, dep1: SharedService, dep2: SharedService):
                self.dep1 = dep1
                self.dep2 = dep2

        instance = resolver.resolve_dependencies(ServiceWithDuplicates, container)

        # Both should be resolved (may or may not be same instance depending on lifetime)
        assert isinstance(instance.dep1, SharedService)
        assert isinstance(instance.dep2, SharedService)


class TestComplexScenarios:
    """Test complex dependency resolution scenarios."""

    def test_deep_dependency_chain(self):
        """Test resolving deep dependency chains."""
        resolver = DependencyResolver()
        container = MockContainer()
        container.resolver = resolver  # Enable recursive resolution

        class Level1:
            def __init__(self):
                pass

        class Level2:
            def __init__(self, l1: Level1):
                self.l1 = l1

        class Level3:
            def __init__(self, l2: Level2):
                self.l2 = l2

        class Level4:
            def __init__(self, l3: Level3):
                self.l3 = l3

        instance = resolver.resolve_dependencies(Level4, container)
        assert isinstance(instance, Level4)
        assert isinstance(instance.l3, Level3)
        assert isinstance(instance.l3.l2, Level2)
        assert isinstance(instance.l3.l2.l1, Level1)

    def test_multiple_dependency_branches(self):
        """Test resolving with multiple dependency branches."""
        resolver = DependencyResolver()
        container = MockContainer()
        container.resolver = resolver  # Enable recursive resolution

        class SharedBase:
            def __init__(self):
                pass

        class BranchA:
            def __init__(self, base: SharedBase):
                self.base = base

        class BranchB:
            def __init__(self, base: SharedBase):
                self.base = base

        class Root:
            def __init__(self, a: BranchA, b: BranchB):
                self.a = a
                self.b = b

        instance = resolver.resolve_dependencies(Root, container)
        assert isinstance(instance.a, BranchA)
        assert isinstance(instance.b, BranchB)
        assert isinstance(instance.a.base, SharedBase)
        assert isinstance(instance.b.base, SharedBase)
