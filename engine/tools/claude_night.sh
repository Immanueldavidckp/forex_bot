#!/bin/bash
# engine/tools/claude_night.sh — David 2026-11-07 "tonight full on, take as much as possible, all strategies":
#   every 30 min: engine/tools/claude_crypto.py scan (new 0.01-lot entries on crypto symbols without a position)
#   stop taking new entries once Claude's trades for the night are down more than $LOSS_CAP (the open ones keep their stops)
cd ~/forex || exit 1
export MT5_NO_LAUNCH=1
LOSS_CAP=${LOSS_CAP:-40}
LOG=engine_data/kronos/claude_crypto.log
while true; do
  pnl=$(python3 - <<'EOF'
import mt5_client as m, json, time
day = time.time() - 24*3600
pos = m.positions(magic=24102099)
deals = [d for d in m.deals(days=1) if d.get("magic") == 24102099 and d.get("entry") == 1]
print(round(sum(float(p["profit"]) for p in pos) + sum(float(d.get("profit", 0)) + float(d.get("commission", 0)) + float(d.get("swap", 0)) for d in deals), 2))
EOF
)
  echo "[night $(date +%H:%M:%S)] Claude P&L last 24 h (open + closed): \$$pnl" | tee -a "$LOG"
  if [ -z "$pnl" ]; then
    echo "[night $(date +%H:%M:%S)] MT5 did not answer (IPC timeout) — skipping this round, not a loss cap" | tee -a "$LOG"
  elif python3 -c "import sys; sys.exit(0 if float('$pnl') > -$LOSS_CAP else 1)"; then
    CLAUDE_PNL24="$pnl" python3 -m engine.tools.claude_crypto scan > /dev/null 2>> "$LOG"   # scan writes its own log lines (stdout too: no double lines)
  else
    echo "[night $(date +%H:%M:%S)] loss cap \$$LOSS_CAP reached — no new entries" | tee -a "$LOG"
  fi
  sleep 1800
done
