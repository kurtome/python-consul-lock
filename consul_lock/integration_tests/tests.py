from unittest import TestCase

import os
import consul
import uuid
import time
from consul_lock import defaults
from consul_lock import EphemeralLock

def get_consul_client():
    host = os.environ.get('CONSUL_LOCK_CONSUL_HOST')
    port = os.environ.get('CONSUL_LOCK_CONSUL_PORT')
    assert host, 'CONSUL_LOCK_CONSUL_HOST environment variable is required for integration testing'
    assert port, 'CONSUL_LOCK_CONSUL_PORT environment variable is required for integration testing'
    client = consul.Consul(host=host, port=int(port))
    return client

def generate_key(key):
    # always prefix key with uuid so tests can always be re-run immediately without
    # clashing on stale locks from a previous run (which will eventually timeout)
    return '%s/%s' % (uuid.uuid4(), key)

class IntegrationTests(TestCase):
    """
    These test require connecting to an actual Consul cluster and will
    write actual data to the key/value store, run carefully.
    """

    @classmethod
    def setUpClass(cls):
        super(IntegrationTests, cls).setUpClass()
        cls.consul_client = get_consul_client()
        defaults.consul_client = cls.consul_client
        print(cls.consul_client)

    def setUp(self):
        super(IntegrationTests, self).setUp()
        defaults.lock_key_pattern = 'consul_lock/test/%s'

    def test_unable_to_acquire_held_lock(self):
        key1 = generate_key('key1')
        lock1_on_key1 = EphemeralLock(key1, acquire_timeout_ms=0, lock_timeout_seconds=10)
        lock2_on_key1 = EphemeralLock(key1, acquire_timeout_ms=0, lock_timeout_seconds=10)
        lock1_on_key1.acquire()
        was_acquired =  lock2_on_key1.acquire(fail_hard=False)
        self.assertFalse(was_acquired)

        lock1_on_key1.release()
        lock3_on_key1 = EphemeralLock(key1, acquire_timeout_ms=0, lock_timeout_seconds=10)
        was_acquired =  lock3_on_key1.acquire(fail_hard=False)
        self.assertTrue(was_acquired)

    def test_unrelated_locks_can_be_acquired_concurrently(self):
        key1 = generate_key('key1')
        lock1_on_key1 = EphemeralLock(key1, acquire_timeout_ms=0, lock_timeout_seconds=10)
        key2 = generate_key('key2')
        lock2_on_key2 = EphemeralLock(key2, acquire_timeout_ms=0, lock_timeout_seconds=10)
        lock1_on_key1.acquire()
        lock2_on_key2.acquire()

    def test_able_to_acquire_after_timeout_lock(self):
        key1 = generate_key('key1')
        lock1_on_key1 = EphemeralLock(key1, acquire_timeout_ms=0, lock_timeout_seconds=10)
        lock1_on_key1.acquire()
        time.sleep(20)
        lock2_on_key1 = EphemeralLock(key1, acquire_timeout_ms=0, lock_timeout_seconds=10)
        was_acquired =  lock2_on_key1.acquire(fail_hard=False)
        self.assertTrue(was_acquired)

    def test_acquire_timeout_will_wait_and_acquire(self):
        key1 = generate_key('key1')
        lock1_on_key1 = EphemeralLock(key1, acquire_timeout_ms=0, lock_timeout_seconds=10)
        lock1_on_key1.acquire()
        lock2_on_key1 = EphemeralLock(key1, acquire_timeout_ms=20 * 1000, lock_timeout_seconds=10)
        was_acquired =  lock2_on_key1.acquire(fail_hard=False)
        self.assertTrue(was_acquired)

    def test_acquire_timeout_blocks_for_reasonable_time(self):
        key1 = generate_key('key1')
        lock1_on_key1 = EphemeralLock(key1, acquire_timeout_ms=0, lock_timeout_seconds=10)
        lock1_on_key1.acquire()
        lock2_on_key1 = EphemeralLock(key1, acquire_timeout_ms=500, lock_timeout_seconds=10)
        start_time = time.time()
        was_acquired =  lock2_on_key1.acquire(fail_hard=False)
        elapsed_time_ms = int(round(1000 * (time.time() - start_time)))
        self.assertFalse(was_acquired)
        self.assertGreater(elapsed_time_ms, 500)
        self.assertLess(elapsed_time_ms, 600)

