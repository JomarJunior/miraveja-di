# GitHub Copilot Instructions for miraveja-di

## Project Overview

miraveja-di is a lightweight, type-hint based Dependency Injection container for Python with auto-wiring capabilities. It follows DDD/Hexagonal Architecture principles with clear separation between Domain, Application, and Infrastructure layers.

## Architecture Principles

### Layered Architecture
- **Domain Layer** (`src/miraveja_di/domain/`): Core business logic, models, enums, interfaces, and exceptions. NO dependencies on other layers.
- **Application Layer** (`src/miraveja_di/application/`): Use cases and orchestration. Depends ONLY on Domain layer.
- **Infrastructure Layer** (`src/miraveja_di/infrastructure/`): External integrations (FastAPI, testing). Depends on Application and Domain layers.

**Dependency Rule**: Domain ← Application ← Infrastructure

### Key Design Patterns
- **Dependency Injection**: Constructor injection with type hints for auto-wiring
- **Factory Pattern**: Lambda-based builders for dependency construction
- **Repository Pattern**: Batch registration using dictionaries
- **Value Objects**: Immutable domain models

## Code Style Guidelines

### Python Standards
- **Python Version**: 3.10+ (use modern type hints)
- **Line Length**: 120 characters maximum
- **Formatter**: black
- **Import Sorter**: isort (black profile)
- **Linter**: pylint
- **Type Checker**: mypy with strict mode

### Naming Conventions
- **Modules**: `snake_case` (e.g., `lifetime_manager.py`)
- **Classes**: `PascalCase` (e.g., `DIContainer`, `DependencyResolver`)
- **Functions/Methods**: `snake_case` (e.g., `register_singletons`, `resolve`)
- **Constants**: `UPPER_CASE` (e.g., `SINGLETON`, `TRANSIENT`)
- **Private members**: Prefix with `_` (e.g., `_cache`, `_resolve_internal`)

### Type Hints
- **Always use type hints** for function parameters and return types
- Use `from typing import` for complex types (Dict, List, Optional, Callable, etc.)
- Use `typing-extensions` for compatibility features
- Generic types: Use `TypeVar` for generic container operations (e.g., `T = TypeVar('T')`)

Example:
```python
from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar('T')

def resolve(self, cls: type[T]) -> T:
    """Resolve and return an instance of the specified type."""
    pass
```

## Registration Pattern

### Dictionary-Based Batch Registration
Use dictionaries for registering multiple dependencies at once:

```python
container.register_singletons({
    ConfigService: lambda c: ConfigService.from_env(),
    DatabaseConnection: lambda c: DatabaseConnection(c.resolve(ConfigService)),
})

container.register_transients({
    RequestHandler: lambda c: RequestHandler(c.resolve(DatabaseConnection)),
})
```

**Key Points**:
- Key: Dependency class type
- Value: Lambda function `lambda c: ...` that receives container and returns instance
- Lambda allows deferred resolution and access to container

### Lifetime Management
- **Singleton**: `register_singletons()` - Single instance for entire application
- **Transient**: `register_transients()` - New instance per resolution
- **Scoped**: Via `create_scope()` - Single instance per scope context

## Testing Standards

### Test Organization
- **Unit Tests**: `tests/unit/miraveja_di/{layer}/` - Isolated component testing
- **Integration Tests**: `tests/integration/miraveja_di/` - Cross-layer scenarios
- Mirror source structure in test directories

### Test Naming
- Test files: `test_{module_name}.py`
- Test classes: `Test{ClassName}`
- Test functions: `test_{behavior}_when_{condition}`

Example:
```python
def test_resolve_returns_singleton_when_registered():
    """Test that resolve returns the same instance for singletons."""
    pass

def test_resolve_raises_error_when_circular_dependency():
    """Test that circular dependencies are detected and raise error."""
    pass
```

### Test Structure
- **Arrange**: Set up container and dependencies
- **Act**: Perform the operation
- **Assert**: Verify the outcome

### Mocking
- Use `pytest-mock` for mocking
- Use `TestContainer` for dependency overrides in tests
- Mock external dependencies, not domain logic

## Domain Layer Guidelines

### Models (`domain/models.py`)
- Use `@dataclass` or Pydantic models for value objects
- Keep models immutable where possible
- No business logic in models - only data and validation

### Exceptions (`domain/exceptions.py`)
- Inherit from `DIException` base class
- Provide clear, actionable error messages
- Include context (e.g., dependency chain for circular errors)

### Interfaces (`domain/interfaces.py`)
- Use `abc.ABC` and `@abstractmethod` for interfaces
- Keep interfaces focused and cohesive
- Name with `I` prefix (e.g., `IContainer`, `IResolver`)

## Application Layer Guidelines

### Container (`application/container.py`)
- Orchestrate domain objects (resolver, lifetime manager, detector)
- Delegate complex logic to specialized components
- Keep public API simple and intuitive

### Resolver (`application/resolver.py`)
- Use `inspect` module for constructor introspection
- Extract type hints from `__init__` parameters
- Handle edge cases (missing hints, forward references, unions)

### Lifetime Manager (`application/lifetime_manager.py`)
- Manage instance caching for singletons
- Create new instances for transients
- Handle scoped contexts with proper cleanup

## Infrastructure Layer Guidelines

### FastAPI Integration (`infrastructure/fastapi/integration.py`)
- Provide `create_fastapi_dependency()` helper
- Support scoped dependencies per request
- Include comprehensive docstrings with usage examples

### Testing Utilities (`infrastructure/testing/utilities.py`)
- `TestContainer` should inherit from parent container
- Allow selective override of registrations
- Automatic cleanup after test execution

## Documentation Standards

### Docstrings
- Use Google-style docstrings
- Include description, parameters, returns, and raises sections
- Provide usage examples for public APIs

Example:
```python
def register_singletons(self, dependencies: Dict[type, Callable[[DIContainer], Any]]) -> None:
    """Register multiple singleton dependencies at once.

    Args:
        dependencies: Dictionary mapping dependency types to builder functions.
                     Each builder receives the container and returns an instance.

    Raises:
        LifetimeError: If a dependency is already registered with a different lifetime.

    Example:
        >>> container.register_singletons({
        ...     ConfigService: lambda c: ConfigService.from_env(),
        ...     Database: lambda c: Database(c.resolve(ConfigService)),
        ... })
    """
    pass
```

### Comments
- Use comments sparingly - prefer self-documenting code
- Explain *why*, not *what* (code shows what)
- Use `# TODO:` for future improvements
- Use `# FIXME:` for known issues

## Common Patterns

### Auto-Wiring
When implementing auto-wiring:
1. Use `inspect.signature()` to get constructor parameters
2. Extract type hints from parameters
3. Recursively resolve dependencies
4. Track resolution stack for circular detection

### Circular Dependency Detection
- Use thread-local storage for resolution stack
- Push class to stack before resolving
- Check for cycles before each resolution
- Pop from stack after successful resolution

### Scoped Lifetimes
- Create child container for scope
- Inherit parent registrations
- Maintain separate instance cache
- Clean up on scope exit

## Error Handling

### Exception Guidelines
- Catch specific exceptions, not generic `Exception`
- Provide context in error messages
- Chain exceptions with `from` when re-raising
- Log errors at appropriate levels

Example:
```python
try:
    instance = builder(self)
except Exception as e:
    raise UnresolvableError(
        f"Failed to build instance of {cls.__name__}: {e}"
    ) from e
```

## Performance Considerations

- Cache resolved singletons to avoid re-inspection
- Lazy initialization by default
- Consider eager initialization option for startup
- Use `__slots__` for frequently instantiated classes

## Commit Message Style

Follow conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions or modifications
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

Example: `feat(container): add batch registration for singletons`

## Dependencies

### Core Dependencies
- `typing-extensions`: Type hint compatibility

### Optional Dependencies
- `fastapi`: Web framework integration

### Development Dependencies
- `pytest`, `pytest-asyncio`, `pytest-cov`: Testing
- `black`: Code formatting
- `isort`: Import sorting
- `pylint`: Linting
- `mypy`: Type checking
- `pre-commit`: Git hooks

## Pre-commit Hooks

Run before each commit:
1. `black` - Format code
2. `isort` - Sort imports
3. `pylint` - Check code quality
4. `mypy` - Type checking
5. `pytest` - Run tests

## References

- [Plan Document](../docs/plan-simpleDependencyInjection.prompt.md)
- [README](../README.md)
- [Architecture: DDD/Hexagonal](https://herbertograca.com/2017/11/16/explicit-architecture-01-ddd-hexagonal-onion-clean-cqrs-how-i-put-it-all-together/)
