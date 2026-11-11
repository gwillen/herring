#!/bin/sh
# Logs into the dev stack's dashboard as admin/admin and prints a cookie jar path (CSRF token in its
# 'csrftoken' row). Port: $HERRING_PORT (default 18000).
B=http://localhost:${HERRING_PORT:-18000}; J=$(mktemp)
T=$(curl -s -c "$J" "$B/accounts/login/" | grep -oP 'name="csrfmiddlewaretoken" value="\K[^"]+')
curl -s -b "$J" -c "$J" -o /dev/null -H "Referer: $B/accounts/login/" -d "csrfmiddlewaretoken=$T&username=admin&password=admin" "$B/accounts/login/?next=/"
echo "$J"
