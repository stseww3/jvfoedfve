#!/usr/bin/env bash
# One round of the whole save (plan/packages/common/export.md): the git part of it. The server is
# only ever started inside a job on a worker node (tools/export.py); this script runs where the
# session is and does nothing but git and one short python script.
#
#   bash c164-realms/tools/exportnext.sh [<commit of the assembly>]
#       merges the assembly (its head, or the commit named) into the export branch and that into the
#       dist branch, pushes both and prints the job to send to the node (tools/exportround.sh): the
#       save for Realms, the same without the shaders and the same with the look, each made and
#       verified
#   bash c164-realms/tools/exportnext.sh done ["what is new in this one"]
#       after the job's receipt: pulls the dist branch, writes dist/history.json and the table of
#       dist/README.md (tools/export.py page), takes the older saves out of the tree, pushes, and
#       prints the lines to report
#
# Two working trees, both the caller's own (never the shared checkout):
#   C164_EXPORT_TREE   the export branch: the tool and its notes  (default: outb's)
#   C164_DIST_TREE     the dist branch: the export branch plus c164-realms/dist/, which never goes
#                      to the assembly (the director's #61069)
# The numbers go up by one each round (A1, A2, ...); only the newest save stays in the tree, the
# older ones are in the branch's history at the commits the table names.
set -euo pipefail

ASSEMBLY=${C164_ASSEMBLY:-cursor/c164-assembly-fable-a9f5}
ET=${C164_EXPORT_TREE:-/agent/repos/c164-outb-export-f3-f4b8}
DT=${C164_DIST_TREE:-/agent/repos/c164-outb-dist-f3-f4b8}
EB=$(git -C "$ET" rev-parse --abbrev-ref HEAD)
DB=$(git -C "$DT" rev-parse --abbrev-ref HEAD)
DIST="$DT/c164-realms/dist"

hush() { "$@" 2>&1 | grep -v "https://" || true; }      # a remote's address is never printed
clean() { [ -z "$(git -C "$1" status --porcelain)" ] || { echo "$1 has changes that are not committed: nothing done"; exit 1; }; }
newest() { ls -d "$DIST"/A[0-9]* 2>/dev/null | sed 's/.*\/A//' | sort -n | tail -1; }

if [ "${1:-}" = "done" ]; then
    clean "$DT"
    hush git -C "$DT" pull -q origin "$DB"
    N=$(newest)
    [ -n "$N" ] || { echo "no whole save under $DIST"; exit 1; }
    HELD=$(git -C "$DT" rev-parse --short=8 HEAD)
    OUT=$(cd "$DT/c164-realms" && python3 tools/export.py page dist --commit "$HELD" ${2:+--note "$2"})
    echo "$OUT" | grep -v "^REPORT " || true
    for old in "$DIST"/A[0-9]*; do
        [ "$old" = "$DIST/A$N" ] || git -C "$DT" rm -q -r "$old"
    done
    git -C "$DT" add "$DIST"
    git -C "$DT" commit -q -m "c164-outb: dist -- the whole save A$N is the newest; the page and the history say what is in it"
    hush git -C "$DT" push -q -u origin "$DB"
    echo "pushed: $DB @ $(git -C "$DT" rev-parse --short=8 HEAD)"
    echo "$OUT" | grep "^REPORT " | sed 's/^REPORT //' | BRANCH="$DB" python3 -c '
import json, os, sys
r = json.load(sys.stdin)
mb = lambda v: "{:.1f} 兆（{:,} 字节）".format(v / 1048576, v).replace(",", " ")
r.update(branch=os.environ["BRANCH"], sha=r["sha256"][:8] + "…" + r["sha256"][-4:], zip=mb(r["zip_bytes"]), pack=mb(r["pack_bytes"]),
         ok="全过" if r["verified"] else "没过：" + "、".join(r["failed"]))
print("【{n}】总装 {assembly}，钟锁 {time}。".format(**r))
print("1. `{branch}`，`c164-realms/dist/{n}/c164-{n}.zip`，sha256 {sha}。".format(**r))
print("2. 存档 {zip}，其中资源包 {pack}（{pack_files} 个文件，上限 250 兆）；{blocks} 方块、{entities} 个显示实体。".format(**r))
print("3. 服务端冷启动两次，{checks} 项{ok}，日志警告和报错 {console} 条。导出 {make_s} 秒，验证 {verify_s} 秒。".format(**r))
print("数据包：函数 {functions}、标签 {tags}、注册表文件 {registry_files}；占位贴图 {standins} 张；资源包里着色器 {shaders} 个。".format(**dict(r, shaders=r.get("shaders") or 0)))
if r.get("plain"):
    print("不带着色器的（资源包加载失败时换这个）：`{}`，{}，sha256 {}，{}。".format(
        r["plain"]["file"], mb(r["plain"]["bytes"]), r["plain"]["sha256"][:8] + "…" + r["plain"]["sha256"][-4:],
        "验证全过" if r["plain"].get("verified") else "验证没过" if r["plain"].get("verified") is False else "没验"))
if r.get("look"):
    print("带天的（只给单人看）：`{}`，{}。".format(r["look"]["file"], mb(r["look"]["bytes"])))
'
    exit 0
fi

clean "$ET"
clean "$DT"
hush git -C "$ET" fetch -q origin "$ASSEMBLY"
AT=$(git -C "$ET" rev-parse --short=8 "${1:-FETCH_HEAD}")
git -C "$ET" merge -q --no-edit "$AT" -m "c164-outb: merge the assembly ($AT) into the export branch" || { echo "the assembly does not merge into $EB: by hand"; exit 1; }
bash "$ET/c164-realms/tools/provenance.sh" HEAD | tail -1 | grep -q "^clean" || { echo "provenance.sh does not say clean: nothing pushed"; exit 1; }
hush git -C "$ET" push -q -u origin "$EB"
hush git -C "$DT" pull -q origin "$DB"
N=$(( $(newest) + 1 ))
git -C "$DT" merge -q --no-edit "$EB" -m "c164-outb: merge the export branch (assembly $AT) for the whole save A$N" || { echo "$EB does not merge into $DB: by hand"; exit 1; }
hush git -C "$DT" push -q -u origin "$DB"
echo "assembly $AT -> $EB @ $(git -C "$ET" rev-parse --short=8 HEAD) -> $DB @ $(git -C "$DT" rev-parse --short=8 HEAD); the next save is A$N"
echo "the job for the node, on the branch $DB (a minute and a half for each variant; timeout 1900). All three:"
echo "bash c164-realms/tools/nodejob.sh --limit 1800 --always --keep c164-realms/dist 'bash tools/exportround.sh $N $AT'"
echo "or the two for Realms first and the one with the look in a job of its own afterwards (then 'done' after each):"
echo "bash c164-realms/tools/nodejob.sh --limit 1800 --always --keep c164-realms/dist 'bash tools/exportround.sh $N $AT main plain'"
echo "bash c164-realms/tools/nodejob.sh --limit 1800 --always --keep c164-realms/dist 'bash tools/exportround.sh $N $AT look'"
