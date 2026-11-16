import unittest
from concurrent.futures import Future

from runtime_guard import UpdateDispatcher


class FakeExecutor:
    def __init__(self):
        self.futures = []
        self.calls = []

    def submit(self, handler, update):
        future = Future()
        self.calls.append((handler, update))
        self.futures.append(future)
        return future


class UpdateDispatcherTests(unittest.TestCase):
    def test_duplicate_update_is_queued_only_once(self):
        dispatcher = UpdateDispatcher(max_pending=5)
        executor = FakeExecutor()
        update = {"update_id": 100, "message": {"text": "hello"}}

        self.assertEqual(dispatcher.submit(executor, lambda _: None, update), "queued")
        self.assertEqual(dispatcher.submit(executor, lambda _: None, update), "duplicate")
        self.assertEqual(len(executor.calls), 1)
        self.assertEqual(dispatcher.pending_count, 1)

    def test_queue_is_bounded_and_can_accept_work_after_completion(self):
        dispatcher = UpdateDispatcher(max_pending=1)
        executor = FakeExecutor()

        self.assertEqual(dispatcher.submit(executor, lambda _: None, {"update_id": 1}), "queued")
        self.assertEqual(dispatcher.submit(executor, lambda _: None, {"update_id": 2}), "full")
        executor.futures[0].set_result(None)
        self.assertEqual(dispatcher.pending_count, 0)
        self.assertEqual(dispatcher.submit(executor, lambda _: None, {"update_id": 2}), "queued")

    def test_expired_update_id_can_be_accepted_again(self):
        now = [100.0]
        dispatcher = UpdateDispatcher(max_pending=5, dedupe_ttl=10, clock=lambda: now[0])
        executor = FakeExecutor()
        handler = lambda _: None
        update = {"update_id": 7}

        self.assertEqual(dispatcher.submit(executor, handler, update), "queued")
        executor.futures[0].set_result(None)
        self.assertEqual(dispatcher.submit(executor, handler, update), "duplicate")
        now[0] = 111.0
        self.assertEqual(dispatcher.submit(executor, handler, update), "queued")

    def test_failed_submit_releases_capacity_and_dedupe_key(self):
        class BrokenExecutor:
            def submit(self, *_args):
                raise RuntimeError("queue unavailable")

        dispatcher = UpdateDispatcher(max_pending=1)
        update = {"update_id": 8}
        with self.assertRaises(RuntimeError):
            dispatcher.submit(BrokenExecutor(), lambda _: None, update)

        self.assertEqual(dispatcher.pending_count, 0)
        executor = FakeExecutor()
        self.assertEqual(dispatcher.submit(executor, lambda _: None, update), "queued")


if __name__ == "__main__":
    unittest.main()
