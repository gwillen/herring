#!/bin/sh
# Posts the dashboard Settings form on the dev stack, e.g.:
#   scripts/dev/save-settings.sh "hunt_id=0&discord_enabled=on&discord_guild_id=1234"
# (Fields left out are cleared or switched off, as with the real form.)
cd "$(dirname "$0")/../.."; B=http://localhost:${HERRING_PORT:-18000}; J=$(scripts/dev/dash-session.sh)
CSRF=$(grep csrftoken "$J" | awk '{print $7}')
curl -s -b "$J" -c "$J" -o /dev/null -w "save settings -> %{http_code}\n" -H "X-CSRFToken: $CSRF" -H "Referer: $B/dashboard/settings/" \
    -d "csrfmiddlewaretoken=$CSRF&$1" "$B/dashboard/settings/save/"
curl -s -b "$J" "$B/dashboard/settings/" | grep -oE 'alert-[a-z]+">[^<]+' | sed 's/.*">/  page says: /'
rm -f "$J"
