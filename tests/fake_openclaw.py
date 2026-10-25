#!/usr/bin/env python3
"""Stand-in for `openclaw agent ... --message-file TICKET`: runs the one command on the ticket, as OpenClaw should."""
import shlex, subprocess, sys

ticket = open(sys.argv[sys.argv.index("--message-file") + 1]).read()
cmd = next(line for line in ticket.splitlines() if line.startswith("python3 "))
args = shlex.split(cmd)
args[0] = sys.executable
out = subprocess.run(args, capture_output=True, text=True)
print(out.stdout.strip() or out.stderr.strip())
