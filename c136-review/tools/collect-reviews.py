#!/usr/bin/env python3
"""collect-reviews.py — 汇总所有复盘员分支上的逐局复盘，机械检查深度验收清单。

用法（在联络分支的工作区里跑）：
    python3 c136-review/tools/collect-reviews.py            # 取远端、检查、写汇总
    python3 c136-review/tools/collect-reviews.py --no-fetch # 只用本地已有的提交

产出：
    c136-review/board/REVIEWS.md           每份复盘一行：分型、数量、清单未过项
    c136-review/ledger/reviews-index.json  全部复盘的结构化索引（决策实例拍平，供跨局计数）
    c136-review/ledger/new-patterns.json   所有 NEW 模式提案（供合并去重）

这里只做机械检查：字段在不在、数量够不够、取值合不合法。内容对不对由 R10 抽查和 c136 复核。
"""
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict

REMOTE = "origin"
PATTERN = "refs/heads/cursor/c136-r[0-9][0-9]-*"
ROOT = "c136-review"
ARCHETYPES = {"early-wipe", "never-grew", "mid-collapse", "lead-thrown",
              "outscaled", "external", "win"}
VERDICTS = {"error", "good", "unclear"}
STATEMENT_TYPES = {"observed", "inferred", "guess"}
REQUIRED_TOP = ["matchId", "reviewer", "context", "outcome", "timeline", "phases",
                "turningPoints", "deaths", "decisions", "newPatterns", "lossArchetype",
                "winnerNotes", "wentWell", "unknowns", "mechanicsQuestions", "scripts",
                "confidenceOverall"]
PROPOSAL_HINTS = re.compile(r"(建议把|建议将|应该?改成|应调[到整为]|调到\s*\d|改为\s*\d|提高到\s*\d|降低到\s*\d)")


def run(args, timeout=100):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def git_show(sha, path):
    r = run(["git", "show", f"{sha}:{path}"], timeout=60)
    return r.stdout if r.returncode == 0 else None


def near(points, target, tol):
    return any(abs(p - target) <= tol for p in points)


def check_review(doc, md_text):
    """返回 (未过项列表, 统计字典)。"""
    fails = []
    for k in REQUIRED_TOP:
        if k not in doc:
            fails.append(f"缺字段 {k}")
    outcome = doc.get("outcome") or {}
    result = outcome.get("result")
    end_tick = outcome.get("endTick") or 0
    timeline = doc.get("timeline") or []
    ts = [p.get("t") for p in timeline if isinstance(p, dict) and isinstance(p.get("t"), (int, float))]
    if len(ts) < 8:
        fails.append(f"时间线只有 {len(ts)} 个点（要求 ≥8）")
    for target, tol in ((180, 120), (600, 150), (1500, 250), (3000, 300)):
        if end_tick and end_tick < target:
            continue
        if not near(ts, target, tol):
            fails.append(f"时间线缺 t≈{target}")
    if end_tick and ts and max(ts) < end_tick - 300:
        fails.append("时间线没有终局点")

    deaths = doc.get("deaths") or []
    for d in deaths:
        if not (d.get("cause") or "").strip():
            fails.append(f"阵亡号 {d.get('bot')} 没写死因")

    tps = doc.get("turningPoints") or []
    if result in ("lost", "over") and not tps:
        fails.append("输局没有转折点")
    for i, tp in enumerate(tps):
        if len(tp.get("evidence") or []) < 3:
            fails.append(f"转折点 {i + 1} 证据不足 3 条")
        pds = tp.get("priorDecisions") or []
        if not pds:
            fails.append(f"转折点 {i + 1} 没有窗口前的决策")
        elif not any((pd.get("codePath") or "").strip() for pd in pds):
            fails.append(f"转折点 {i + 1} 的决策没追到代码路径")
        if tp.get("statementType") not in STATEMENT_TYPES:
            fails.append(f"转折点 {i + 1} 没标观察/推断/猜测")

    decisions = doc.get("decisions") or []
    vc = Counter(d.get("verdict") for d in decisions)
    if len(decisions) < 10:
        fails.append(f"决策实例只有 {len(decisions)} 条（要求 ≥10）")
    if vc.get("good", 0) < 2:
        fails.append(f"判为「对」的决策只有 {vc.get('good', 0)} 条（要求 ≥2）")
    bad_verdict = [d for d in decisions if d.get("verdict") not in VERDICTS]
    if bad_verdict:
        fails.append(f"{len(bad_verdict)} 条决策的 verdict 取值不合法")
    no_code = [d for d in decisions if not (d.get("codePath") or "").strip()]
    if no_code:
        fails.append(f"{len(no_code)} 条决策没有代码路径")
    no_pat = [d for d in decisions if not (d.get("patternId") or "").strip()]
    if no_pat:
        fails.append(f"{len(no_pat)} 条决策没有模式编号")

    arch = doc.get("lossArchetype")
    if arch not in ARCHETYPES:
        fails.append(f"分型取值不合法：{arch}")
    if result == "won" and arch != "win":
        fails.append("赢局的分型应为 win")
    if result in ("lost", "over") and arch == "win":
        fails.append("输局的分型不能是 win")
    if not (doc.get("winnerNotes") or "").strip():
        fails.append("没写赢家是谁、怎么赢的")
    if not doc.get("scripts"):
        fails.append("没列脚本")

    hints = []
    blob = json.dumps(doc, ensure_ascii=False) + "\n" + (md_text or "")
    for m in PROPOSAL_HINTS.finditer(blob):
        s = max(0, m.start() - 20)
        hints.append(blob[s:m.end() + 20].replace("\n", " "))
    if md_text is None:
        fails.append("缺叙述版 .md")
    elif md_text.count("\n") > 160:
        fails.append(f"叙述版 {md_text.count(chr(10))} 行（上限 150）")

    stats = {
        "timeline": len(ts), "turningPoints": len(tps), "deaths": len(deaths),
        "decisions": len(decisions), "verdicts": dict(vc),
        "newPatterns": len(doc.get("newPatterns") or []),
        "unknowns": len(doc.get("unknowns") or []),
        "mechanicsQuestions": len(doc.get("mechanicsQuestions") or []),
        "proposalHints": hints[:5],
    }
    return fails, stats


def main():
    no_fetch = "--no-fetch" in sys.argv
    r = run(["git", "ls-remote", REMOTE, PATTERN], timeout=60)
    if r.returncode != 0:
        print("COLLECT: ERROR ls-remote 失败：" + r.stderr.strip()[:200])
        return 2
    refs = []
    for line in r.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        m = re.match(r"refs/heads/cursor/c136-r(\d\d)-", ref)
        if m:
            refs.append((f"R{m.group(1)}", sha, ref))
    refs.sort()

    rows, index, new_patterns = [], [], []
    for agent, sha, ref in refs:
        if run(["git", "cat-file", "-e", f"{sha}^{{commit}}"]).returncode != 0:
            if no_fetch:
                continue
            f = run(["git", "fetch", "-q", "--no-tags", "--refmap=", REMOTE, ref], timeout=110)
            if f.returncode != 0:
                print(f"COLLECT: WARN 取不到 {ref}")
                continue
        base = f"{ROOT}/agents/{agent}/reviews"
        ls = run(["git", "ls-tree", "-r", "--name-only", sha, "--", base], timeout=60)
        for path in sorted(p for p in ls.stdout.splitlines() if p.endswith(".json")):
            text = git_show(sha, path)
            md = git_show(sha, path[:-5] + ".md")
            name = path.rsplit("/", 1)[1][:-5]
            try:
                doc = json.loads(text)
            except Exception as e:  # noqa: BLE001
                rows.append({"agent": agent, "file": name, "fails": [f"JSON 解析失败：{e}"],
                             "stats": {}, "doc": {}, "sha": sha[:8]})
                continue
            fails, stats = check_review(doc, md)
            rows.append({"agent": agent, "file": name, "fails": fails, "stats": stats,
                         "doc": doc, "sha": sha[:8]})
            oc = doc.get("outcome") or {}
            index.append({
                "matchId": doc.get("matchId"), "file": name, "reviewer": agent, "sha": sha[:8],
                "result": oc.get("result"), "archetype": doc.get("lossArchetype"),
                "context": doc.get("context"), "outcome": oc,
                "turningPoints": doc.get("turningPoints") or [],
                "deaths": doc.get("deaths") or [],
                "decisions": doc.get("decisions") or [],
                "unknowns": doc.get("unknowns") or [],
                "mechanicsQuestions": doc.get("mechanicsQuestions") or [],
                "checklistFails": fails,
            })
            for np_ in doc.get("newPatterns") or []:
                new_patterns.append({"matchId": doc.get("matchId"), "reviewer": agent, **np_})

    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    out = [f"# 逐局复盘汇总（机械检查，{now}）", "",
           "只查字段、数量和取值；内容对不对由 R10 抽查和 c136 复核。", "",
           f"共 {len(rows)} 份复盘，来自 {len({r['agent'] for r in rows})} 名复盘员。", "",
           "| 对局 | 复盘员 | 结果 | 分型 | 时间线 | 转折点 | 阵亡 | 决策（错/对/不清） | 新模式 | 未解 | 清单未过 |",
           "| :-- | :-: | :-: | :-- | --: | --: | --: | :-- | --: | --: | :-- |"]
    for r in rows:
        d, s = r["doc"], r["stats"]
        v = s.get("verdicts", {})
        out.append("| {m} | {a} | {res} | {arch} | {tl} | {tp} | {de} | {dc}（{e}/{g}/{u}） | {np} | {un} | {f} |".format(
            m=d.get("matchId") or r["file"], a=r["agent"],
            res=(d.get("outcome") or {}).get("result", "?"), arch=d.get("lossArchetype", "?"),
            tl=s.get("timeline", 0), tp=s.get("turningPoints", 0), de=s.get("deaths", 0),
            dc=s.get("decisions", 0), e=v.get("error", 0), g=v.get("good", 0), u=v.get("unclear", 0),
            np=s.get("newPatterns", 0), un=s.get("unknowns", 0),
            f="；".join(r["fails"]) if r["fails"] else "全过"))
    hints = [(r["agent"], r["file"], h) for r in rows for h in r["stats"].get("proposalHints", [])]
    if hints:
        out += ["", "## 疑似参数改动建议（关键词命中，需人工看）", ""]
        out += [f"- {a} {f}：…{h}…" for a, f, h in hints]

    by_match = defaultdict(list)
    for e in index:
        by_match[e["matchId"]].append(e)
    doubles = {m: es for m, es in by_match.items() if len(es) > 1}
    if doubles:
        out += ["", "## 双审对局", "", "| 对局 | 复盘员 | 分型 | 最大转折点窗口 |", "| :-- | :-- | :-- | :-- |"]
        for m, es in doubles.items():
            for e in es:
                tps = e["turningPoints"]
                big = max(tps, key=lambda t: abs((t.get("shareBefore") or 0) - (t.get("shareAfter") or 0))) if tps else None
                win = f"{big.get('t0')}~{big.get('t1')}" if big else "—"
                out.append(f"| {m} | {e['reviewer']} | {e['archetype']} | {win} |")

    pc = Counter()
    for e in index:
        for d in e["decisions"]:
            pc[(d.get("patternId") or "?", d.get("verdict") or "?")] += 1
    if pc:
        out += ["", "## 模式编号出现次数（复盘员手工标注，不是全量计数）", "", "| 模式 | 错 | 对 | 不清 |", "| :-- | --: | --: | --: |"]
        for pid in sorted({k[0] for k in pc}):
            out.append(f"| {pid} | {pc.get((pid, 'error'), 0)} | {pc.get((pid, 'good'), 0)} | {pc.get((pid, 'unclear'), 0)} |")

    with open(f"{ROOT}/board/REVIEWS.md", "w") as f:
        f.write("\n".join(out) + "\n")
    with open(f"{ROOT}/ledger/reviews-index.json", "w") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    with open(f"{ROOT}/ledger/new-patterns.json", "w") as f:
        json.dump(new_patterns, f, ensure_ascii=False, indent=1)
    print(f"COLLECT: OK {len(rows)} 份复盘，{sum(1 for r in rows if not r['fails'])} 份清单全过，"
          f"{len(new_patterns)} 条新模式提案")
    for r in rows:
        if r["fails"]:
            print(f"  {r['agent']} {r['file']}: " + "；".join(r["fails"][:6]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
