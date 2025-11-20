"""Unit tests for LifetimeManager."""

import pytest

from miraveja_di.application.lifetime_manager import LifetimeManager
from miraveja_di.domain import DependencyMetadata, Lifetime, Registration, UnresolvableError


class TestLifetimeManagerInitialization:
    """Test cases for LifetimeManager initialization."""

    def test_manager_initialization(self):
        """Test that manager initializes with empty caches."""
        manager = LifetimeManager()
        assert manager._singleton_cache == {}
        assert manager._scoped_cache == {}

    def test_manager_implements_interface(self):
        """Test that LifetimeManager implements ILifetimeManager."""
        from miraveja_di.domain import ILifetimeManager

        manager = LifetimeManager()
        assert isinstance(manager, ILifetimeManager)


class TestSingletonLifetime:
    """Test cases for singleton lifetime management."""

    def test_singleton_creates_instance_once(self):
        """Test that singleton creates instance only once."""
        manager = LifetimeManager()

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration)

        # First call creates instance
        instance1 = manager.get_or_create(metadata, lambda: TestService())

        # Second call returns same instance
        instance2 = manager.get_or_create(metadata, lambda: TestService())

        assert instance1 is instance2

    def test_singleton_caches_instance(self):
        """Test that singleton instance is stored in cache."""
        manager = LifetimeManager()

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration)

        instance = manager.get_or_create(metadata, lambda: TestService())

        assert TestService in manager._singleton_cache
        assert manager._singleton_cache[TestService] is instance

    def test_singleton_factory_called_once(self):
        """Test that factory function is called only once for singleton."""
        manager = LifetimeManager()
        call_count = [0]

        class TestService:
            pass

        def factory():
            call_count[0] += 1
            return TestService()

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration)

        # Call multiple times
        manager.get_or_create(metadata, factory)
        manager.get_or_create(metadata, factory)
        manager.get_or_create(metadata, factory)

        # Factory should only be called once
        assert call_count[0] == 1

    def test_multiple_singleton_types(self):
        """Test that different singleton types have separate instances."""
        manager = LifetimeManager()

        class ServiceA:
            pass

        class ServiceB:
            pass

        reg_a = Registration(
            dependency_type=ServiceA,
            builder=lambda c: ServiceA(),
            lifetime=Lifetime.SINGLETON,
        )
        meta_a = DependencyMetadata(registration=reg_a)

        reg_b = Registration(
            dependency_type=ServiceB,
            builder=lambda c: ServiceB(),
            lifetime=Lifetime.SINGLETON,
        )
        meta_b = DependencyMetadata(registration=reg_b)

        instance_a = manager.get_or_create(meta_a, lambda: ServiceA())
        instance_b = manager.get_or_create(meta_b, lambda: ServiceB())

        assert isinstance(instance_a, ServiceA)
        assert isinstance(instance_b, ServiceB)
        assert instance_a is not instance_b
        assert len(manager._singleton_cache) == 2


class TestTransientLifetime:
    """Test cases for transient lifetime management."""

    def test_transient_creates_new_instance_each_time(self):
        """Test that transient creates new instance on each call."""
        manager = LifetimeManager()

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.TRANSIENT,
        )
        metadata = DependencyMetadata(registration=registration)

        # Each call creates new instance
        instance1 = manager.get_or_create(metadata, lambda: TestService())
        instance2 = manager.get_or_create(metadata, lambda: TestService())
        instance3 = manager.get_or_create(metadata, lambda: TestService())

        assert instance1 is not instance2
        assert instance2 is not instance3
        assert instance1 is not instance3

    def test_transient_not_cached(self):
        """Test that transient instances are not cached."""
        manager = LifetimeManager()

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.TRANSIENT,
        )
        metadata = DependencyMetadata(registration=registration)

        manager.get_or_create(metadata, lambda: TestService())

        # Should not be in any cache
        assert TestService not in manager._singleton_cache
        assert TestService not in manager._scoped_cache

    def test_transient_factory_called_each_time(self):
        """Test that factory is called on each resolution for transient."""
        manager = LifetimeManager()
        call_count = [0]

        class TestService:
            pass

        def factory():
            call_count[0] += 1
            return TestService()

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.TRANSIENT,
        )
        metadata = DependencyMetadata(registration=registration)

        # Call multiple times
        manager.get_or_create(metadata, factory)
        manager.get_or_create(metadata, factory)
        manager.get_or_create(metadata, factory)

        # Factory should be called each time
        assert call_count[0] == 3


class TestScopedLifetime:
    """Test cases for scoped lifetime management."""

    def test_scoped_creates_instance_once_per_scope(self):
        """Test that scoped creates instance once within same scope."""
        manager = LifetimeManager()

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SCOPED,
        )
        metadata = DependencyMetadata(registration=registration)

        # First call creates instance
        instance1 = manager.get_or_create(metadata, lambda: TestService())

        # Second call returns same instance (same scope)
        instance2 = manager.get_or_create(metadata, lambda: TestService())

        assert instance1 is instance2

    def test_scoped_caches_instance(self):
        """Test that scoped instance is stored in scoped cache."""
        manager = LifetimeManager()

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SCOPED,
        )
        metadata = DependencyMetadata(registration=registration)

        instance = manager.get_or_create(metadata, lambda: TestService())

        assert TestService in manager._scoped_cache
        assert manager._scoped_cache[TestService] is instance

    def test_scoped_cleared_on_clear_scoped_cache(self):
        """Test that scoped cache is cleared by clear_scoped_cache."""
        manager = LifetimeManager()

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SCOPED,
        )
        metadata = DependencyMetadata(registration=registration)

        instance1 = manager.get_or_create(metadata, lambda: TestService())

        # Clear scoped cache
        manager.clear_scoped_cache()

        # Next call creates new instance
        instance2 = manager.get_or_create(metadata, lambda: TestService())

        assert instance1 is not instance2

    def test_scoped_not_in_singleton_cache(self):
        """Test that scoped instances are not in singleton cache."""
        manager = LifetimeManager()

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SCOPED,
        )
        metadata = DependencyMetadata(registration=registration)

        manager.get_or_create(metadata, lambda: TestService())

        assert TestService not in manager._singleton_cache
        assert TestService in manager._scoped_cache


class TestCacheClear:
    """Test cases for cache clearing operations."""

    def test_clear_cache_clears_singletons(self):
        """Test that clear_cache clears singleton cache."""
        manager = LifetimeManager()

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration)

        manager.get_or_create(metadata, lambda: TestService())
        assert len(manager._singleton_cache) == 1

        manager.clear_cache()
        assert len(manager._singleton_cache) == 0

    def test_clear_cache_clears_scoped(self):
        """Test that clear_cache clears scoped cache."""
        manager = LifetimeManager()

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SCOPED,
        )
        metadata = DependencyMetadata(registration=registration)

        manager.get_or_create(metadata, lambda: TestService())
        assert len(manager._scoped_cache) == 1

        manager.clear_cache()
        assert len(manager._scoped_cache) == 0

    def test_clear_cache_clears_both_caches(self):
        """Test that clear_cache clears both singleton and scoped caches."""
        manager = LifetimeManager()

        class SingletonService:
            pass

        class ScopedService:
            pass

        reg_singleton = Registration(
            dependency_type=SingletonService,
            builder=lambda c: SingletonService(),
            lifetime=Lifetime.SINGLETON,
        )
        meta_singleton = DependencyMetadata(registration=reg_singleton)

        reg_scoped = Registration(
            dependency_type=ScopedService,
            builder=lambda c: ScopedService(),
            lifetime=Lifetime.SCOPED,
        )
        meta_scoped = DependencyMetadata(registration=reg_scoped)

        manager.get_or_create(meta_singleton, lambda: SingletonService())
        manager.get_or_create(meta_scoped, lambda: ScopedService())

        assert len(manager._singleton_cache) == 1
        assert len(manager._scoped_cache) == 1

        manager.clear_cache()

        assert len(manager._singleton_cache) == 0
        assert len(manager._scoped_cache) == 0

    def test_clear_cache_on_empty_cache(self):
        """Test that clear_cache on empty cache doesn't raise error."""
        manager = LifetimeManager()
        # Should not raise
        manager.clear_cache()
        assert len(manager._singleton_cache) == 0
        assert len(manager._scoped_cache) == 0

    def test_clear_scoped_cache_only_clears_scoped(self):
        """Test that clear_scoped_cache only clears scoped cache."""
        manager = LifetimeManager()

        class SingletonService:
            pass

        class ScopedService:
            pass

        reg_singleton = Registration(
            dependency_type=SingletonService,
            builder=lambda c: SingletonService(),
            lifetime=Lifetime.SINGLETON,
        )
        meta_singleton = DependencyMetadata(registration=reg_singleton)

        reg_scoped = Registration(
            dependency_type=ScopedService,
            builder=lambda c: ScopedService(),
            lifetime=Lifetime.SCOPED,
        )
        meta_scoped = DependencyMetadata(registration=reg_scoped)

        manager.get_or_create(meta_singleton, lambda: SingletonService())
        manager.get_or_create(meta_scoped, lambda: ScopedService())

        manager.clear_scoped_cache()

        # Singleton should remain
        assert len(manager._singleton_cache) == 1
        # Scoped should be cleared
        assert len(manager._scoped_cache) == 0

    def test_clear_scoped_cache_on_empty_cache(self):
        """Test that clear_scoped_cache on empty cache doesn't raise error."""
        manager = LifetimeManager()
        # Should not raise
        manager.clear_scoped_cache()
        assert len(manager._scoped_cache) == 0


class TestLifetimeManagerEdgeCases:
    """Test edge cases for LifetimeManager."""

    def test_factory_can_return_none(self):
        """Test that factory can return None value."""
        manager = LifetimeManager()

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: None,
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration)

        instance = manager.get_or_create(metadata, lambda: None)
        assert instance is None

        # Should still be cached
        assert TestService in manager._singleton_cache
        assert manager._singleton_cache[TestService] is None

    def test_mixed_lifetimes_same_type(self):
        """Test behavior when same type used with different lifetimes."""
        manager = LifetimeManager()

        class TestService:
            pass

        # Register as singleton first
        reg_singleton = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        meta_singleton = DependencyMetadata(registration=reg_singleton)
        singleton_instance = manager.get_or_create(meta_singleton, lambda: TestService())

        # Try to use as transient with different metadata
        reg_transient = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.TRANSIENT,
        )
        meta_transient = DependencyMetadata(registration=reg_transient)
        transient_instance = manager.get_or_create(meta_transient, lambda: TestService())

        # Singleton should be cached, transient should be new
        assert TestService in manager._singleton_cache
        assert singleton_instance is manager._singleton_cache[TestService]
        assert transient_instance is not singleton_instance

    def test_factory_exception_not_cached(self):
        """Test that factory exceptions don't result in cached None values."""
        manager = LifetimeManager()

        class TestService:
            pass

        registration = Registration(
            dependency_type=TestService,
            builder=lambda c: TestService(),
            lifetime=Lifetime.SINGLETON,
        )
        metadata = DependencyMetadata(registration=registration)

        def failing_factory():
            raise ValueError("Factory failed")

        # Should wrap ValueError in UnresolvableError
        with pytest.raises(UnresolvableError, match="Failed to create instance"):
            manager.get_or_create(metadata, failing_factory)

        # Should not be cached
        assert TestService not in manager._singleton_cache
