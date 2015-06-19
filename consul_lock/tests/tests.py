from unittest import TestCase

import consul
from consul_lock import defaults
from consul_lock import EphemeralLock
from mock import patch
from mock import MagicMock


def patch_object(test_case, target, attribute, new=None):
    if not new:
        new = MagicMock()
    patcher = patch.object(target, attribute, new)
    test_case.addCleanup(patcher.stop)
    mock = patcher.start()
    return mock


class EphemeralLockTests(TestCase):
    def setUp(self):
        super(EphemeralLockTests, self).setUp()
        self.session_id = 'fake-session'
        self.key = 'fake-key'
        self.value = 'fake-value'

        self.mock_consul = patch_object(self, consul, 'Consul')
        self.mock_consul.session.create.return_value = self.session_id
        self.mock_consul.kv.put.return_value = True

        defaults.consul_client = self.mock_consul
        defaults.generate_value = lambda: self.value

    def test_simple_success(self):
        lock = EphemeralLock(self.key)
        lock.lock()

        self.mock_consul.session.create.asssert_called_once(
            lock_delay=0,
            ttl=180,
            behavior='destroy',
        )
        self.mock_consul.kv.put.asssert_called_once(
            key=self.key,
            value=self.value,
            acquire=self.session_id
        )

        lock.release()
        self.mock_consul.session.destroy.asssert_called_once(
            session=self.session_id
        )

    def test_simple_success_context_manager(self):
        lock = EphemeralLock(self.key)
        with lock.hold():
            self.mock_consul.session.create.asssert_called_once(
                lock_delay=0,
                ttl=180,
                behavior='destroy',
            )
            self.mock_consul.kv.put.asssert_called_once(
                key=self.key,
                value=self.value,
                acquire=self.session_id
            )

        self.mock_consul.session.destroy.asssert_called_once(
            session=self.session_id
        )
