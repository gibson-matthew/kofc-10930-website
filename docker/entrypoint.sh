#!/bin/sh
set -eu

mkdir -p /data/uploads /tmp/nginx/client /tmp/nginx/proxy /tmp/nginx/fastcgi /tmp/nginx/uwsgi /tmp/nginx/scgi

uvicorn main:app --app-dir /app/backend --host 127.0.0.1 --port 8000 &
api_pid=$!

nginx -c /app/docker/nginx.conf -g "daemon off;" &
web_pid=$!

trap 'kill "$api_pid" "$web_pid" 2>/dev/null || true' TERM INT

while kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null; do
    sleep 1
done

kill "$api_pid" "$web_pid" 2>/dev/null || true
wait || true
exit 1
