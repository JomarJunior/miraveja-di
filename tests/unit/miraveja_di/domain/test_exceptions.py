"""Unit tests for domain exceptions."""

import pytest

from miraveja_di.domain.exceptions import (
    CircularDependencyError,
    DIException,
    LifetimeError,
    ScopeError,
    UnresolvableError,
)


class TestDIException:
    """Test cases for the base DIException class."""

    def test_di_exception_is_exception(self):
        """Test that DIException inherits from Exception."""
        assert issubclass(DIException, Exception)

    def test_di_exception_can_be_raised(self):
        """Test that DIException can be raised with a message."""
        with pytest.raises(DIException, match="Test error"):
            raise DIException("Test error")

    def test_di_exception_without_message(self):
        """Test that DIException can be raised without a message."""
        with pytest.raises(DIException):
            raise DIException()

    def test_di_exception_with_args(self):
        """Test that DIException can be raised with multiple arguments."""
        exception = DIException("Error", "Additional info")
        assert exception.args == ("Error", "Additional info")

    def test_di_exception_string_representation(self):
        """Test string representation of DIException."""
        exception = DIException("Test error message")
        assert str(exception) == "Test error message"


class TestCircularDependencyError:
    """Test cases for the CircularDependencyError class."""

    def test_circular_dependency_error_inherits_from_di_exception(self):
        """Test that CircularDependencyError inherits from DIException."""
        assert issubclass(CircularDependencyError, DIException)

    def test_circular_dependency_error_with_simple_chain(self):
        """Test CircularDependencyError with a simple dependency chain."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        chain = [ServiceA, ServiceB, ServiceA]
        error = CircularDependencyError(chain)

        assert error.dependency_chain == chain
        assert "ServiceA -> ServiceB -> ServiceA" in str(error)

    def test_circular_dependency_error_with_single_self_reference(self):
        """Test CircularDependencyError when a class depends on itself."""

        class SelfReferentialService:
            pass

        chain = [SelfReferentialService, SelfReferentialService]
        error = CircularDependencyError(chain)

        assert error.dependency_chain == chain
        assert "SelfReferentialService -> SelfReferentialService" in str(error)

    def test_circular_dependency_error_with_long_chain(self):
        """Test CircularDependencyError with a longer dependency chain."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            pass

        class ServiceD:
            pass

        chain = [ServiceA, ServiceB, ServiceC, ServiceD, ServiceA]
        error = CircularDependencyError(chain)

        expected = "ServiceA -> ServiceB -> ServiceC -> ServiceD -> ServiceA"
        assert expected in str(error)

    def test_circular_dependency_error_message_format(self):
        """Test that the error message has correct format."""

        class FirstService:
            pass

        class SecondService:
            pass

        chain = [FirstService, SecondService, FirstService]
        error = CircularDependencyError(chain)

        assert "Circular dependency detected:" in str(error)
        assert str(error).startswith("Circular dependency detected:")

    def test_circular_dependency_error_chain_attribute(self):
        """Test that dependency_chain attribute is accessible."""

        class ServiceX:
            pass

        class ServiceY:
            pass

        chain = [ServiceX, ServiceY, ServiceX]
        error = CircularDependencyError(chain)

        assert hasattr(error, "dependency_chain")
        assert error.dependency_chain is chain

    def test_circular_dependency_error_can_be_caught(self):
        """Test that CircularDependencyError can be caught as DIException."""

        class ServiceA:
            pass

        chain = [ServiceA, ServiceA]

        with pytest.raises(DIException):
            raise CircularDependencyError(chain)

    def test_circular_dependency_error_empty_chain(self):
        """Test CircularDependencyError with empty chain."""
        chain = []
        error = CircularDependencyError(chain)
        assert error.dependency_chain == []
        assert str(error) == "Circular dependency detected: "


class TestUnresolvableError:
    """Test cases for the UnresolvableError class."""

    def test_unresolvable_error_inherits_from_di_exception(self):
        """Test that UnresolvableError inherits from DIException."""
        assert issubclass(UnresolvableError, DIException)

    def test_unresolvable_error_with_class_only(self):
        """Test UnresolvableError with only a class type."""

        class MyService:
            pass

        error = UnresolvableError(MyService)
        assert "Cannot resolve dependency for type: MyService" in str(error)

    def test_unresolvable_error_with_reason(self):
        """Test UnresolvableError with class and reason."""

        class DatabaseService:
            pass

        error = UnresolvableError(DatabaseService, "Missing type hint")
        assert "Cannot resolve dependency for type: DatabaseService" in str(error)
        assert "Missing type hint" in str(error)

    def test_unresolvable_error_with_detailed_reason(self):
        """Test UnresolvableError with detailed error reason."""

        class ConfigService:
            pass

        reason = "Parameter 'config_file' lacks type hint and has no default value"
        error = UnresolvableError(ConfigService, reason)

        assert "ConfigService" in str(error)
        assert reason in str(error)

    def test_unresolvable_error_without_reason(self):
        """Test UnresolvableError message format without reason."""

        class SimpleService:
            pass

        error = UnresolvableError(SimpleService)
        assert str(error) == "Cannot resolve dependency for type: SimpleService"

    def test_unresolvable_error_can_be_caught(self):
        """Test that UnresolvableError can be caught as DIException."""

        class FailingService:
            pass

        with pytest.raises(DIException):
            raise UnresolvableError(FailingService, "Test reason")

    def test_unresolvable_error_with_empty_reason(self):
        """Test UnresolvableError with empty string reason."""

        class TestService:
            pass

        error = UnresolvableError(TestService, "")
        assert "Cannot resolve dependency for type: TestService" in str(error)


class TestLifetimeError:
    """Test cases for the LifetimeError class."""

    def test_lifetime_error_inherits_from_di_exception(self):
        """Test that LifetimeError inherits from DIException."""
        assert issubclass(LifetimeError, DIException)

    def test_lifetime_error_with_message(self):
        """Test LifetimeError with custom message."""
        error = LifetimeError("Invalid lifetime configuration")
        assert str(error) == "Invalid lifetime configuration"

    def test_lifetime_error_with_detailed_message(self):
        """Test LifetimeError with detailed configuration conflict."""
        message = "Dependency MyService is already registered with lifetime singleton"
        error = LifetimeError(message)
        assert message in str(error)

    def test_lifetime_error_without_message(self):
        """Test LifetimeError without message."""
        error = LifetimeError()
        assert str(error) == ""

    def test_lifetime_error_can_be_caught(self):
        """Test that LifetimeError can be caught as DIException."""
        with pytest.raises(DIException):
            raise LifetimeError("Configuration conflict")

    def test_lifetime_error_with_multiple_args(self):
        """Test LifetimeError with multiple arguments."""
        error = LifetimeError("Error", "Additional context")
        assert error.args == ("Error", "Additional context")


class TestScopeError:
    """Test cases for the ScopeError class."""

    def test_scope_error_inherits_from_di_exception(self):
        """Test that ScopeError inherits from DIException."""
        assert issubclass(ScopeError, DIException)

    def test_scope_error_with_message(self):
        """Test ScopeError with custom message."""
        error = ScopeError("Scoped instance requested outside scope")
        assert str(error) == "Scoped instance requested outside scope"

    def test_scope_error_with_detailed_message(self):
        """Test ScopeError with detailed context."""
        message = "Cannot resolve scoped dependency RequestContext outside of request scope"
        error = ScopeError(message)
        assert message in str(error)

    def test_scope_error_without_message(self):
        """Test ScopeError without message."""
        error = ScopeError()
        assert str(error) == ""

    def test_scope_error_can_be_caught(self):
        """Test that ScopeError can be caught as DIException."""
        with pytest.raises(DIException):
            raise ScopeError("No active scope")

    def test_scope_error_can_be_caught_as_exception(self):
        """Test that ScopeError can be caught as generic Exception."""
        with pytest.raises(Exception):
            raise ScopeError("Scope context error")


class TestExceptionHierarchy:
    """Test cases for the exception hierarchy."""

    def test_all_custom_exceptions_inherit_from_di_exception(self):
        """Test that all custom exceptions inherit from DIException."""
        assert issubclass(CircularDependencyError, DIException)
        assert issubclass(UnresolvableError, DIException)
        assert issubclass(LifetimeError, DIException)
        assert issubclass(ScopeError, DIException)

    def test_all_custom_exceptions_are_exceptions(self):
        """Test that all custom exceptions are proper Exception types."""
        assert issubclass(DIException, Exception)
        assert issubclass(CircularDependencyError, Exception)
        assert issubclass(UnresolvableError, Exception)
        assert issubclass(LifetimeError, Exception)
        assert issubclass(ScopeError, Exception)

    def test_catching_di_exception_catches_all_subtypes(self):
        """Test that catching DIException catches all subtype exceptions."""

        class TestService:
            pass

        exceptions_to_test = [
            CircularDependencyError([TestService]),
            UnresolvableError(TestService),
            LifetimeError("Test"),
            ScopeError("Test"),
        ]

        for exception in exceptions_to_test:
            with pytest.raises(DIException):
                raise exception
