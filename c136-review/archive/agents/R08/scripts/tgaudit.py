#!/usr/bin/env python3
"""tgaudit.py — 模拟器这一侧「建局 / 跑局」代码的逐行对照（会审提案议题 1 的代码事实底）。

只做一件事：把提案里引用到的代码行找出来、带行号原样打印，免得行号和写法靠手抄。不执行任何被审的代码。
只读 /agent/repos/c136-data/src/sim/ 和 src/strategy/ 下的 c110 / c116 两个策略文件（不读 src/v28、src/stats）。

    python3 tgaudit.py [--quiet]      → out/_cross/tgaudit.txt

节：
  [TG-A] tools/c117/teamgate.mjs：默认参数、建局、出生、主循环、判胜、检查点。
  [TG-B] teamgate.mjs 里有没有这些东西（名字、离开、指令通道、延迟、限流）：按关键词数出现次数。
  [TG-C] sim/clone.js：克隆出来的对象是什么类、不认识的字段怎么办。
  [TG-D] sim/game.js：isBot / leave / 难度表 / 四分之一线；策略文件里只在线上才走的分支（g.online、typeof window）各有几处。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out", "_cross")
SRC = "/agent/repos/c136-data/src"

lines_out = []


def P(s=""):
    lines_out.append(s)


def load(rel):
    L = open(os.path.join(SRC, rel), encoding="utf-8").read().split("\n")
    return L[:-1] if L and L[-1] == "" else L


def show(rel, L, pats, width=230):
    """pats: [(说明, 正则, 最多几处)]；每处打印 行号 + 原文。"""
    for label, pat, limit in pats:
        hits = [(i, ln) for i, ln in enumerate(L, 1) if re.search(pat, ln)]
        if not hits:
            P(f"  {label}：没找到（/{pat}/）")
            continue
        P(f"  {label}：{len(hits)} 处" + ("" if len(hits) <= limit else f"（只列前 {limit} 处）"))
        for i, ln in hits[:limit]:
            P(f"    L{i}: {ln.strip()[:width]}")


def count(L, pat):
    return sum(len(re.findall(pat, ln)) for ln in L)


def main():
    quiet = "--quiet" in sys.argv
    tg = load("sim/tools/c117/teamgate.mjs")
    P(f"tgaudit.py — 模拟器建局 / 跑局代码逐行对照（teamgate.mjs {len(tg)} 行）")
    P()
    P("[TG-A] sim/tools/c117/teamgate.mjs")
    show("teamgate", tg, [
        ("策略装载入口（数据镜像里没有这个文件，所以 teamgate 在镜像里跑不起来）", r"strategy/run\.js", 2),
        ("文件头：内置 AI 怎么入队", r"round robin", 2),
        ("文件头：window 对象", r"bare `window`|guarded browser hooks", 3),
        ("判胜份额", r"WIN_SHARE\s*=", 1),
        ("检查点", r"CHECKPOINTS\s*=", 1),
        ("装策略时的 window", r"globalThis\.window", 2),
        ("编队策略的参数", r"spawnRoll: 0, planEvery: 0", 3),
        ("真人数 / 分队", r"const humans = |teams\[h\] = ", 3),
        ("建局（用的是哪个类、传了什么）", r"new Game\(", 2),
        ("对手的策略", r"job\.others\[", 2),
        ("出生：每个席位调几次", r"chooseSpawn\(|endSpawnPhase", 6),
        ("主循环：每拍谁出手", r"\.act\(g\)|g\.tick\(\)", 6),
        ("判胜", r"WIN_SHARE|winnerTeam", 6),
    ])
    P("  默认参数（命令行没给时的取值）：")
    for i, ln in enumerate(tg, 1):
        if re.search(r"\+?opt\('(squad-policy|squad-size|teams|per|others|diff|maps|seeds|ticks)',", ln):
            P(f"    L{i}: {ln.strip()[:230]}")
    P()
    P("[TG-B] teamgate.mjs 里各关键词出现的次数（0 = 这件事在 teamgate 里不存在）")
    for label, pat in [("g.names / names:（席位名字）", r"g\.names|\bnames\s*:"), ("leave（离开 / 空壳）", r"\bleave\b|\.leave\("), ("delay / lag / latency（指令时延）", r"delay|\blag\b|latency"),
                       ("queue / pending（在途指令）", r"queue|pending"), ("% 7（回合格点）", r"%\s*7\b"), ("rate limit / per turn（每回合限流）", r"rate.?limit|per.?turn|\blimit\b"),
                       ("online（线上分支开关）", r"\bonline\b"), ("clone（断面克隆）", r"\bclone\b"), ("difficulty / diff", r"difficulty|\bdiff\b"),
                       ("setupColors / assignTeams / botsTeamed（组队配色、减队、AI 入不入队）", r"setupColors|assignTeams|botsTeamed")]:
        P(f"  {label}：{count(tg, pat)}")
    P()
    cl = load("sim/sim/clone.js")
    P(f"[TG-C] sim/sim/clone.js（{len(cl)} 行）")
    show("clone", cl, [
        ("克隆出来的对象的原型", r"Object\.create\(", 2),
        ("不认识的字段", r"unhandled field", 2),
        ("共享不拷的字段表", r"const SHARED", 1),
    ])
    P()
    gm = load("sim/sim/game.js")
    P(f"[TG-D] sim/sim/game.js（{len(gm)} 行）和策略文件")
    show("game", gm, [
        ("基类缺省的内置 AI 难度", r"this\.difficulty = opts\.difficulty", 1),
        ("基类的分队：内置 AI 入不入队", r"index as the live game does|opts\.botTeams !== false", 3),
        ("isBot：离开的真人算不算 AI", r"return p >= this\.humans \|\| this\.state\[p\] === 2", 2),
        ("leave：离开以后", r"this\.runAsBot\(p\)", 2),
        ("四分之一线", r"if \(bx <= iV\(jP, 4\)\) this\.collapse\(p\)", 1),
        ("峰值怎么降", r"this\.peak\[p\] = jP - Math\.max", 1),
        ("出局清零", r"^\s*this\.bal\[p\] = 0;", 4),
    ])
    P(f"  game.js 里 names 出现 {count(gm, r'names')} 处（基类不存席位名字；策略读到的 g.names 是 undefined）")
    for tag, rel in (("c110", "strategy/v27-team-c110.js"), ("c116", "strategy/v27-team-c116.js")):
        S = load(rel)
        P(f"  {tag}（{len(S)} 行）：g.online 出现 {count(S, r'g\.online')} 处，typeof window 出现 {count(S, r'typeof window')} 处，window.__ 开头的钩子名 {len(set(re.findall(r'window\.(__\w+)', chr(10).join(S))))} 个；"
          f"isBot 的定义 {sum(1 for ln in S if re.search(r'isBot\s*[:(].*=>|^\s*isBot\(', ln))} 处")
        show(tag, S, [
            ("策略文件里唯一的 isBot 定义（出生期用的局面副本；线上那一层给策略的 g.isBot 不在这个文件里）", r"isBot: \(o\) => o >= g\.humans", 2),
            ("按名字认编队友", r"SQUAD_POOL_SET\.has\(raw\.toLowerCase\(\)\)", 2),
            ("保护开关", r"g\.terr\[p\] >= 80 && !g\.isBot\(p\) && !this\.isOurSquadBot", 2),
            ("出生槽位", r"__tsbSquadSlot", 3),
        ])
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "tgaudit.txt"), "w", encoding="utf-8").write("\n".join(lines_out) + "\n")
    if not quiet:
        print("\n".join(lines_out))


if __name__ == "__main__":
    main()
