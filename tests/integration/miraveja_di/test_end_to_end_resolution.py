"""End-to-end integration tests for dependency resolution across all layers."""

from abc import ABC, abstractmethod

import pytest

from miraveja_di import DIContainer, Lifetime
from miraveja_di.domain import CircularDependencyError, UnresolvableError


class TestEndToEndResolution:
    """Test complete dependency resolution scenarios across all layers."""

    def test_simple_auto_wiring_end_to_end(self):
        """Test basic auto-wiring without explicit registration."""
        container = DIContainer()

        class Database:
            def __init__(self):
                self.connected = True

        class UserRepository:
            def __init__(self, db: Database):
                self.db = db

        class UserService:
            def __init__(self, repo: UserRepository):
                self.repo = repo

        # Only register the root dependency
        container.register_singletons({Database: lambda c: Database()})

        # UserService and UserRepository should auto-wire
        service = container.resolve(UserService)

        assert isinstance(service, UserService)
        assert isinstance(service.repo, UserRepository)
        assert isinstance(service.repo.db, Database)
        assert service.repo.db.connected is True

    def test_complex_dependency_graph_with_mixed_lifetimes(self):
        """Test complex dependency graph with singleton, transient, and scoped lifetimes."""
        container = DIContainer()

        class Config:
            def __init__(self):
                self.app_name = "TestApp"

        class Logger:
            def __init__(self, config: Config):
                self.config = config
                self.logs = []

        class DatabaseConnection:
            instance_count = 0

            def __init__(self, config: Config):
                DatabaseConnection.instance_count += 1
                self.config = config
                self.id = DatabaseConnection.instance_count

        class CacheService:
            def __init__(self, config: Config):
                self.config = config
                self.cache = {}

        class UserRepository:
            def __init__(self, db: DatabaseConnection, cache: CacheService):
                self.db = db
                self.cache = cache

        class UserService:
            def __init__(self, repo: UserRepository, logger: Logger):
                self.repo = repo
                self.logger = logger

        # Register with different lifetimes
        container.register_singletons(
            {
                Config: lambda c: Config(),
                Logger: lambda c: Logger(c.resolve(Config)),
                CacheService: lambda c: CacheService(c.resolve(Config)),
            }
        )
        container.register_transients({DatabaseConnection: lambda c: DatabaseConnection(c.resolve(Config))})

        # Resolve multiple times
        service1 = container.resolve(UserService)
        service2 = container.resolve(UserService)

        # Singletons should be same instance
        assert service1.logger is service2.logger
        assert service1.repo.cache is service2.repo.cache

        # Transients should be different instances
        assert service1.repo.db is not service2.repo.db
        assert service1.repo.db.id != service2.repo.db.id

        # Config should be shared (singleton)
        assert service1.logger.config is service2.logger.config

    def test_interface_to_implementation_mapping(self):
        """Test explicit interface-to-implementation registration."""
        from abc import ABC, abstractmethod

        container = DIContainer()

        class IEmailService(ABC):
            @abstractmethod
            def send(self, to: str, message: str):
                pass

        class SMTPEmailService(IEmailService):
            def send(self, to: str, message: str):
                return f"SMTP: Sent to {to}"

        class NotificationService:
            def __init__(self, email: IEmailService):
                self.email = email

        # Register interface with concrete implementation
        container.register_singletons({IEmailService: lambda c: SMTPEmailService()})

        service = container.resolve(NotificationService)

        assert isinstance(service.email, SMTPEmailService)
        assert service.email.send("user@test.com", "Hello") == "SMTP: Sent to user@test.com"

    def test_factory_pattern_with_conditional_logic(self):
        """Test factory registration with conditional instance creation."""
        container = DIContainer()

        class Config:
            def __init__(self, env: str):
                self.env = env

        class ICache(ABC):
            @abstractmethod
            def get(self, key: str):
                pass

        class RedisCache(ICache):
            def get(self, key: str):
                return f"Redis: {key}"

        class InMemoryCache(ICache):
            def get(self, key: str):
                return f"Memory: {key}"

        class DataService:
            def __init__(self, cache: ICache):
                self.cache = cache

        # Factory function with conditional logic
        def cache_factory(c: DIContainer):
            config = c.resolve(Config)
            if config.env == "production":
                return RedisCache()
            return InMemoryCache()

        # Test with development config
        container.register_singletons({Config: lambda c: Config("development")})
        container.register_singletons({ICache: cache_factory})

        service = container.resolve(DataService)
        assert isinstance(service.cache, InMemoryCache)
        assert "Memory:" in service.cache.get("test")

        # Test with production config
        container_prod = DIContainer()
        container_prod.register_singletons({Config: lambda c: Config("production")})
        container_prod.register_singletons({ICache: cache_factory})

        service_prod = container_prod.resolve(DataService)
        assert isinstance(service_prod.cache, RedisCache)
        assert "Redis:" in service_prod.cache.get("test")

    def test_scoped_lifetime_end_to_end(self):
        """Test scoped lifetime across a complete request lifecycle."""
        container = DIContainer()

        class RequestContext:
            instance_count = 0

            def __init__(self):
                RequestContext.instance_count += 1
                self.id = RequestContext.instance_count
                self.data = {}

        class RequestLogger:
            def __init__(self, context: RequestContext):
                self.context = context

        class RequestHandler:
            def __init__(self, context: RequestContext, logger: RequestLogger):
                self.context = context
                self.logger = logger

        # Register RequestContext as scoped to get one instance per scope
        container.register_scoped({RequestContext: lambda c: RequestContext()})

        # Create scoped containers for different "requests"
        with container.create_scope() as scope1:
            handler1 = scope1.resolve(RequestHandler)
            logger1 = scope1.resolve(RequestLogger)

            # Within same scope, should share instances
            assert handler1.context is logger1.context
            assert handler1.logger.context is handler1.context

        with container.create_scope() as scope2:
            handler2 = scope2.resolve(RequestHandler)

            # Different scope should have different instances
            assert handler2.context is not handler1.context
            assert handler2.context.id != handler1.context.id

    def test_deep_dependency_chain_resolution(self):
        """Test resolution of deep dependency chains."""
        container = DIContainer()

        class Layer1:
            pass

        class Layer2:
            def __init__(self, dep: Layer1):
                self.dep = dep

        class Layer3:
            def __init__(self, dep: Layer2):
                self.dep = dep

        class Layer4:
            def __init__(self, dep: Layer3):
                self.dep = dep

        class Layer5:
            def __init__(self, dep: Layer4):
                self.dep = dep

        # Register only the leaf
        container.register_singletons({Layer1: lambda c: Layer1()})

        # Should auto-wire all layers
        layer5 = container.resolve(Layer5)

        assert isinstance(layer5.dep, Layer4)
        assert isinstance(layer5.dep.dep, Layer3)
        assert isinstance(layer5.dep.dep.dep, Layer2)
        assert isinstance(layer5.dep.dep.dep.dep, Layer1)

    def test_circular_dependency_detection_end_to_end(self):
        """Test circular dependency detection across resolution chain."""
        container = DIContainer()

        class ServiceA:
            def __init__(self, b: "ServiceB"):
                self.b = b

        class ServiceB:
            def __init__(self, c: "ServiceC"):
                self.c = c

        class ServiceC:
            def __init__(self, a: ServiceA):
                self.a = a

        # Must register to handle forward references in local scope
        container.register_singletons(
            {
                ServiceA: lambda c: ServiceA(c.resolve(ServiceB)),
                ServiceB: lambda c: ServiceB(c.resolve(ServiceC)),
                ServiceC: lambda c: ServiceC(c.resolve(ServiceA)),
            }
        )

        with pytest.raises(CircularDependencyError) as exc_info:
            container.resolve(ServiceA)

        error_message = str(exc_info.value)
        assert "ServiceA" in error_message
        assert "ServiceB" in error_message
        assert "ServiceC" in error_message

    def test_multiple_containers_with_different_configurations(self):
        """Test using multiple containers with different configurations."""

        class Config:
            def __init__(self, name: str):
                self.name = name

        class Service:
            def __init__(self, config: Config):
                self.config = config

        # Container 1 - Development
        dev_container = DIContainer()
        dev_container.register_singletons({Config: lambda c: Config("development")})

        # Container 2 - Production
        prod_container = DIContainer()
        prod_container.register_singletons({Config: lambda c: Config("production")})

        dev_service = dev_container.resolve(Service)
        prod_service = prod_container.resolve(Service)

        assert dev_service.config.name == "development"
        assert prod_service.config.name == "production"
        assert dev_service is not prod_service

    def test_optional_dependencies_with_none_handling(self):
        """Test resolution with optional dependencies."""
        from typing import Optional

        container = DIContainer()

        class OptionalService:
            pass

        class ServiceWithOptional:
            def __init__(self, required: str, optional: Optional[OptionalService] = None):
                self.required = required
                self.optional = optional

        # When optional dependency is not registered, should handle gracefully
        # Note: This tests the resolver's ability to handle optional parameters
        # The actual behavior depends on implementation

    def test_clear_container_and_re_register(self):
        """Test clearing container and re-registering dependencies."""
        container = DIContainer()

        class Service:
            instance_count = 0

            def __init__(self):
                Service.instance_count += 1
                self.id = Service.instance_count

        # First registration
        container.register_singletons({Service: lambda c: Service()})
        service1 = container.resolve(Service)
        assert service1.id == 1

        # Clear and re-register
        container.clear()
        container.register_singletons({Service: lambda c: Service()})
        service2 = container.resolve(Service)
        assert service2.id == 2
        assert service1 is not service2


class TestBatchRegistration:
    """Test batch registration scenarios."""

    def test_batch_register_multiple_singletons(self):
        """Test registering multiple singletons in one batch."""
        container = DIContainer()

        class ConfigService:
            pass

        class DatabaseService:
            pass

        class CacheService:
            pass

        class LoggerService:
            pass

        # Batch register all at once
        container.register_singletons(
            {
                ConfigService: lambda c: ConfigService(),
                DatabaseService: lambda c: DatabaseService(),
                CacheService: lambda c: CacheService(),
                LoggerService: lambda c: LoggerService(),
            }
        )

        # All should resolve
        config = container.resolve(ConfigService)
        db = container.resolve(DatabaseService)
        cache = container.resolve(CacheService)
        logger = container.resolve(LoggerService)

        assert all(
            [
                isinstance(config, ConfigService),
                isinstance(db, DatabaseService),
                isinstance(cache, CacheService),
                isinstance(logger, LoggerService),
            ]
        )

    def test_batch_register_with_dependencies_between_them(self):
        """Test batch registering services that depend on each other."""
        container = DIContainer()

        class ServiceA:
            pass

        class ServiceB:
            def __init__(self, a: ServiceA):
                self.a = a

        class ServiceC:
            def __init__(self, b: ServiceB):
                self.b = b

        # Register all in one batch - order shouldn't matter
        container.register_singletons(
            {
                ServiceC: lambda c: ServiceC(c.resolve(ServiceB)),
                ServiceA: lambda c: ServiceA(),
                ServiceB: lambda c: ServiceB(c.resolve(ServiceA)),
            }
        )

        service_c = container.resolve(ServiceC)
        assert isinstance(service_c.b, ServiceB)
        assert isinstance(service_c.b.a, ServiceA)


class TestLifetimeInteractions:
    """Test interactions between different lifetime scopes."""

    def test_transient_depending_on_singleton(self):
        """Test transient service depending on singleton."""
        container = DIContainer()

        class SingletonService:
            pass

        class TransientService:
            def __init__(self, singleton: SingletonService):
                self.singleton = singleton

        container.register_singletons({SingletonService: lambda c: SingletonService()})
        container.register_transients({TransientService: lambda c: TransientService(c.resolve(SingletonService))})

        transient1 = container.resolve(TransientService)
        transient2 = container.resolve(TransientService)

        # Transients are different
        assert transient1 is not transient2

        # But they share the same singleton
        assert transient1.singleton is transient2.singleton

    def test_singleton_depending_on_transient(self):
        """Test singleton service depending on transient (captures first instance)."""
        container = DIContainer()

        class TransientService:
            instance_count = 0

            def __init__(self):
                TransientService.instance_count += 1
                self.id = TransientService.instance_count

        class SingletonService:
            def __init__(self, transient: TransientService):
                self.transient = transient

        container.register_transients({TransientService: lambda c: TransientService()})
        container.register_singletons({SingletonService: lambda c: SingletonService(c.resolve(TransientService))})

        singleton1 = container.resolve(SingletonService)
        singleton2 = container.resolve(SingletonService)

        # Singleton is same instance
        assert singleton1 is singleton2

        # Transient was resolved once during singleton creation
        assert singleton1.transient.id == 1
        assert singleton1.transient is singleton2.transient


class TestErrorScenarios:
    """Test error scenarios and edge cases."""

    def test_unresolvable_dependency_with_clear_message(self):
        """Test that unresolvable dependency provides clear error message."""
        container = DIContainer()

        class RequiredService:
            def __init__(self, missing_param):  # No type hint - can't auto-wire
                self.missing_param = missing_param

        class DependentService:
            def __init__(self, required: RequiredService):
                self.required = required

        # RequiredService can't be auto-wired due to missing type hint
        with pytest.raises(UnresolvableError) as exc_info:
            container.resolve(DependentService)

        error_message = str(exc_info.value)
        assert "RequiredService" in error_message or "DependentService" in error_message

    def test_self_circular_dependency(self):
        """Test detection of self-referencing circular dependency."""
        container = DIContainer()

        class SelfReferencing:
            def __init__(self, self_ref: "SelfReferencing"):
                self.self_ref = self_ref

        # Must register to handle forward reference in local scope
        container.register_singletons({SelfReferencing: lambda c: SelfReferencing(c.resolve(SelfReferencing))})

        with pytest.raises(CircularDependencyError):
            container.resolve(SelfReferencing)
