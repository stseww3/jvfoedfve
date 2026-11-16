#!/usr/bin/env bash
# Look at your own work in the game, on your own node: one view some times over, seconds apart,
# and what moved between the pictures. One node job of your own branch:
#
#   run_workspace_job(agent=<you>, node="<your node>", repo="stseww3/jvfoedfve", branch="<your branch>",
#       timeout_sec=1500,
#       command="bash c164-realms/tools/nodejob.sh --wip --always --tail 25 --limit 1400 'git fetch -q origin cursor/c164-s1-render-f3-fd9c && git show FETCH_HEAD:c164-realms/tools/look.sh | bash -s -- <scene> --from X Y Z --to X Y Z --shots 6 --every 2'")
#
#   <scene>                  a test scene of your build/scenes/, or obs for the whole observatory
#   --from X Y Z --to X Y Z  where the eye is and the point it looks at, in the scene's own
#                            coordinates (as in its shots.json; obs: the world's)
#   --only <shot>[,<shot>]   instead: shots of the scene's own shots.json by name (obs: board views,
#                            v01_arrival ...); neither given: every shot of the scene's list
#   --shots <n>              pictures a view (6), --every <seconds> apart (2)
#   --time <tick>            the hour (default: the scene's own, 14000)
#
# Push your commits first: the node shoots what GitHub has of your branch. What comes back, on the
# scratch branch <your branch>-wip, in c164-realms/renders/_wip/look/<scene>/:
#   <shot>_0.jpg ...   the pictures        <shot>_strip.jpg   all of them on one sheet
#   <shot>_moved.jpg   the first one with a frame around every place that moved
#   moved.txt          how many places moved in each view and where; its lines close the receipt
#   trip.log           what the trip said (why a scene did not place, what the game complained of)
# To see one:  git fetch -q origin <your branch>-wip && git show FETCH_HEAD:c164-realms/renders/_wip/look/<scene>/look_strip.jpg > /tmp/c164_<you>/strip.jpg
#
# A node that never ran the game installs it in the same job, by itself (Java, the game's files
# from Mojang, a display): the first look on a node takes about four minutes longer, and must be
# the only job on that node meanwhile. A test scene then takes two to three minutes, the whole
# observatory about ten. The tools are the render station's (s1), taken from its branch as they
# are at that moment; nothing of them is written into your branch.
main() {
  set -uo pipefail
  local station="cursor/c164-s1-render-f3-fd9c"
  local proj repo real branch commit tools side code
  proj="$PWD"
  repo="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "look: not inside a git repository" >&2; return 2; }
  real="$(realpath "$repo")"
  case "$real" in
    /tmp/dais_jobs/*) ;;
    *) echo "look: the game is opened on a worker node only; send this as a node job (see the head of tools/look.sh)" >&2; return 2 ;;
  esac
  if [ ! -d "$proj/build/scenes" ]; then
    echo "look: run in c164-realms/ of the job's tree (nodejob.sh does that)" >&2; return 2
  fi
  branch="$(git rev-parse --abbrev-ref HEAD)"
  if [ "$branch" = "HEAD" ]; then echo "look: the job's tree is on no branch" >&2; return 2; fi
  commit="$(git rev-parse HEAD)"
  if ! timeout 180 git fetch -q origin "$station"; then
    echo "look: $station could not be fetched" >&2; return 3
  fi
  tools="$(git rev-parse FETCH_HEAD)"
  side="$real-look"
  git worktree remove --force "$side" >/dev/null 2>&1
  git worktree prune >/dev/null 2>&1
  rm -rf "$side"
  if ! git worktree add -q --detach "$side" "$tools"; then
    echo "look: the render station's tools (${tools:0:8}) could not be checked out at $side" >&2; return 3
  fi
  echo "look: $branch @ ${commit:0:8}, with the render station's tools @ ${tools:0:8}"
  code=0
  ( cd "$side/c164-realms" && python tools/looktrip.py --code "$proj" --branch "$branch" --at "$commit" "$@" ) || code=$?
  git worktree remove --force "$side" >/dev/null 2>&1
  git worktree prune >/dev/null 2>&1
  return "$code"
}
main "$@" </dev/null
