"""Integration tests for edge cases and unusual scenarios."""

from abc import ABC, abstractmethod
from typing import Optional

import pytest

from miraveja_di import DIContainer
from miraveja_di.domain import CircularDependencyError, LifetimeError, UnresolvableError


class TestMissingTypeHints:
    """Test scenarios with missing or incomplete type hints."""

    def test_class_without_type_hints_requires_registration(self):
        """Test that classes without type hints require explicit registration."""
        container = DIContainer()

        class NoHintsService:
            def __init__(self, dependency):  # No type hint
                self.dependency = dependency

        class RequiredDependency:
            pass

        # Should require explicit registration of both
        container.register_singletons(
            {
                RequiredDependency: lambda c: RequiredDependency(),
                NoHintsService: lambda c: NoHintsService(c.resolve(RequiredDependency)),
            }
        )

        service = container.resolve(NoHintsService)
        assert isinstance(service.dependency, RequiredDependency)

    def test_mixed_type_hints(self):
        """Test class with some parameters having type hints and others not."""
        container = DIContainer()

        class TypedService:
            pass

        class MixedService:
            def __init__(self, typed: TypedService, untyped):
                self.typed = typed
                self.untyped = untyped

        # Register with explicit builder
        container.register_singletons({TypedService: lambda c: TypedService()})
        container.register_singletons({MixedService: lambda c: MixedService(c.resolve(TypedService), "manual_value")})

        service = container.resolve(MixedService)
        assert isinstance(service.typed, TypedService)
        assert service.untyped == "manual_value"

    def test_no_constructor_class(self):
        """Test class without __init__ method."""
        container = DIContainer()

        class SimpleClass:
            value = 42

        # Should work without explicit registration (auto-wire empty constructor)
        instance = container.resolve(SimpleClass)
        assert instance.value == 42


class TestAbstractClasses:
    """Test scenarios with abstract base classes."""

    def test_cannot_resolve_abstract_class_directly(self):
        """Test that resolving abstract class without registration fails."""
        container = DIContainer()

        class AbstractService(ABC):
            @abstractmethod
            def do_work(self):
                pass

        # Should fail to resolve abstract class without registration
        with pytest.raises(UnresolvableError):
            container.resolve(AbstractService)

    def test_abstract_class_with_concrete_implementation(self):
        """Test mapping abstract class to concrete implementation."""
        container = DIContainer()

        class IRepository(ABC):
            @abstractmethod
            def get_data(self):
                pass

        class ConcreteRepository(IRepository):
            def get_data(self):
                return "data"

        class Service:
            def __init__(self, repo: IRepository):
                self.repo = repo

        # Register interface with concrete implementation
        container.register_singletons({IRepository: lambda c: ConcreteRepository()})

        service = container.resolve(Service)
        assert isinstance(service.repo, ConcreteRepository)
        assert service.repo.get_data() == "data"

    def test_multiple_implementations_of_same_interface(self):
        """Test that only one implementation can be registered per interface."""
        container = DIContainer()

        class IService(ABC):
            @abstractmethod
            def execute(self):
                pass

        class Implementation1(IService):
            def execute(self):
                return "impl1"

        class Implementation2(IService):
            def execute(self):
                return "impl2"

        # Register first implementation
        container.register_singletons({IService: lambda c: Implementation1()})

        # Attempting to register second implementation with different lifetime should fail
        with pytest.raises(LifetimeError):
            container.register_transients({IService: lambda c: Implementation2()})

        # Registering with same lifetime skips (first registration wins)
        container.register_singletons({IService: lambda c: Implementation2()})
        service = container.resolve(IService)
        # Should still be Implementation1
        assert isinstance(service, Implementation1)


class TestOptionalDependencies:
    """Test scenarios with optional dependencies."""

    def test_optional_dependency_with_default_none(self):
        """Test service with optional dependency defaulting to None."""
        container = DIContainer()

        class OptionalService:
            pass

        class ServiceWithOptional:
            def __init__(self, optional: Optional[OptionalService] = None):
                self.optional = optional

        # Register without the optional dependency
        # Auto-wiring should use default value
        container.register_singletons({ServiceWithOptional: lambda c: ServiceWithOptional()})

        service = container.resolve(ServiceWithOptional)
        assert service.optional is None

    def test_optional_dependency_when_registered(self):
        """Test service with optional dependency when it is registered."""
        container = DIContainer()

        class OptionalService:
            pass

        class ServiceWithOptional:
            def __init__(self, optional: Optional[OptionalService] = None):
                self.optional = optional

        # Register both
        container.register_singletons({OptionalService: lambda c: OptionalService()})
        container.register_singletons({ServiceWithOptional: lambda c: ServiceWithOptional(c.resolve(OptionalService))})

        service = container.resolve(ServiceWithOptional)
        assert isinstance(service.optional, OptionalService)


class TestBuiltInTypes:
    """Test scenarios with built-in Python types."""

    def test_primitive_type_dependencies(self):
        """Test service depending on primitive types requires explicit registration."""
        container = DIContainer()

        class ConfigService:
            def __init__(self, host: str, port: int):
                self.host = host
                self.port = port

        # Primitive types must be explicitly provided
        container.register_singletons({ConfigService: lambda c: ConfigService("localhost", 8080)})

        service = container.resolve(ConfigService)
        assert service.host == "localhost"
        assert service.port == 8080

    def test_list_dict_dependencies(self):
        """Test service depending on list or dict types."""
        container = DIContainer()

        class DataService:
            def __init__(self, items: list, config: dict):
                self.items = items
                self.config = config

        # Collections must be explicitly provided
        container.register_singletons({DataService: lambda c: DataService([1, 2, 3], {"key": "value"})})

        service = container.resolve(DataService)
        assert service.items == [1, 2, 3]
        assert service.config == {"key": "value"}


class TestForwardReferences:
    """Test scenarios with forward references."""

    def test_forward_reference_in_type_hint(self):
        """Test class with forward reference in type hint."""
        container = DIContainer()

        class ServiceA:
            def __init__(self, b: "ServiceB"):
                self.b = b

        class ServiceB:
            def __init__(self):
                self.name = "ServiceB"

        # Register both
        container.register_singletons({ServiceB: lambda c: ServiceB()})
        container.register_singletons({ServiceA: lambda c: ServiceA(c.resolve(ServiceB))})

        service_a = container.resolve(ServiceA)
        assert isinstance(service_a.b, ServiceB)
        assert service_a.b.name == "ServiceB"

    def test_mutual_forward_references_detects_circular(self):
        """Test that mutual forward references with explicit registration work."""
        container = DIContainer()

        class ServiceX:
            def __init__(self, y: "ServiceY"):
                self.y = y

        class ServiceY:
            def __init__(self, x: ServiceX):
                self.x = x

        # Forward references in local scope can't be resolved by get_type_hints
        # Must use explicit registration with circular detection
        container.register_singletons(
            {
                ServiceY: lambda c: ServiceY(c.resolve(ServiceX)),
                ServiceX: lambda c: ServiceX(c.resolve(ServiceY)),
            }
        )

        # Should detect circular dependency when resolving
        with pytest.raises(CircularDependencyError):
            container.resolve(ServiceX)


class TestComplexGenericTypes:
    """Test scenarios with complex generic types."""

    def test_generic_class_without_type_parameters(self):
        """Test generic class used without specific type parameters."""
        from typing import Generic, TypeVar

        container = DIContainer()

        T = TypeVar("T")

        class GenericService(Generic[T]):
            def __init__(self):
                self.items = []

        # Should work as regular class
        container.register_singletons({GenericService: lambda c: GenericService()})

        service = container.resolve(GenericService)
        assert service.items == []


class TestExceptionHandling:
    """Test exception handling and error scenarios."""

    def test_exception_in_builder_function(self):
        """Test that exception in builder function is properly propagated."""
        container = DIContainer()

        class FailingService:
            def __init__(self):
                raise ValueError("Initialization failed")

        container.register_singletons({FailingService: lambda c: FailingService()})

        with pytest.raises(UnresolvableError) as exc_info:
            container.resolve(FailingService)

        # Should wrap the original ValueError
        assert "Initialization failed" in str(exc_info.value) or "FailingService" in str(exc_info.value)

    def test_exception_in_dependency_chain(self):
        """Test exception propagation through dependency chain."""
        container = DIContainer()

        class FailingDependency:
            def __init__(self):
                raise RuntimeError("Dependency failed")

        class DependentService:
            def __init__(self, dep: FailingDependency):
                self.dep = dep

        container.register_singletons({FailingDependency: lambda c: FailingDependency()})

        with pytest.raises(UnresolvableError):
            container.resolve(DependentService)


class TestNameClashes:
    """Test scenarios with name clashes and similar class names."""

    def test_classes_with_same_name_different_modules(self):
        """Test handling of classes with same name from different contexts."""
        container = DIContainer()

        # Simulate classes from different modules by using nested classes
        class Module1:
            class Service:
                def __init__(self):
                    self.module = "module1"

        class Module2:
            class Service:
                def __init__(self):
                    self.module = "module2"

        # Register both with different registrations
        container.register_singletons({Module1.Service: lambda c: Module1.Service()})
        container.register_singletons({Module2.Service: lambda c: Module2.Service()})

        service1 = container.resolve(Module1.Service)
        service2 = container.resolve(Module2.Service)

        assert service1.module == "module1"
        assert service2.module == "module2"
        assert service1 is not service2


class TestContainerEdgeCases:
    """Test edge cases specific to container behavior."""

    def test_resolve_from_empty_container(self):
        """Test resolving from empty container."""
        container = DIContainer()

        class Service:
            pass

        # Should work with auto-wiring if no dependencies
        service = container.resolve(Service)
        assert isinstance(service, Service)

    def test_clear_container_multiple_times(self):
        """Test clearing container multiple times."""
        container = DIContainer()

        class Service:
            pass

        container.register_singletons({Service: lambda c: Service()})
        container.clear()
        container.clear()  # Second clear should be safe

        # Container should be empty
        assert len(container._registry) == 0

    def test_resolve_after_clear_requires_re_registration(self):
        """Test that resolving after clear clears registered dependencies but auto-wiring still works."""
        container = DIContainer()

        class Service:
            pass

        container.register_singletons({Service: lambda c: Service()})
        service1 = container.resolve(Service)

        container.clear()

        # Registry is cleared, but auto-wiring still works for simple classes
        service2 = container.resolve(Service)
        assert isinstance(service2, Service)
        # Should be different instance since singleton cache was cleared
        assert service1 is not service2

    def test_registry_copy_isolation(self):
        """Test that registry copies are properly isolated."""
        container = DIContainer()

        class Service:
            pass

        container.register_singletons({Service: lambda c: Service()})

        # Get registry copy (internal operation)
        registry_copy = container.get_registry_copy()

        # Clear original container
        container.clear()

        # Copy should still have the registration
        assert Service in registry_copy
        assert Service not in container._registry


class TestDataClasses:
    """Test scenarios with dataclasses."""

    def test_dataclass_without_dependencies(self):
        """Test resolving dataclass without dependencies."""
        from dataclasses import dataclass

        container = DIContainer()

        @dataclass
        class Config:
            host: str = "localhost"
            port: int = 8080

        # Should work but requires explicit registration due to default values
        container.register_singletons({Config: lambda c: Config()})

        config = container.resolve(Config)
        assert config.host == "localhost"
        assert config.port == 8080

    def test_dataclass_with_dependencies(self):
        """Test resolving dataclass with dependencies."""
        from dataclasses import dataclass

        container = DIContainer()

        class Database:
            pass

        @dataclass
        class Service:
            db: Database

        container.register_singletons({Database: lambda c: Database()})
        container.register_singletons({Service: lambda c: Service(c.resolve(Database))})

        service = container.resolve(Service)
        assert isinstance(service.db, Database)


class TestPropertyBasedInjection:
    """Test that property-based injection is not supported (constructor only)."""

    def test_properties_are_not_auto_injected(self):
        """Test that properties are not automatically injected."""
        container = DIContainer()

        class Dependency:
            pass

        class ServiceWithProperty:
            dependency: Dependency  # Type hint as property, not constructor parameter

            def __init__(self):
                pass

        # Only constructor injection is supported
        container.register_singletons({ServiceWithProperty: lambda c: ServiceWithProperty()})

        service = container.resolve(ServiceWithProperty)
        # Property should not be auto-injected
        assert not hasattr(service, "dependency") or service.dependency is None


class TestSpecialMethods:
    """Test scenarios with classes having special methods."""

    def test_class_with_new_method(self):
        """Test class with custom __new__ method."""
        container = DIContainer()

        class Singleton:
            _instance = None

            def __new__(cls):
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                return cls._instance

            def __init__(self):
                self.initialized = True

        # Register with builder
        container.register_singletons({Singleton: lambda c: Singleton()})

        instance1 = container.resolve(Singleton)
        instance2 = container.resolve(Singleton)

        # Should be same instance (container singleton + class singleton)
        assert instance1 is instance2
