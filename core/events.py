"""A tiny synchronous event bus used by live and backtest components.

Limitations:
- Event delivery is in-process and synchronous; it is not durable.
"""

from collections import defaultdict
from typing import Any, Callable


class EventBus:
    """Simple publish-subscribe event bus."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Callable[[Any], None]) -> None:
        self._handlers[event_name].append(handler)

    def publish(self, event_name: str, payload: Any) -> None:
        for handler in self._handlers[event_name]:
            handler(payload)
