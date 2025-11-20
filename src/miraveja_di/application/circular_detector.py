"""Application layer - Circular dependency detection."""

import threading
from typing import List, Type

from miraveja_di.domain import CircularDependencyError


class CircularDependencyDetector:
    """Detects circular dependencies during resolution.

    Uses thread-local storage to track the current resolution stack.
    When a type appears twice in the stack, a circular dependency is detected.

    Attributes:
        _local: Thread-local storage for resolution stacks.
    """

    def __init__(self) -> None:
        """Initialize the circular dependency detector with thread-local storage."""
        self._local = threading.local()

    def _get_stack(self) -> List[Type]:
        """Get the current thread's resolution stack.

        Returns:
            The resolution stack for the current thread.
        """
        if not hasattr(self._local, "stack"):
            self._local.stack = []
        return self._local.stack

    def push(self, dependency_type: Type) -> None:
        """Add a dependency to the resolution stack.

        Args:
            dependency_type: The type being resolved.

        Raises:
            CircularDependencyError: If the type is already in the stack.

        Example:
            >>> detector = CircularDependencyDetector()
            >>> detector.push(ServiceA)
            >>> detector.push(ServiceB)
            >>> detector.push(ServiceA)  # Raises CircularDependencyError
        """
        stack = self._get_stack()

        # Check if dependency is already in stack (circular reference)
        if dependency_type in stack:
            # Build cycle path from first occurrence to current
            cycle_start_index = stack.index(dependency_type)
            cycle = stack[cycle_start_index:] + [dependency_type]
            raise CircularDependencyError(cycle)

        stack.append(dependency_type)

    def pop(self) -> None:
        """Remove the last dependency from the resolution stack.

        Called after successful resolution of a dependency.
        """
        stack = self._get_stack()
        if stack:
            stack.pop()

    def clear(self) -> None:
        """Clear the entire resolution stack.

        Useful for testing or error recovery.
        """
        if hasattr(self._local, "stack"):
            self._local.stack.clear()
