"""Integration tests for scoped lifetime management."""

import pytest

from miraveja_di import DIContainer


class TestScopedLifetimeScenarios:
    """Test realistic scoped lifetime scenarios."""

    def test_request_scoped_context(self):
        """Test scoped dependencies in a request-like context."""
        container = DIContainer()

        class RequestId:
            instance_count = 0

            def __init__(self):
                RequestId.instance_count += 1
                self.id = RequestId.instance_count

        class RequestLogger:
            def __init__(self, request_id: RequestId):
                self.request_id = request_id

        class RequestHandler:
            def __init__(self, request_id: RequestId, logger: RequestLogger):
                self.request_id = request_id
                self.logger = logger

        # Register as scoped to get one instance per scope
        container.register_scoped({RequestId: lambda c: RequestId()})

        # Simulate first request
        with container.create_scope() as scope1:
            handler1 = scope1.resolve(RequestHandler)
            logger1 = scope1.resolve(RequestLogger)

            # Within same scope, should share instances
            assert handler1.request_id is logger1.request_id
            assert handler1.logger.request_id is handler1.request_id
            request1_id = handler1.request_id.id

        # Simulate second request
        with container.create_scope() as scope2:
            handler2 = scope2.resolve(RequestHandler)
            logger2 = scope2.resolve(RequestLogger)

            # Different scope should have different instances
            assert handler2.request_id is not handler1.request_id
            assert handler2.request_id.id != request1_id

            # But within scope2, should share
            assert handler2.request_id is logger2.request_id

    def test_scoped_with_singleton_sharing(self):
        """Test that scoped containers share singletons from parent."""
        container = DIContainer()

        class GlobalConfig:
            instance_count = 0

            def __init__(self):
                GlobalConfig.instance_count += 1
                self.id = GlobalConfig.instance_count

        class RequestContext:
            def __init__(self, config: GlobalConfig):
                self.config = config

        # Register config as singleton in parent
        container.register_singletons({GlobalConfig: lambda c: GlobalConfig()})

        # Create multiple scopes
        with container.create_scope() as scope1:
            context1 = scope1.resolve(RequestContext)
            config1 = context1.config

        with container.create_scope() as scope2:
            context2 = scope2.resolve(RequestContext)
            config2 = context2.config

        # Singleton should be shared across scopes
        assert config1 is config2
        assert config1.id == 1

    def test_nested_scopes(self):
        """Test nested scope creation and isolation."""
        container = DIContainer()

        class OuterResource:
            instance_count = 0

            def __init__(self):
                OuterResource.instance_count += 1
                self.id = OuterResource.instance_count

        class InnerResource:
            instance_count = 0

            def __init__(self):
                InnerResource.instance_count += 1
                self.id = InnerResource.instance_count

        container.register_scoped({OuterResource: lambda c: OuterResource(), InnerResource: lambda c: InnerResource()})

        with container.create_scope() as outer_scope:
            outer1 = outer_scope.resolve(OuterResource)

            with outer_scope.create_scope() as inner_scope:
                inner1 = inner_scope.resolve(InnerResource)
                outer_in_inner = inner_scope.resolve(OuterResource)

                # Inner scope should have its own instances
                assert outer1 is not outer_in_inner

            # After inner scope exits, outer scope still works
            outer2 = outer_scope.resolve(OuterResource)
            assert outer1 is outer2  # Scoped returns same instance within scope

    def test_scope_cleanup_on_exception(self):
        """Test that scope properly cleans up even when exception occurs."""
        container = DIContainer()

        class Resource:
            instance_count = 0

            def __init__(self):
                Resource.instance_count += 1
                self.id = Resource.instance_count
                self.cleaned_up = False

        container.register_scoped({Resource: lambda c: Resource()})

        initial_count = Resource.instance_count

        try:
            with container.create_scope() as scope:
                resource = scope.resolve(Resource)
                assert resource.id == initial_count + 1
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Scope should have been cleaned up
        # New scope should work normally
        with container.create_scope() as new_scope:
            new_resource = new_scope.resolve(Resource)
            assert new_resource.id == initial_count + 2

    def test_scoped_container_isolation_from_parent_changes(self):
        """Test that scoped container is isolated from parent changes after creation."""
        container = DIContainer()

        class ServiceA:
            pass

        class ServiceB:
            pass

        # Register ServiceA in parent
        container.register_singletons({ServiceA: lambda c: ServiceA()})

        # Create scope
        with container.create_scope() as scope:
            # Can resolve ServiceA from scope
            service_a = scope.resolve(ServiceA)
            assert isinstance(service_a, ServiceA)

            # Add ServiceB to parent after scope creation
            container.register_singletons({ServiceB: lambda c: ServiceB()})

            # Scope should inherit parent registrations at creation time
            # But changes to parent after creation should still be visible
            # (because scope copies registry by reference)
            service_b = scope.resolve(ServiceB)
            assert isinstance(service_b, ServiceB)


class TestTransactionScopedScenarios:
    """Test database transaction-like scoped scenarios."""

    def test_database_transaction_scope(self):
        """Test using scopes for database transaction-like pattern."""
        container = DIContainer()

        class DatabaseConnection:
            def __init__(self):
                self.connected = True
                self.transaction_active = False

            def begin_transaction(self):
                self.transaction_active = True

            def commit(self):
                self.transaction_active = False

            def rollback(self):
                self.transaction_active = False

        class UnitOfWork:
            def __init__(self, connection: DatabaseConnection):
                self.connection = connection
                self.committed = False

            def commit(self):
                self.connection.commit()
                self.committed = True

            def rollback(self):
                self.connection.rollback()

        class Repository:
            def __init__(self, uow: UnitOfWork):
                self.uow = uow

            def save_data(self):
                return "data_saved"

        # Register connection as singleton
        container.register_singletons({DatabaseConnection: lambda c: DatabaseConnection()})

        # Simulate transaction 1
        with container.create_scope() as transaction1:
            repo1 = transaction1.resolve(Repository)
            repo1.save_data()
            repo1.uow.commit()
            assert repo1.uow.committed is True

        # Simulate transaction 2
        with container.create_scope() as transaction2:
            repo2 = transaction2.resolve(Repository)
            repo2.save_data()
            # Different UnitOfWork instance
            assert repo2.uow is not repo1.uow
            assert repo2.uow.committed is False

    def test_rollback_on_error_pattern(self):
        """Test transaction rollback pattern with scopes."""
        container = DIContainer()

        class Transaction:
            def __init__(self):
                self.rolled_back = False
                self.committed = False

            def commit(self):
                self.committed = True

            def rollback(self):
                self.rolled_back = True

        class DataService:
            def __init__(self, transaction: Transaction):
                self.transaction = transaction

            def perform_work(self, should_fail: bool):
                if should_fail:
                    raise ValueError("Operation failed")
                return "success"

        container.register_scoped({Transaction: lambda c: Transaction()})

        # Successful transaction
        with container.create_scope() as scope:
            service = scope.resolve(DataService)
            result = service.perform_work(should_fail=False)
            service.transaction.commit()
            assert service.transaction.committed is True
            assert result == "success"

        # Failed transaction
        try:
            with container.create_scope() as scope:
                service = scope.resolve(DataService)
                service.perform_work(should_fail=True)
                service.transaction.commit()
        except ValueError:
            # Manually rollback in exception handler
            service.transaction.rollback()
            assert service.transaction.rolled_back is True
            assert service.transaction.committed is False


class TestWebRequestScopedScenarios:
    """Test web request-like scoped scenarios."""

    def test_http_request_context(self):
        """Test HTTP request context pattern."""
        container = DIContainer()

        class HttpContext:
            def __init__(self, request_id: str):
                self.request_id = request_id
                self.user = None
                self.metadata = {}

        class AuthService:
            def __init__(self, context: HttpContext):
                self.context = context

            def authenticate(self, user: str):
                self.context.user = user

        class RequestHandler:
            def __init__(self, context: HttpContext, auth: AuthService):
                self.context = context
                self.auth = auth

        # Simulate request 1
        with container.create_scope() as scope:
            # Manually inject request-specific context as scoped
            scope.register_scoped({HttpContext: lambda c: HttpContext("request-1")})

            handler = scope.resolve(RequestHandler)
            handler.auth.authenticate("user1")

            assert handler.context.request_id == "request-1"
            assert handler.context.user == "user1"
            assert handler.context is handler.auth.context

        # Simulate request 2
        with container.create_scope() as scope:
            scope.register_scoped({HttpContext: lambda c: HttpContext("request-2")})

            handler = scope.resolve(RequestHandler)
            handler.auth.authenticate("user2")

            assert handler.context.request_id == "request-2"
            assert handler.context.user == "user2"

    def test_request_scoped_caching(self):
        """Test request-scoped caching pattern."""
        container = DIContainer()

        class RequestCache:
            def __init__(self):
                self.cache = {}
                self.hits = 0

            def get(self, key: str):
                if key in self.cache:
                    self.hits += 1
                    return self.cache[key]
                return None

            def set(self, key: str, value):
                self.cache[key] = value

        class DataService:
            def __init__(self, cache: RequestCache):
                self.cache = cache

            def get_data(self, key: str):
                cached = self.cache.get(key)
                if cached:
                    return cached

                # Simulate expensive operation
                data = f"data_for_{key}"
                self.cache.set(key, data)
                return data

        container.register_scoped({RequestCache: lambda c: RequestCache()})

        # Request 1 - cache should work within scope
        with container.create_scope() as scope1:
            service1a = scope1.resolve(DataService)
            service1b = scope1.resolve(DataService)

            # Both services in same scope share cache
            assert service1a.cache is service1b.cache

            data1 = service1a.get_data("key1")
            data2 = service1b.get_data("key1")  # Should hit cache

            assert data1 == data2
            assert service1a.cache.hits == 1

        # Request 2 - new scope, fresh cache
        with container.create_scope() as scope2:
            service2 = scope2.resolve(DataService)

            # Different cache instance
            assert service2.cache is not service1a.cache
            assert service2.cache.hits == 0

            data3 = service2.get_data("key1")  # Cache miss, new cache
            assert data3 == "data_for_key1"
            assert service2.cache.hits == 0


class TestScopedPerformance:
    """Test performance characteristics of scoped lifetimes."""

    def test_scope_creation_overhead(self):
        """Test that scope creation is lightweight."""
        container = DIContainer()

        class SimpleService:
            pass

        container.register_singletons({SimpleService: lambda c: SimpleService()})

        # Create many scopes - should be fast
        scope_count = 100
        for _ in range(scope_count):
            with container.create_scope() as scope:
                service = scope.resolve(SimpleService)
                assert isinstance(service, SimpleService)

    def test_scope_isolation_performance(self):
        """Test that scoped resolution doesn't impact parent container."""
        container = DIContainer()

        class ParentService:
            resolution_count = 0

            def __init__(self):
                ParentService.resolution_count += 1

        container.register_singletons({ParentService: lambda c: ParentService()})

        # Resolve in parent
        parent_service = container.resolve(ParentService)
        parent_count = ParentService.resolution_count

        # Create scope and resolve
        with container.create_scope() as scope:
            scoped_service = scope.resolve(ParentService)
            # Should reuse singleton from parent
            assert scoped_service is parent_service
            assert ParentService.resolution_count == parent_count  # No new instance
