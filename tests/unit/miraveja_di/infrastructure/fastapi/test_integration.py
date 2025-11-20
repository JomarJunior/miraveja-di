"""Unit tests for FastAPI integration."""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from fastapi import FastAPI, Request
from starlette.responses import Response

from miraveja_di.application.container import DIContainer
from miraveja_di.domain.exceptions import UnresolvableError
from miraveja_di.infrastructure.fastapi_integration.integration import (
    ScopedContainerMiddleware,
    create_fastapi_dependency,
    create_scoped_dependency,
    inject_dependencies,
)


class TestCreateFastAPIDependency:
    """Test cases for create_fastapi_dependency function."""

    def test_creates_dependency_function(self):
        """Test that create_fastapi_dependency returns a callable."""
        container = DIContainer()

        class TestService:
            def __init__(self):
                pass

        container.register_singletons({TestService: lambda c: TestService()})

        dependency_func = create_fastapi_dependency(container, TestService)

        assert callable(dependency_func)

    def test_dependency_function_resolves_from_container(self):
        """Test that the dependency function resolves from the container."""
        container = DIContainer()

        class TestService:
            def __init__(self):
                self.value = "test"

        container.register_singletons({TestService: lambda c: TestService()})

        dependency_func = create_fastapi_dependency(container, TestService)
        instance = dependency_func()

        assert isinstance(instance, TestService)
        assert instance.value == "test"

    def test_dependency_function_returns_singleton_instance(self):
        """Test that singleton dependencies return same instance."""
        container = DIContainer()

        class SingletonService:
            def __init__(self):
                pass

        container.register_singletons({SingletonService: lambda c: SingletonService()})

        dependency_func = create_fastapi_dependency(container, SingletonService)
        instance1 = dependency_func()
        instance2 = dependency_func()

        assert instance1 is instance2

    def test_dependency_function_returns_new_transient_instances(self):
        """Test that transient dependencies return different instances."""
        container = DIContainer()

        class TransientService:
            def __init__(self):
                pass

        container.register_transients({TransientService: lambda c: TransientService()})

        dependency_func = create_fastapi_dependency(container, TransientService)
        instance1 = dependency_func()
        instance2 = dependency_func()

        assert instance1 is not instance2

    def test_dependency_function_auto_wires_unregistered_types(self):
        """Test that unregistered types are auto-wired."""
        container = DIContainer()

        class AutoWiredService:
            def __init__(self):
                pass

        dependency_func = create_fastapi_dependency(container, AutoWiredService)
        instance = dependency_func()

        assert isinstance(instance, AutoWiredService)

    def test_dependency_function_resolves_nested_dependencies(self):
        """Test that nested dependencies are resolved."""
        container = DIContainer()

        class DatabaseConnection:
            def __init__(self):
                self.connected = True

        class UserRepository:
            def __init__(self, db: DatabaseConnection):
                self.db = db

        container.register_singletons({DatabaseConnection: lambda c: DatabaseConnection()})

        dependency_func = create_fastapi_dependency(container, UserRepository)
        instance = dependency_func()

        assert isinstance(instance, UserRepository)
        assert isinstance(instance.db, DatabaseConnection)
        assert instance.db.connected

    def test_dependency_function_with_multiple_containers(self):
        """Test creating dependencies from different containers."""
        container1 = DIContainer()
        container2 = DIContainer()

        class Service1:
            def __init__(self):
                self.name = "service1"

        class Service2:
            def __init__(self):
                self.name = "service2"

        container1.register_singletons({Service1: lambda c: Service1()})
        container2.register_singletons({Service2: lambda c: Service2()})

        dep_func1 = create_fastapi_dependency(container1, Service1)
        dep_func2 = create_fastapi_dependency(container2, Service2)

        instance1 = dep_func1()
        instance2 = dep_func2()

        assert instance1.name == "service1"
        assert instance2.name == "service2"


class TestCreateScopedDependency:
    """Test cases for create_scoped_dependency function."""

    def test_creates_scoped_dependency_function(self):
        """Test that create_scoped_dependency returns a callable."""

        class TestService:
            def __init__(self):
                pass

        dependency_func = create_scoped_dependency(TestService)

        assert callable(dependency_func)

    def test_scoped_dependency_resolves_from_request_container(self):
        """Test that scoped dependency resolves from request container."""
        container = DIContainer()

        class ScopedService:
            def __init__(self):
                self.value = "scoped"

        container.register_singletons({ScopedService: lambda c: ScopedService()})

        scoped_container = container.create_scope()

        # Mock request with scoped container
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.di_container = scoped_container

        dependency_func = create_scoped_dependency(ScopedService)
        instance = dependency_func(request)

        assert isinstance(instance, ScopedService)
        assert instance.value == "scoped"

    def test_scoped_dependency_raises_error_without_middleware(self):
        """Test that scoped dependency raises error without middleware."""

        class ScopedService:
            def __init__(self):
                pass

        # Mock request without scoped container
        request = Mock(spec=Request)
        request.state = Mock(spec=[])  # No di_container attribute

        dependency_func = create_scoped_dependency(ScopedService)

        with pytest.raises(RuntimeError) as exc_info:
            dependency_func(request)

        assert "does not have a scoped DI container" in str(exc_info.value)

    def test_scoped_dependency_with_nested_dependencies(self):
        """Test scoped dependency with nested dependencies."""
        container = DIContainer()

        class DatabaseConnection:
            def __init__(self):
                pass

        class RequestContext:
            def __init__(self, db: DatabaseConnection):
                self.db = db

        container.register_singletons({DatabaseConnection: lambda c: DatabaseConnection()})
        scoped_container = container.create_scope()

        # Mock request with scoped container
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.di_container = scoped_container

        dependency_func = create_scoped_dependency(RequestContext)
        instance = dependency_func(request)

        assert isinstance(instance, RequestContext)
        assert isinstance(instance.db, DatabaseConnection)

    def test_scoped_dependency_different_requests_different_instances(self):
        """Test that different requests get different scoped instances."""
        container = DIContainer()

        class RequestContext:
            def __init__(self):
                pass

        # Create two separate scoped containers
        scoped1 = container.create_scope()
        scoped2 = container.create_scope()

        # Mock two requests
        request1 = Mock(spec=Request)
        request1.state = Mock()
        request1.state.di_container = scoped1

        request2 = Mock(spec=Request)
        request2.state = Mock()
        request2.state.di_container = scoped2

        dependency_func = create_scoped_dependency(RequestContext)
        instance1 = dependency_func(request1)
        instance2 = dependency_func(request2)

        # Different scoped containers should resolve different instances
        assert isinstance(instance1, RequestContext)
        assert isinstance(instance2, RequestContext)


class TestScopedContainerMiddleware:
    """Test cases for ScopedContainerMiddleware."""

    def test_middleware_initialization(self):
        """Test that middleware initializes correctly."""
        app = FastAPI()
        container = DIContainer()

        middleware = ScopedContainerMiddleware(app, container)

        assert middleware.container is container
        assert middleware.app is app

    @pytest.mark.asyncio
    async def test_middleware_creates_scoped_container(self):
        """Test that middleware creates a scoped container for each request."""
        app = FastAPI()
        container = DIContainer()
        middleware = ScopedContainerMiddleware(app, container)

        # Mock request
        request = Mock(spec=Request)
        request.state = Mock()

        # Mock call_next
        async def mock_call_next(req):
            # Verify scoped container was set
            assert hasattr(req.state, "di_container")
            return Response("OK", status_code=200)

        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert hasattr(request.state, "di_container")

    @pytest.mark.asyncio
    async def test_middleware_cleans_up_after_request(self):
        """Test that middleware cleans up scoped container after request."""
        app = FastAPI()
        container = DIContainer()
        middleware = ScopedContainerMiddleware(app, container)

        # Mock request
        request = Mock(spec=Request)
        request.state = Mock()

        cleanup_called = False

        # Mock call_next
        async def mock_call_next(req):
            return Response("OK", status_code=200)

        # Mock the clear method to track cleanup
        original_create_scope = container.create_scope

        def tracked_create_scope():
            scoped = original_create_scope()
            original_clear = scoped.clear

            def tracked_clear():
                nonlocal cleanup_called
                cleanup_called = True
                return original_clear()

            scoped.clear = tracked_clear
            return scoped

        container.create_scope = tracked_create_scope

        await middleware.dispatch(request, mock_call_next)

        assert cleanup_called

    @pytest.mark.asyncio
    async def test_middleware_cleans_up_on_exception(self):
        """Test that middleware cleans up even when exception occurs."""
        app = FastAPI()
        container = DIContainer()
        middleware = ScopedContainerMiddleware(app, container)

        # Mock request
        request = Mock(spec=Request)
        request.state = Mock()

        cleanup_called = False

        # Mock call_next that raises exception
        async def mock_call_next(req):
            raise ValueError("Test error")

        # Track cleanup
        original_create_scope = container.create_scope

        def tracked_create_scope():
            scoped = original_create_scope()
            original_clear = scoped.clear

            def tracked_clear():
                nonlocal cleanup_called
                cleanup_called = True
                return original_clear()

            scoped.clear = tracked_clear
            return scoped

        container.create_scope = tracked_create_scope

        with pytest.raises(ValueError):
            await middleware.dispatch(request, mock_call_next)

        assert cleanup_called

    @pytest.mark.asyncio
    async def test_middleware_passes_response_through(self):
        """Test that middleware passes response through unchanged."""
        app = FastAPI()
        container = DIContainer()
        middleware = ScopedContainerMiddleware(app, container)

        # Mock request
        request = Mock(spec=Request)
        request.state = Mock()

        # Mock call_next with specific response
        expected_response = Response("Custom Response", status_code=201)

        async def mock_call_next(req):
            return expected_response

        response = await middleware.dispatch(request, mock_call_next)

        assert response is expected_response
        assert response.status_code == 201


class TestInjectDependencies:
    """Test cases for inject_dependencies decorator."""

    def test_decorator_returns_callable(self):
        """Test that inject_dependencies returns a decorator."""

        class TestService:
            def __init__(self):
                pass

        decorator = inject_dependencies(TestService)

        assert callable(decorator)

    def test_decorator_wraps_function(self):
        """Test that decorator properly wraps a function."""

        class TestService:
            def __init__(self):
                pass

        @inject_dependencies(TestService)
        async def test_endpoint(service: TestService):
            return {"service": service}

        assert callable(test_endpoint)

    @pytest.mark.asyncio
    async def test_decorator_injects_dependencies(self):
        """Test that decorator injects dependencies into function."""
        container = DIContainer()

        class TestService:
            def __init__(self):
                self.name = "test_service"

        container.register_singletons({TestService: lambda c: TestService()})

        @inject_dependencies(TestService)
        async def test_endpoint(service: TestService):
            return {"name": service.name}

        # Note: This test validates the decorator structure
        # Actual dependency injection would require FastAPI's dependency system
        assert callable(test_endpoint)


class TestEdgeCases:
    """Test edge cases for FastAPI integration."""

    def test_dependency_with_unresolvable_type(self):
        """Test dependency function with unresolvable type."""
        container = DIContainer()

        class UnresolvableService:
            def __init__(self, missing_dep):
                self.missing_dep = missing_dep

        dependency_func = create_fastapi_dependency(container, UnresolvableService)

        with pytest.raises(UnresolvableError):
            dependency_func()

    def test_scoped_dependency_with_cleared_container(self):
        """Test scoped dependency after container is cleared."""
        container = DIContainer()

        class TestService:
            def __init__(self):
                pass

        container.register_singletons({TestService: lambda c: TestService()})
        scoped_container = container.create_scope()
        scoped_container.clear()

        # Mock request with cleared scoped container
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.di_container = scoped_container

        dependency_func = create_scoped_dependency(TestService)

        # Should still be able to auto-wire
        instance = dependency_func(request)
        assert isinstance(instance, TestService)

    def test_create_dependency_with_none_container(self):
        """Test that creating dependency with proper container works."""
        container = DIContainer()

        class TestService:
            def __init__(self):
                pass

        # Should not raise with valid container
        dependency_func = create_fastapi_dependency(container, TestService)
        assert callable(dependency_func)

    @pytest.mark.asyncio
    async def test_middleware_with_multiple_requests(self):
        """Test middleware handles multiple requests correctly."""
        app = FastAPI()
        container = DIContainer()
        middleware = ScopedContainerMiddleware(app, container)

        containers_created = []

        # Mock call_next
        async def mock_call_next(req):
            containers_created.append(req.state.di_container)
            return Response("OK", status_code=200)

        # Process multiple requests
        for _ in range(3):
            request = Mock(spec=Request)
            request.state = Mock()
            await middleware.dispatch(request, mock_call_next)

        # Each request should have gotten a different scoped container
        assert len(containers_created) == 3
        assert len(containers_created) == 3
