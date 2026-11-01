#!/usr/bin/env bash
# engine/tools/public_tunnel.sh <hostname> — put the VIEW-ONLY dashboard (v5-dashboard-public, :8771) on the
# internet at https://<hostname> through a named Cloudflare tunnel, as the systemd user unit v5-tunnel.
# Never points at :8770 (the copy with the trading buttons).
#
#   1. the domain (e.g. from DigitalPlat FreeDomain) uses Cloudflare's nameservers and is "Active" in Cloudflare
#   2. cloudflared tunnel login                          (browser: pick that domain)
#   3. engine/tools/public_tunnel.sh v5.example.dpdns.org
set -euo pipefail
HOST=${1:?usage: public_tunnel.sh v5.example.dpdns.org}
NAME=v5-dashboard
CF=$HOME/.cloudflared

[ -f "$CF/cert.pem" ] || { echo "first run: cloudflared tunnel login"; exit 1; }
cloudflared tunnel info "$NAME" >/dev/null 2>&1 || cloudflared tunnel create "$NAME"
ID=$(cloudflared tunnel list -o json | python3 -c "import json,sys; print(next(t['id'] for t in json.load(sys.stdin) if t['name']=='$NAME'))")
cloudflared tunnel route dns --overwrite-dns "$NAME" "$HOST"

cat > "$CF/$NAME.yml" <<EOF
tunnel: $ID
credentials-file: $CF/$ID.json
ingress:
  - hostname: $HOST
    service: http://127.0.0.1:8771
  - service: http_status:404
EOF

cat > "$HOME/.config/systemd/user/v5-tunnel.service" <<EOF
[Unit]
Description=Cloudflare tunnel https://$HOST -> view-only V5 dashboard (:8771)
After=network-online.target v5-dashboard-public.service

[Service]
ExecStart=/usr/bin/cloudflared tunnel --no-autoupdate --config $CF/$NAME.yml run
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now v5-tunnel
echo "live in ~1 min: https://$HOST   (status: systemctl --user status v5-tunnel)"
