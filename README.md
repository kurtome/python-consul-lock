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


### Examples

In order to create a lock, you must either pass in a reference to a `consul.Consul` client each time, or assign a default client to use.

##### Setup `consul_lock` defaults
```python
import consul
import consul_lock


consul_client = consul.Consul()
consul_lock.defaults.consul_client = consul_client
```

The simplest way to use a lock is in a `with` block as a context manager. The lock will be automatically released then the `with` block exits.

##### Creating and holding a lock with as a context manager
```python
from consul_lock import EphemeralLock

ephemeral_lock = EphemeralLock('my/special/key', acquire_timeout_ms=500)
with ephemeral_lock.hold():
    # do dangerous stuff here
    print 'here be dragons'
```

It is also possible to manually acquire and release the lock. The following is equivalent to the previous example.

##### Creating a lock and acquiring and releasing it explicitly
```python
from consul_lock import EphemeralLock

ephemeral_lock = EphemeralLock('my/special/key', acquire_timeout_ms=500)
try:
    ephemeral_lock.acquire()
    # do dangerous stuff here
    print 'here be dragons'
finally:
    ephemeral_lock.release()
```

By default acquiring a lock (with `acquire` or `hold`) is assumed to be a critical operation and will throw an exception if it is unable to acquire the lock within the specified timeout. Sometimes it may be desirable to react to the fact that the lock is being held concurrently by some other code or host. In that case you can set the `fail_hard` option and `acquire` will return whether or not is was able to acquire the lock.

#### Reacting to `acquire` attempt
```python
from consul_lock import EphemeralLock

ephemeral_lock = EphemeralLock('my/special/key', acquire_timeout_ms=500)
try:
    was_acquired = ephemeral_lock.acquire(fail_hard=False)
    if was_acquired:
        # do dangerous stuff here
        print 'here be dragons'
    else:
        print 'someone else has the lock :\ try again later'
finally:
    ephemeral_lock.release()
```

FAQ
---

#### Is this "production ready"?
Use at your own risk, this code is young and has hopes and dreams of being battletested and rugged someday.

#### Why is this useful?
Well, that really depends on what you're doing, but generally [distributed locks](https://en.wikipedia.org/wiki/Distributed_lock_manager) are useful to prevent [race conditions](https://en.wikipedia.org/wiki/Race_condition).

#### Is the lock reentrant?
Nope, so be careful not to deadlock! It could be implemented since Consul's session API allows the same session to reacquire the same locked key, feel free to submit a pull request if you want that.
