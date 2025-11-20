"""Unit tests for domain models."""

import pytest
from pydantic import ValidationError

from miraveja_di.domain.enums import Lifetime
from miraveja_di.domain.exceptions import CircularDependencyError
from miraveja_di.domain.interfaces import IContainer
from miraveja_di.domain.models import DependencyMetadata, Registration, ResolutionContext


class TestRegistration:
    """Test cases for the Registration model."""

    def test_registration_creation_with_valid_data(self):
        """Test creating a Registration with valid data."""

        class TestService:
            pass

        builder = lambda c: TestService()
        registration = Registration(dependency_type=TestService, builder=builder, lifetime=Lifetime.SINGLETON)

        assert registration.dependency_type == TestService
        assert registration.builder == builder
        assert registration.lifetime == Lifetime.SINGLETON

    def test_registration_is_frozen(self):
        """Test that Registration is immutable (frozen)."""

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )

        with pytest.raises(ValidationError):
            registration.lifetime = Lifetime.TRANSIENT

    def test_registration_with_transient_lifetime(self):
        """Test Registration with transient lifetime."""

        class TransientService:
            pass

        registration = Registration(
            dependency_type=TransientService,
            builder=lambda c: TransientService(),
            lifetime=Lifetime.TRANSIENT,
        )

        assert registration.lifetime == Lifetime.TRANSIENT

    def test_registration_with_scoped_lifetime(self):
        """Test Registration with scoped lifetime."""

        class ScopedService:
            pass

        registration = Registration(
            dependency_type=ScopedService,
            builder=lambda c: ScopedService(),
            lifetime=Lifetime.SCOPED,
        )

        assert registration.lifetime == Lifetime.SCOPED

    def test_registration_builder_accepts_container(self):
        """Test that builder function can accept container parameter."""

        class DependentService:
            def __init__(self, dep):
                self.dep = dep

        # Mock container
        class MockContainer:
            def resolve(self, cls):
                return "resolved_dependency"

        def builder(container: IContainer):
            return DependentService(container.resolve(str))

        registration = Registration(dependency_type=DependentService, builder=builder, lifetime=Lifetime.SINGLETON)

        # Test builder can be called with container
        instance = registration.builder(MockContainer())
        assert isinstance(instance, DependentService)

    def test_registration_equality(self):
        """Test that two registrations with same data are equal."""

        class TestService:
            pass

        builder = lambda c: TestService()

        reg1 = Registration(dependency_type=TestService, builder=builder, lifetime=Lifetime.SINGLETON)
        reg2 = Registration(dependency_type=TestService, builder=builder, lifetime=Lifetime.SINGLETON)

        assert reg1 == reg2

    def test_registration_inequality_different_type(self):
        """Test that registrations with different types are not equal."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        reg1 = Registration(dependency_type=ServiceA, builder=lambda c: ServiceA(), lifetime=Lifetime.SINGLETON)
        reg2 = Registration(dependency_type=ServiceB, builder=lambda c: ServiceB(), lifetime=Lifetime.SINGLETON)

        assert reg1 != reg2

    def test_registration_requires_all_fields(self):
        """Test that Registration requires all fields."""
        with pytest.raises(ValidationError):
            Registration(dependency_type=str)

    def test_registration_model_dump(self):
        """Test that Registration can be converted to dict."""

        class TestService:
            pass

        builder = lambda c: TestService()
        registration = Registration(dependency_type=TestService, builder=builder, lifetime=Lifetime.SINGLETON)

        data = registration.model_dump()
        assert "dependency_type" in data
        assert "builder" in data
        assert "lifetime" in data


class TestDependencyMetadata:
    """Test cases for the DependencyMetadata model."""

    def test_dependency_metadata_creation_with_registration(self):
        """Test creating DependencyMetadata with a registration."""

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration)

        assert metadata.registration == registration
        assert metadata.cached_instance is None
        assert metadata.resolution_count == 0

    def test_dependency_metadata_with_cached_instance(self):
        """Test DependencyMetadata with a cached instance."""

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        instance = TestService()
        metadata = DependencyMetadata(registration=registration, cached_instance=instance)

        assert metadata.cached_instance is instance

    def test_dependency_metadata_with_resolution_count(self):
        """Test DependencyMetadata with custom resolution count."""

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration, resolution_count=5)

        assert metadata.resolution_count == 5

    def test_dependency_metadata_is_mutable(self):
        """Test that DependencyMetadata is mutable (not frozen)."""

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration)

        # Should be able to update cached instance
        instance = TestService()
        metadata.cached_instance = instance
        assert metadata.cached_instance is instance

        # Should be able to update resolution count
        metadata.resolution_count = 10
        assert metadata.resolution_count == 10

    def test_dependency_metadata_defaults(self):
        """Test that DependencyMetadata has correct default values."""

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration)

        assert metadata.cached_instance is None
        assert metadata.resolution_count == 0

    def test_dependency_metadata_increment_resolution_count(self):
        """Test incrementing resolution count."""

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration)

        metadata.resolution_count += 1
        assert metadata.resolution_count == 1

        metadata.resolution_count += 1
        assert metadata.resolution_count == 2


class TestResolutionContext:
    """Test cases for the ResolutionContext model."""

    def test_resolution_context_creation_empty(self):
        """Test creating an empty ResolutionContext."""
        context = ResolutionContext()
        assert context.stack == []

    def test_resolution_context_push_adds_to_stack(self):
        """Test that push adds a type to the stack."""

        class ServiceA:
            pass

        context = ResolutionContext()
        context.push(ServiceA)

        assert ServiceA in context.stack
        assert len(context.stack) == 1

    def test_resolution_context_push_multiple_types(self):
        """Test pushing multiple types to the stack."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            pass

        context = ResolutionContext()
        context.push(ServiceA)
        context.push(ServiceB)
        context.push(ServiceC)

        assert context.stack == [ServiceA, ServiceB, ServiceC]

    def test_resolution_context_push_detects_circular_dependency(self):
        """Test that push detects circular dependencies."""

        class ServiceA:
            pass

        context = ResolutionContext()
        context.push(ServiceA)

        with pytest.raises(CircularDependencyError) as exc_info:
            context.push(ServiceA)

        assert ServiceA in exc_info.value.dependency_chain

    def test_resolution_context_push_detects_circular_in_chain(self):
        """Test that push detects circular dependencies in a chain."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            pass

        context = ResolutionContext()
        context.push(ServiceA)
        context.push(ServiceB)
        context.push(ServiceC)

        with pytest.raises(CircularDependencyError) as exc_info:
            context.push(ServiceB)

        # Cycle should be ServiceB -> ServiceC -> ServiceB
        chain = exc_info.value.dependency_chain
        assert chain == [ServiceB, ServiceC, ServiceB]

    def test_resolution_context_pop_removes_last_type(self):
        """Test that pop removes the last type from the stack."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        context = ResolutionContext()
        context.push(ServiceA)
        context.push(ServiceB)

        context.pop()
        assert context.stack == [ServiceA]

        context.pop()
        assert context.stack == []

    def test_resolution_context_pop_empty_stack(self):
        """Test that pop on empty stack doesn't raise error."""
        context = ResolutionContext()
        context.pop()  # Should not raise
        assert context.stack == []

    def test_resolution_context_clear_empties_stack(self):
        """Test that clear empties the entire stack."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            pass

        context = ResolutionContext()
        context.push(ServiceA)
        context.push(ServiceB)
        context.push(ServiceC)

        context.clear()
        assert context.stack == []

    def test_resolution_context_clear_on_empty_stack(self):
        """Test that clear on empty stack doesn't raise error."""
        context = ResolutionContext()
        context.clear()  # Should not raise
        assert context.stack == []

    def test_resolution_context_push_pop_cycle(self):
        """Test normal push/pop cycle for successful resolution."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        context = ResolutionContext()

        # Simulate resolving ServiceA which depends on ServiceB
        context.push(ServiceA)
        context.push(ServiceB)
        context.pop()  # ServiceB resolved
        context.pop()  # ServiceA resolved

        assert context.stack == []

    def test_resolution_context_stack_is_mutable(self):
        """Test that the stack can be directly accessed and modified."""

        class ServiceA:
            pass

        context = ResolutionContext()
        context.stack.append(ServiceA)

        assert ServiceA in context.stack

    def test_resolution_context_with_custom_initial_stack(self):
        """Test creating ResolutionContext with custom initial stack."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        context = ResolutionContext(stack=[ServiceA, ServiceB])

        assert context.stack == [ServiceA, ServiceB]

    def test_resolution_context_circular_detection_preserves_stack(self):
        """Test that failed push preserves the stack state."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        context = ResolutionContext()
        context.push(ServiceA)
        context.push(ServiceB)

        try:
            context.push(ServiceA)
        except CircularDependencyError:
            pass

        # Stack should still contain original items
        assert context.stack == [ServiceA, ServiceB]
