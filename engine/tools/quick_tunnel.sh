#!/usr/bin/env bash
# engine/tools/quick_tunnel.sh start|url|stop — share the VIEW-ONLY dashboard (:8771) with no account, no login
# and no domain: a Cloudflare quick tunnel (user unit v5-quick-tunnel). The address changes on every (re)start,
# so after a reboot run `quick_tunnel.sh url` and send the new link.
set -euo pipefail
U=v5-quick-tunnel
url() { journalctl --user -u $U --since "${1:-2000-01-01}" -o cat --no-pager 2>/dev/null \
          | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -1; }
case "${1:-url}" in
  start) since=$(date '+%F %T')
         systemctl --user enable $U >/dev/null 2>&1
         systemctl --user restart $U
         for _ in $(seq 30); do u=$(url "$since" || true); [ -n "$u" ] && { echo "$u"; exit 0; }; sleep 1; done
         echo "no address yet, see: journalctl --user -u $U"; exit 1 ;;
  url)   systemctl --user is-active -q $U && url || echo "not running: $0 start" ;;
  stop)  systemctl --user disable --now $U ;;
  *)     echo "usage: $0 start|url|stop"; exit 2 ;;
esac
