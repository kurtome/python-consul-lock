
"""
Default settings for locks created. Update this global object to change the defaults!
"""

# if you don't want to pass the consul_client into every lock
consul_client = None

acquire_timeout_ms = 0

lock_timeout_seconds = 60 * 3

# the key will always be substituted into the this pattern before locking,
# a good prefix is recommended for organization
lock_key_pattern = 'locks/ephemeral/%s'

import json
from datetime import datetime
def _json_date_value():
    return json.dumps(dict(
        locked_at=str(datetime.now())
    ))

generate_value = _json_date_value
