# Python Consul Lock

Simple locking client built on top of [python-consul](https://github.com/cablehead/python-consul).


Ephemeral Lock
--------------

Designed for relatively short-lived use-cases, primarily preventing race-conditions in
application logic hot-spots. Locks are single use! The lock guarantees that no other client has
locked that key concurrently.

Usable with `lock`/`release` in a try/finally block, or more easily via the the `hold` method in a with block.
By default acquiring the lock is assumed to be a critical path, and will throw an exception if unable to acquire.
The lock has a maximum (configurable) lifespan, which can prevent deadlocks or stale locks in the event that a
lock is never released due to code crashes. No guarentees are made about the behavior if a client continues to hold
the lock for longer than its maximum lifespan (lock_timeout_seconds), Consul may release the lock at any point after 
the timeout.

The ephemeral lock is implemented with Consul's [session](http://python-consul.readthedocs.org/en/latest/#consul-session) and [kv] (http://python-consul.readthedocs.org/en/latest/#consul-kv) API and the key/value associated with the lock will be deleted upon release.


Example
-------

```python
import consul
import consul_locks
from consul_locks import EphemeralLock

consul_client = consul.Consul()
consul_locks.defaults.consul_client = consul_client

ephemeral_lock = EphemeralLock('my/special/key', acquire_timeout_ms=500)
with ephemeral_lock.hold():
    # do dangerous stuff here
    print 'here be dragons'
```
