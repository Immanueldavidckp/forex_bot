#!/usr/bin/env bash
# Opens the whole forex desk in tmux: 6 Claude Code agents in one window, conductor in another,
# plus the stop watcher when trading through OpenClaw.
#
#   ./start_desk.sh              real Claude agents, live prices, paper money
#   ./start_desk.sh paper mock   no Claude calls, fake prices (plumbing test)
#   ./start_desk.sh openclaw     real agents -> OpenClaw -> place_order.py (LIVE only if desk.env has LIVE=1)
#
#   SYMBOL=USD/JPY INTERVAL=4h BUDGET=200 MODEL=sonnet ./start_desk.sh
#
# Inside tmux: Ctrl+b then n/p to switch windows, Ctrl+b then d to detach (keeps running).
# Stop everything: tmux kill-session -t desk
# Without tmux the desk runs in this terminal instead, agent output in team/logs/ (Ctrl+C stops it all).
set -e
cd "$(dirname "$0")"
MODE=${1:-paper}
MOCK=${2:-}
AFLAG="--model ${MODEL:-opus}"; CFLAG="--symbol ${SYMBOL:-EUR/USD} --interval ${INTERVAL:-1h} --budget ${BUDGET:-50}"
if [ "$MOCK" = "mock" ]; then AFLAG="--mock"; CFLAG="$CFLAG --mock-data --cycles 20"; fi
ROLES="research news strategy code risk boss"

if ! command -v tmux >/dev/null; then
  echo "tmux not found - running the desk here, agent output in team/logs/ (Ctrl+C stops everything)"
  mkdir -p logs
  trap 'kill $(jobs -p) 2>/dev/null' EXIT
  for r in $ROLES; do python3 agent.py $r $AFLAG > logs/$r.log 2>&1 & done
  if [ "$MODE" = "openclaw" ]; then python3 ../place_order.py watch > logs/stops.log 2>&1 & fi
  python3 conductor.py --handoff $MODE $CFLAG
  exit
fi

tmux kill-session -t desk 2>/dev/null || true
tmux new-session -d -s desk -n team "python3 agent.py research $AFLAG; read"
for r in news strategy code risk boss; do
  tmux split-window -t desk:team "python3 agent.py $r $AFLAG; read"
  tmux select-layout -t desk:team tiled
done
tmux new-window -t desk -n conductor "python3 conductor.py --handoff $MODE $CFLAG; read"
if [ "$MODE" = "openclaw" ]; then
  tmux new-window -t desk -n stops "python3 ../place_order.py watch; read"
fi
tmux select-window -t desk:team
tmux attach -t desk
