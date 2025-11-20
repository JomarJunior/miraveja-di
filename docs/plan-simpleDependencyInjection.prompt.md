# Plan: miraveja-di - Auto-Wiring Dependency Injection Module

A lightweight, reusable Python DI container for the Miraveja ecosystem using type hints for automatic resolution. Requires explicit registration only for interface-to-implementation mappings. Built on Python's `inspect` module for constructor introspection with FastAPI integration support.

## Project Structure

Organized following DDD/Hexagonal Architecture principles:

```
miraveja-di/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── miraveja_di/
│       ├── __init__.py                    # Public API exports
│       │
│       ├── domain/                        # Domain Layer - Core business rules and models
│       │   ├── __init__.py
│       │   ├── models.py                  # Registration, DependencyMetadata, ResolutionContext
│       │   ├── enums.py                   # Lifetime enum (Singleton, Transient, Scoped)
│       │   ├── exceptions.py              # DI-specific domain exceptions
│       │   └── interfaces.py              # IContainer, IResolver, ILifetimeManager interfaces
│       │
│       ├── application/                   # Application Layer - Use cases and orchestration
│       │   ├── __init__.py
│       │   ├── container.py               # DIContainer implementation (orchestrates domain)
│       │   ├── resolver.py                # DependencyResolver - auto-wiring logic
│       │   ├── lifetime_manager.py        # LifetimeManager - manages singleton/transient/scoped
│       │   └── circular_detector.py       # CircularDependencyDetector - tracks resolution stack
│       │
│       └── infrastructure/                # Infrastructure Layer - External integrations
│           ├── __init__.py
│           ├── fastapi/
│           │   ├── __init__.py
│           │   └── integration.py         # FastAPI Depends() helpers and middleware
│           └── testing/
│               ├── __init__.py
│               └── utilities.py           # TestContainer, mocking utilities
│
└── tests/
    ├── unit/                              # Unit tests - isolated component testing
    │   └── miraveja_di/
    │       ├── __init__.py
    │       ├── domain/
    │       │   ├── __init__.py
    │       │   ├── test_models.py
    │       │   ├── test_enums.py
    │       │   ├── test_exceptions.py
    │       │   └── test_interfaces.py
    │       ├── application/
    │       │   ├── __init__.py
    │       │   ├── test_container.py
    │       │   ├── test_resolver.py
    │       │   ├── test_lifetime_manager.py
    │       │   └── test_circular_detector.py
    │       └── infrastructure/
    │           ├── __init__.py
    │           ├── fastapi/
    │           │   ├── __init__.py
    │           │   └── test_integration.py
    │           └── testing/
    │               ├── __init__.py
    │               └── test_utilities.py
    │
    └── integration/                       # Integration tests - cross-layer scenarios
        └── miraveja_di/
            ├── __init__.py
            ├── test_end_to_end_resolution.py
            ├── test_fastapi_integration.py
            ├── test_scoped_lifetime.py
            └── test_edge_cases.py
```

## Implementation Steps

### 1. Initialize miraveja-di project structure

Create new Python package with Poetry configuration:
- Package name: `miraveja-di`
- Dependencies: `typing-extensions` (for Python 3.8-3.9 compatibility)
- Optional dependencies: `fastapi` (for FastAPI integration)
- Development dependencies: `pytest`, `pytest-asyncio`, `pytest-cov`, `black`, `pylint`, `isort`, `pre-commit`

### 2. Implement Domain Layer - Core models and rules

Create `src/miraveja_di/domain/` with:

**`models.py`:**
- `Registration` - Value object representing a dependency registration (class, builder, lifetime)
- `DependencyMetadata` - Tracks registration details and cached instances
- `ResolutionContext` - Tracks current resolution stack for circular detection

**`enums.py`:**
- `Lifetime` enum: `SINGLETON`, `TRANSIENT`, `SCOPED`

**`interfaces.py`:**
- `IContainer` - Abstract interface for container operations
- `IResolver` - Abstract interface for dependency resolution
- `ILifetimeManager` - Abstract interface for lifetime management

**`exceptions.py`:**
- `DIException` - Base exception
- `CircularDependencyError` - Shows dependency chain
- `UnresolvableError` - Missing registration or type hint
- `LifetimeError` - Invalid lifetime configuration
- `ScopeError` - Scoped instance requested outside scope

### 3. Implement Application Layer - Use cases and orchestration

Create `src/miraveja_di/application/` with:

**`container.py` (DIContainer):**
- `register_singletons(dependencies: dict[type, Callable[[DIContainer], Any]])` - Register multiple singletons
- `register_transients(dependencies: dict[type, Callable[[DIContainer], Any]])` - Register multiple transients
- `register_factories(dependencies: dict[type, Callable[[DIContainer], Any]])` - Register multiple factories
- `resolve(cls)` - Orchestrates resolution using resolver and lifetime manager
- `create_scope()` - Create child container for scoped lifetime
- `clear()` - Clear all registrations

**`resolver.py` (DependencyResolver):**
- Auto-wiring logic using `inspect` module
- Constructor introspection and type hint analysis
- Dependency graph building

**`lifetime_manager.py` (LifetimeManager):**
- Singleton instance caching
- Transient instance creation
- Scoped instance management per context
- Scope context manager for request/transaction boundaries

**`circular_detector.py` (CircularDependencyDetector):**
- Resolution stack tracking using thread-local storage
- Cycle detection and error reporting with full chain

### 4. Implement Infrastructure Layer - External integrations

Create `src/miraveja_di/infrastructure/` with:

**`fastapi/integration.py`:**
- `create_fastapi_dependency(container, cls)` - Generate FastAPI `Depends()` callable
- `get_from_container(cls)` - Decorator for dependency functions
- `inject_container()` - Middleware to create scoped container per request
- Example usage patterns in docstrings

**`testing/utilities.py`:**
- `TestContainer(parent_container)` - Container that inherits registrations but can override
- `mock_singleton(cls, mock_instance)` - Replace singleton with mock
- `mock_interface(interface, mock_implementation)` - Replace interface mapping
- Auto-cleanup after test execution

### 5. Wire up public API exports

Create `src/miraveja_di/__init__.py` to expose:
- From domain: `Lifetime` enum, all exceptions
- From application: `DIContainer`, `DependencyResolver`, `LifetimeManager`
- From infrastructure: FastAPI integration functions, testing utilities

Follow dependency rule: Domain ← Application ← Infrastructure
- Domain has no dependencies on other layers
- Application depends only on Domain
- Infrastructure depends on Application and Domain

### 6. Write comprehensive tests

Test coverage organized by layer:

**Domain tests:**
- Model validation and value objects
- Enum behavior
- Exception construction and messages

**Application tests:**
- Container registration and resolution (singleton/transient/scoped)
- Resolver auto-wiring with constructor type hints
- Lifetime manager instance caching and scope management
- Circular dependency detector with various cycle scenarios

**Infrastructure tests:**
- FastAPI integration (mocked FastAPI app)
- Testing utilities (mock replacements and overrides)

**Integration tests:**
- End-to-end scenarios across all layers
- Edge cases (missing type hints, abstract classes, etc.)

### 7. Document API and usage patterns

Create `README.md` with:
- Installation instructions
- Quick start examples
- Auto-wiring explanation
- Lifetime comparison table
- FastAPI integration guide
- Testing guide
- Migration from other DI frameworks
- API reference

### 8. Publish to private package registry

- Configure Poetry for Miraveja private registry (PyPI/Artifactory/GitHub Packages)
- Set up CI/CD for automated testing and publishing
- Version: `0.1.0` initial release
- Tag repository with semantic versioning

## Integration with ModelMora

After publishing `miraveja-di`, integrate into ModelMora:

### 1. Add dependency to ModelMora

```toml
[tool.poetry.dependencies]
miraveja-di = "^0.1.0"
```

### 2. Create `src/ModelMora/Dependencies.py`

```python
from miraveja_di import DIContainer
from .configuration import ModelMoraConfig

# Initialize container
container = DIContainer()

# Register singletons using dictionary
container.register_singletons({
    ModelMoraConfig: lambda c: ModelMoraConfig.from_env(),
    DatabaseConnection: lambda c: DatabaseConnection(c.resolve(ModelMoraConfig)),
})

# Register transients using dictionary
container.register_transients({
    ModelHandler: lambda c: ModelHandler(c.resolve(ModelMoraConfig)),
    RequestProcessor: lambda c: RequestProcessor(c.resolve(DatabaseConnection)),
})

# Register factories using dictionary
container.register_factories({
    IModelProvider: lambda c: model_provider_factory(c.resolve(ModelMoraConfig).model_type),
})

# All other services can auto-wire via type hints or be explicitly registered
```

### 3. Use in FastAPI routes

```python
from fastapi import Depends
from miraveja_di.fastapi_integration import create_fastapi_dependency
from .Dependencies import container

get_model_manager = create_fastapi_dependency(container, ModelManager)

@app.get("/models")
async def list_models(manager: ModelManager = Depends(get_model_manager)):
    return await manager.list_loaded_models()
```

## Further Considerations

### 1. Async initialization support?

Some services need `async def __init__()` or `async def initialize()`. Consider:
- `register_async_singleton(cls, init_fn)` - Calls async init on first resolve
- `await container.initialize_async()` - Warm up async singletons on startup

### 2. Decorator-based registration?

Syntactic sugar for registration (alternative to dictionary batch registration):
```python
@container.singleton
class MyService:
    pass

@container.transient
class MyHandler:
    pass
```

Note: Dictionary batch registration is preferred for bulk setup as it's more explicit:
```python
container.register_singletons({
    MyService: lambda c: MyService(),
    MyOtherService: lambda c: MyOtherService(c.resolve(MyService)),
})
```

### 3. Configuration validation?

Validate all registrations before first resolve:
- Detect unresolvable dependencies early
- Check for ambiguous registrations
- Warn about unused registrations

### 4. Performance optimization?

- Cache resolved singletons (avoid re-inspection)
- Pre-compile dependency graphs
- Lazy vs eager singleton initialization options

### 5. Multi-container support?

Named containers for different contexts (e.g., separate containers for API vs Worker):
```python
api_container = DIContainer()
worker_container = DIContainer()
```
