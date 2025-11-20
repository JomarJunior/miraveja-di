"""Integration tests for resolver working with container."""

from miraveja_di.application.resolver import DependencyResolver
from miraveja_di.domain.interfaces import IContainer


class TestResolverContainerIntegration:
    """Test cases for resolver integration with container."""

    def test_resolver_calls_container_resolve(self):
        """Test that resolver calls container.resolve for dependencies."""
        resolver = DependencyResolver()
        resolve_calls = []

        class TrackingContainer(IContainer):
            def register_singletons(self, dependencies):
                pass

            def register_transients(self, dependencies):
                pass

            def resolve(self, dependency_type):
                resolve_calls.append(dependency_type)
                return dependency_type()

            def create_scope(self):
                return self

            def clear(self):
                pass

            def get_registry_copy(self):
                return {}

        container = TrackingContainer()

        class DatabaseService:
            def __init__(self):
                pass

        class UserService:
            def __init__(self, db: DatabaseService):
                self.db = db

        resolver.resolve_dependencies(UserService, container)

        # Container should have been called to resolve DatabaseService
        assert DatabaseService in resolve_calls

    def test_resolver_uses_container_resolved_instances(self):
        """Test that resolver uses instances from container."""
        resolver = DependencyResolver()

        class MockContainer(IContainer):
            def __init__(self):
                self.resolved = {}

            def register_singletons(self, dependencies):
                pass

            def register_transients(self, dependencies):
                pass

            def resolve(self, dependency_type):
                if dependency_type in self.resolved:
                    return self.resolved[dependency_type]
                return dependency_type()

            def create_scope(self):
                return self

            def clear(self):
                pass

            def get_registry_copy(self):
                return {}

        container = MockContainer()

        class DatabaseService:
            def __init__(self):
                self.id = "specific_instance"

        class UserService:
            def __init__(self, db: DatabaseService):
                self.db = db

        # Pre-register specific instance
        db_instance = DatabaseService()
        container.resolved[DatabaseService] = db_instance

        instance = resolver.resolve_dependencies(UserService, container)

        # Should use the pre-registered instance
        assert instance.db is db_instance
