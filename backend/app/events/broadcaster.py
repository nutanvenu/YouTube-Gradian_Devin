import asyncio
from dataclasses import dataclass, field
from uuid import UUID


@dataclass(eq=False)
class Connection:
    family_id: UUID
    child_id: UUID | None
    queue: asyncio.Queue[dict[str, object]] = field(
        default_factory=lambda: asyncio.Queue(maxsize=100)
    )


class EventBroadcaster:
    def __init__(self, queue_size: int = 100) -> None:
        self._queue_size = queue_size
        self._connections: set[Connection] = set()

    def subscribe(self, family_id: UUID, child_id: UUID | None = None) -> Connection:
        connection = Connection(
            family_id=family_id,
            child_id=child_id,
            queue=asyncio.Queue(maxsize=self._queue_size),
        )
        self._connections.add(connection)
        return connection

    def unsubscribe(self, connection: Connection) -> None:
        self._connections.discard(connection)

    def publish(
        self,
        family_id: UUID,
        event: dict[str, object],
        child_id: UUID | None = None,
    ) -> None:
        for connection in tuple(self._connections):
            if connection.family_id != family_id:
                continue
            if connection.child_id is not None and connection.child_id != child_id:
                continue
            if connection.queue.full():
                connection.queue.get_nowait()
            connection.queue.put_nowait(event)


broadcaster = EventBroadcaster()
