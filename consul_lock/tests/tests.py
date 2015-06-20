from unittest import TestCase

import consul
import json
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

class JsonKeyMatcher(object):
    def __init__(self, keys):
        self.keys = set(keys)

    def __eq__(self, other):
        other_dict = json.loads(other)
        return self.keys == set(other_dict.keys())

    def __str__(self):
        return 'JsonKeyMatcher(%s)' % (self.keys)

    __unicode__ = __repr__ = __str__

class EphemeralLockTests(TestCase):
    def setUp(self):
        super(EphemeralLockTests, self).setUp()
        self.session_id = 'fake-session'
        self.key = 'fake-key'
        self.value_matcher = JsonKeyMatcher(keys=['locked_at'])

        self.mock_consul = patch_object(self, consul, 'Consul')
        self._setup_mock_consul(self.mock_consul)

        defaults.consul_client = self.mock_consul
        defaults.lock_key_pattern = '%s'

    def _setup_mock_consul(self, mock_consul):
        mock_consul.session.create.return_value = self.session_id
        mock_consul.kv.put.return_value = True

    def test_simple_success(self):
        lock = EphemeralLock(self.key)
        lock.lock()

        self.mock_consul.session.create.assert_called_once_with(
            lock_delay=0,
            ttl=defaults.lock_timeout_seconds,
            behavior='destroy',
        )
        self.mock_consul.kv.put.assert_called_once_with(
            key=self.key,
            value=self.value_matcher,
            acquire=self.session_id
        )

        lock.release()
        self.mock_consul.session.destroy.assert_called_once_with(
            session_id=self.session_id
        )

    def test_success_override_defaults(self):
        acquire_timeout_ms = 10
        lock_timeout_seconds = 20
        mock_consul = MagicMock()
        self._setup_mock_consul(mock_consul)
        value = 'fake-value'
        original_generate_value = defaults.generate_value
        def return_to_original():
            defaults.generate_value = original_generate_value
        self.addCleanup(return_to_original)
        defaults.generate_value = lambda: value

        lock = EphemeralLock(
            key=self.key,
            acquire_timeout_ms=acquire_timeout_ms,
            lock_timeout_seconds=lock_timeout_seconds,
            consul_client=mock_consul,
        )
        lock.lock()
        mock_consul.session.create.assert_called_once_with(
            lock_delay=0,
            ttl=lock_timeout_seconds,
            behavior='destroy',
        )
        mock_consul.kv.put.assert_called_once_with(
            key=self.key,
            value=value,
            acquire=self.session_id
        )

        lock.release()
        mock_consul.session.destroy.assert_called_once_with(
            session_id=self.session_id
        )

    def test_simple_success_context_manager(self):
        lock = EphemeralLock(self.key)
        with lock.hold():
            self.mock_consul.session.create.assert_called_once_with(
                lock_delay=0,
                ttl=defaults.lock_timeout_seconds,
                behavior='destroy',
            )
            self.mock_consul.kv.put.assert_called_once_with(
                key=self.key,
                value=self.value_matcher,
                acquire=self.session_id
            )

        self.mock_consul.session.destroy.assert_called_once_with(
            session_id=self.session_id
        )

    def test_release_gracefully_if_never_locked(self):
        lock = EphemeralLock(self.key)
        self.mock_consul.session.create.side_effect = consul.Timeout('unable to create session')
        try:
            with lock.hold():
                self.fail('should have raised an exception')
        except consul.Timeout:
            pass
        self.mock_consul.session.create.assert_called_once_with(
            lock_delay=0,
            ttl=defaults.lock_timeout_seconds,
            behavior='destroy',
        )
        self.assertEquals([], self.mock_consul.kv.put.mock_calls)
        self.assertEquals([], self.mock_consul.session.destroy.mock_calls)

