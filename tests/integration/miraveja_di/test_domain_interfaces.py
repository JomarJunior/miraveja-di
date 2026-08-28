"""Integration tests for domain interfaces working together."""

from abc import ABC

import pytest

from miraveja_di.application.container import DIContainer
from miraveja_di.domain.enums import Lifetime
from miraveja_di.domain.interfaces import IContainer, ILifetimeManager, IResolver
from miraveja_di.domain.models import DependencyMetadata


class TestInterfacesIntegration:
    """Integration tests for domain interfaces working together."""

    def test_all_interfaces_are_abstract(self):
        """Test that all domain interfaces are abstract base classes."""
        assert issubclass(IContainer, ABC)
        assert issubclass(IResolver, ABC)
        assert issubclass(ILifetimeManager, ABC)

    def test_all_interfaces_cannot_be_instantiated(self):
        """Test that none of the interfaces can be instantiated directly."""
        with pytest.raises(TypeError):
            IContainer()
        with pytest.raises(TypeError):
            IResolver()
        with pytest.raises(TypeError):
            ILifetimeManager()

    def test_container_can_use_resolver_and_lifetime_manager(self):
        """Test that a container implementation can use resolver and lifetime manager."""

        class SimpleResolver(IResolver):
            def resolve_dependencies(self, dependency_type, container):
                return dependency_type()

        class SimpleManager(ILifetimeManager):
            def __init__(self):
                self.cache = {}

            def get_or_create(self, metadata, factory):
                return factory()

            def clear_cache(self):
                self.cache.clear()

            def clear_scoped_cache(self):
                pass

        class SimpleContainer(IContainer):
            def __init__(self):
                self.resolver = SimpleResolver()
                self.lifetime_manager = SimpleManager()
                self.registry = {}

            def register_singletons(self, dependencies):
                from miraveja_di.domain.models import Registration

                for dep_type, builder in dependencies.items():
                    registration = Registration(dependency_type=dep_type, builder=builder, lifetime=Lifetime.SINGLETON)
                    self.registry[dep_type] = DependencyMetadata(registration=registration)

            def register_transients(self, dependencies):
                from miraveja_di.domain.models import Registration

                for dep_type, builder in dependencies.items():
                    registration = Registration(dependency_type=dep_type, builder=builder, lifetime=Lifetime.TRANSIENT)
                    self.registry[dep_type] = DependencyMetadata(registration=registration)

            def register_scoped(self, dependencies):
                from miraveja_di.domain.models import Registration

                for dep_type, builder in dependencies.items():
                    registration = Registration(dependency_type=dep_type, builder=builder, lifetime=Lifetime.SCOPED)
                    self.registry[dep_type] = DependencyMetadata(registration=registration)

            def resolve(self, dependency_type):
                if dependency_type in self.registry:
                    metadata = self.registry[dependency_type]
                    return self.lifetime_manager.get_or_create(metadata, lambda: metadata.registration.builder(self))
                return self.resolver.resolve_dependencies(dependency_type, self)

            def create_scope(self):
                return self

            def clear(self):
                self.registry.clear()
                self.lifetime_manager.clear_cache()

            def get_registry_copy(self):
                return self.registry.copy()

        class TestService:
            pass

        container = SimpleContainer()

        # Register a service
        container.register_singletons({TestService: lambda c: TestService()})

        # Resolve the service
        instance = container.resolve(TestService)
        assert isinstance(instance, TestService)

        # Clear the container
        container.clear()
        assert len(container.registry) == 0

    def test_interfaces_support_type_hints(self):
        """Test that interfaces work correctly with type hints."""

        def accepts_container(container: IContainer) -> None:
            pass

        def accepts_resolver(resolver: IResolver) -> None:
            pass

        def accepts_manager(manager: ILifetimeManager) -> None:
            pass

        # These should not raise at definition time
        # (runtime type checking would require a type checker like mypy)
        assert callable(accepts_container)
        assert callable(accepts_resolver)
        assert callable(accepts_manager)
        assert callable(accepts_manager)


class TestScopedRegistrationThroughInterface:
    """The interface must expose everything needed to use scoped lifetimes."""

    def test_scoped_dependencies_registrable_through_the_interface(self):
        """Test that a container held as IContainer can register scoped dependencies."""

        class RequestContext:
            pass

        container: IContainer = DIContainer()
        container.register_scoped({RequestContext: lambda c: RequestContext()})

        scope = container.create_scope()
        assert scope.resolve(RequestContext) is scope.resolve(RequestContext)

    def test_separate_scopes_get_separate_instances_through_the_interface(self):
        """Test that scoping semantics survive being used through the interface."""

        class RequestContext:
            pass

        container: IContainer = DIContainer()
        container.register_scoped({RequestContext: lambda c: RequestContext()})

        assert container.create_scope().resolve(RequestContext) is not (
            container.create_scope().resolve(RequestContext)
        )

    def test_concrete_container_satisfies_the_whole_interface(self):
        """Test that DIContainer implements every abstract method IContainer declares."""
        assert issubclass(DIContainer, IContainer)
        for name in IContainer.__abstractmethods__:
            assert getattr(DIContainer, name) is not getattr(IContainer, name), name
