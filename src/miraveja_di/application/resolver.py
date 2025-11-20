import inspect
from typing import Any, Type, get_type_hints

from miraveja_di.domain import IContainer, IResolver, UnresolvableError


class DependencyResolver(IResolver):
    """Resolves dependencies using constructor introspection and type hints.

    Uses Python's inspect module to analyze constructor signatures and
    automatically resolve dependencies based on type hints.
    """

    def resolve_dependencies(self, dependency_type: Type, container: IContainer) -> Any:
        """Resolve all constructor dependencies and create instance.

        Args:
            dependency_type: The type to instantiate.
            container: The container to resolve dependencies from.

        Returns:
            Instance with all dependencies injected.

        Raises:
            UnresolvableError: If any dependency cannot be resolved or lacks type hint.

        Example:
            >>> class UserService:
            ...     def __init__(self, db: DatabaseConnection, logger: Logger):
            ...         self.db = db
            ...         self.logger = logger
            >>>
            >>> resolver = DependencyResolver()
            >>> instance = resolver.resolve_dependencies(UserService, container)
        """
        try:
            # Get constructor signature
            signature = inspect.signature(dependency_type.__init__)

            # Get type hints for constructor parameters
            type_hints = get_type_hints(dependency_type.__init__)

            # Build kwargs for constructor
            kwargs = {}
            for param_name, param in signature.parameters.items():
                # Skip 'self' parameter
                if param_name == "self":
                    continue

                # Skip *args and **kwargs parameters (VAR_POSITIONAL and VAR_KEYWORD)
                if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                    continue

                # Skip parameters with defaults (let them use default values)
                if param.default is not inspect.Parameter.empty:
                    continue

                # Check if parameter has type hint
                if param_name not in type_hints:
                    raise UnresolvableError(
                        dependency_type,
                        f"Parameter '{param_name}' lacks type hint and has no default value.",
                    )

                # Get parameter type
                param_type = type_hints[param_name]

                # Resolve dependency recursively
                try:
                    kwargs[param_name] = container.resolve(param_type)
                except Exception as e:
                    raise UnresolvableError(
                        dependency_type,
                        f"Failed to resolve dependency for parameter '{param_name}': {e}",
                    ) from e

            # Create instance with resolved dependencies
            instance = dependency_type(**kwargs)
            return instance

        except UnresolvableError:
            raise
        except Exception as e:
            raise UnresolvableError(
                dependency_type,
                f"Failed to auto-wire constructor for {dependency_type}: {e}",
            ) from e
