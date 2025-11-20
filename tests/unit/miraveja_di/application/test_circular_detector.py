"""Unit tests for CircularDependencyDetector."""

import threading

import pytest

from miraveja_di.application.circular_detector import CircularDependencyDetector
from miraveja_di.domain import CircularDependencyError


class TestCircularDependencyDetector:
    """Test cases for CircularDependencyDetector class."""

    def test_detector_initialization(self):
        """Test that detector initializes with empty stack."""
        detector = CircularDependencyDetector()
        assert detector._local is not None
        # Stack should not exist yet (lazy creation)
        assert not hasattr(detector._local, "stack")

    def test_push_adds_to_stack(self):
        """Test that push adds dependency to stack."""
        detector = CircularDependencyDetector()

        class ServiceA:
            pass

        detector.push(ServiceA)
        stack = detector._get_stack()
        assert len(stack) == 1
        assert stack[0] == ServiceA

    def test_push_multiple_dependencies(self):
        """Test that push can add multiple dependencies in sequence."""
        detector = CircularDependencyDetector()

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            pass

        detector.push(ServiceA)
        detector.push(ServiceB)
        detector.push(ServiceC)

        stack = detector._get_stack()
        assert len(stack) == 3
        assert stack == [ServiceA, ServiceB, ServiceC]

    def test_push_detects_circular_dependency(self):
        """Test that push detects circular dependency when same type appears twice."""
        detector = CircularDependencyDetector()

        class ServiceA:
            pass

        class ServiceB:
            pass

        detector.push(ServiceA)
        detector.push(ServiceB)

        # Pushing ServiceA again should detect circular dependency
        with pytest.raises(CircularDependencyError) as exc_info:
            detector.push(ServiceA)

        error = exc_info.value
        assert error.dependency_chain == [ServiceA, ServiceB, ServiceA]
        assert "ServiceA -> ServiceB -> ServiceA" in str(error)

    def test_push_detects_self_reference(self):
        """Test that push detects immediate self-reference."""
        detector = CircularDependencyDetector()

        class ServiceA:
            pass

        detector.push(ServiceA)

        # Pushing ServiceA again immediately should detect circular dependency
        with pytest.raises(CircularDependencyError) as exc_info:
            detector.push(ServiceA)

        error = exc_info.value
        assert error.dependency_chain == [ServiceA, ServiceA]

    def test_push_detects_long_circular_chain(self):
        """Test that push detects circular dependencies in long chains."""
        detector = CircularDependencyDetector()

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            pass

        class ServiceD:
            pass

        detector.push(ServiceA)
        detector.push(ServiceB)
        detector.push(ServiceC)
        detector.push(ServiceD)

        # Circular reference back to ServiceB
        with pytest.raises(CircularDependencyError) as exc_info:
            detector.push(ServiceB)

        error = exc_info.value
        assert error.dependency_chain == [ServiceB, ServiceC, ServiceD, ServiceB]

    def test_pop_removes_last_dependency(self):
        """Test that pop removes the last dependency from stack."""
        detector = CircularDependencyDetector()

        class ServiceA:
            pass

        class ServiceB:
            pass

        detector.push(ServiceA)
        detector.push(ServiceB)

        detector.pop()
        stack = detector._get_stack()
        assert len(stack) == 1
        assert stack[0] == ServiceA

    def test_pop_on_empty_stack(self):
        """Test that pop handles empty stack gracefully."""
        detector = CircularDependencyDetector()
        # Should not raise
        detector.pop()

    def test_pop_after_clear(self):
        """Test that pop after clear doesn't raise error."""
        detector = CircularDependencyDetector()

        class ServiceA:
            pass

        detector.push(ServiceA)
        detector.clear()
        # Should not raise
        detector.pop()

    def test_clear_empties_stack(self):
        """Test that clear empties the resolution stack."""
        detector = CircularDependencyDetector()

        class ServiceA:
            pass

        class ServiceB:
            pass

        detector.push(ServiceA)
        detector.push(ServiceB)

        detector.clear()
        stack = detector._get_stack()
        assert len(stack) == 0

    def test_clear_on_empty_stack(self):
        """Test that clear on empty stack doesn't raise error."""
        detector = CircularDependencyDetector()
        # Should not raise
        detector.clear()

    def test_clear_before_stack_creation(self):
        """Test that clear before stack creation doesn't raise error."""
        detector = CircularDependencyDetector()
        assert not hasattr(detector._local, "stack")
        # Should not raise
        detector.clear()

    def test_push_pop_cycle(self):
        """Test that push/pop cycle maintains stack correctly."""
        detector = CircularDependencyDetector()

        class ServiceA:
            pass

        class ServiceB:
            pass

        # Push A
        detector.push(ServiceA)
        assert len(detector._get_stack()) == 1

        # Push B
        detector.push(ServiceB)
        assert len(detector._get_stack()) == 2

        # Pop B
        detector.pop()
        assert len(detector._get_stack()) == 1
        assert detector._get_stack()[0] == ServiceA

        # Push B again (no circular dependency since B was popped)
        detector.push(ServiceB)
        assert len(detector._get_stack()) == 2

    def test_get_stack_creates_stack_lazily(self):
        """Test that _get_stack creates stack on first access."""
        detector = CircularDependencyDetector()
        assert not hasattr(detector._local, "stack")

        stack = detector._get_stack()
        assert hasattr(detector._local, "stack")
        assert stack == []

    def test_get_stack_returns_same_stack(self):
        """Test that _get_stack returns the same stack instance."""
        detector = CircularDependencyDetector()

        stack1 = detector._get_stack()
        stack2 = detector._get_stack()
        assert stack1 is stack2

    def test_thread_isolation(self):
        """Test that each thread has its own resolution stack."""
        detector = CircularDependencyDetector()

        class ServiceA:
            pass

        class ServiceB:
            pass

        # Main thread stack
        detector.push(ServiceA)
        main_stack = detector._get_stack()

        # Track thread results
        thread_stack = []
        exception_raised = []

        def thread_worker():
            # Thread should have empty stack
            detector.push(ServiceB)
            thread_stack.append(detector._get_stack().copy())

            # Thread should be able to push ServiceA without circular error
            try:
                detector.push(ServiceA)
                thread_stack.append(detector._get_stack().copy())
            except CircularDependencyError:
                exception_raised.append(True)

        thread = threading.Thread(target=thread_worker)
        thread.start()
        thread.join()

        # Main thread should still have only ServiceA
        assert len(main_stack) == 1
        assert main_stack[0] == ServiceA

        # Thread should have had its own stack
        assert len(thread_stack) == 2
        assert thread_stack[0] == [ServiceB]
        assert thread_stack[1] == [ServiceB, ServiceA]
        assert not exception_raised  # No circular error in thread

    def test_circular_detection_preserves_stack_on_error(self):
        """Test that stack is preserved when circular dependency is detected."""
        detector = CircularDependencyDetector()

        class ServiceA:
            pass

        class ServiceB:
            pass

        detector.push(ServiceA)
        detector.push(ServiceB)

        try:
            detector.push(ServiceA)
        except CircularDependencyError:
            pass

        # Stack should still have A and B
        stack = detector._get_stack()
        assert len(stack) == 2
        assert stack == [ServiceA, ServiceB]


class TestCircularDetectorEdgeCases:
    """Test edge cases and error scenarios for CircularDependencyDetector."""

    def test_multiple_circular_detections(self):
        """Test that detector can detect multiple circular dependencies."""
        detector = CircularDependencyDetector()

        class ServiceA:
            pass

        class ServiceB:
            pass

        # First circular dependency
        detector.push(ServiceA)
        with pytest.raises(CircularDependencyError):
            detector.push(ServiceA)

        # Clear and test second circular dependency
        detector.clear()
        detector.push(ServiceB)
        with pytest.raises(CircularDependencyError):
            detector.push(ServiceB)

    def test_complex_dependency_chain(self):
        """Test circular detection in complex dependency chains."""
        detector = CircularDependencyDetector()

        classes = [type(f"Service{i}", (), {}) for i in range(10)]

        # Build chain: S0 -> S1 -> S2 -> ... -> S9
        for cls in classes:
            detector.push(cls)

        # Try to create circle back to S5
        with pytest.raises(CircularDependencyError) as exc_info:
            detector.push(classes[5])

        error = exc_info.value
        # Chain should be from S5 onwards plus S5 again
        expected_chain = classes[5:] + [classes[5]]
        assert error.dependency_chain == expected_chain

    def test_different_types_no_circular_error(self):
        """Test that different types don't trigger circular dependency."""
        detector = CircularDependencyDetector()

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            pass

        # All different types - no circular dependency
        detector.push(ServiceA)
        detector.push(ServiceB)
        detector.push(ServiceC)

        stack = detector._get_stack()
        assert len(stack) == 3
        assert stack == [ServiceA, ServiceB, ServiceC]
