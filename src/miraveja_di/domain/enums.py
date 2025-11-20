from enum import Enum


class Lifetime(str, Enum):
    """Defines the lifetime of a dependency instance.

    Attributes:
        SINGLETON: Single instance shared across entire application.
        TRANSIENT: New instance created on each resolution.
        SCOPED: Single instance per scope (e.g., per HTTP request).
    """

    TRANSIENT = "transient"
    SCOPED = "scoped"
    SINGLETON = "singleton"

    def __str__(self) -> str:
        return self.value
