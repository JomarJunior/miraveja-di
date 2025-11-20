"""Integration tests for domain models working together."""

from miraveja_di.domain.enums import Lifetime
from miraveja_di.domain.models import DependencyMetadata, Registration, ResolutionContext


class TestModelsIntegration:
    """Integration tests for domain models working together."""

    def test_registration_in_dependency_metadata(self):
        """Test that Registration works correctly within DependencyMetadata."""

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration)

        assert metadata.registration.dependency_type == TestService
        assert metadata.registration.lifetime == Lifetime.SINGLETON

    def test_metadata_tracks_singleton_instance(self):
        """Test that metadata can track singleton instances."""

        class SingletonService:
            pass

        registration = Registration(
            dependency_type=SingletonService,
            builder=lambda c: SingletonService(),
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration)

        # Simulate singleton creation and caching
        instance = SingletonService()
        metadata.cached_instance = instance
        metadata.resolution_count += 1

        assert metadata.cached_instance is instance
        assert metadata.resolution_count == 1

    def test_resolution_context_tracks_metadata_resolution(self):
        """Test using ResolutionContext during metadata resolution."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        context = ResolutionContext()

        # Simulate resolving ServiceA
        context.push(ServiceA)

        # ServiceA depends on ServiceB
        context.push(ServiceB)

        # ServiceB resolved successfully
        context.pop()

        # ServiceA resolved successfully
        context.pop()

        assert context.stack == []
