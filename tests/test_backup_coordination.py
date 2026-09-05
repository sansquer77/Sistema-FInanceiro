from __future__ import annotations

import threading
import time
import unittest

from financeiro.backup_coordination import InstallationAccessGate


class InstallationAccessGateTests(unittest.TestCase):
    def test_restore_waits_for_active_requests_and_blocks_new_requests(self) -> None:
        gate = InstallationAccessGate()
        first_entered = threading.Event()
        release_first = threading.Event()
        restore_entered = threading.Event()
        release_restore = threading.Event()
        late_entered = threading.Event()

        def first_request() -> None:
            with gate.shared():
                first_entered.set()
                release_first.wait(2)

        def restore() -> None:
            first_entered.wait(2)
            with gate.exclusive():
                restore_entered.set()
                release_restore.wait(2)

        def late_request() -> None:
            first_entered.wait(2)
            time.sleep(0.02)
            with gate.shared():
                late_entered.set()

        threads = [
            threading.Thread(target=first_request),
            threading.Thread(target=restore),
            threading.Thread(target=late_request),
        ]
        for thread in threads:
            thread.start()
        self.assertTrue(first_entered.wait(1))
        self.assertFalse(restore_entered.wait(0.05))
        self.assertFalse(late_entered.wait(0.05))
        release_first.set()
        self.assertTrue(restore_entered.wait(1))
        self.assertFalse(late_entered.wait(0.05))
        release_restore.set()
        self.assertTrue(late_entered.wait(1))
        for thread in threads:
            thread.join(1)
            self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
