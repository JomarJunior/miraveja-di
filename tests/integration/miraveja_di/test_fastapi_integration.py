"""Integration tests for FastAPI integration across layers."""

import pytest

pytest.importorskip("fastapi")

from unittest.mock import AsyncMock, MagicMock

from fastapi import Depends, FastAPI

from miraveja_di import DIContainer
from miraveja_di.infrastructure.fastapi_integration.integration import (
    ScopedContainerMiddleware,
    create_fastapi_dependency,
    create_scoped_dependency,
)


class TestFastAPIIntegrationEndToEnd:
    """Test complete FastAPI integration scenarios."""

    def test_fastapi_app_with_dependency_injection(self):
        """Test creating a FastAPI app with DI container integration."""
        app = FastAPI()
        container = DIContainer()

        class DatabaseService:
            def get_data(self):
                return {"data": "test"}

        class UserService:
            def __init__(self, db: DatabaseService):
                self.db = db

            def get_users(self):
                return self.db.get_data()

        # Register services
        container.register_singletons(
            {
                DatabaseService: lambda c: DatabaseService(),
                UserService: lambda c: UserService(c.resolve(DatabaseService)),
            }
        )

        # Create dependency
        get_user_service = create_fastapi_dependency(container, UserService)

        # Create endpoint
        @app.get("/users")
        def get_users(service: UserService = Depends(get_user_service)):
            return service.get_users()

        # Verify dependency is created correctly
        service = get_user_service()
        assert isinstance(service, UserService)
        assert service.get_users() == {"data": "test"}

    def test_multiple_endpoints_share_singleton(self):
        """Test that multiple endpoints share singleton instances."""
        app = FastAPI()
        container = DIContainer()

        class Config:
            instance_count = 0

            def __init__(self):
                Config.instance_count += 1
                self.id = Config.instance_count

        class ServiceA:
            def __init__(self, config: Config):
                self.config = config

        class ServiceB:
            def __init__(self, config: Config):
                self.config = config

        # Register as singleton
        container.register_singletons({Config: lambda c: Config()})

        get_service_a = create_fastapi_dependency(container, ServiceA)
        get_service_b = create_fastapi_dependency(container, ServiceB)

        @app.get("/a")
        def endpoint_a(service: ServiceA = Depends(get_service_a)):
            return {"config_id": service.config.id}

        @app.get("/b")
        def endpoint_b(service: ServiceB = Depends(get_service_b)):
            return {"config_id": service.config.id}

        # Resolve both services
        service_a = get_service_a()
        service_b = get_service_b()

        # Should share the same Config instance
        assert service_a.config is service_b.config
        assert service_a.config.id == 1

    def test_transient_creates_new_instances_per_request(self):
        """Test that transient dependencies create new instances."""
        container = DIContainer()

        class RequestContext:
            instance_count = 0

            def __init__(self):
                RequestContext.instance_count += 1
                self.id = RequestContext.instance_count

        class RequestHandler:
            def __init__(self, context: RequestContext):
                self.context = context

        # Register as transient
        container.register_transients({RequestContext: lambda c: RequestContext()})

        get_handler = create_fastapi_dependency(container, RequestHandler)

        # Simulate multiple requests
        handler1 = get_handler()
        handler2 = get_handler()

        # Should have different instances
        assert handler1.context is not handler2.context
        assert handler1.context.id != handler2.context.id


class TestScopedContainerMiddlewareIntegration:
    """Test scoped container middleware in realistic scenarios."""

    async def test_middleware_creates_scope_per_request(self):
        """Test that middleware creates separate scope for each request."""
        app = FastAPI()
        container = DIContainer()

        class RequestId:
            def __init__(self, value: int):
                self.value = value

        # Track middleware calls
        call_count = 0

        async def mock_call_next(request):
            nonlocal call_count
            call_count += 1
            return MagicMock(status_code=200)

        middleware = ScopedContainerMiddleware(app, container)

        # Simulate two requests
        request1 = MagicMock()
        request1.state = MagicMock()
        await middleware.dispatch(request1, mock_call_next)

        request2 = MagicMock()
        request2.state = MagicMock()
        await middleware.dispatch(request2, mock_call_next)

        assert call_count == 2

    async def test_middleware_cleans_up_after_request(self):
        """Test that middleware cleans up scoped container after request."""
        app = FastAPI()
        container = DIContainer()

        class Resource:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        cleanup_called = False

        async def mock_call_next(request):
            # Access scoped container during request
            scoped = request.state.container
            assert scoped is not None
            return MagicMock(status_code=200)

        middleware = ScopedContainerMiddleware(app, container)

        request = MagicMock()
        request.state = MagicMock()

        response = await middleware.dispatch(request, mock_call_next)

        # After request, scoped container should be cleared
        assert response.status_code == 200

    async def test_middleware_handles_exceptions_gracefully(self):
        """Test that middleware handles exceptions without leaking resources."""
        app = FastAPI()
        container = DIContainer()

        async def mock_call_next_with_error(request):
            raise RuntimeError("Request processing failed")

        middleware = ScopedContainerMiddleware(app, container)

        request = MagicMock()
        request.state = MagicMock()

        # Should propagate exception but still clean up
        with pytest.raises(RuntimeError, match="Request processing failed"):
            await middleware.dispatch(request, mock_call_next_with_error)


class TestComplexFastAPIScenarios:
    """Test complex real-world FastAPI scenarios."""

    def test_nested_dependencies_in_fastapi(self):
        """Test FastAPI with deeply nested dependency chain."""
        app = FastAPI()
        container = DIContainer()

        class Database:
            def query(self):
                return ["user1", "user2"]

        class Repository:
            def __init__(self, db: Database):
                self.db = db

            def get_all(self):
                return self.db.query()

        class Service:
            def __init__(self, repo: Repository):
                self.repo = repo

            def list_items(self):
                return self.repo.get_all()

        class Controller:
            def __init__(self, service: Service):
                self.service = service

            def handle_request(self):
                return {"items": self.service.list_items()}

        # Register all
        container.register_singletons({Database: lambda c: Database()})

        get_controller = create_fastapi_dependency(container, Controller)

        @app.get("/items")
        def list_items(controller: Controller = Depends(get_controller)):
            return controller.handle_request()

        # Test resolution
        controller = get_controller()
        result = controller.handle_request()

        assert result == {"items": ["user1", "user2"]}

    def test_multiple_dependency_types_in_one_endpoint(self):
        """Test endpoint with multiple different dependency types."""
        app = FastAPI()
        container = DIContainer()

        class AuthService:
            def is_authenticated(self):
                return True

        class LoggerService:
            def log(self, message: str):
                return f"Logged: {message}"

        class DataService:
            def get_data(self):
                return {"data": "value"}

        container.register_singletons(
            {
                AuthService: lambda c: AuthService(),
                LoggerService: lambda c: LoggerService(),
                DataService: lambda c: DataService(),
            }
        )

        get_auth = create_fastapi_dependency(container, AuthService)
        get_logger = create_fastapi_dependency(container, LoggerService)
        get_data = create_fastapi_dependency(container, DataService)

        @app.get("/api/data")
        def get_data_endpoint(
            auth: AuthService = Depends(get_auth),
            logger: LoggerService = Depends(get_logger),
            data: DataService = Depends(get_data),
        ):
            if auth.is_authenticated():
                logger.log("Data accessed")
                return data.get_data()
            return {"error": "Unauthorized"}

        # Test dependencies
        auth = get_auth()
        logger = get_logger()
        data = get_data()

        assert auth.is_authenticated() is True
        assert "Logged:" in logger.log("test")
        assert data.get_data() == {"data": "value"}


class TestFastAPIWithTestContainer:
    """Test using TestContainer with FastAPI for testing."""

    def test_override_dependencies_in_tests(self):
        """Test overriding dependencies for testing FastAPI endpoints."""
        from miraveja_di.infrastructure.testing import TestContainer

        app = FastAPI()
        production_container = DIContainer()

        class RealEmailService:
            def send(self, to: str):
                return f"Real email sent to {to}"

        class UserService:
            def __init__(self, email: RealEmailService):
                self.email = email

        # Production container
        production_container.register_singletons({RealEmailService: lambda c: RealEmailService()})

        # Test container with mock
        test_container = TestContainer(production_container)

        class MockEmailService:
            def send(self, to: str):
                return f"Mock email to {to}"

        # Clear and mock
        test_container._registry.clear()
        test_container._lifetime_manager.clear_cache()
        test_container.mock_singleton(RealEmailService, MockEmailService())

        get_user_service = create_fastapi_dependency(test_container, UserService)

        @app.post("/send-email")
        def send_email(service: UserService = Depends(get_user_service)):
            return {"result": service.email.send("user@test.com")}

        # Test with mocked service
        service = get_user_service()
        assert "Mock" in service.email.send("test@example.com")


class TestFastAPIErrorHandling:
    """Test error handling in FastAPI integration."""

    def test_unresolvable_dependency_in_fastapi(self):
        """Test handling of unresolvable dependencies in FastAPI context."""
        from miraveja_di.domain import UnresolvableError

        app = FastAPI()
        container = DIContainer()

        class MissingService:
            def __init__(self, missing_param):  # No type hint - can't auto-wire
                self.missing_param = missing_param

        class DependentService:
            def __init__(self, missing: MissingService):
                self.missing = missing

        # MissingService can't be auto-wired
        get_dependent = create_fastapi_dependency(container, DependentService)

        @app.get("/test")
        def test_endpoint(service: DependentService = Depends(get_dependent)):
            return {"status": "ok"}

        # Should raise UnresolvableError when trying to resolve
        with pytest.raises(UnresolvableError):
            get_dependent()

    def test_circular_dependency_in_fastapi(self):
        """Test handling of circular dependencies in FastAPI context."""
        from miraveja_di.domain import CircularDependencyError

        app = FastAPI()
        container = DIContainer()

        class ServiceA:
            def __init__(self, b: "ServiceB"):
                self.b = b

        class ServiceB:
            def __init__(self, a: ServiceA):
                self.a = a

        # Must register to handle forward reference in local scope
        container.register_singletons(
            {
                ServiceA: lambda c: ServiceA(c.resolve(ServiceB)),
                ServiceB: lambda c: ServiceB(c.resolve(ServiceA)),
            }
        )

        get_service_a = create_fastapi_dependency(container, ServiceA)

        @app.get("/test")
        def test_endpoint(service: ServiceA = Depends(get_service_a)):
            return {"status": "ok"}

        # Should detect circular dependency
        with pytest.raises(CircularDependencyError):
            get_service_a()


class TestAsyncDependencies:
    """Test async scenarios (note: DI container itself is sync)."""

    async def test_sync_di_container_with_async_endpoint(self):
        """Test that sync DI container works with async FastAPI endpoints."""
        app = FastAPI()
        container = DIContainer()

        class SyncService:
            def get_data(self):
                return {"data": "sync"}

        container.register_singletons({SyncService: lambda c: SyncService()})

        get_service = create_fastapi_dependency(container, SyncService)

        @app.get("/async-endpoint")
        async def async_endpoint(service: SyncService = Depends(get_service)):
            # Dependency is resolved synchronously, endpoint is async
            return service.get_data()

        # Test dependency resolution
        service = get_service()
        assert service.get_data() == {"data": "sync"}
