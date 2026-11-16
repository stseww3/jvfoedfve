#!/usr/bin/env python3
"""tools/check.py on many scenes in one go: the round the merge-key holder makes after a merge or
after a change of the public files (plan/roles/S2-integrator.md), and anyone's look at "what else
did my change touch".

    checkall.py                       every scene under build/scenes/ called obs or obs_*
    checkall.py obs obs_site_court    the scenes named (any scene check.py reads)

    --out <folder>   where the whole report of each scene goes, <scene>.txt as check.py prints it
                     and <scene>.json as check.py --json writes it, beside summary.txt, which is
                     what this script prints (default renders/_wip/check, the folder
                     tools/nodejob.sh --wip brings home)
    --jobs <n>       scenes checked at a time (default: the machine's cores)
    --jar <file>     passed on to check.py

Heavy for the machine the sessions share: send it to your node,

    bash c164-realms/tools/nodejob.sh --wip --always python tools/checkall.py

It prints one line per scene, PASS or FAIL with the counts, and under it the checks that warned or
failed, each with the first line of what check.py said; a scene whose check.py ended without a
result line (it broke before it could report) counts as failed and its last lines are shown. The
exit code is 1 when a scene fails.
"""
import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.normpath(os.path.join(HERE, ".."))
SCENES = os.path.join(PROJECT, "build", "scenes")
WIDTH = 200                 # of a line of the summary


def all_scenes():
    return sorted(n for n in os.listdir(SCENES)
                  if (n == "obs" or n.startswith("obs_")) and os.path.exists(os.path.join(SCENES, n, "__init__.py")))


def run(scene, out, jar):
    """One scene through check.py. Returns (scene, seconds, exit code, report rows or None, last lines)."""
    text, report = os.path.join(out, f"{scene}.txt"), os.path.join(out, f"{scene}.json")
    if os.path.exists(report):
        os.remove(report)
    cmd = [sys.executable, os.path.join(HERE, "check.py"), "--scene", scene, "--json", report]
    if jar:
        cmd += ["--jar", jar]
    t0 = time.time()
    with open(text, "w", encoding="utf-8") as fh:
        code = subprocess.run(cmd, cwd=PROJECT, stdout=fh, stderr=subprocess.STDOUT).returncode
    rows = None
    if os.path.exists(report):
        with open(report, encoding="utf-8") as fh:
            rows = json.load(fh)["checks"]
    with open(text, encoding="utf-8", errors="replace") as fh:
        tail = fh.read().rstrip().split("\n")[-6:]
    return scene, time.time() - t0, code, rows, tail


def main():
    ap = argparse.ArgumentParser(description="tools/check.py on many scenes")
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--out", default=os.path.join(PROJECT, "renders", "_wip", "check"))
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--jar")
    args = ap.parse_args()
    scenes = args.scenes or all_scenes()
    unknown = [s for s in scenes if not os.path.isdir(os.path.join(SCENES, s))]
    if unknown:
        sys.exit(f"no such scene under build/scenes/: {', '.join(unknown)}")
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        results = list(pool.map(lambda s: run(s, out, args.jar), scenes))
    lines, failed, warned = [], [], []
    for scene, secs, code, rows, tail in results:
        if rows is None:
            failed.append(scene)
            lines.append(f"FAIL  {scene}: check.py ended with {code} and no report ({secs:.0f} s)")
            lines += [f"          {line}"[:WIDTH] for line in tail]
            continue
        fails = [r for r in rows if r["status"] == "FAIL"]
        warns = [r for r in rows if r["status"] == "WARN"]
        skips = [r["check"] for r in rows if r["status"] == "SKIP"]
        (failed if fails else warned if warns else []).append(scene)
        lines.append(f"{'FAIL' if fails else 'PASS'}  {scene}: {len(fails)} failed, {len(warns)} with warnings"
                     + (f", skipped: {', '.join(skips)}" if skips else "") + f" ({secs:.0f} s)")
        for r in fails + warns:
            lines.append(f"      [{r['status']}] {r['check']}: {r['summary']}"[:WIDTH])
            lines += [f"          {d}"[:WIDTH] for d in r["details"][:3 if r["status"] == "FAIL" else 1]]
    lines.append(f"{len(scenes)} scenes in {time.time() - t0:.0f} s: {len(scenes) - len(failed)} pass"
                 + (f" ({len(warned)} with warnings)" if warned else "")
                 + (f", {len(failed)} FAIL: {', '.join(failed)}" if failed else ""))
    print("\n".join(lines))
    with open(os.path.join(out, "summary.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
