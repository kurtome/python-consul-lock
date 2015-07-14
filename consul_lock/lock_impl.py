import time
import contextlib
import defaults

import consul

class ConsulLockException(consul.ConsulException):
    # Extends the base ConsulException in case caller wants to group the exception handling together
    pass

class LockAcquisitionException(ConsulLockException):
    pass




def _coerce_required(value, attr_name):
    if value is not None:
        return value

    default = getattr(defaults, attr_name, None)
    if default is not None:
        return default

    raise Exception('%s is required for locking.' % attr_name)


class EphemeralLock(object):
    """
    Designed for relatively short-lived use-cases, primarily preventing race-conditions in
    application logic hot-spots. Locks are single use!

    Usable with `lock`/`release` in a try/finally block,
    or more easily via the the `hold` method in a with block.

    Consul docs:
        https://www.consul.io/docs/internals/sessions.html
        https://www.consul.io/docs/agent/http/kv.html
        https://github.com/hashicorp/consul/issues/968
    """

    def __init__(self,
            key,
            acquire_timeout_ms=None,
            lock_timeout_seconds=None,
            consul_client=None):
        """
        :param key: the unique key to lock
        :param acquire_timeout_ms: how long the caller is willing to wait to acquire the lock
        :param lock_timeout_seconds: how long the lock will stay alive if it is never released,
            this is controlled by Consul's Session TTL and may stay alive a bit longer according
            to their docs. As of the current version of Consul, this must be between 10s and 3600s
        :param consul_client: client to use instead of the one defined in Settings
        """
        self._consul = _coerce_required(consul_client, 'consul_client')

        self.key = key
        assert key, 'key is required for locking.'
        self.full_key = defaults.lock_key_pattern % key
        self.lock_timeout_seconds = _coerce_required(lock_timeout_seconds, 'lock_timeout_seconds')
        self.acquire_timeout_ms = _coerce_required(acquire_timeout_ms, 'acquire_timeout_ms')
        self.session_id = None
        self._started_locking = False
        assert self.lock_timeout_seconds >= 10 and self.lock_timeout_seconds <= 3600, \
            'lock_timeout_seconds must be between 10 and 3600 to due to Consul\'s session ttl settings'


    def acquire(self, fail_hard=True):
        """
        Attempt to acquire the lock.

        :param fail_hard: when true, this method will only return gracefully
            if the lock has been been acquired and will throw an exception if
            it cannot acquire the lock.

        :return: True if the lock was successfully acquired,
            false if it was not (unreachable if failing hard)
        """
        assert not self._started_locking, 'can only lock once'
        assert not self._started_locking, 'can only lock once'
        start_time = time.time()

        # how long to hold locks after session times out.
        # we don't want to hold on to them since this is a temporary session just for this lock
        session_lock_delay = 0

        # how long to keep the session alive without a renew (heartbeat/keepalive) sent.
        # we are using this to timeout the individual lock
        session_ttl = self.lock_timeout_seconds

        # delete locks when session is invalidated/destroyed
        session_invalidate_behavior = 'delete'

        self.session_id = self._consul.session.create(
            lock_delay=session_lock_delay,
            ttl=session_ttl,
            behavior=session_invalidate_behavior
        )

        self._started_locking = True

        is_success = False

        max_loop_iter = 1000 #  don't loop forever
        for attempt_number in range(0, max_loop_iter):
            is_success = self._acquire_consul_key()

            # exponential backoff yo
            sleep_ms = 50 * pow(attempt_number, 2)
            elapsed_time_ms = int(round(1000 * (time.time() - start_time)))
            time_left_ms = self.acquire_timeout_ms - elapsed_time_ms
            sleep_ms = min(time_left_ms, sleep_ms)

            retry_acquire = (not is_success) and (time_left_ms > 0)

            if retry_acquire:
                sleep_seconds_float = sleep_ms / 1000.0
                time.sleep(sleep_seconds_float)
            else:
                break

        if not is_success and fail_hard:
            raise LockAcquisitionException("Failed to acquire %s" % self.full_key)
        else:
            return is_success

    def _acquire_consul_key(self):
        assert self.session_id, 'must have a session id to acquire lock'

        value = defaults.generate_value()
        return self._consul.kv.put(
            key=self.full_key,
            value=value,
            acquire=self.session_id
        )

    def release(self):
        """
        Release the lock immediately. Does nothing if never locked.
        """
        if not self._started_locking:
            return False

        # destroying the session will is the safest way to release the lock. we'd like to delete the
        # key, but since it's possible we don't actually have the lock anymore (in distributed systems, there is no spoon)
        # it's best to just destroy the session and let the lock get cleaned up by Consul
        #
        # More info:
        # https://www.consul.io/docs/internals/sessions.html
        return self._consul.session.destroy(
            session_id=self.session_id
        )

    @contextlib.contextmanager
    def hold(self):
        """
        Context manager for holding the lock
        """
        try:
            self.acquire(fail_hard=True)
            yield
        finally:
            self.release()
