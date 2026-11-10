#!/usr/bin/env bash
# CD for the Oracle server: run every 2 min by forex-deploy.timer.
# When main on GitHub has a new commit AND its CI run passed, fast-forward ~/forex to it and restart the
# services that are running. Pull-only: the server needs no GitHub key and GitHub holds no server key.
set -euo pipefail
cd "$HOME/forex"
REPO=Immanueldavidckp/forex_bot

git fetch -q origin main
new=$(git rev-parse origin/main)
cur=$(git rev-parse HEAD)
[ "$new" = "$cur" ] && exit 0

state=$(curl -fsS "https://api.github.com/repos/$REPO/commits/$new/check-runs" | python3 -c '
import json, sys
runs = json.load(sys.stdin)["check_runs"]
if not runs: print("none")
elif any(r["status"] != "completed" for r in runs): print("pending")
elif all(r["conclusion"] == "success" for r in runs): print("success")
else: print("failure")')

if [ "$state" != success ]; then
    echo "$(date -u +%FT%TZ) ${new:0:7} CI=$state, not deployed"
    exit 0
fi

git merge --ff-only -q origin/main   # never overwrites local edits on the server; stops instead
echo "$(date -u +%FT%TZ) deployed ${cur:0:7} -> ${new:0:7}"
# try-restart: only services that are already running are restarted, nothing new is started
for s in ${DEPLOY_RESTART:-v5-dashboard v5-engine kronos-signals}; do
    systemctl --user try-restart "$s" || true
done
