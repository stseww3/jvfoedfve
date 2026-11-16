#!/usr/bin/env bash
# One round of the whole save (plan/packages/common/export.md): the git part of it. The server is
# only ever started inside a job on a worker node (tools/export.py); this script runs where the
# session is and does nothing but git and one short python script.
#
#   bash c164-realms/tools/exportnext.sh [<commit of the assembly>]
#       merges the assembly (its head, or the commit named) into the export branch and that into the
#       dist branch, pushes both and prints the job to send to the node (tools/exportround.sh): the
#       save for Realms and the same without the shaders, each made and verified
#   bash c164-realms/tools/exportnext.sh done ["what is new in this one"]
#       after the job's receipt: pulls the dist branch, writes dist/history.json and the table of
#       dist/README.md (tools/export.py page), pushes, and prints the lines to report.
#       C164_CANDIDATE=A8 names the save to upload; the history keeps it until another is named,
#       and while the newest save is not it the page and the report say which one is
#
# Two working trees, both the caller's own (never the shared checkout):
#   C164_EXPORT_TREE   the export branch: the tool and its notes  (default: outb's)
#   C164_DIST_TREE     the dist branch: the export branch plus c164-realms/dist/, which never goes
#                      to the assembly (the director's #61069)
# A save is named by its series and its number in it: A1, A2, ... were the first round's (A8 its
# candidate), B1, B2, ... are the second round's (the director's #85337). The number goes up by
# one each round; C164_SERIES=B starts a series (the next save is B1) where the newest folder is
# of an earlier one, and names the series to go on with otherwise. A numbered folder is never taken out of the
# tree again: its path may have been handed to somebody, and a path that was given out must not go
# dead (the director's #77375, after A5 had gone from the head with the round of A6). A1 to A4,
# from before that rule, are in the branch's history at the commits the table names.
set -euo pipefail

ASSEMBLY=${C164_ASSEMBLY:-cursor/c164-assembly-fable-a9f5}
ET=${C164_EXPORT_TREE:-/agent/repos/c164-outb-export-f3-f4b8}
DT=${C164_DIST_TREE:-/agent/repos/c164-outb-dist-f3-f4b8}
EB=$(git -C "$ET" rev-parse --abbrev-ref HEAD)
DB=$(git -C "$DT" rev-parse --abbrev-ref HEAD)
DIST="$DT/c164-realms/dist"

hush() { "$@" 2>&1 | grep -v "https://" || true; }      # a remote's address is never printed
clean() { [ -z "$(git -C "$1" status --porcelain)" ] || { echo "$1 has changes that are not committed: nothing done"; exit 1; }; }
# the newest save's name (B2 is newer than B1, and any B newer than any A), and the one after it
newest() { ls -d "$DIST"/[A-Z][0-9]* 2>/dev/null | sed 's/.*\///' | grep -E '^[A-Z][0-9]+$' | sort -k1.1,1.1 -k1.2n | tail -1; }
after() {
    local last=$1 series=${C164_SERIES:-}
    [ -n "$series" ] || series=${last:0:1}
    [ -n "$series" ] || series=A
    case "$series" in [A-Z]) ;; *) echo "C164_SERIES is one capital letter, not $series" >&2; return 1 ;; esac
    if [ "${last:0:1}" = "$series" ]; then echo "$series$(( ${last:1} + 1 ))"
    elif [ -z "$last" ] || [[ "$series" > "${last:0:1}" ]]; then echo "${series}1"
    else echo "series $series is older than the newest save, $last" >&2; return 1; fi
}

if [ "${1:-}" = "done" ]; then
    clean "$DT"
    hush git -C "$DT" pull -q origin "$DB"
    N=$(newest)
    [ -n "$N" ] || { echo "no whole save under $DIST"; exit 1; }
    HELD=$(git -C "$DT" rev-parse --short=8 HEAD)
    OUT=$(cd "$DT/c164-realms" && python3 tools/export.py page dist --commit "$HELD" ${2:+--note "$2"} ${C164_CANDIDATE:+--candidate "$C164_CANDIDATE"})
    echo "$OUT" | grep -v "^REPORT " || true
    git -C "$DT" add "$DIST"
    git -C "$DT" commit -q -m "c164-outb: dist -- the whole save $N is the newest; the page and the history say what is in it"
    hush git -C "$DT" push -q -u origin "$DB"
    echo "pushed: $DB @ $(git -C "$DT" rev-parse --short=8 HEAD)"
    echo "$OUT" | grep "^REPORT " | sed 's/^REPORT //' | BRANCH="$DB" python3 -c '
import json, os, sys
r = json.load(sys.stdin)
mb = lambda v: "{:.1f} 兆（{:,} 字节）".format(v / 1048576, v).replace(",", " ")
r.update(branch=os.environ["BRANCH"], sha=r["sha256"][:8] + "…" + r["sha256"][-4:], zip=mb(r["zip_bytes"]), pack=mb(r["pack_bytes"]),
         ok="全过" if r["verified"] else "没过：" + "、".join(r["failed"]))
print("【{n}】总装 {assembly}，钟锁 {time}。".format(**r) + ("" if r.get("chosen") in (None, r["n"]) else "在做的一版；要传 Realms 的仍是 {}。".format(r["chosen"])))
print("1. `{branch}`，`c164-realms/dist/{n}/c164-{n}.zip`，sha256 {sha}。".format(**r))
print("2. 存档 {zip}，其中资源包 {pack}（{pack_files} 个文件，上限 250 兆）；{blocks} 方块、{entities} 个显示实体。".format(**r))
print("3. 服务端冷启动两次，{checks} 项{ok}，日志警告和报错 {console} 条。导出 {make_s} 秒，验证 {verify_s} 秒。".format(**r))
print("数据包：函数 {functions}、标签 {tags}、注册表文件 {registry_files}；占位贴图 {standins} 张；资源包里着色器 {shaders} 个。".format(**dict(r, shaders=r.get("shaders") or 0)))
print("光照：存盘前等到不再变（{} 秒）。".format(r["light"]) if r.get("light") else "光照：存盘时还在变，这一版的光不全！" if r.get("light") is False else "光照：没等。")
print("导览：带（进服的标题、牌子、星图）" + ("；存档在世界列表里叫「{}」。".format(r["title"]) if r.get("title") else "。") if r.get("guide") else "导览：不带。")
if r.get("bare"):
    print("不带导览的：`{}`，{}，sha256 {}，{}。".format(
        r["bare"]["file"], mb(r["bare"]["bytes"]), r["bare"]["sha256"][:8] + "…" + r["bare"]["sha256"][-4:],
        "验证全过" if r["bare"].get("verified") else "验证没过" if r["bare"].get("verified") is False else "没验"))
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
N=$(after "$(newest)")
git -C "$DT" merge -q --no-edit "$EB" -m "c164-outb: merge the export branch (assembly $AT) for the whole save $N" || { echo "$EB does not merge into $DB: by hand"; exit 1; }
hush git -C "$DT" push -q -u origin "$DB"
echo "assembly $AT -> $EB @ $(git -C "$ET" rev-parse --short=8 HEAD) -> $DB @ $(git -C "$DT" rev-parse --short=8 HEAD); the next save is $N"
echo "the job for the node, on the branch $DB (a minute and a half for each variant; timeout 1900):"
echo "bash c164-realms/tools/nodejob.sh --limit 1800 --always --keep c164-realms/dist 'bash tools/exportround.sh $N $AT'"
