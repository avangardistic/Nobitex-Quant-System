from core.events import EventBus


def test_event_bus_publish_subscribe():
    seen = []
    bus = EventBus()
    bus.subscribe("tick", seen.append)
    bus.publish("tick", 1)
    assert seen == [1]
