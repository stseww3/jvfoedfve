#!/usr/bin/env bash
# The light audit (tools/darkfloor.py) of whatever tree this is run in, with the tool and the list
# before as the audit branch has them. For a job on another branch than the audit's (the assembly's,
# somebody's own), run in c164-realms/:
#
#   git fetch -q origin cursor/c164-sound-lightaudit-f3-cbc6 && git show FETCH_HEAD:c164-realms/tools/darkrun.sh | bash
#
# The whole job, from a node, measuring the assembly's head and leaving the list where it always is:
#
#   run_workspace_job(node=<a node that answers>, repo="stseww3/jvfoedfve", branch="cursor/c164-assembly-fable-a9f5",
#     command='bash c164-realms/tools/nodejob.sh --wip --to cursor/c164-sound-lightaudit-f3-cbc6-wip --always --tail 60 "<the line above>"')
#
# It only reads the tree; what it writes is renders/_wip/light/dark.md and dark.json.
set -euo pipefail
git show FETCH_HEAD:c164-realms/tools/darkfloor.py > /tmp/darkfloor.py
git show FETCH_HEAD:c164-realms/tools/darkfloor_before.json > /tmp/darkfloor_before.json
python /tmp/darkfloor.py --head auto --before /tmp/darkfloor_before.json --out renders/_wip/light
