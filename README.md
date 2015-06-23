# Python Consul Lock

Simple client for distributed locking built  on top of [python-consul](https://github.com/cablehead/python-consul).

When running app servers in parallel, distributed locks come in handy on the rare occasion you need guarentees that only one server is running a particular block of code at a time. This library lets you do that in a straightforward way using [Consul](https://www.consul.io/) as the central authority for who owns the lock currently.

Installation
------------
```
pip install consul-lock
```

Ephemeral Lock
--------------

Designed for relatively short-lived use-cases, primarily preventing race-conditions in
application logic hot-spots. Locks are single use! The lock guarantees that no other client has
locked that key concurrently.

Usable with `lock`/`release` in a try/finally block, or more easily via the the `hold` method in a with block.
By default acquiring the lock is assumed to be a critical path, and will throw an exception if unable to acquire.
The lock has a maximum (configurable) lifespan, which can prevent deadlocks or stale locks in the event that a
lock is never released due to code crashes. 

No guarentees are made about the behavior if a client continues to hold
the lock for longer than its maximum lifespan (`lock_timeout_seconds`), Consul will release the lock at some point soon after the timeout. This is a good in thing, it is in fact the entire point of an ephemeral lock, because it makes it nearly impossible for stale locks to gum up whatever you are processing. The ideal setup if to configure the `lock_timeout_seconds` to be just long enough that there is no way your critical block could still be running, so it's safe enough to assume that the code that originally acquired the lock simply died.

The ephemeral lock is implemented with Consul's [session](http://python-consul.readthedocs.org/en/latest/#consul-session) and [kv] (http://python-consul.readthedocs.org/en/latest/#consul-kv) API and the key/value associated with the lock will be deleted upon release.

### Examples

##### Setup `consul_lock` defaults
In order to create a lock, you must either pass in a reference to a `consul.Consul` client each time, or assign a default client to use.

```python
import consul
import consul_lock

consul_client = consul.Consul()
consul_lock.defaults.consul_client = consul_client
```

##### Creating and holding a lock with as a context manager
The simplest way to use a lock is in a `with` block as a context manager. The lock will be automatically released then the `with` block exits.

```python
from consul_lock import EphemeralLock

ephemeral_lock = EphemeralLock('my/special/key', acquire_timeout_ms=500)
with ephemeral_lock.hold():
    # do dangerous stuff here
    print 'here be dragons'
```

##### Creating a lock and acquiring and releasing it explicitly
It is also possible to manually acquire and release the lock. The following is equivalent to the previous example.

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

##### Reacting to `acquire` attempt
By default acquiring a lock (with `acquire` or `hold`) is assumed to be a critical operation and will throw an exception if it is unable to acquire the lock within the specified timeout. Sometimes it may be desirable to react to the fact that the lock is being held concurrently by some other code or host. In that case you can set the `fail_hard` option and `acquire` will return whether or not is was able to acquire the lock.

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

### Lock configuration

Most of these settings can be both configured in `consul_locks.defaults` and overridden on each creation of the lock as keyword argments to the lock class. 

 - `consul_client` - The instance of `consul.Consul` to use for accessing the Consul API. (no default, must be set or overridden)

 - `acquire_timeout_ms` - How long, in milliseconds, the caller is willing to wait to acquire the lock. When set to 0 lock acquisition will fail if the lock cannot be acquired immediately. (default = 0)

 - `lock_timeout_seconds` - How long, in seconds, the lock will stay alive if it is never released, this is controlled by Consul's Session TTL and may stay alive a bit longer according to their docs. As of the current version of Consul, this must be between 10 and 3600. (default = 180)

 - `lock_key_pattern` - A format string which will be combined with the `key` parameter for each lock to determine the full key path in Consul's key/value store. Useful for setting up a prefix path which all locks live under. This can only be set in `consul_locks.defaults`. (default = `'locks/ephemeral/%s'`)

 - `generate_value` - This can only be set in the `consul_locks.defaults`. (defaults to a function returning a JSON string containing `"locked_at": str(datetime.now())`)


FAQ
---

##### Is this "production ready"?
Use at your own risk, this code is young and has hopes and dreams of being battletested and rugged someday. Oyster has been using this in production since tag [0.1.4](https://github.com/oysterbooks/python-consul-lock/tree/0.1.4).

##### Why is this useful?
Well, that really depends on what you're doing, but generally [distributed locks](https://en.wikipedia.org/wiki/Distributed_lock_manager) are useful to prevent [race conditions](https://en.wikipedia.org/wiki/Race_condition).

##### How should I choose my key when locking?
Lock keys should be a specific as possible to the critical block of code the lock is protecting. 

For example, one use case of locking may be to prevent emailing a welcome email upon signing up for a service.:
 - "send/email" - this is a terrible key to lock on, because it would affect all user emails across your entire code base. You would only be able to send one email at a time!
 - "send/user-123456/welcome-email" - assuming that the "123456" part is the user's ID, this is actually a pretty good lock because if user "123457" signs up at the exact same time, no problem! The locks for each user are unique, and can be acquired concurrently.

##### Ephemeral?!
So, you may be asking yourself, "I just double checked the definition for ephemeral, and dissapearing locks doen't sound too safe...wtf?" There is something to be said for not being too safe, if locks never dissapeared then what would happen if a [chaos monkey](http://techblog.netflix.com/2011/07/netflix-simian-army.html) came in and unplugged the server that acquired the lock? It would never be released, and you'd have to go in by hand and delete the lock in order to run your critical block of code.

##### Is the lock reentrant?
Nope, so be careful not to deadlock! If you somehow try to lock the same key while already holding a lock on that key, it will always fail until something times out.

Reentrant locking could be implemented since Consul's session API allows the same session to reacquire the same locked key, feel free to submit a pull request if you want that.

##### Has anyone actually asked any of these questions?
Nope.
