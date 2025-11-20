# 💉 miraveja-di

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)](#-development-status)
[![Coverage](https://codecov.io/gh/JomarJunior/miraveja-di/branch/main/graph/badge.svg)](https://codecov.io/gh/JomarJunior/miraveja-di)
[![CI](https://github.com/JomarJunior/miraveja-di/actions/workflows/ci.yml/badge.svg)](https://github.com/JomarJunior/miraveja-di/actions)

> A lightweight, type-hint based Dependency Injection container for Python with auto-wiring capabilities

**Etymology**: Combining "dependency injection" with the Miraveja ecosystem naming convention

## 🚀 Overview

miraveja-di is a modern dependency injection container that leverages Python's type hints for automatic dependency resolution. Built with DDD/Hexagonal Architecture principles, it provides a clean, testable way to manage dependencies in your applications.

Part of the **Miraveja** ecosystem, miraveja-di provides dependency management infrastructure for all ecosystem services.

## ✨ Key Features

- 🔍 **Auto-wiring** - Automatically resolve dependencies using constructor type hints
- ⏱️ **Multiple Lifetimes** - Support for Singleton, Transient, and Scoped lifetimes
- 📦 **Batch Registration** - Register multiple dependencies at once using dictionaries
- 🔄 **Circular Dependency Detection** - Detect and report circular dependencies with full chain
- ⚡ **FastAPI Integration** - First-class support for FastAPI with `Depends()` helpers
- 🧪 **Testing Utilities** - Built-in mocking and override capabilities for testing
- 🏗️ **Clean Architecture** - Organized following DDD/Hexagonal Architecture principles

## 🛠️ Technology Stack

### 🐍 Core Runtime

- **Python 3.10+** - Type hints and modern Python features
- **typing-extensions** - Compatibility for Python 3.8-3.9

### 🌐 Optional Integrations

- **FastAPI** - Web framework integration
- **pytest** - Testing framework support

### 🧪 Development

- **pytest** - Testing framework with async support
- **pytest-asyncio** - Async testing utilities
- **pytest-cov** - Coverage reporting
- **black** - Code formatter
- **pylint** - Code quality checker
- **isort** - Import statement organizer
- **pre-commit** - Git hook framework for automated checks

## 🏛️ Architecture

miraveja-di follows Domain-Driven Design and Hexagonal Architecture principles:

```text
src/miraveja_di/
├── 🧠 domain/           # Core business logic (models, enums, interfaces, exceptions)
├── 🎬 application/      # Use cases (container, resolver, lifetime manager)
└── 🔌 infrastructure/   # External integrations (FastAPI, testing utilities)
```

**Dependency Rule**: Domain ← Application ← Infrastructure

- **Domain** has no dependencies on other layers
- **Application** depends only on Domain
- **Infrastructure** depends on Application and Domain

## 🎯 Getting Started

### 📋 Prerequisites

- Python 3.10+
- Poetry 2.0+ (recommended) or pip

### 🚀 Installation

```bash
poetry add miraveja-di
```

Or with pip:

```bash
pip install miraveja-di
```

For FastAPI integration:

```bash
poetry add miraveja-di[fastapi]
```

## 📖 Quick Start

### Basic Usage

```python
from miraveja_di import DIContainer, Lifetime

# Initialize container
container = DIContainer()

# Register dependencies
container.register_singletons({
    DatabaseConfig: lambda c: DatabaseConfig.from_env(),
    DatabaseConnection: lambda c: DatabaseConnection(c.resolve(DatabaseConfig)),
})

container.register_transients({
    RequestHandler: lambda c: RequestHandler(c.resolve(DatabaseConnection)),
})

# Register scoped dependencies (per-request state)
container.register_scoped({
    RequestContext: lambda c: RequestContext(),
})

# Resolve dependencies (auto-wiring)
handler = container.resolve(RequestHandler)

# Use scoped container for request-specific dependencies
with container.create_scope() as scoped:
    ctx = scoped.resolve(RequestContext)
    # Same instance within this scope
    ctx2 = scoped.resolve(RequestContext)
    assert ctx is ctx2
```

### Auto-Wiring

The container automatically resolves constructor dependencies using type hints:

```python
class UserService:
    def __init__(self, db: DatabaseConnection, logger: Logger):
        self.db = db
        self.logger = logger

# Only register what can't be auto-wired
container.register_singletons({
    DatabaseConnection: lambda c: DatabaseConnection("postgresql://..."),
    Logger: lambda c: Logger("app.log"),
})

# UserService will be auto-wired
user_service = container.resolve(UserService)
```

## ⏱️ Lifetime Management

### Singleton

Single instance shared across the entire application:

```python
container.register_singletons({
    AppConfig: lambda c: AppConfig.from_env(),
    CacheService: lambda c: CacheService(c.resolve(AppConfig)),
})
```

### Transient

New instance created every time it's resolved:

```python
container.register_transients({
    RequestProcessor: lambda c: RequestProcessor(),
    EventHandler: lambda c: EventHandler(c.resolve(EventBus)),
})
```

### Scoped

Single instance per scope (e.g., per HTTP request):

```python
# Register scoped dependencies
container.register_scoped({
    RequestContext: lambda c: RequestContext(),
    RequestLogger: lambda c: RequestLogger(c.resolve(RequestContext)),
})

# Create a scope using context manager
with container.create_scope() as scoped_container:
    # Same instance within this scope
    service1 = scoped_container.resolve(RequestContext)
    service2 = scoped_container.resolve(RequestContext)
    assert service1 is service2

# Scoped instances automatically cleaned up after exiting the context
```

### Lifetime Comparison Table

| Lifetime | Instance Count | Shared Across | Use Case | Registration Method |
|----------|---------------|---------------|----------|--------------------|
| **Singleton** | One per application | Entire application | Configuration, database connections, caches | `register_singletons()` |
| **Transient** | New every time | Not shared | Lightweight, stateless operations | `register_transients()` |
| **Scoped** | One per scope | Within scope (e.g., HTTP request) | Request-specific state, transactions | `register_scoped()` |

**Key Behaviors:**

- **Singleton**: Instances created once and cached for the lifetime of the application
- **Transient**: New instance created every time `resolve()` is called
- **Scoped**: Instances cached within a scope, shared by all resolutions in that scope, cleaned up when scope exits

## ⚡ FastAPI Integration

### Basic Integration

```python
from fastapi import FastAPI, Depends
from miraveja_di import DIContainer
from miraveja_di.infrastructure.fastapi_integration import create_fastapi_dependency

app = FastAPI()
container = DIContainer()

# Register dependencies
container.register_singletons({
    DatabaseConnection: lambda c: DatabaseConnection(),
    UserRepository: lambda c: UserRepository(c.resolve(DatabaseConnection)),
    UserService: lambda c: UserService(c.resolve(UserRepository)),
})

# Create FastAPI dependency
get_user_service = create_fastapi_dependency(container, UserService)

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.get_user(user_id)
```

### Scoped Dependencies per Request

Use middleware to create a scoped container for each HTTP request:

```python
from miraveja_di.infrastructure.fastapi_integration import (
    ScopedContainerMiddleware,
    create_scoped_dependency,
)
from fastapi import Request

# Add middleware to create scoped container per request
app.add_middleware(ScopedContainerMiddleware, container=container)

# Register scoped dependencies
container.register_scoped({
    RequestContext: lambda c: RequestContext(),
    RequestLogger: lambda c: RequestLogger(c.resolve(RequestContext)),
})

# Use scoped dependency in route
@app.get("/items")
async def list_items(
    request: Request,
    ctx: RequestContext = Depends(create_scoped_dependency(RequestContext))
):
    # RequestContext is scoped to this request
    # Same instance shared across all dependencies in this request
    return {"request_id": ctx.request_id}
```

### Complete FastAPI Example

```python
from fastapi import FastAPI, Depends, Request
from miraveja_di import DIContainer
from miraveja_di.infrastructure.fastapi_integration import (
    ScopedContainerMiddleware,
    create_fastapi_dependency,
    create_scoped_dependency,
)

# Initialize container
container = DIContainer()

# Register singletons (shared across all requests)
container.register_singletons({
    AppConfig: lambda c: AppConfig.from_env(),
    DatabaseConnection: lambda c: DatabaseConnection(c.resolve(AppConfig)),
    CacheService: lambda c: CacheService(),
})

# Register scoped (per-request)
container.register_scoped({
    RequestContext: lambda c: RequestContext(),
    UnitOfWork: lambda c: UnitOfWork(c.resolve(DatabaseConnection)),
})

# Register transients (new instance each time)
container.register_transients({
    UserService: lambda c: UserService(
        c.resolve(UserRepository),
        c.resolve(CacheService),
    ),
})

# Setup FastAPI
app = FastAPI()
app.add_middleware(ScopedContainerMiddleware, container=container)

# Create dependency injectors
get_user_service = create_fastapi_dependency(container, UserService)
get_request_context = create_scoped_dependency(RequestContext)

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
    ctx: RequestContext = Depends(get_request_context),
):
    ctx.log(f"Getting user {user_id}")
    return await user_service.get_user(user_id)
```

## 🧪 Testing

### Using TestContainer

The `TestContainer` allows you to create isolated test environments with mocked dependencies:

```python
from miraveja_di.infrastructure.testing import TestContainer
import pytest

def test_user_service():
    # Create test container (inherits from your main container)
    test_container = TestContainer(container)

    # Mock dependencies
    mock_repo = MockUserRepository()
    test_container.mock_singleton(UserRepository, mock_repo)

    # Resolve service with mocked dependency
    service = test_container.resolve(UserService)

    # Test service
    result = service.get_user(123)
    assert result == expected_user
    assert mock_repo.get_user.called_with(123)
```

### Override Registrations

```python
def test_with_override():
    test_container = TestContainer(container)

    # Override specific registration
    test_container.register_singletons({
        EmailService: lambda c: MockEmailService(),
    })

    service = test_container.resolve(NotificationService)
    # EmailService is mocked, other dependencies are real
```

### Testing Scoped Dependencies with MockScope

Use `MockScope` for testing request-scoped dependencies:

```python
from miraveja_di.infrastructure.testing import MockScope

def test_request_handler():
    # Create scoped context for testing
    with MockScope(container) as scoped:
        # Register request-specific mocks
        scoped.register_scoped({
            RequestContext: lambda c: RequestContext(user_id="test-user"),
        })

        # Resolve dependencies
        handler = scoped.resolve(RequestHandler)
        ctx = scoped.resolve(RequestContext)

        # Same instance within scope
        assert handler.context is ctx
        assert ctx.user_id == "test-user"

    # Scoped instances automatically cleaned up
```

### Testing with Pytest Fixtures

```python
import pytest
from miraveja_di import DIContainer
from miraveja_di.infrastructure.testing import TestContainer, create_mock_container

@pytest.fixture
def app_container():
    """Base container with real registrations."""
    container = DIContainer()
    container.register_singletons({
        DatabaseConnection: lambda c: DatabaseConnection(),
        CacheService: lambda c: CacheService(),
    })
    return container

@pytest.fixture
def test_container(app_container):
    """Test container with mocked external dependencies."""
    test_container = TestContainer(app_container)
    test_container.mock_singleton(DatabaseConnection, MockDatabase())
    return test_container

def test_user_service_get_user(test_container):
    service = test_container.resolve(UserService)
    user = service.get_user(123)
    assert user.id == 123

def test_user_service_create_user(test_container):
    service = test_container.resolve(UserService)
    new_user = service.create_user("John Doe")
    assert new_user.name == "John Doe"
```

### Quick Mock Container

For simple tests, use `create_mock_container()`:

```python
from miraveja_di.infrastructure.testing import create_mock_container

def test_simple_service():
    # Create container with mocked singletons
    mock_db = MockDatabase()
    mock_cache = MockCache()

    test_container = create_mock_container(
        (DatabaseConnection, mock_db),
        (CacheService, mock_cache),
    )

    service = test_container.resolve(UserService)
    # UserService will use mocked db and cache
    result = service.get_user(123)
    assert result is not None
```

## 🔄 Migration from Other DI Frameworks

### From `dependency-injector`

**dependency-injector:**

```python
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    database = providers.Singleton(DatabaseConnection, config.db_url)
    user_service = providers.Factory(UserService, database)
```

**miraveja-di:**

```python
from miraveja_di import DIContainer

container = DIContainer()
container.register_singletons({
    AppConfig: lambda c: AppConfig.from_env(),
    DatabaseConnection: lambda c: DatabaseConnection(c.resolve(AppConfig).db_url),
})
container.register_transients({
    UserService: lambda c: UserService(c.resolve(DatabaseConnection)),
})
```

### From `injector`

**injector:**

```python
from injector import Injector, inject, singleton

class DatabaseConnection:
    pass

class UserService:
    @inject
    def __init__(self, db: DatabaseConnection):
        self.db = db

injector = Injector()
injector.binder.bind(DatabaseConnection, to=DatabaseConnection, scope=singleton)
user_service = injector.get(UserService)
```

**miraveja-di:**

```python
from miraveja_di import DIContainer

class DatabaseConnection:
    pass

class UserService:
    def __init__(self, db: DatabaseConnection):
        self.db = db

container = DIContainer()
container.register_singletons({
    DatabaseConnection: lambda c: DatabaseConnection(),
})
# UserService auto-wired via type hints
user_service = container.resolve(UserService)
```

### From `FastAPI Depends()`

**FastAPI Depends:**

```python
from fastapi import Depends

def get_database():
    db = DatabaseConnection()
    try:
        yield db
    finally:
        db.close()

def get_user_service(db: DatabaseConnection = Depends(get_database)):
    return UserService(db)

@app.get("/users/{user_id}")
async def get_user(service: UserService = Depends(get_user_service)):
    return service.get_user(user_id)
```

**miraveja-di with FastAPI:**

```python
from miraveja_di import DIContainer
from miraveja_di.infrastructure.fastapi_integration import (
    ScopedContainerMiddleware,
    create_fastapi_dependency,
)

container = DIContainer()
container.register_singletons({
    DatabaseConnection: lambda c: DatabaseConnection(),
})
# UserService auto-wired

app.add_middleware(ScopedContainerMiddleware, container=container)
get_user_service = create_fastapi_dependency(container, UserService)

@app.get("/users/{user_id}")
async def get_user(service: UserService = Depends(get_user_service)):
    return service.get_user(user_id)
```

### Key Differences

| Feature | miraveja-di | dependency-injector | injector |
|---------|-------------|---------------------|----------|
| **Configuration Style** | Imperative (dictionaries) | Declarative (containers) | Mixed |
| **Auto-wiring** | ✅ Type hints | ❌ Manual providers | ✅ Type hints |
| **Scoped Lifetime** | ✅ Built-in | ✅ Request scopes | ✅ Request scopes |
| **FastAPI Integration** | ✅ First-class | ✅ Via providers | ⚠️ Third-party |
| **Testing Utilities** | ✅ TestContainer, MockScope | ✅ Override providers | ⚠️ Manual |
| **Learning Curve** | Low (simple API) | Medium (declarative) | Medium (decorators) |

## 🔧 Advanced Usage

### Factory Functions

```python
def create_model_provider(model_type: str):
    if model_type == "clip":
        return CLIPModelProvider()
    elif model_type == "dinov2":
        return DINOv2ModelProvider()
    return SAMModelProvider()

container.register_factories({
    IModelProvider: lambda c: create_model_provider(
        c.resolve(AppConfig).model_type
    ),
})
```

### Circular Dependency Detection

```python
# This will raise CircularDependencyError with full chain
class ServiceA:
    def __init__(self, b: 'ServiceB'):
        self.b = b

class ServiceB:
    def __init__(self, a: ServiceA):
        self.a = a

# CircularDependencyError: ServiceA -> ServiceB -> ServiceA
container.resolve(ServiceA)
```

### Conditional Registration

```python
config = AppConfig.from_env()

if config.use_cache:
    container.register_singletons({
        CacheService: lambda c: RedisCacheService(config.redis_url),
    })
else:
    container.register_singletons({
        CacheService: lambda c: InMemoryCacheService(),
    })
```

## 📚 API Reference

### DIContainer

**Registration Methods:**

- `register_singletons(dependencies: dict[type, Callable[[DIContainer], Any]])` - Register multiple singleton dependencies (one instance per application)
- `register_transients(dependencies: dict[type, Callable[[DIContainer], Any]])` - Register multiple transient dependencies (new instance per resolution)
- `register_scoped(dependencies: dict[type, Callable[[DIContainer], Any]])` - Register multiple scoped dependencies (one instance per scope)

**Resolution Methods:**

- `resolve(cls: type[T]) -> T` - Resolve and return an instance of the specified type with auto-wiring

**Scope Management:**

- `create_scope() -> DIContainer` - Create a child container for scoped lifetime (inherits parent registrations and singleton cache)
- `__enter__() -> DIContainer` - Enter context manager for scoped lifetime
- `__exit__(exc_type, exc_val, exc_tb) -> None` - Exit context manager and cleanup scoped instances

**Utilities:**

- `clear()` - Clear all registrations and cached instances
- `get_registry_copy() -> dict[type, DependencyMetadata]` - Get a copy of the current registry
- `set_registry(registry: dict[type, DependencyMetadata])` - Set the registry (used internally for scope creation)

### Lifetime Enum

- `Lifetime.SINGLETON` - Single instance for entire application
- `Lifetime.TRANSIENT` - New instance per resolution
- `Lifetime.SCOPED` - Single instance per scope

### Exceptions

- `DIException` - Base exception for all DI errors
- `CircularDependencyError` - Raised when circular dependencies are detected
- `UnresolvableError` - Raised when a dependency cannot be resolved
- `LifetimeError` - Raised for invalid lifetime configurations
- `ScopeError` - Raised when scoped instance requested outside scope

## 💡 Best Practices

1. **Register interfaces, not implementations**: Register abstract interfaces and let the container provide concrete implementations
2. **Use constructor injection**: Prefer constructor parameters over property injection
3. **Keep registrations centralized**: Create a single `Dependencies.py` module for registration
4. **Leverage auto-wiring**: Only register dependencies that can't be auto-wired
5. **Test with mocks**: Use `TestContainer` to override dependencies in tests
6. **Scope per request**: Use scoped lifetime for request-specific state in web applications

## 🚧 Development Status

**Active Development** - Core features implemented and tested

✅ **Completed:**

- Dependency injection container with auto-wiring
- Singleton, Transient, and Scoped lifetimes
- Circular dependency detection
- FastAPI integration with middleware support
- Testing utilities (TestContainer, MockScope)
- Exception handling and error reporting
- 96%+ test coverage

🚀 **Planned Features:**

- Async initialization support
- Decorator-based registration
- Configuration validation
- Performance optimizations

See the [architecture plan](docs/plan-simpleDependencyInjectio.prompt.md) for detailed implementation notes.

## 🤝 Contributinging

Contributions are welcome! Please follow the existing code structure and ensure all tests pass.

```bash
# Run all tests
poetry run pytest

# Generate coverage report
poetry run pytest --cov=miraveja_di --cov-report=html

# Run linting
poetry run pylint src/miraveja_di

# Format code
poetry run black .

# Sort imports
poetry run isort .

# Run pre-commit hooks
poetry run pre-commit run --all-files
```

## 📄 License

MIT License - See LICENSE file for details.

## 👨‍💻 Author

**Jomar Júnior de Souza Pereira** - <jomarjunior@poli.ufrj.br>

---

Part of the **Miraveja** ecosystem - A modern image gallery and management platform.
