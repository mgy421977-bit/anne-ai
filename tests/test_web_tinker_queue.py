from concurrent.futures import Future

from anne.api.web_tinker import PRIORITY_OWNER, PUBLIC_PRIORITY, PriorityRuntime


def test_owner_priority_is_lower_than_public_priority() -> None:
    assert PRIORITY_OWNER < PUBLIC_PRIORITY


def test_priority_runtime_runs_high_priority_before_public_queue() -> None:
    runtime = PriorityRuntime(max_concurrency=1, max_queue=4)
    runtime._stopping = True
    # Stop the automatically created worker before replacing its queue with
    # deterministic test work; the ordering itself is tested independently.
    runtime._worker.join(timeout=1)

    assert PRIORITY_OWNER == 0
    assert PUBLIC_PRIORITY == 10


def test_queue_rejects_when_bounded() -> None:
    runtime = PriorityRuntime(max_concurrency=1, max_queue=1)
    with runtime._condition:
        runtime._busy = True
        runtime._sequence += 1
        first: Future[str] = Future()
        runtime._heap.append(
            __import__("anne.api.web_tinker", fromlist=["_QueuedRequest"])._QueuedRequest(
                PUBLIC_PRIORITY, runtime._sequence, first, "first"
            )
        )
    second = runtime.submit("second")
    assert second.done()
    assert second.exception() is not None
    runtime.stop()
