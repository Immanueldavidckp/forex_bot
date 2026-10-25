#!/usr/bin/env python3
"""
agent.py ROLE - one forex desk member, powered by Claude Code in headless mode (claude -p).
Run one per terminal, or let start_desk.sh open all six in tmux.

  python3 agent.py research          # roles: research news strategy code risk boss
  python3 agent.py news --mock       # no Claude calls, for testing the plumbing

Each agent watches team/cycles/<id>/ and starts as soon as the files it needs exist:
  market -> research + news -> strategy -> code -> risk -> boss
"""
import argparse, glob, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from claude_trading_desk import mock_agent, parse_json  # noqa: E402

NEEDS = {"research": ["market"], "news": ["market"], "strategy": ["research", "news"],
         "code": ["strategy"], "risk": ["code"], "boss": ["risk"]}
TOOLS = {"news": "WebSearch,WebFetch"}          # everyone else gets no tools at all
CYCLES = os.path.join(HERE, "cycles")
WORK = os.path.join(HERE, "workspace")          # empty dir, so your project's CLAUDE.md isn't loaded


def ready_cycles(role):
    for d in sorted(glob.glob(os.path.join(CYCLES, "*")))[-3:]:
        if os.path.exists(os.path.join(d, "closed")) or os.path.exists(os.path.join(d, f"{role}.json")):
            continue
        if all(os.path.exists(os.path.join(d, f"{n}.json")) for n in NEEDS[role]):
            yield d


def read_cycle(d):
    return {os.path.basename(f)[:-5]: json.load(open(f))
            for f in sorted(glob.glob(os.path.join(d, "*.json"))) if not f.endswith("final.json")}


def run_claude(role, data, model):
    rules = "\n".join(open(os.path.join(HERE, "roles", f)).read() for f in ("desk.md", f"{role}.md"))
    prompt = ("Everything the desk has for this cycle:\n" + json.dumps(data, indent=1) +
              "\n\nDo your job and reply with ONLY the JSON object your role defines.")
    # --safe-mode: no CLAUDE.md, MCP servers, hooks or skills from your own setup reach the desk;
    # --tools: the only tools that exist for this role (none, or web search for news)
    cmd = ["claude", "-p", "--output-format", "json", "--model", model, "--safe-mode",
           "--append-system-prompt", rules, "--tools", TOOLS.get(role, "")]
    if role in TOOLS:
        cmd += ["--allowedTools", TOOLS[role]]
    out = subprocess.run(cmd, input=prompt, cwd=WORK, capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        return {"error": (out.stderr.strip() or out.stdout.strip())[-300:] or f"exit {out.returncode}"}
    return parse_json(json.loads(out.stdout).get("result", ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("role", choices=NEEDS)
    ap.add_argument("--model", default="opus", help="any model name/alias your Claude Code accepts")
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()
    os.makedirs(CYCLES, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    print(f"=== {args.role.upper()} agent ready ({'mock' if args.mock else 'Claude Code ' + args.model}) ===",
          flush=True)

    while True:
        for d in ready_cycles(args.role):
            cid, t0 = os.path.basename(d), time.time()
            print(f"[{cid}] working...", flush=True)
            data = read_cycle(d)
            try:
                res = mock_agent(args.role, data) if args.mock else run_claude(args.role, data, args.model)
            except subprocess.TimeoutExpired:
                res = {"error": "timeout"}
            except Exception as e:
                res = {"error": f"{type(e).__name__}: {e}"[:300]}
            tmp = os.path.join(d, f".{args.role}.tmp")
            with open(tmp, "w") as f:
                json.dump(res, f, indent=1)
            os.replace(tmp, os.path.join(d, f"{args.role}.json"))
            brief = res.get("error") or res.get("summary") or res.get("reasoning") or res.get("verdict") or res
            print(f"[{cid}] done in {time.time() - t0:.0f}s -> {str(brief)[:110]}", flush=True)
        time.sleep(3)


if __name__ == "__main__":
    main()
