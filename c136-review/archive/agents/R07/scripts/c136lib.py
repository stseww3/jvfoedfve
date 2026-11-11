#!/usr/bin/env python3
"""c136lib.py — R07 复盘脚本的公共解析库（只用标准库）。

输入约定：
  slice 文件由 10_slice_game.py 生成，每行 "<原始行号>\\t<原文>"。
  结算记录是数据 A 的 G01-G09-results.jsonl；它的第 k 条与整份日志里第 k 条 [RESULT …] 行一一对应
  （match_results() 里逐条核对 bot / place / peak，不一致就报错）。

解析出的事件统一为 dict：{"line": 原始行号, "bot": 号名或 None, "type": 类型, "t": 拍或 None, ...字段}
类型：INIT / COORD / SPAWN / OPENING / OPENCHECK / TICK / SLOW / DONATE / ASSIST / INTERCEPT / RESULT / ERROR / HOTIMPORT / OTHER

HL-TICK 字段的来历（v27-team-live.js@917e6b1 第 5285 / 5329 行，Policy.act）：
  terr  = g.terr[me]                 本号领土像素数
  pct   = 100*terr/g.land            占全图陆地的百分比（保留 1 位小数）
  bal   = g.bal[me]                  本号在家兵力（不含在途进攻、船上的兵）
  dens  = bal/terr                   密度
  nb    = this.nb.length             与本号陆地接壤的「非队友」玩家数（含内置 AI 和敌方真人；Strategy.analyze 第 373~401 行）
  neut  = this.neutral               与本号边界相邻的无主陆地像素数（同上）
  cmds  = this.cmds                  本策略实例累计发出的指令数（实例重建会清零）
  boats = this.boats                 本策略实例累计发船数
  avgMs/maxMs/skip                   headless-bot.mjs 的 __hlPerf：每拍平均耗时、最大耗时、累计跳过的拍数
  打印条件：t>=600 且 t%90==0（t<1500 时还要 t%2==0；t>=1500 时每 period=2 拍进一次），所以第一条在 t=630。
"""
import json
import re

BOT_PREFIX = re.compile(r"^\[\[Nope\] ([A-Za-z0-9_]+)\] ?(.*)$", re.S)

RE_INIT = re.compile(r"^\[HL-GAME-INIT\] mode=(-?\d+) map=(-?\d+) mapSeed=(-?\d+) players=(\d+) me=(\d+)")
RE_COORD = re.compile(r"^\[BACKEND-SPAWN-COORD\] Solved (\d+) bots in ([\d.]+)ms \(map=(\d+)x(\d+), minSep=(\d+)px, boss=([^)]*)\): (.*)$")
RE_COORD_ITEM = re.compile(r"\[Nope\] ([A-Za-z0-9_]+)\(([A-Z_]+)\)->\((-?\d+),(-?\d+)\)")
RE_SPAWN = re.compile(r"^\[HL-SPAWN-BACKEND\] me=(\d+) slot=(\d+) role=([A-Z_]+) -> \((-?\d+),(-?\d+)\) bossDist=(-?\d+) minAllyDist=(-?\d+) voronoi=(-?\d+)")
RE_OPENING = re.compile(r"^\[HL-OPENING\] t=(\d+) cyc=(\d+) DP expand rings=(\d+) spend=(\d+)/(\d+) terr=(\d+)")
RE_OPENCHECK = re.compile(r"^\[OPENING-CHECK (\d+) bots @ tick (\d+)\] (.*)$")
RE_OPENCHECK_ITEM = re.compile(r"\[Nope\] ([A-Za-z0-9_]+):tick=(\d+),terr=(\d+),sent=(\d+)\(([A-Z_a-z]+)\)")
RE_TICK = re.compile(r"^\[HL-TICK\] t=(\d+) terr=(\d+)\(([\d.]+)%\) bal=(-?\d+) dens=([\d.]+) nb=(\d+) neut=(\d+) cmds=(\d+) boats=(\d+)"
                     r"(?: avgMs=([\d.]+) maxMs=([\d.]+) skip=(\d+))?")
RE_SLOW = re.compile(r"^\[HL-SLOW-TICK\] t=(\d+) took ([\d.]+)ms \(max=([\d.]+)ms\)")
RE_DONATE = re.compile(r"^\[HL-DONATE\] t=(\d+) (surplus|squad rescue|boss|emergency boss) donate pct=(\d+)/1024 \(~5%\) -> (?:ally|boss)=(\d+)\((.*?)\)"
                       r"(?: boxedIn=(true|false))? myBal=(-?\d+) dMe=(-?\d+)(?: dAlly=(-?\d+))?(?: dBoss=(-?\d+))?")
RE_ASSIST = re.compile(r"^\[HL-ASSIST\] t=(\d+) 10% squad-rescue poke -> enemy=(\d+)\((.*)\) for ally=(\d+)\((.*?)\)$")
RE_ASSIST_BOSS = re.compile(r"^\[HL-ASSIST\] t=(\d+) 10% boss-assist poke -> target=(\d+)\((.*)\) myBal=(-?\d+) dMe=(-?\d+)")
RE_INTERCEPT = re.compile(r"^\[HL-INTERCEPT\] t=(\d+) unified sea intercept pct=(\d+)/1024 -> boatId=(\d+) owner=(\d+)\((.*)\) boatTroops=(\d+)")
RE_RESULT = re.compile(r"^\[RESULT \[Nope\] ([A-Za-z0-9_]+)\] result=(\w+) event=(\w+) place=(\d+) peak=(\d+) team=(.*)$")
RE_HOT = re.compile(r"^\[HOT-IMPORT\] Injected updated (\S+) \((\d+) bytes\) into \[Nope\] ([A-Za-z0-9_]+) live!")


def parse_line(orig_line, text):
    m = BOT_PREFIX.match(text)
    bot = m.group(1) if m else None
    body = m.group(2) if m else text
    ev = {"line": orig_line, "bot": bot, "type": "OTHER", "t": None, "raw": text}
    mm = RE_TICK.match(body)
    if mm:
        ev.update(type="TICK", t=int(mm.group(1)), terr=int(mm.group(2)), pct=float(mm.group(3)), bal=int(mm.group(4)),
                  dens=float(mm.group(5)), nb=int(mm.group(6)), neut=int(mm.group(7)), cmds=int(mm.group(8)),
                  boats=int(mm.group(9)),
                  avgMs=float(mm.group(10)) if mm.group(10) else None,
                  maxMs=float(mm.group(11)) if mm.group(11) else None,
                  skip=int(mm.group(12)) if mm.group(12) else None)
        return ev
    mm = RE_SPAWN.match(body)
    if mm:
        ev.update(type="SPAWN", me=int(mm.group(1)), slot=int(mm.group(2)), role=mm.group(3), x=int(mm.group(4)),
                  y=int(mm.group(5)), bossDist=int(mm.group(6)), minAllyDist=int(mm.group(7)), voronoi=int(mm.group(8)))
        return ev
    mm = RE_OPENING.match(body)
    if mm:
        ev.update(type="OPENING", t=int(mm.group(1)), cyc=int(mm.group(2)), rings=int(mm.group(3)), spend=int(mm.group(4)),
                  bal=int(mm.group(5)), terr=int(mm.group(6)))
        return ev
    mm = RE_DONATE.match(body)
    if mm:
        ev.update(type="DONATE", t=int(mm.group(1)), kind=mm.group(2), pct=int(mm.group(3)), to=int(mm.group(4)),
                  toName=mm.group(5), boxedIn=(None if mm.group(6) is None else mm.group(6) == "true"),
                  myBal=int(mm.group(7)), dMe=int(mm.group(8)),
                  dAlly=int(mm.group(9)) if mm.group(9) else None,
                  dBoss=int(mm.group(10)) if mm.group(10) else None)
        return ev
    mm = RE_ASSIST.match(body)
    if mm:
        ev.update(type="ASSIST", t=int(mm.group(1)), kind="squad-rescue", enemy=int(mm.group(2)), enemyName=mm.group(3),
                  ally=int(mm.group(4)), allyName=mm.group(5))
        return ev
    mm = RE_ASSIST_BOSS.match(body)
    if mm:
        ev.update(type="ASSIST", t=int(mm.group(1)), kind="boss-assist", enemy=int(mm.group(2)), enemyName=mm.group(3),
                  ally=None, allyName=None, myBal=int(mm.group(4)), dMe=int(mm.group(5)))
        return ev
    mm = RE_INTERCEPT.match(body)
    if mm:
        ev.update(type="INTERCEPT", t=int(mm.group(1)), pct=int(mm.group(2)), boatId=int(mm.group(3)), owner=int(mm.group(4)),
                  ownerName=mm.group(5), boatTroops=int(mm.group(6)))
        return ev
    mm = RE_SLOW.match(body)
    if mm:
        ev.update(type="SLOW", t=int(mm.group(1)), ms=float(mm.group(2)), maxMs=float(mm.group(3)))
        return ev
    mm = RE_INIT.match(body)
    if mm:
        ev.update(type="INIT", mode=int(mm.group(1)), map=int(mm.group(2)), mapSeed=int(mm.group(3)), humans=int(mm.group(4)),
                  me=int(mm.group(5)))
        return ev
    mm = RE_COORD.match(body)
    if mm:
        items = [{"bot": a, "role": b, "x": int(c), "y": int(d)} for a, b, c, d in RE_COORD_ITEM.findall(mm.group(7))]
        ev.update(type="COORD", n=int(mm.group(1)), ms=float(mm.group(2)), W=int(mm.group(3)), H=int(mm.group(4)),
                  minSep=int(mm.group(5)), boss=mm.group(6), items=items)
        return ev
    mm = RE_OPENCHECK.match(body)
    if mm:
        items = [{"bot": a, "tick": int(b), "terr": int(c), "sent": int(d), "status": e}
                 for a, b, c, d, e in RE_OPENCHECK_ITEM.findall(mm.group(3))]
        ev.update(type="OPENCHECK", n=int(mm.group(1)), t=int(mm.group(2)), items=items)
        return ev
    mm = RE_RESULT.match(body)
    if mm:
        team = None if mm.group(6).strip() == "null" else json.loads(mm.group(6))
        ev.update(type="RESULT", bot=mm.group(1), result=mm.group(2), event=mm.group(3), place=int(mm.group(4)),
                  peak=int(mm.group(5)), team=team)
        return ev
    mm = RE_HOT.match(body)
    if mm:
        ev.update(type="HOTIMPORT", file=mm.group(1), size=int(mm.group(2)), bot=mm.group(3))
        return ev
    if body.startswith("ERROR: Strategy"):
        ev.update(type="ERROR", msg=body)
        return ev
    return ev


def load_slice(path):
    evs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            ln, _, text = line.partition("\t")
            evs.append(parse_line(int(ln), text))
    return evs


def load_results(raw_dir):
    recs = []
    with open(f"{raw_dir}/G01-G09-results.jsonl", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if line:
                r = json.loads(line)
                r["_line"] = i
                recs.append(r)
    return recs


def all_result_lines(raw_dir):
    """整份日志里全部 [RESULT …] 行（按出现顺序），返回 [(原始行号, event dict)]。"""
    out = []
    with open(f"{raw_dir}/G01-G09-squad.log", encoding="utf-8", errors="replace") as f:
        for ln, line in enumerate(f, 1):
            if line.startswith("[RESULT "):
                out.append((ln, parse_line(ln, line.rstrip("\n"))))
    return out


def match_results(raw_dir, first_line, last_line):
    """返回切片 [first_line, last_line] 内每条 [RESULT] 行对应的 results.jsonl 记录（逐条核对后）。"""
    recs = load_results(raw_dir)
    rl = all_result_lines(raw_dir)
    if len(recs) != len(rl):
        raise SystemExit(f"results.jsonl 条数 {len(recs)} != 日志 RESULT 行数 {len(rl)}")
    out = []
    for (ln, ev), rec in zip(rl, recs):
        short = rec["bot"].replace("[Nope] ", "")
        if short != ev["bot"] or rec.get("place") != ev["place"] or rec.get("peak") != ev["peak"]:
            raise SystemExit(f"第 {rec['_line']} 条结算与日志第 {ln} 行对不上：{short}/{ev['bot']}")
        if first_line <= ln <= last_line:
            rec = dict(rec)
            rec["_logLine"] = ln
            rec["_bot"] = short
            out.append(rec)
    return out


BOTS = ["mark07", "kevin_k", "ethan21", "lucas94", "dave_w", "ryan_m", "noah88", "leo_tx"]
