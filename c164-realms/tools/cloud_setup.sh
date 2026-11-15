#!/usr/bin/env bash
# Make a cloud machine ready for c164 work: the machine the sessions share, and every worker node
# (tools/nodejob.sh runs this there). Whatever lies outside the repository is gone when a machine is
# replaced, so everyone runs this once after coming online. Running it again is harmless: what is in
# place is left alone.
#
#   bash c164-realms/tools/cloud_setup.sh [--no-smoke] [<code> <branch> [<from>]]
#
# The repository lies under /agent/repos/jvfoedfve on its main branch, which does not hold this
# file. Take it from the assembly branch and run it, in one line:
#
#   cd /agent/repos/jvfoedfve && git fetch -q origin cursor/c164-assembly-fable-a9f5 && git show FETCH_HEAD:c164-realms/tools/cloud_setup.sh | bash -s -- <code> <branch> <from>
#
# What it leaves, at the paths the documents and the scripts already use:
#
#   /agent/realms-study/.venv                             Python with numpy, Pillow, nbtlib and numba (what
#                                                         check.py, delivery.py and the offline renderer need)
#   /agent/realms-study/client26/versions/26.3/26.3.jar   the game's client jar, from Mojang, SHA-1 checked
#   /agent/realms-study/inbox/                            where pictures sent back from the admin's computer land
#   /agent/repos/<branch without cursor/>                 your working tree on <branch>, when code and branch are
#                                                         given: the branch as the remote has it, or a new one cut
#                                                         from <from> (a commit: the head your predecessor of the
#                                                         first shift left) or, without <from>, from the assembly
#   /tmp/c164_<code>/                                     your folder for temporary files
#
# Nothing of the second shift (plan/roles/HANDOVER.md, section 0) is built on: a branch or a <from>
# with one of its commits in its history is refused, by the test tools/provenance.sh makes.
#
# It ends with a smoke test, tools/check.py --scene obs, on a clean copy of the assembly head: that
# tests the machine, not the code on your branch. --no-smoke leaves it out.
#
# Environment: MC_ROOT (default /agent/realms-study), C164_REPO (default /agent/repos/jvfoedfve).
set -euo pipefail

ASSEMBLY="cursor/c164-assembly-fable-a9f5"
VERSION="26.3"

say() { printf '[cloud_setup %4ds] %s\n' "$SECONDS" "$*"; }
die() { printf '[cloud_setup] FAILED: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
cloud_setup.sh [--no-smoke] [<code> <branch> [<from>]]
  --no-smoke   skip the closing check.py --scene obs
  <code>       your code name; temporary files go to /tmp/c164_<code>/
  <branch>     your branch; the working tree is /agent/repos/<branch without cursor/>. Taken from the
               remote, or cut anew if the remote has none of that name
  <from>       the commit a new branch is cut from (default: the assembly head)
EOF
}

# Does the history of a commit hold a commit of the second shift? The test of tools/provenance.sh:
# committed 2026-11-15 13:40 to 17:58 UTC, or listed in the assembly's plan/shift2-commits.txt.
second_shift() {
  local repo="$1" commit="$2" listed
  listed="$(git -C "$repo" show "origin/$ASSEMBLY:c164-realms/plan/shift2-commits.txt" 2>/dev/null | awk '$1 !~ /^#/ {print $1}')"
  git -C "$repo" log --format='%ct %H' "$commit" | awk -v lo=1794750000 -v hi=1794765480 -v listed="$listed" '
    BEGIN { n = split(listed, w, "\n"); for (i = 1; i <= n; i++) if (w[i] != "") deny[w[i]] = 1 }
    ($1 >= lo && $1 <= hi) || ($2 in deny) { hit = 1; exit }
    END { exit hit ? 0 : 1 }'
}

# The body is one function called on the last line, so the whole file is read before anything runs:
# piped into `bash -s`, a command that reads standard input could otherwise swallow the rest of it.
main() {
  local smoke=1 code="" branch="" from=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --no-smoke) smoke=0 ;;
      -h|--help) usage; return 0 ;;
      -*) usage >&2; die "unknown option $1" ;;
      *) if [ -z "$code" ]; then code="$1"
         elif [ -z "$branch" ]; then branch="$1"
         elif [ -z "$from" ]; then from="$1"
         else usage >&2; die "too many arguments"; fi ;;
    esac
    shift
  done
  if [ -n "$code" ] && [ -z "$branch" ]; then usage >&2; die "give the branch along with the code"; fi

  local repo="${C164_REPO:-/agent/repos/jvfoedfve}" root="${MC_ROOT:-/agent/realms-study}"
  [ -e "$repo/.git" ] || die "no repository at $repo (set C164_REPO)"
  say "machine: $(nproc) cores, load $(cut -d' ' -f1-3 /proc/loadavg), $(python3 --version 2>&1)"

  # 1. folders
  if [ ! -d "$root" ] || [ ! -w "$root" ]; then
    sudo mkdir -p "$root" </dev/null && sudo chown -R "$(id -un):$(id -gn)" "$root" </dev/null \
      || die "cannot make $root (no sudo here? make the folder by hand, or set MC_ROOT to one you can write)"
  fi
  mkdir -p "$root/inbox" "$root/client26/versions/$VERSION"

  # 2. Python
  local py="$root/.venv/bin/python" want="numpy, PIL, nbtlib, numba" pkgs=("nbtlib==2.0.4" "numpy>=2.0" "Pillow" "numba")
  if [ -x "$py" ] && "$py" -c "import $want" >/dev/null 2>&1; then
    say "python: $root/.venv already has $want"
  else
    if [ ! -x "$py" ]; then
      if ! python3 -c 'import ensurepip' >/dev/null 2>&1; then
        local deb
        deb="python$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')-venv"
        say "python: installing $deb (the system Python has no venv module)"
        if ! sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$deb" </dev/null >/dev/null 2>&1; then
          sudo apt-get update -qq </dev/null >/dev/null 2>&1 || true
          sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$deb" </dev/null >/dev/null \
            || die "apt-get could not install $deb"
        fi
      fi
      python3 -m venv "$root/.venv" </dev/null || die "python3 -m venv failed"
    fi
    say "python: installing ${pkgs[*]}"
    "$root/.venv/bin/pip" install -q --disable-pip-version-check "${pkgs[@]}" </dev/null \
      || die "pip could not install ${pkgs[*]}"
    "$py" -c "import $want" || die "the venv cannot import $want"
  fi
  say "python: $("$py" -c "import sys, numpy, PIL, nbtlib, numba; print(sys.version.split()[0], 'numpy', numpy.__version__, 'Pillow', PIL.__version__, 'numba', numba.__version__)")"

  # 3. the game's client jar
  local jar="$root/client26/versions/$VERSION/$VERSION.jar"
  "$py" - "$VERSION" "$jar" <<'PYEOF' || die "the client jar is not in place"
import hashlib
import json
import os
import sys
import time
import urllib.request

version, path = sys.argv[1:3]
MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


def get(url, tries=5):
    last = None
    for attempt in range(tries):
        if attempt:
            time.sleep(2 ** attempt)
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                return resp.read()
        except Exception as exc:  # retried, then reported
            last = exc
    raise IOError(f"cannot fetch {url}: {last}")


def sha1_of(name):
    h = hashlib.sha1()
    with open(name, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


try:
    entry = next((v for v in json.loads(get(MANIFEST))["versions"] if v["id"] == version), None)
    if entry is None:
        sys.exit(f"Mojang's manifest lists no version {version}")
    client = json.loads(get(entry["url"]))["downloads"]["client"]
except IOError as exc:
    if os.path.exists(path):
        print(f"jar: kept {path} unchecked ({exc})")
        sys.exit(0)
    sys.exit(str(exc))
if os.path.exists(path) and sha1_of(path) == client["sha1"]:
    print(f"jar: already there, SHA-1 {client['sha1']}")
else:
    data = get(client["url"])
    if hashlib.sha1(data).hexdigest() != client["sha1"]:
        sys.exit(f"jar: the download does not have SHA-1 {client['sha1']}")
    with open(path + ".part", "wb") as fh:
        fh.write(data)
    os.replace(path + ".part", path)
    print(f"jar: fetched {len(data) >> 20} MB, SHA-1 {client['sha1']}")
PYEOF
  say "jar: $jar"

  # 4. the working tree
  git -C "$repo" fetch -q origin "+refs/heads/$ASSEMBLY:refs/remotes/origin/$ASSEMBLY" </dev/null \
    || die "cannot fetch the assembly branch"
  local tree=""
  if [ -n "$code" ]; then
    mkdir -p "/tmp/c164_$code"
    tree="$(dirname "$repo")/${branch#cursor/}"
    if [ -e "$tree/.git" ]; then
      say "tree: $tree exists, on $(git -C "$tree" rev-parse --abbrev-ref HEAD) @ $(git -C "$tree" rev-parse --short=8 HEAD); left as it is"
    else
      local found=0
      git -C "$repo" ls-remote --exit-code --heads origin "refs/heads/$branch" </dev/null >/dev/null 2>&1 || found=$?
      case "$found" in
        0) git -C "$repo" fetch -q origin "+refs/heads/$branch:refs/remotes/origin/$branch" </dev/null \
             || die "cannot fetch $branch"
           second_shift "$repo" "origin/$branch" \
             && die "$branch carries commits of the second shift, which are not built on. Give a new branch name (cursor/c164-<code>-<package>-f3) and, as the third argument, the head your predecessor of the first shift left (plan/ROSTER.md)"
           if git -C "$repo" show-ref --verify --quiet "refs/heads/$branch"; then
             git -C "$repo" worktree add -q "$tree" "$branch" </dev/null \
               || die "cannot put $branch in $tree (is it checked out in another folder? see: git -C $repo worktree list)"
             git -C "$tree" merge -q --ff-only "origin/$branch" </dev/null >/dev/null 2>&1 \
               || say "tree: the local $branch and the remote one have parted; look before you push"
           else
             git -C "$repo" worktree add -q --track -b "$branch" "$tree" "origin/$branch" </dev/null \
               || die "cannot put $branch in $tree"
           fi
           say "tree: $tree on $branch @ $(git -C "$tree" rev-parse --short=8 HEAD), as the remote has it" ;;
        2) local start="origin/$ASSEMBLY" what="the assembly head"
           if [ -n "$from" ]; then
             if ! git -C "$repo" rev-parse -q --verify "$from^{commit}" >/dev/null; then
               say "tree: $from is not here yet, fetching the project's branches"
               git -C "$repo" fetch -q origin '+refs/heads/cursor/c164-*:refs/remotes/origin/cursor/c164-*' </dev/null \
                 || die "cannot fetch the project's branches"
               git -C "$repo" rev-parse -q --verify "$from^{commit}" >/dev/null \
                 || die "no commit $from on any of the project's branches"
             fi
             second_shift "$repo" "$from" \
               && die "$from carries commits of the second shift, which are not built on. Take the head of the first shift from plan/ROSTER.md"
             start="$from" what="$from"
           fi
           git -C "$repo" worktree add -q --no-track -b "$branch" "$tree" "$start" </dev/null \
             || die "cannot cut $branch into $tree"
           say "tree: $tree on the new branch $branch, cut from $what ($(git -C "$tree" rev-parse --short=8 HEAD)); push it with: git push -u origin $branch" ;;
        *) die "cannot ask the remote about $branch" ;;
      esac
    fi
  fi

  # 5. smoke test on a clean copy of the assembly head
  if [ "$smoke" = 1 ]; then
    local tmp head
    head="$(git -C "$repo" rev-parse --short=8 "origin/$ASSEMBLY")"
    tmp="$(mktemp -d /tmp/c164_setup.XXXXXX)"
    git -C "$repo" archive "origin/$ASSEMBLY" c164-realms/build c164-realms/tools | tar -x -C "$tmp"
    local t0=$SECONDS ok=0 log="$root/cloud_setup-smoke.log"
    (cd "$tmp/c164-realms" && MC_ROOT="$root" nice "$py" tools/check.py --scene obs </dev/null) >"$log" 2>&1 || ok=$?
    rm -rf "$tmp"
    if [ "$ok" != 0 ]; then
      cat "$log"
      die "check.py --scene obs on the assembly head $head exited with $ok: the machine is not ready"
    fi
    say "smoke: check.py --scene obs on the assembly head $head, $((SECONDS - t0)) s: $(grep '^result:' "$log" | tail -n 1) (all of it: $log)"
  fi

  say "ready. Python: $py"
  if [ -n "$tree" ]; then say "work in $tree/c164-realms"; fi
}

main "$@"
