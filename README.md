# 💉 miraveja-di

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Status](https://img.shields.io/badge/status-planning-yellow.svg)](#-development-status)

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

# Resolve dependencies (auto-wiring)
handler = container.resolve(RequestHandler)
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
# Create a scope
with container.create_scope() as scoped_container:
    # Same instance within this scope
    service1 = scoped_container.resolve(RequestContext)
    service2 = scoped_container.resolve(RequestContext)
    assert service1 is service2
```

## ⚡ FastAPI Integration

```python
from fastapi import FastAPI, Depends
from miraveja_di import DIContainer
from miraveja_di.infrastructure.fastapi import create_fastapi_dependency

app = FastAPI()
container = DIContainer()

# Register dependencies
container.register_singletons({
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

```python
from miraveja_di.infrastructure.fastapi import inject_container

# Add middleware to create scoped container per request
app.add_middleware(inject_container(container))

# Now scoped registrations work per-request
container.register_scoped({
    RequestContext: lambda c: RequestContext(),
})
```

## 🧪 Testing

### Mock Dependencies

```python
from miraveja_di.infrastructure.testing import TestContainer

def test_user_service():
    # Create test container with overrides
    test_container = TestContainer(container)

    # Mock dependencies
    mock_repo = MockUserRepository()
    test_container.mock_singleton(UserRepository, mock_repo)

    # Resolve service with mocked dependency
    service = test_container.resolve(UserService)

    # Test service
    result = service.get_user(123)
    assert result == expected_user
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

- `register_singletons(dependencies: dict[type, Callable[[DIContainer], Any]])` - Register multiple singleton dependencies
- `register_transients(dependencies: dict[type, Callable[[DIContainer], Any]])` - Register multiple transient dependencies
- `register_factories(dependencies: dict[type, Callable[[DIContainer], Any]])` - Register multiple factory dependencies
- `resolve(cls: type[T]) -> T` - Resolve and return an instance of the specified type
- `create_scope() -> DIContainer` - Create a child container for scoped lifetime
- `clear()` - Clear all registrations

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

**Planning Phase** - Architecture and design in progress

See the [architecture plan](docs/plan-simpleDependencyInjectio.prompt.md) for the implementation roadmap.

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
