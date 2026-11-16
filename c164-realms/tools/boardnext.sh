#!/usr/bin/env bash
# The render station's round of the board, the half done in the session's own checkout (git and a
# few seconds of arithmetic; nothing heavy): take the assembly's head into this branch and print the
# job that draws and shoots its board on a node (tools/boardround.py).
#
#   bash tools/boardnext.sh            from c164-realms/ of the render station's work tree
#
#   1. fetch the assembly and name the commit its build/ is of: the oldest commit down the
#      assembly's first parents with the same build/ tree. The pictures are named after that one,
#      so a head that only merged pictures or documents does not ask for a new board;
#   2. the head's history must be clean (tools/provenance.sh): nothing of the second shift;
#   3. merge it; a conflict stops the round here, nothing is pushed;
#   4. the stations: when the skeleton moved one, tools/win/shots/obs-board.json is written anew;
#   5. the plots: a scene that has none in tools/win/plots.json gets the next free one;
#   6. push, and print the job.
#
# Ends with 0 and the line "JOB: ..." when there is a board to make, with 3 when this branch
# already holds pictures of that commit's board, with 1 when something is wrong.
set -u
cd "$(dirname "$0")/.." || exit 1
ASSEMBLY=${C164_ASSEMBLY:-cursor/c164-assembly-fable-a9f5}
PY=${C164_PY:-/agent/realms-study/.venv/bin/python}
[ -x "$PY" ] || PY=python3
branch=$(git rev-parse --abbrev-ref HEAD)
if [ -n "$(git status --porcelain -- . | head -1)" ]; then
    echo "boardnext: this checkout has changes that are not committed; commit them first"; exit 1
fi
timeout 180 git fetch -q origin "$ASSEMBLY" || { echo "boardnext: the assembly could not be fetched"; exit 1; }
A=$(git rev-parse FETCH_HEAD)
T=$(git rev-parse "$A:c164-realms/build")
B=$A
for c in $(git rev-list --first-parent "$A" | head -400); do
    [ "$(git rev-parse "$c:c164-realms/build" 2>/dev/null)" = "$T" ] && B=$c || break
done
a=${A:0:8}; b=${B:0:8}
echo "assembly $a ($(git log -1 --format=%cd --date=format:'%m-%d %H:%M' "$A") UTC); its build/ is that of $b: $(git log -1 --format=%s "$B" | cut -c1-90)"

shown=$(grep -v '^#' renders/real/obs/real.txt 2>/dev/null | awk '{print $3}' | sort -u | tr '\n' ' ')
if git merge-base --is-ancestor "$A" HEAD && [ "$shown" = "$b " ] && [ -f "renders/board/${B:0:7}/sheet.jpg" ]; then
    echo "boardnext: the board of $b is here already (renders/real/obs/, renders/board/${B:0:7}/): nothing to make"
    exit 3
fi

if ! git merge-base --is-ancestor "$A" HEAD; then
    said=$(bash tools/provenance.sh "$A" 2>&1 | tail -1)
    case "$said" in
        clean*) ;;
        *) echo "boardnext: tools/provenance.sh does not call $a clean: $said"; exit 1 ;;
    esac
    if ! git merge --no-edit -q -m "c164-s1: merge the assembly ($a); its build/ is that of $b" "$A"; then
        echo "boardnext: the merge of $a stopped:"; git status --short | head -20
        echo "boardnext: nothing is pushed; settle it by hand (git merge --abort undoes it)"; exit 1
    fi
fi

if ! "$PY" tools/boardshots.py --check >/dev/null 2>&1; then
    "$PY" tools/boardshots.py --write || { echo "boardnext: tools/boardshots.py --write failed"; exit 1; }
    git add tools/win/shots/obs-board.json
    git commit -q -m "c164-s1: the board's stations as the skeleton of $a gives them" || true
    echo "boardnext: the skeleton moved a station: tools/win/shots/obs-board.json is written anew"
    "$PY" tools/boardshots.py --check | tail -1
fi

added=$("$PY" - <<'EOF'
import json, os
path = "tools/win/plots.json"
table = json.load(open(path, encoding="utf-8"))
plots = table["plots"]
new = sorted(name for name in os.listdir("build/scenes")
             if not name.startswith("_") and os.path.isdir(os.path.join("build/scenes", name))
             and os.path.exists(os.path.join("build/scenes", name, "__init__.py")) and name not in plots)
for name in new:
    plots[name] = max(plots.values()) + 1
if new:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(table, f, indent=2, ensure_ascii=False)
        f.write("\n")
print(" ".join(f"{name}={plots[name]}" for name in new))
EOF
) || { echo "boardnext: tools/win/plots.json could not be read"; exit 1; }
if [ -n "$added" ]; then
    git add tools/win/plots.json
    git commit -q -m "c164-s1: plots for the scenes new in $a ($added)"
    echo "boardnext: new plots: $added"
fi

if ! timeout 180 git push -q -u origin "$branch" >/dev/null 2>&1; then
    echo "boardnext: the push failed (fetch this branch, merge the node's commits, run this again)"; exit 1
fi
echo "pushed: $(git rev-parse --short=8 HEAD) on $branch"
echo "JOB: bash c164-realms/tools/nodejob.sh --always --tail 40 --limit 780 python tools/boardround.py --at $b --budget 600"
