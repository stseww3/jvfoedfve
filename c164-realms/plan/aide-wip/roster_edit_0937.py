p = "c164-realms/plan/ROSTER.md"
t = open(p, encoding="utf-8").read()
n = 0

def swap(old, new):
    global t, n
    assert t.count(old) == 1, (t.count(old), old[:40])
    t = t.replace(old, new)
    n += 1

swap("| s2 | c318 | node61、node100 |", "| s2 | c318 | node62、node100（node61 没了） |")
swap("| s1 | c319 | node62；真机 node12、node97、node98、node99 |", "| s1 | c319 | 真机 node12、node97、node98、node99（node62 给了 s2） |")
swap("节点号 = 聊天号 − 257**（c318 是 node61，c353 是 node96），「节点」一栏照这个填了。",
     "节点号 = 聊天号 − 257**（c321 是 node64，c353 是 node96），「节点」一栏照这个填了。两处例外（总控 11-16 09:33）：node61 总控 09:20 拨给了别的项目的人（c274，独占），**谁也不要再往 node61 投**；s2 改用 node62（独占 c318）和 node100 两台并行，s1 只用真机。")
swap("- 别的机器：s2 多一台 node100（守总装头的 checkall）；", "- 别的机器：s2 的 node100（守总装头的 checkall）；")
open(p, "w", encoding="utf-8").write(t)
print("swaps:", n)
