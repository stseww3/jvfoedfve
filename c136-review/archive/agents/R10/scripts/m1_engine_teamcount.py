#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
m1_engine_teamcount.py — 从游戏客户端代码里把「队伍数怎么定、谁在哪个队」的几段原文按锚点抽出来。（R10，M1）

只抽和组队规则有关的片段（策略 / 评估层），不碰连接、验证、代理相关的代码。
输入：c99 分支 tsb/squad/live_game_js.js（压缩代码，整个文件没几行，所以用字符偏移定位）
      c99 分支 tsb/squad/page.js（结算记录的生成逻辑）
输出：out/m1/engine-teamcount.txt（每段：锚点、字符偏移、原文）

取数：
  bash c136-review/tools/bus-get.sh cursor/team-squad-c99-67fd tsb/squad /tmp/c136-r10/c99-squad
  （本脚本写成时该分支提交号 e923d6db7515）

用法：python3 m1_engine_teamcount.py [c99-squad 目录] [out 目录]
"""

from __future__ import annotations

import hashlib
import os
import sys

# (名字, 起始锚点, 结束锚点, 说明)。结束锚点取起始锚点之后第一次出现的位置；片段含结束锚点。
SNIPPETS = [
    ("A. 大厅模式 → 名义队伍数",
     "if(aFy.vz<7){fc.gameMode=1;fc.numberTeams=aFy.vz+2}",
     "fc.numberTeams=2}",
     "vz 是大厅给的模式号；vz<7 是组队局，名义队伍数 = vz + 2（2~8 队）。"
     "小队日志里 [HL-GAME-INIT] mode=<vz>（headless-bot.mjs：modeVal = tN.vz ?? tN.aFp）。"),
    ("B. 开局时的模式变量",
     "this.lC=this.data.gameMode===0?",
     "this.a0L=this.data.numberTeams;",
     "lC = numberTeams − 2；iT（是否组队局）= lC<7 或 lC==9；a0L = 队伍数（后面会被改）。"),
    ("C. 分队入口",
     "this.dk=function(){this.fX.fill(0);this.aDn.fill(0);",
     "aef();aeg()};",
     "fX[玩家] = 队伍槽位，0 表示不属于任何队。多人组队局走 this.ee()。"),
    ("D. 多人组队局的分队主流程",
     "this.ee=function(){var a2F=new Uint8Array(aE.ku);",
     "this.aem()};",
     "依次：按颜色算每个真人的第一、第二志愿队 → 按人气给颜色排序 → 战队整体入队（含队伍数下调）→ 散人入队 → 内置 AI 的处理。"),
    ("E. 战队整体入队 + 队伍数下调（关键）",
     "this.aek=function(aei,a2F,a2G){",
     "aet[fc]=true}};",
     "按名字里的 [标签] 把真人归成战队；aeu = 最大战队人数。"
     "while(a0L>2 && aeu > floor(真人数/a0L)) { a0L--; lC-- }：最大战队装不进一个队，就减少队伍数，最少 2 队。"
     "之后每个战队（从大到小）整体放进同一个队：选战队成员颜色志愿得分最高的队，但跳过「人数已经严格多于其他所有队」的那个队。"),
    ("F. 散人入队（每队人数上限 = ceil(真人数/队伍数)）",
     "this.ael=function(a2F,a2G,aei){",
     "this.fX[aC]=ft}}}};",
     "border = floor(H/T)，有余数再加 1。先按第一志愿、再按第二志愿、最后从最后一个队往前补满。"),
    ("G. 内置 AI 的归属",
     "this.aem=function(){",
     "this.fX[aC]=1+aC%aE.a0L}};",
     "队伍数 < 8：内置 AI 不入队（fX 保持 0），a0L 加 1；队伍数 = 8：内置 AI 轮流分进 8 个队。"),
    ("H. 敌我判定",
     "this.fS=function(player,k3){",
     "};",
     "fS(a,b) 为真 = a 可以打 b：a 不属于任何队（fX==0），或两人队伍不同。所以没入队的内置 AI 和所有人为敌，彼此之间也为敌。"),
    ("I. 战队标签的解析",
     "this.a3r=function(username){",
     "return null};",
     "名字里第一个 '[' 到第一个 ']' 之间的 1~7 个字符，转大写去空格。没有就是散人。"),
    ("J. 整数除法",
     "this.g0=function(fs,ft){",
     "};",
     "g0(a,b) = floor((a+0.5)/b)，即整除。"),
]

PAGE_SNIPPETS = [
    ("P1. 结算记录里的 team 字段",
     "  function teams(d, g) {",
     "  function meta(d, g) {",
     "totals 只统计领土>0 的玩家，按 fX 分组求和（键 \"0\" = 不属于任何队的玩家，即内置 AI）；best = 领土最大的组；mine = 我的队伍槽位。"),
    ("P2. 结算记录的生成（每个号每局只报一次）",
     "  function report(r, event, why) {",
     "    post({",
     "died → 一律 lost（不管本队后来赢没赢）；end → 终局时本队领土最大记 won，否则活着记 over、死了记 lost；left → 不带 team。"),
    ("P3. 什么时候报",
     "  function track(info) {",
     "  function frame(info) {",
     "活过又死了且对局仍在进行 → died；对局结束（gameState==2）→ end；还没报就离开了对局 → left。"),
]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract(text: str, start: str, end: str) -> tuple[int, int, str] | None:
    i = text.find(start)
    if i < 0:
        return None
    j = text.find(end, i + len(start))
    if j < 0:
        return None
    return i, j + len(end), text[i:j + len(end)]


def main(argv: list[str]) -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    src_dir = argv[1] if len(argv) > 1 else "/tmp/c136-r10/c99-squad"
    out_dir = argv[2] if len(argv) > 2 else os.path.join(here, "..", "out", "m1")
    os.makedirs(out_dir, exist_ok=True)
    out = []
    missing = 0
    for fname, snippets in (("live_game_js.js", SNIPPETS), ("page.js", PAGE_SNIPPETS)):
        path = os.path.join(src_dir, fname)
        text = open(path, encoding="utf-8", errors="replace").read()
        out.append(f"##### tsb/squad/{fname}  sha256={sha256(path)}  chars={len(text)}")
        out.append("")
        for name, start, end, note in snippets:
            r = extract(text, start, end)
            n_occ = text.count(start)
            if r is None:
                out.append(f"=== {name}  锚点没找到：{start!r}")
                missing += 1
                continue
            i, j, snip = r
            line_no = text.count("\n", 0, i) + 1
            out.append(f"=== {name}")
            out.append(f"说明：{note}")
            out.append(f"位置：字符偏移 {i}~{j}（第 {line_no} 行）；起始锚点在文件里出现 {n_occ} 次")
            out.append(snip)
            out.append("")
    with open(os.path.join(out_dir, "engine-teamcount.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"snippets={len(SNIPPETS) + len(PAGE_SNIPPETS)} missing={missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
