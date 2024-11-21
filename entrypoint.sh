#!/bin/bash

# Set up user with the provided UID and GID
if [ -n "$HOST_UID" ] && [ -n "$HOST_GID" ]; then
    groupadd -g "$HOST_GID" linbpq || true
    useradd -u "$HOST_UID" -g "$HOST_GID" -m linbpq || true
    chown -R linbpq:linbpq /config
    exec gosu linbpq "$@"
else
    exec "$@"
fi

