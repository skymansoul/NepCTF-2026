#!/bin/sh
set -eu

echo $FLAG > /flag
unset FLAG

chown ctf:ctf /flag
chmod 777 /flag

exec su-exec ctf npm run start
