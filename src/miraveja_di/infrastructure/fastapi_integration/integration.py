import inspect
from typing import Any, Awaitable, Callable, Type, TypeVar

from fastapi import Depends, FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from miraveja_di.application import DIContainer
from miraveja_di.domain import IContainer

T = TypeVar("T")


def create_fastapi_dependency(container: IContainer, dependency_type: Type[T]) -> Callable[[], T]:
    """Create a FastAPI Depends() callable that resolves from the DI container.

    This function generates a dependency function compatible with FastAPI's
    Depends() system. The resolved instance lifetime follows the registration
    in the container (singleton, transient, or scoped).

    Args:
        container: The DI container to resolve dependencies from.
        dependency_type: The type to resolve when the dependency is called.

    Returns:
        A callable that FastAPI can use with Depends().

    Example:
        >>> container = DIContainer()
        >>> container.register_singletons({
        ...     UserRepository: lambda c: UserRepository(c.resolve(DatabaseConnection)),
        ... })
        >>>
        >>> get_user_repo = create_fastapi_dependency(container, UserRepository)
        >>>
        >>> @app.get("/users")
        >>> async def list_users(repo: UserRepository = Depends(get_user_repo)):
        ...     return await repo.get_all()
    """

    def dependency() -> T:
        """Resolve the dependency from the container."""
        return container.resolve(dependency_type)

    return dependency


def create_scoped_dependency(dependency_type: Type[T]) -> Callable[[Request], T]:
    """Create a FastAPI dependency that uses request-scoped container.

    This function creates a dependency that resolves from the request's scoped
    container, ensuring each request gets its own instance of scoped dependencies.

    Requires the ScopedContainerMiddleware to be installed.

    Args:
        dependency_type: The type to resolve from the scoped container.

    Returns:
        A callable that resolves from the request-scoped container.

    Example:
        >>> app.add_middleware(ScopedContainerMiddleware, container=container)
        >>>
        >>> get_request_context = create_scoped_dependency(RequestContext)
        >>>
        >>> @app.get("/process")
        >>> async def process_request(ctx: RequestContext = Depends(get_request_context)):
        ...     return {"request_id": ctx.request_id}
    """

    def scoped_dependency(request: Request) -> T:
        """Resolve from the request's scoped container."""
        if not hasattr(request.state, "di_container"):
            raise RuntimeError(
                "Reqeust does not have a scoped DI container. ", "Did you forget to add ScopedContainerMiddleware?"
            )
        scoped_container: IContainer = request.state.di_container
        return scoped_container.resolve(dependency_type)

    return scoped_dependency


class ScopedContainerMiddleware(BaseHTTPMiddleware):
    """Middleware that creates a scoped DI container for each request.

    This middleware creates a child container for each HTTP request, allowing
    scoped lifetime dependencies to be properly isolated per request.

    The scoped container is accessible via `request.state.di_container`.

    Attributes:
        container: The parent DI container to create scopes from.

    Example:
        >>> container = DIContainer()
        >>> container.register_singletons({
        ...     DatabaseConnection: lambda c: DatabaseConnection(),
        ... })
        >>>
        >>> app = FastAPI()
        >>> app.add_middleware(ScopedContainerMiddleware, container=container)
        >>>
        >>> @app.get("/")
        >>> async def root(request: Request):
        ...     scoped_container = request.state.di_container
        ...     # Use scoped container for request-specific dependencies
        ...     return {"message": "Hello"}
    """

    def __init__(self, app: FastAPI, container: IContainer):
        """Initialize the middleware with a parent container.

        Args:
            app: The FastAPI/Starlette application.
            container: The parent DI container to create scopes from.
        """
        super().__init__(app)
        self.container = container

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Create a scoped container for the request and execute the endpoint.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or endpoint handler.

        Returns:
            The response from the endpoint.
        """
        # Create scoped container for this request
        scoped_container = self.container.create_scope()
        request.state.di_container = scoped_container

        try:
            response = await call_next(request)
            return response
        finally:
            # Cleanup scoped instances after request
            scoped_container.clear()


def inject_dependencies(*dependency_types: Type[Any]) -> Callable:
    """Decorator that injects dependencies into a FastAPI endpoint function.

    This decorator automatically resolves and injects the specified dependencies
    as keyword arguments to the decorated function.

    Args:
        *dependency_types: Types to resolve and inject.

    Returns:
        A decorator function.

    Example:
        >>> container = DIContainer()
        >>>
        >>> @app.get("/users")
        >>> @inject_dependencies(UserService, Logger)
        >>> async def list_users(user_service: UserService, logger: Logger):
        ...     logger.info("Listing users")
        ...     return await user_service.get_all()
    """

    def decorator(func: Callable) -> Callable:
        """Wrap the function with dependency injection logic."""
        signature = inspect.signature(func)
        param_names = list(signature.parameters.keys())

        # Create dependency resolvers
        dependencies = []
        for dep_type in dependency_types:
            dep_func = create_fastapi_dependency(DIContainer(), dep_type)
            dependencies.append(Depends(dep_func))

        async def wrapper(*args, **kwargs):
            """Resolve dependencies and call the original function."""
            # Add resolved dependencies to kwargs
            for param_name, dep in zip(param_names, dependencies):
                if param_name not in kwargs:
                    kwargs[param_name] = dep()

            return await func(*args, **kwargs)

        return wrapper

    return decorator
