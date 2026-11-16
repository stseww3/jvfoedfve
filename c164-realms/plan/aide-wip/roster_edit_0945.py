p = "c164-realms/plan/ROSTER.md"
t = open(p, encoding="utf-8").read()
n = 0

def swap(old, new):
    global t, n
    assert t.count(old) == 1, (t.count(old), old[:40])
    t = t.replace(old, new)
    n += 1

swap("| cable（c338）的 `machines/cablecar-winch` | m3（09:22 起） |\n",
     "| cable（c338）的 `machines/cablecar-winch`（09:38 进了总装） | m3（09:22 到 09:41：下平台东沿漏口的量，明细在 `cursor/c164-m3-cablehelp-f3-8e52-wip`） |\n"
     "| sdome（c328）的 `interiors/astroroom`（四间新房里只有它没有搭档） | rec（09:34 起；他的 `machines/recorders` 09:33 进了总装） |\n"
     "| a4（c323）：室内走查、每版候选重走、site 清单上他自己的三处 | m3（09:43 起；重走的量或者栏杆墩，a4 挑） |\n")
open(p, "w", encoding="utf-8").write(t)
print("swaps:", n)
