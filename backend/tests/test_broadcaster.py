from uuid import uuid4

from app.events.broadcaster import EventBroadcaster


def test_broadcaster_delivers_only_to_matching_family_and_child() -> None:
    broadcaster = EventBroadcaster(queue_size=2)
    family_a = uuid4()
    family_b = uuid4()
    child_a = uuid4()
    first = broadcaster.subscribe(family_a, child_a)
    second = broadcaster.subscribe(family_a)
    other_family = broadcaster.subscribe(family_b)

    broadcaster.publish(family_a, {"type": "policy-version-changed"}, child_a)

    assert first.queue.get_nowait()["type"] == "policy-version-changed"
    assert second.queue.get_nowait()["type"] == "policy-version-changed"
    assert other_family.queue.empty()


def test_broadcaster_drops_oldest_event_when_queue_is_full() -> None:
    broadcaster = EventBroadcaster(queue_size=2)
    family_id = uuid4()
    connection = broadcaster.subscribe(family_id)

    for index in range(3):
        broadcaster.publish(family_id, {"type": "device-status", "index": index})

    assert connection.queue.qsize() == 2
    assert connection.queue.get_nowait()["index"] == 1
    assert connection.queue.get_nowait()["index"] == 2
