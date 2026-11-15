#!/usr/bin/env python3
"""stage.py <path> <regex> [<regex> ...]

Put into the index those hunks of the file's unstaged change whose changed lines match one of the
patterns. The hunks are taken without context, so two changes a line apart can go into two commits.
"""
import re
import subprocess
import sys

path, pats = sys.argv[1], [re.compile(p) for p in sys.argv[2:]]
diff = subprocess.run(["git", "diff", "-U0", "--", path], capture_output=True, text=True, check=True).stdout
head, *hunks = re.split(r"(?m)^(?=@@ )", diff)
out, delta, picked = [], 0, 0
for h in hunks:
    first, _, body = h.partition("\n")
    m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", first)
    a, b = int(m.group(1)), int(m.group(2) or 1)
    d = int(m.group(4) or 1)
    changed = "\n".join(line for line in body.splitlines() if line[:1] in "+-")
    if not any(p.search(changed) for p in pats):
        continue
    start = a + delta + (1 if b == 0 else 0) - (1 if d == 0 else 0)
    out.append(f"@@ -{a},{b} +{start},{d} @@\n{body}")
    delta += d - b
    picked += 1
    print("  " + first[:60] + " | " + changed.splitlines()[0][:70])
print(f"{picked} of {len(hunks)} hunks")
if out:
    r = subprocess.run(["git", "apply", "--cached", "--unidiff-zero", "-"], input=head + "".join(out), text=True,
                       capture_output=True)
    print(r.stderr.strip() or "staged")
    sys.exit(r.returncode)
