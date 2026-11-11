#!/bin/sh
# Applies a server-setup plan's default-ticked operations on the dev stack (confirming any safety warning),
# waits for them, and summarizes the results. Usage: scripts/dev/apply-plan.sh PLAN_ID
# Compose project: $HERRING_DEV_PROJECT (default herring-claude); port: $HERRING_PORT (default 18000).
set -eu
cd "$(dirname "$0")/../.."; PLAN=$1; B=http://localhost:${HERRING_PORT:-18000}; J=$(scripts/dev/dash-session.sh)
CSRF=$(grep csrftoken "$J" | awk '{print $7}')
shell() { docker compose -p "${HERRING_DEV_PROJECT:-herring-claude}" exec -T project python herring/manage.py shell -c "$1" 2>/dev/null | grep -v "^\[20\|objects imported"; }
KEYS=$(shell "from dashboard.models import SetupPlan
print('&'.join('operation=' + o.key for o in SetupPlan.objects.get(id=$PLAN).operations.filter(default_selected=True)))" | tail -1)
curl -s -b "$J" -c "$J" -o /dev/null -w "apply -> %{http_code}\n" -H "X-CSRFToken: $CSRF" -H "Referer: $B/dashboard/discord/setup/$PLAN/" \
    -d "csrfmiddlewaretoken=$CSRF&acknowledge=yes&$KEYS" "$B/dashboard/discord/setup/$PLAN/apply/"
rm -f "$J"; start=$(date +%s)
while [ "$(shell "from dashboard.models import SetupOperation as O; print(O.objects.filter(plan_id=$PLAN, status='queued').count())" | tail -1)" != 0 ]; do
    [ $(( $(date +%s) - start )) -gt 600 ] && echo "still running after 600s" && break; sleep 5
done
echo "elapsed $(( $(date +%s) - start ))s"
shell "from dashboard.models import SetupOperation as O
import collections
ops = O.objects.filter(plan_id=$PLAN)
print(dict(collections.Counter(o.status for o in ops)))
for o in ops.exclude(status__in=['applied', 'pending']): print(' ', o.status, o.key, '|', o.error[:400].replace(chr(10), ' '))"
