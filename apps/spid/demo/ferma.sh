#!/usr/bin/env bash
cd "$(dirname "$0")"
for n in ta op rp; do [ -f log/$n.pid ] && kill "$(cat log/$n.pid)" 2>/dev/null; rm -f log/$n.pid; done
pkill -f "runserver 127.0.0.1:801[012]" 2>/dev/null || true
echo "fermati"
