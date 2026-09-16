import heapq
from concurrent.futures import Future

from anne.api.web_tinker import (
    PRIORITY_OWNER,
    PUBLIC_PRIORITY,
    PriorityRuntime,
    _QueuedRequest,
)


def test_owner_priority_is_lower_than_public_priority() -> None:
    assert PRIORITY_OWNER < PUBLIC_PRIORITY


def test_priority_queue_orders_owner_before_public() -> None:
    owner: Future[str] = Future()
    public: Future[str] = Future()
    heap = [
        _QueuedRequest(PUBLIC_PRIORITY, 1, public, "public-actor", "public"),
        _QueuedRequest(PRIORITY_OWNER, 2, owner, "owner-actor", "owner"),
    ]
    heapq.heapify(heap)
    assert heapq.heappop(heap).prompt == "owner"
    assert heapq.heappop(heap).prompt == "public"


def test_queue_rejects_when_bounded() -> None:
    runtime = PriorityRuntime(max_queue=1)
    with runtime._condition:
        runtime._busy = True
        runtime._sequence += 1
        first: Future[str] = Future()
        runtime._heap.append(
            _QueuedRequest(
                PUBLIC_PRIORITY, runtime._sequence, first, "first-actor", "first"
            )
        )
    second = runtime.submit("second-actor", "second")
    assert second.done()
    assert second.exception() is not None
    runtime.stop()
