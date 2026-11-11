#!/usr/bin/env python3
"""dossier.py <matchId> [--map T[,T2..]] [--tl T[,T2..]] [--full] — 一局的「卷宗」。
（--tl：给 facts.json 的 timeline 额外加几个时间点，比如编队峰值拍；必须是 10 的倍数）

把 resim.mjs 的全量重放账本（out/cache/<mid>-resim.json，逐拍精确）和对局包（card/results/traj/
events/anomalies/in_game.log）拼成一份可读事实表，写到 out/dossier/<mid>.txt 并打印。
复盘里引用的数字都出自这里；每一节的口径写在节标题后面。

先跑：bash c136-review/tools/run-heavy.sh node resim.mjs <mid> --quiet --maps 630,1530,...
"""
import bisect
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c136lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "out", "cache")
OUTDIR = os.path.join(HERE, "..", "out", "dossier")
NEUTRAL = 512


def version_of(mid):
    if mid[0] == "B":
        return "c110"
    if mid[0] == "G":
        return "g09"
    n = int(mid[1:])
    return "Va" if n <= 17 else ("Vb" if n <= 95 else "Vc")


def k(x):
    x = float(x)
    a = abs(x)
    if a >= 1e6:
        return f"{x / 1e6:.2f}M"
    if a >= 1e4:
        return f"{x / 1e3:.0f}k"
    if a >= 1e3:
        return f"{x / 1e3:.1f}k"
    return f"{x:.0f}"


class Dossier:
    def __init__(self, mid):
        self.mid = mid
        self.R = R = json.load(open(os.path.join(CACHE, f"{mid}-resim.json")))
        self.H = R["H"]
        self.land = R["land"]
        self.T = R["snapT"]
        self.card = L.load_card(mid)
        self.results = L.load_results(mid)
        self.traj = L.load_traj(mid)
        self.sq = {b: s["id"] for b, s in R["squad"].items() if s["id"] >= 0 and not s.get("mismatch")}
        self.foreign = [b for b, s in R["squad"].items() if s["id"] < 0 or s.get("mismatch")]
        self.bot_of = {p: b for b, p in self.sq.items()}
        self.sqids = sorted(self.bot_of)
        self.my_team = R["teams"][self.sqids[0]] if self.sqids else 0
        self.team_game = R["nTeams"] > 0
        self.left = R["leftT"]
        self.death = R["deathT"]
        self.out = []
        # 指令按玩家分组
        self.cmds = defaultdict(list)
        for c in R["cmdLog"]:
            self.cmds[c[1]].append(c)
        self.don_in = defaultdict(list)  # 受捐方 -> [(t, 捐方, 到账)]
        for c in R["cmdLog"]:
            if c[2] == 2 and c[5]:
                self.don_in[min(c[4], NEUTRAL)].append((c[0], c[1], c[6]))
        self.land_in = defaultdict(list)  # 船靠岸给到队友 / 回到自己
        for t, p, target, troops, got, q0, cap in R["landings"]:
            self.land_in[target].append((t, p, troops, got))
        self.pair_att = defaultdict(list)
        self.pair_def = defaultdict(list)
        for row in R["pairLog"]:
            self.pair_att[row[1]].append(row)
            self.pair_def[row[2]].append(row)
        self.exit = {}
        for r in self.results:
            b = r["bot"]
            if b in self.sq:
                self.exit[b] = r

    # ---------- 基础 ----------
    def p(self, s=""):
        self.out.append(s)

    def ix(self, t):
        i = bisect.bisect_right(self.T, t) - 1
        return max(i, 0)

    def terr(self, pl, t):
        return self.R["snapTerr"][self.ix(t)][pl]

    def bal(self, pl, t):
        return self.R["snapBal"][self.ix(t)][pl]

    def nm(self, q, t=None):
        if q >= NEUTRAL:
            return "中立"
        if q in self.bot_of:
            return self.bot_of[q]
        if q >= self.H:
            return f"AI{q}"
        raw = re.sub(r"\s+", " ", str(self.R["names"][q])).strip()
        raw = raw[:12]
        tag = f"T{self.R['teams'][q]}" if self.team_game else ""
        gone = "*" if (t is not None and 0 <= self.left[q] <= t) else ""
        return f"{raw}#{q}{tag}{gone}"

    def cls(self, q, t):
        if q >= NEUTRAL:
            return "N"
        if q >= self.H:
            return "AI"
        if 0 <= self.left[q] <= t:
            return "AI"  # 离线真人由内置 AI 接管
        return "H"

    def alive_until(self, pl):
        d = self.death[pl]
        return d if d >= 0 else self.R["endTick"]

    # ---------- 区间账 ----------
    def ledger(self, pl, a, b):
        """[a, b) 内 pl 的全部出入账（重放精确值）。"""
        ia, ib = self.ix(a), self.ix(b)
        R = self.R
        d = {
            "terr0": R["snapTerr"][ia][pl], "terr1": R["snapTerr"][ib][pl],
            "bal0": R["snapBal"][ia][pl], "bal1": R["snapBal"][ib][pl],
            "inc": R["snapInc"][ib][pl] - R["snapInc"][ia][pl],
            "ret": R["snapRet"][ib][pl] - R["snapRet"][ia][pl],
            "out0": R["snapOut"][ia][pl], "out1": R["snapOut"][ib][pl],
        }
        ta, tb = self.T[ia], self.T[ib]
        sent = defaultdict(lambda: [0, 0, 0])  # 类 -> [兵, 费, 条数]
        tgt_h = Counter()
        noop = 0
        don_out = [0, 0, 0]
        don_to = Counter()
        boat = [0, 0, 0]
        retreat = 0
        for c in self.cmds.get(pl, ()):
            t = c[0]
            if t < ta or t >= tb:
                continue
            if c[2] == 1:
                if not c[5]:
                    noop += 1
                    continue
                q = min(c[4], NEUTRAL)
                cl = self.cls(q, t)
                s = sent[cl]
                s[0] += c[6]; s[1] += c[7]; s[2] += 1
                if cl == "H":
                    tgt_h[q] += c[6]
            elif c[2] == 2 and c[5]:
                don_out[0] += c[6]; don_out[1] += c[7]; don_out[2] += 1
                don_to[min(c[4], NEUTRAL)] += c[6]
            elif c[2] == 3 and c[5]:
                boat[0] += c[6]; boat[1] += c[7]; boat[2] += 1
            elif c[2] == 5 and c[5]:
                retreat += c[6]
        d.update(sent=sent, tgt_h=tgt_h, noop=noop, don_out=don_out, don_to=don_to, boat=boat, retreat=retreat)
        gain = defaultdict(lambda: [0, 0])  # 类 -> [得地, 烧兵]
        gain_h = defaultdict(lambda: [0, 0, 0])  # 对手 -> [得地, 烧兵, 对方掉余额]
        for t, att, de, tiles, burnt, dB, dS, n in self.pair_att.get(pl, ()):
            if t <= ta or t > tb:
                continue
            cl = self.cls(de, t)
            gain[cl][0] += tiles; gain[cl][1] += burnt
            if cl == "H":
                g = gain_h[de]
                g[0] += tiles; g[1] += burnt; g[2] += dB
        lost = defaultdict(lambda: [0, 0, 0, 0])  # 攻方 -> [失地, 掉余额, 掉反击槽, 攻方烧兵]
        for t, att, de, tiles, burnt, dB, dS, n in self.pair_def.get(pl, ()):
            if t <= ta or t > tb:
                continue
            x = lost[att]
            x[0] += tiles; x[1] += dB; x[2] += dS; x[3] += burnt
        d.update(gain=gain, gain_h=gain_h, lost=lost)
        din = sum(g for (t, p, g) in self.don_in.get(pl, ()) if ta <= t < tb)
        lin = sum(g for (t, p, tr, g) in self.land_in.get(pl, ()) if ta <= t < tb and p != pl)
        lown = sum(tr for (t, p, tr, g) in self.land_in.get(pl, ()) if ta <= t < tb and p == pl)
        d.update(don_in=din, boat_in=lin, boat_back=lown)
        spent = sum(s[0] + s[1] for s in sent.values()) + don_out[0] + don_out[1] + boat[0] + boat[1]
        def_bal = sum(x[1] for x in lost.values())
        d["def_bal"] = def_bal
        d["spent"] = spent
        d["resid"] = (d["bal1"] - d["bal0"]) - (d["inc"] + d["ret"] + retreat + din + lin + lown - spent - def_bal)
        return d

    def fmt_ledger(self, pl, a, b, d=None):
        d = d or self.ledger(pl, a, b)
        seg = [f"{a:>5}-{b:<5} 地 {d['terr0']:>6}→{d['terr1']:<6} 兵 {k(d['bal0']):>6}→{k(d['bal1']):<6} 密 {d['bal1'] / max(1, d['terr1']):5.1f}", f"息+{k(d['inc'])}"]
        for cl, lab in (("N", "中立"), ("AI", "AI"), ("H", "真人")):
            s = d["sent"].get(cl)
            g = d["gain"].get(cl, [0, 0])
            if s or g[0] or g[1]:
                s = s or [0, 0, 0]
                txt = f"攻{lab} {s[2]}令 出{k(s[0])} 费{k(s[1])} 烧{k(g[1])} 得地{g[0]}"
                if cl == "H":
                    txt += " [" + " ".join(f"{self.nm(q, a)}:{k(v[1])}/{v[0]}格" for q, v in sorted(d["gain_h"].items(), key=lambda x: -x[1][1])[:3]) + "]"
                seg.append(txt)
        if d["lost"]:
            tl = sum(x[0] for x in d["lost"].values())
            bl = sum(x[1] for x in d["lost"].values())
            sl = sum(x[2] for x in d["lost"].values())
            top = sorted(d["lost"].items(), key=lambda x: -(x[1][0] * 2 + x[1][1]))[:3]
            if tl or bl or sl:
                seg.append(f"挨打 失地{tl} 掉兵{k(bl)}" + (f" 反击槽-{k(sl)}" if sl else "") + " [" + " ".join(f"{self.nm(q, a)}:{x[0]}格/{k(x[1])}" for q, x in top) + "]")
        if d["don_out"][2]:
            seg.append(f"捐出 {d['don_out'][2]}笔 {k(d['don_out'][0])} 税{k(d['don_out'][1])} [" + " ".join(f"{self.nm(q)}:{k(v)}" for q, v in d["don_to"].most_common(3)) + "]")
        if d["don_in"] or d["boat_in"]:
            seg.append(f"收捐 {k(d['don_in'])}" + (f" 船移交{k(d['boat_in'])}" if d["boat_in"] else ""))
        if d["boat"][2]:
            seg.append(f"船 {d['boat'][2]}条 {k(d['boat'][0])} 费{k(d['boat'][1])}")
        if d["boat_back"]:
            seg.append(f"船回岸+{k(d['boat_back'])}")
        if d["noop"]:
            seg.append(f"空令{d['noop']}")
        if d["ret"] > 0:
            seg.append(f"退兵+{k(d['ret'])}")
        if abs(d["resid"]) > max(50, 0.002 * max(d["bal0"], d["bal1"])):
            seg.append(f"未归类{k(d['resid'])}")
        return " | ".join(seg)

    def quiet(self, d):
        return not (d["sent"] or d["lost"] or d["don_out"][2] or d["don_in"] or d["boat"][2] or d["noop"] or d["boat_in"] or any(v[0] or v[1] for v in d["gain"].values()))

    # ---------- 各节 ----------
    def sec_header(self):
        R, c = self.R, self.card
        oc = c.get("outcome", {})
        sizes = R["teamSizes"]
        self.p(f"===== {self.mid} 卷宗（重放精确值；traj 核对 {R['validate']['bothExact']}/{R['validate']['rows']} 行一致）=====")
        teams = " ".join(f"T{i}={sizes[i]}" for i in range(1, len(sizes))) if self.team_game else "自由混战（无队伍）"
        self.p(f"[A] {c.get('cohort')} 策略 {version_of(self.mid)} | 图 {c.get('mapId')} 陆地 {self.land} | 真人 {self.H} AI {R['players'] - self.H}{'（未入队，与所有人为敌）' if self.team_game and not R['botsTeamed'] else ''} | 录像头队数 {R['nTeamsHeader']} → 实际 {R['nTeams']}：{teams}")
        self.p(f"    本队 T{self.my_team}，本房间 {len(self.sq)} 个号{('，不在本房间：' + ','.join(self.foreign)) if self.foreign else ''} | 结果 {oc.get('resultLabel')} 结束拍 {oc.get('endTick')} 赢家 T{oc.get('winnerTeam')} | 录像到 {R['endTick']} 拍 over={R['over']} winnerTeam={R['winnerTeam']}")
        self.p("    战队标签：" + " ".join(f"{x['tag']}×{x['size']}→T{x['team']}" for x in R["clans"]))
        peer = c.get("sameMatchPeer")
        if peer:
            self.p(f"    同局另一编队：{json.dumps(peer, ensure_ascii=False)}")
        if R["engineEvents"]:
            ev = R["engineEvents"]
            self.p("    引擎事件：" + " ".join(f"{e[0]}:{'猎杀' if e[1] == 'hunt' else '提速'}(T{e[2]})" for e in ev[:8]) + (f" …共{len(ev)}" if len(ev) > 8 else ""))

    def team_rows(self, ticks):
        R = self.R
        nT = R["nTeams"]
        rows = []
        for t in ticks:
            i = self.ix(t)
            tl = R["teamLand"][i]
            terr, bal = R["snapTerr"][i], R["snapBal"][i]
            tb = [0] * (nT + 1)
            ta = [0] * (nT + 1)
            for q in range(self.H):
                if terr[q] > 0 and not (0 <= self.left[q] <= t):
                    tb[R["teams"][q]] += bal[q]
                    ta[R["teams"][q]] += 1
            # 本队只算仍在我方控制下的号；已离线（交给内置 AI 托管）的号单列为「空壳」
            ctl = [q for q in self.sqids if not (0 <= self.left[q] <= t)]
            hsk = [q for q in self.sqids if 0 <= self.left[q] <= t and terr[q] > 0]
            sq_t = sum(terr[q] for q in ctl)
            sq_b = sum(bal[q] for q in ctl)
            sq_n = sum(1 for q in ctl if terr[q] > 0)
            husk = (len(hsk), sum(terr[q] for q in hsk), sum(bal[q] for q in hsk))
            tot = sum(tl) + R["botLand"][i]
            rows.append((self.T[i], tl, R["botLand"][i], self.land - tot, ta, tb, sq_t, sq_b, sq_n, husk))
        return rows

    def sec_teams(self, step=300):
        R = self.R
        end = R["endTick"]
        ticks = sorted(set(list(range(0, end, step)) + [90, 180, 630, 1530] + [end]))
        ticks = [t for t in ticks if t <= end]
        self.p()
        self.p("[B] 各队走势（占全图陆地 %；AI=未入队的内置 AI；真=该队还在线且有地的真人数；兵=该队在线真人余额合计）")
        nT = R["nTeams"]
        if self.team_game:
            head = "     t | " + " ".join(f"T{i}%  " for i in range(1, nT + 1)) + "| AI%  中立% | " + " ".join(f"真T{i}" for i in range(1, nT + 1)) + " | " + " ".join(f"兵T{i}   " for i in range(1, nT + 1)) + f"| 本队 号 地%   兵     密 | 空壳 号 地%   兵 | 本队路人 地%"
        else:
            head = "     t | 真人%  AI%  中立% | 在线真人 | 本队 号 地%   兵     密 | 空壳 号 地%   兵"
        self.p(head)
        for (t, tl, bl, neu, ta, tb, sq_t, sq_b, sq_n, husk) in self.team_rows(ticks):
            hs = f" | {husk[0]:>4} {100 * husk[1] / self.land:5.2f} {k(husk[2]):>6}"
            if self.team_game:
                line = f"{t:>6} | " + " ".join(f"{100 * tl[i] / self.land:5.1f}" for i in range(1, nT + 1)) + f" | {100 * bl / self.land:4.1f} {100 * neu / self.land:5.1f} | " + " ".join(f"{ta[i]:>4}" for i in range(1, nT + 1)) + " | " + " ".join(f"{k(tb[i]):>6}" for i in range(1, nT + 1)) + f" | {sq_n:>2} {100 * sq_t / self.land:5.2f} {k(sq_b):>6} {sq_b / max(1, sq_t):5.1f}" + hs + f" | {100 * (tl[self.my_team] - sq_t - husk[1]) / self.land:5.2f}"
            else:
                line = f"{t:>6} | {100 * tl[0] / self.land:5.1f} {100 * bl / self.land:5.1f} {100 * neu / self.land:5.1f} | {ta[0]:>4} | {sq_n:>2} {100 * sq_t / self.land:5.2f} {k(sq_b):>6} {sq_b / max(1, sq_t):5.1f}" + hs
            self.p(line)

    def sec_top(self, ticks):
        self.p()
        self.p("[C] 各时点地盘前 8 的真人（名#号 队 地% 兵 密；* = 已离线由 AI 接管）")
        for t in ticks:
            if t > self.R["endTick"]:
                continue
            i = self.ix(t)
            terr, bal = self.R["snapTerr"][i], self.R["snapBal"][i]
            order = sorted(range(self.H), key=lambda q: -terr[q])[:8]
            self.p(f"  t={self.T[i]}: " + "  ".join(f"{self.nm(q, t)} {100 * terr[q] / self.land:.1f}% {k(bal[q])} d{bal[q] / max(1, terr[q]):.0f}" for q in order if terr[q] > 0))

    def sec_roster(self):
        R = self.R
        self.p()
        self.p("[D] 名册与出生（出生框中心=重放里选点期结束时的实际位置；近邻距离单位像素）")
        spawn = L.load_spawn(self.mid)
        last_role = {}
        for r in spawn:
            last_role[r["bot"]] = r
        rep = L.load_replay(self.mid)
        n_spawn = Counter()
        if rep:
            for t, cid, pl, a, b in rep["cmds"]:
                if cid == 0:
                    n_spawn[pl] += 1
        cen = {}
        for q in range(self.H):
            bx = R["startBox"][q]
            if bx and bx[2] >= bx[0] and R["snapTerr"][0][q] > 0:
                cen[q] = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)
        t630 = min(630, R["endTick"])
        order630 = sorted(range(self.H), key=lambda q: -self.terr(q, t630))
        rank630 = {q: i + 1 for i, q in enumerate(order630)}
        for b, pl in sorted(self.sq.items(), key=lambda x: x[1]):
            ex = self.exit.get(b, {})
            lr = last_role.get(b, {})
            line = f"  {b:<7}#{pl:<3}"
            if pl in cen:
                cx, cy = cen[pl]
                def near(pred):
                    best = None
                    for q, (x, y) in cen.items():
                        if q == pl or not pred(q):
                            continue
                        dd = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                        if best is None or dd < best[0]:
                            best = (dd, q)
                    return best
                ally = near(lambda q: q in self.bot_of)
                foe = near(lambda q: q not in self.bot_of and (not self.team_game or R["teams"][q] != self.my_team))
                mate = near(lambda q: q not in self.bot_of and self.team_game and R["teams"][q] == self.my_team)
                foes150 = sum(1 for q, (x, y) in cen.items() if q != pl and q not in self.bot_of and (not self.team_game or R["teams"][q] != self.my_team) and ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 <= 150)
                line += f" 出生({cx:.0f},{cy:.0f}) 令{n_spawn.get(pl, 0)}条 末次指派({lr.get('x')},{lr.get('y')}){lr.get('role', '')}"
                line += f" | 最近队内号 {self.nm(ally[1])} {ally[0]:.0f}" if ally else ""
                line += f" 最近敌真人 {self.nm(foe[1])} {foe[0]:.0f}（150内{foes150}个）" if foe else ""
                line += f" 最近路人队友 {self.nm(mate[1])} {mate[0]:.0f}" if mate else ""
            else:
                line += " 无出生地"
            self.p(line)
            peak_t, peak_v = 0, 0
            for i, t in enumerate(self.T):
                v = R["snapTerr"][i][pl]
                if v > peak_v:
                    peak_v, peak_t = v, t
            lt, dt = self.left[pl], self.death[pl]
            self.p(f"          t={t630} 地 {self.terr(pl, t630)}（真人第 {rank630[pl]}/{self.H}） 峰值 {peak_v}@{peak_t} | 结局 {ex.get('event')}@本地{ex.get('tick')} 服务器：离线 {lt if lt >= 0 else '—'} 灭亡 {dt if dt >= 0 else '—'} | 本地指令 {self.traj[b][-1]['cmds'] if self.traj.get(b) else '?'} 条，录像执行 {sum(1 for c in self.cmds.get(pl, ()) if c[2] in (1, 2, 3, 4))} 条（其中空令 {sum(1 for c in self.cmds.get(pl, ()) if c[2] == 1 and not c[5])}）")
        # 全场对比
        if self.team_game:
            for team in range(1, R["nTeams"] + 1):
                vals = sorted(self.terr(q, t630) for q in range(self.H) if R["teams"][q] == team and q not in self.bot_of and self.terr(q, t630) > 0)
                if vals:
                    self.p(f"  t={t630} T{team} 路人真人 {len(vals)} 个：地中位 {vals[len(vals) // 2]}，最大 {vals[-1]}")
        sv = sorted(self.terr(q, t630) for q in self.sqids)
        if sv:
            self.p(f"  t={t630} 本队 {len(sv)} 个号：地中位 {sv[len(sv) // 2]}，最小 {sv[0]}，最大 {sv[-1]}")

    def sec_ledger(self, step=300):
        self.p()
        self.p(f"[E] 逐号分段账（每 {step} 拍一段，连续无事段合并；出=发出的进攻兵，烧=实际烧掉的兵，得地=打下的格数；挨打 [攻方:失地/掉兵]）")
        end = self.R["endTick"]
        for b, pl in sorted(self.sq.items(), key=lambda x: x[1]):
            stop = min(self.alive_until(pl), end)
            self.p(f"  -- {b}#{pl}（{'灭亡 ' + str(self.death[pl]) if self.death[pl] >= 0 else '存活到录像结束'}{'，离线 ' + str(self.left[pl]) if self.left[pl] >= 0 else ''}）")
            a = 0
            qa = None
            while a < stop:
                bnd = min(a + step, ((stop // 10) + 1) * 10)
                d = self.ledger(pl, a, bnd)
                if self.quiet(d):
                    if qa is None:
                        qa = a
                else:
                    if qa is not None:
                        self.p("     " + self.fmt_ledger(pl, qa, a))
                        qa = None
                    self.p("     " + self.fmt_ledger(pl, a, bnd, d))
                a = bnd
            if qa is not None:
                self.p("     " + self.fmt_ledger(pl, qa, a))

    def sec_pairs(self):
        self.p()
        self.p("[F] 本队与真人对手的逐对战损（整局合计；交换比=对方掉的余额/我方烧的兵）")
        rows = []
        for pl in self.sqids:
            agg = defaultdict(lambda: [0, 0, 0, 0, 10 ** 9, 0])
            for t, att, de, tiles, burnt, dB, dS, n in self.pair_att.get(pl, ()):
                if self.cls(de, t) != "H":
                    continue
                x = agg[de]
                x[0] += tiles; x[1] += burnt; x[2] += dB; x[3] += dS
                x[4] = min(x[4], t - 30); x[5] = max(x[5], t)
            for de, x in agg.items():
                if x[1] >= 3000 or x[0] >= 200:
                    rows.append((x[4], f"  攻 {self.bot_of[pl]:<7}→ {self.nm(de):<20} {x[4]:>5}-{x[5]:<5} 烧 {k(x[1]):>6} 得地 {x[0]:>6} 对方掉余额 {k(x[2]):>6} 掉反击槽 {k(x[3]):>6} 交换比 {x[2] / max(1, x[1]):.2f}"))
            agg = defaultdict(lambda: [0, 0, 0, 0, 10 ** 9, 0])
            for t, att, de, tiles, burnt, dB, dS, n in self.pair_def.get(pl, ()):
                x = agg[att]
                x[0] += tiles; x[1] += burnt; x[2] += dB; x[3] += dS
                x[4] = min(x[4], t - 30); x[5] = max(x[5], t)
            for att, x in agg.items():
                if x[1] >= 3000 or x[0] >= 200:
                    rows.append((x[4], f"  守 {self.bot_of[pl]:<7}← {self.nm(att):<20} {x[4]:>5}-{x[5]:<5} 对方烧 {k(x[1]):>6} 我失地 {x[0]:>6} 我掉余额 {k(x[2]):>6} 掉反击槽 {k(x[3]):>6}"))
        for _, line in sorted(rows):
            self.p(line)

    def sec_deaths(self):
        R = self.R
        self.p()
        self.p("[G] 退出与死因链（每 60 拍一行：地 兵 | 压在身上的进攻兵 [谁:多少] | 这 60 拍被谁打掉多少格/多少兵 | 自己在外的进攻兵 | 收捐/捐出）")
        dmap = {}
        for d in R["deaths"]:
            if d["p"] in self.bot_of:
                dmap.setdefault(d["p"], d)
        for b, pl in sorted(self.sq.items(), key=lambda x: (self.alive_until(x[1]), x[1])):
            ex = self.exit.get(b, {})
            lt, dt = self.left[pl], self.death[pl]
            d = dmap.get(pl)
            head = f"  -- {b}#{pl}: 结局 {ex.get('event')}@本地{ex.get('tick')}"
            if ex.get("event") == "left" and self.traj.get(b):
                last = self.traj[b][-1]
                head += f"（results.csv 的状态拍；页面日志最后一行在本地 {last['t']} 拍：地 {last['terr']} 兵 {k(float(last['bal']))} cmds={last['cmds']}）"
            if lt >= 0:
                head += f"，服务器 {lt} 拍离线（离线时 地 {self.terr(pl, lt)} 兵 {k(self.bal(pl, lt))}；此后由内置 AI 接管：余额利率为 0，只剩每 100 拍每格 1 兵的领土收入）"
            if d:
                head += f"，{d['t']} 拍灭亡：当时地 {d['terr']} 兵 {k(d['bal'])} 峰值 {d['peak']}，在场攻击者 " + (" ".join(f"{self.nm(a, d['t'])}:{k(tr)}" for a, tr in sorted(d["attackers"], key=lambda x: -x[1])[:5]) or "无")
            elif dt < 0:
                head += "，录像结束时仍存活"
            self.p(head)
            end = dt if dt >= 0 else None
            if end is None:
                continue
            s = R["sq"][b]
            ti = {t: i for i, t in enumerate(s["t"])}
            a0 = max(0, (end // 60) * 60 - 540)
            for a in range(a0, end + 1, 60):
                bnd = min(a + 60, end + 1)
                ld = self.ledger(pl, a, bnd)
                i = ti.get(a)
                inn = s["inn"][i] if i is not None else []
                out = s["out"][i] if i is not None else []
                lost = " ".join(f"{self.nm(q, a)}:{x[0]}格/{k(x[1])}" for q, x in sorted(ld["lost"].items(), key=lambda x: -(2 * x[1][0] + x[1][1]))[:3] if x[0] or x[1])
                self.p(f"     {a:>5} 地 {self.terr(pl, a):>6} 兵 {k(self.bal(pl, a)):>6} | 压 [{' '.join(f'{self.nm(q, a)}:{k(tr)}' for q, tr in sorted(inn, key=lambda x: -x[1])[:3])}] | 失 [{lost}] | 外 [{' '.join(f'{self.nm(q, a)}:{k(tr)}' for q, tr in out[:3])}] | 收 {k(ld['don_in'] + ld['boat_in'])} 捐 {k(ld['don_out'][0])} 出兵 {k(sum(v[0] for v in ld['sent'].values()))}")

    def parse_dispatch(self):
        path = os.path.join(L.bundle_dir(self.mid), "in_game.log")
        out = defaultdict(list)
        re_d = re.compile(r"\[([^\]]+)\] \[HL-(?:DISPATCH|DONATE)\] t=(\d+) ([a-z_ ]+?) pct=(\d+)/1024 -> (?:ally|boss)=(\d+)\(([^)]*)\)(?: boxedIn=(true|false))? myBal=(\d+) dMe=(-?\d+)(?: dAlly=(-?\d+))?")
        if not os.path.exists(path):
            return out
        for line in open(path, encoding="utf-8", errors="replace"):
            m = re_d.search(line)
            if m:
                out[m.group(1)].append({"t": int(m.group(2)), "kind": m.group(3).strip().replace(" ", "_"), "pct": int(m.group(4)), "to": int(m.group(5)), "boxed": m.group(7) == "true", "myBal": int(m.group(8)), "dMe": int(m.group(9)), "dAlly": int(m.group(10)) if m.group(10) else None})
        return out

    def sec_donations(self):
        R = self.R
        self.p()
        self.p("[H] 捐款审计（日志=策略打印的捐款/调度；成交=录像里执行了的；额度拒=按受捐方当时已用额度+本笔点数>上限判定）")
        logs = self.parse_dispatch()
        self.don_stats = {"logged": 0, "exec": 0, "quota": 0, "other": 0, "amount": 0, "fee": 0}
        if not logs and not any(c[2] == 2 for c in R["cmdLog"]):
            self.p("  本局没有任何捐款日志或捐款指令。")
            return
        tot_l = tot_e = tot_q = tot_o = 0
        amt = fee = 0
        by_pair = defaultdict(lambda: [0, 0, 0, 0, 0, 0])  # 日志, 成交, 到账, 税, 额度拒, 其它未成交
        streaks = []
        for b, pl in sorted(self.sq.items(), key=lambda x: x[1]):
            lg = logs.get(b, [])
            ex = [c for c in self.cmds.get(pl, ()) if c[2] == 2]
            # 批内逆序配对
            batches = []
            for c in ex:
                if batches and batches[-1][0] == c[0]:
                    batches[-1][1].append((2, c[3], c[4]))
                else:
                    batches.append((c[0], [(2, c[3], c[4])]))
            rows, _ = L.match_donations([(x["t"], x["pct"], x["to"]) for x in lg], batches)
            used = set()
            lat = []
            for (S, tmin, tmax, pct, tgt) in rows:
                if tmax is not None:
                    for j, x in enumerate(lg):
                        if x["t"] == tmax and x["pct"] == pct and x["to"] == tgt and j not in used:
                            used.add(j)
                            lat.append(S - tmax)
                            break
            for c in ex:
                key = (b, self.nm(min(c[4], NEUTRAL)))
                by_pair[key][1] += 1; by_pair[key][2] += c[6]; by_pair[key][3] += c[7]
                amt += c[6]; fee += c[7]
            run = None
            for j, x in enumerate(lg):
                key = (b, self.nm(x["to"]))
                by_pair[key][0] += 1
                if j in used:
                    if run:
                        streaks.append(run); run = None
                    continue
                # 未成交：按额度判定（本地拍 +12 的受捐方状态）
                t_srv = x["t"] + 12
                q = x["to"]
                B = x["myBal"]
                want = min(L.g0(B * (x["pct"] + 1), 1024), B - L.g0(64 * B, 1024))
                tr_q = self.terr(q, t_srv) if q < self.H else 0
                room = max(0, min(want, 150 * tr_q - self.bal(q, t_srv))) if q < self.H else 0
                verdict = "其它"
                if q < self.H and t_srv < L.QUOTA_FREE_FROM and not (0 <= self.left[q] <= t_srv):
                    qb = self.bot_of.get(q)
                    usedq = None
                    if qb:
                        s = R["sq"][qb]
                        i = bisect.bisect_right(s["t"], t_srv) - 1
                        usedq = s["quota"][max(i, 0)]
                    pts = L.quota_points(t_srv, room, self.land, tr_q) if room >= 1 else 0
                    cap = L.quota_cap(t_srv)
                    if usedq is not None and usedq + pts > cap:
                        verdict = "额度"
                        x["need"], x["room"] = pts, cap - usedq
                if verdict == "额度":
                    by_pair[key][4] += 1; tot_q += 1
                else:
                    by_pair[key][5] += 1; tot_o += 1
                if run and run["to"] == q and x["t"] - run["t1"] <= 60 and run["verdict"] == verdict:
                    run["t1"] = x["t"]; run["n"] += 1; run["bal1"] = B
                else:
                    if run:
                        streaks.append(run)
                    run = {"bot": b, "to": q, "t0": x["t"], "t1": x["t"], "n": 1, "verdict": verdict, "kind": x["kind"], "pct": x["pct"], "bal0": B, "bal1": B, "dMe": x["dMe"], "dAlly": x["dAlly"], "need": x.get("need"), "room": x.get("room")}
            if run:
                streaks.append(run)
            tot_l += len(lg); tot_e += len(ex)
            if lat:
                lat.sort()
                self.p(f"  {b}: 日志 {len(lg)} 成交 {len(ex)}，成交延迟（拍）中位 {lat[len(lat) // 2]} 最大 {lat[-1]}")
        self.p(f"  合计：日志 {tot_l} 笔，成交 {tot_e} 笔（到账 {k(amt)}，税 {k(fee)}，税/到账 {100 * fee / max(1, amt):.0f}%），未成交 {tot_l - sum(v[1] for kk, v in by_pair.items() if v[0]) if False else tot_q + tot_o}（额度拒 {tot_q}，其它 {tot_o}）")
        self.don_stats = {"logged": tot_l, "exec": tot_e, "quota": tot_q, "other": tot_o, "amount": amt, "fee": fee}
        for (b, to), v in sorted(by_pair.items(), key=lambda x: -(x[1][0] + x[1][1]))[:14]:
            self.p(f"    {b:<7}→ {to:<10} 日志 {v[0]:>3} 成交 {v[1]:>3} 到账 {k(v[2]):>6} 税 {k(v[3]):>6} | 额度拒 {v[4]:>3} 其它未成交 {v[5]:>3}")
        big = sorted(streaks, key=lambda r: -r["n"])[:10]
        if big:
            self.p("  最长的连续未成交串：")
            for r in sorted(big, key=lambda r: r["t0"]):
                self.p(f"    {r['bot']:<7}→ {self.nm(r['to']):<8} t={r['t0']}-{r['t1']} 共 {r['n']} 次 {r['kind']} pct={r['pct']}（{r['verdict']}拒；首次需 {r['need']} 点、剩 {r['room']} 点）捐方余额 {k(r['bal0'])}→{k(r['bal1'])} dMe={r['dMe']} dAlly={r['dAlly']}")
        # 成交明细（大额）
        exs = sorted((c for c in R["cmdLog"] if c[2] == 2 and c[5] and c[1] in self.bot_of), key=lambda c: -c[6])[:12]
        if exs:
            self.p("  成交的大额捐款（拍 捐方→受捐方 pct 到账 税 | 捐方余额 → 受捐方捐前 地/兵/密 | 额度 用前+本笔/上限）：")
            for c in sorted(exs, key=lambda c: c[0]):
                q = min(c[4], NEUTRAL)
                self.p(f"    {c[0]:>5} {self.bot_of[c[1]]:<7}→ {self.nm(q):<8} pct={c[3]:<4} 到账 {k(c[6]):>6} 税 {k(c[7]):>6} | 捐方 {k(c[8])}（密 {c[8] / max(1, c[9]):.0f}）→ 受方 地 {c[13]} 兵 {k(c[14])} 密 {c[14] / max(1, c[13]):.0f} | 额度 {c[10]}+{c[12]}/{c[11]}")
        # 船移交
        lb = [(t, p, tg, tr, got) for (t, p, tg, tr, got, q0, cap) in R["landings"] if p in self.bot_of and tg < self.H and tg != p and self.team_game and R["teams"][tg] == self.my_team]
        self.boat_handovers = []
        if lb:
            lost = sum(tr - got for (t, p, tg, tr, got) in lb)
            self.p(f"  船靠队友岸移交：{len(lb)} 次，船上兵 {k(sum(x[3] for x in lb))}，到账 {k(sum(x[4] for x in lb))}，蒸发 {k(lost)}"
                   f"；其中给编队外的队友 {sum(1 for x in lb if x[2] not in self.bot_of)} 次 {k(sum(x[3] for x in lb if x[2] not in self.bot_of))}")
            # 给每条靠岸的船找回它的发船指令：海上每 5 拍掉 1/128，按「发船兵×(127/128)^(航程/5)」最接近的那条配对
            used = set()
            for (t, p, tg, tr, got) in sorted(lb):
                best = None
                for i, c in enumerate(self.cmds.get(p, ())):
                    if c[2] != 3 or not c[5] or c[0] >= t or i in used:
                        continue
                    exp = c[6] * (127 / 128) ** ((t - c[0]) // 5)
                    err = abs(exp - tr) / max(1.0, tr)
                    if best is None or err < best[0]:
                        best = (err, i, c)
                row = {"t": t, "bot": self.bot_of[p], "to": self.nm(tg), "toSquad": tg in self.bot_of, "landed": tr, "got": got}
                if best and best[0] < 0.05:
                    used.add(best[1])
                    c = best[2]
                    row.update({"launchT": c[0], "launched": c[6], "fee": c[7], "B0": c[8], "pct": c[3]})
                self.boat_handovers.append(row)
            for r in sorted(self.boat_handovers, key=lambda x: -x["landed"])[:8]:
                extra = f"（{r['launchT']} 拍发船 {k(r['launched'])} 兵、船费 {k(r['fee'])}，当时余额 {k(r['B0'])}；航程 {r['t'] - r['launchT']} 拍，海上损耗 {k(r['launched'] - r['landed'])}）" if "launchT" in r else ""
                self.p(f"    {r['t']:>5} {r['bot']}→{r['to']}{'' if r['toSquad'] else '（编队外）'} 靠岸 {k(r['landed'])} 到账 {k(r['got'])}{extra}")

    def sec_drops(self):
        self.p()
        an = json.load(open(os.path.join(L.bundle_dir(self.mid), "anomalies.json")))
        # anomalies.json 的 drop30Events 最多只列 30 条（按号名截断），这里直接从 traj 取全量：
        # 同一个号相邻两行快照余额下跌 ≥30%（与 drop30Count 同口径）。
        evs = []
        for b in sorted(self.traj):
            rows = self.traj[b]
            for r0, r1 in zip(rows, rows[1:]):
                b0, b1 = int(float(r0["bal"])), int(float(r1["bal"]))
                if b0 > 0 and (b0 - b1) / b0 >= 0.30:
                    evs.append({"bot": b, "t0": int(r0["t"]), "t1": int(r1["t"]), "bal0": b0, "bal1": b1,
                                "dropPct": round(100.0 * (b0 - b1) / b0, 1), "terr0": int(float(r0["terr"])), "terr1": int(float(r1["terr"]))})
        self.drop_count_card = an.get("drop30Count")
        self.p(f"[I] DROP30 逐笔对账（traj 相邻两行快照余额跌幅≥30% 的全部区间，共 {len(evs)} 个；anomalies.json 的 drop30Count={an.get('drop30Count')}，其 drop30Events 只列了 {len(an.get('drop30Events', []))} 条；各项为该区间重放精确值）")
        self.drops = []
        for e in evs:
            b = e["bot"]
            if b not in self.sq:
                continue
            pl = self.sq[b]
            d = self.ledger(pl, e["t0"], e["t1"])
            parts = {}
            for cl, lab in (("N", "攻中立"), ("AI", "攻AI"), ("H", "攻真人")):
                s = d["sent"].get(cl)
                if s:
                    parts[lab] = s[0] + s[1]
            if d["don_out"][2]:
                parts["捐款"] = d["don_out"][0] + d["don_out"][1]
            if d["boat"][2]:
                parts["发船"] = d["boat"][0] + d["boat"][1]
            if d["def_bal"]:
                parts["挨打"] = d["def_bal"]
            main = max(parts.items(), key=lambda x: x[1])[0] if parts else "无"
            ncmd = sum(s[2] for s in d["sent"].values()) + d["don_out"][2] + d["boat"][2]
            tgt = ""
            if main == "攻真人":
                tgt = " 对 " + ",".join(self.nm(q, e["t0"]) for q, v in d["tgt_h"].most_common(2))
            elif main == "捐款":
                tgt = " 给 " + ",".join(self.nm(q) for q, v in d["don_to"].most_common(2))
            elif main == "挨打":
                tgt = " 被 " + ",".join(self.nm(q, e["t0"]) for q, x in sorted(d["lost"].items(), key=lambda x: -x[1][1])[:2])
            gain_t = sum(v[0] for v in d["gain"].values())
            gain_b = sum(v[1] for v in d["gain"].values())
            self.p(f"  {b:<7} {e['t0']:>5}-{e['t1']:<5} 兵 {k(e['bal0']):>6}→{k(e['bal1']):<6}(-{e['dropPct']:.0f}%) 地 {e['terr0']}→{e['terr1']} | 主因 {main}{tgt} | " + " ".join(f"{a}{k(v)}" for a, v in sorted(parts.items(), key=lambda x: -x[1])) + f" | {ncmd}令 空令{d['noop']} 烧{k(gain_b)} 得地{gain_t} 退兵{k(d['ret'])} 末尾在外{k(d['out1'])}")
            self.drops.append({"bot": b, "t0": e["t0"], "t1": e["t1"], "bal0": e["bal0"], "bal1": e["bal1"], "dropPct": e["dropPct"], "main": main, "parts": {a: int(v) for a, v in parts.items()}, "cmds": ncmd, "tilesGained": gain_t, "burnt": int(gain_b), "target": tgt.strip()})

    def sec_batches(self):
        self.p()
        self.p("[J] 执行层：同一拍落地 ≥2 条花钱指令的批（清仓批 = 批后余额 < 批前 20%）与空令")
        rows = []
        for pl in self.sqids:
            cur = []
            for c in self.cmds.get(pl, ()):
                if c[2] not in (1, 2, 3):
                    continue
                if cur and cur[-1][0] != c[0]:
                    rows.append(cur); cur = []
                cur.append(c)
            if cur:
                rows.append(cur)
        self.batches = []
        n_multi = n_dump = 0
        lines = []
        for cur in rows:
            if len(cur) < 2:
                continue
            n_multi += 1
            b0 = cur[0][8]
            last = cur[-1]
            b1 = last[8] - last[6] - last[7] if last[5] else last[8]
            okn = sum(1 for c in cur if c[5])
            dump = b1 < 0.2 * b0 and okn >= 2
            if dump:
                n_dump += 1
            if dump or len(cur) >= 6:
                tg = Counter()
                for c in cur:
                    if c[2] == 1:
                        tg[self.nm(min(c[4], NEUTRAL), c[0])] += 1
                    elif c[2] == 2:
                        tg["捐→" + self.nm(min(c[4], NEUTRAL))] += 1
                    else:
                        tg["船"] += 1
                pcts = [c[3] for c in cur]
                gained = ""
                pl = cur[0][1]
                t = cur[0][0]
                lines.append(f"  {t:>5} {self.bot_of[pl]:<7} {len(cur)}条（生效{okn}）{'清仓' if dump else '    '} 兵 {k(b0):>6}→{k(b1):<6} 地 {cur[0][9]} | " + " ".join(f"{a}×{n}" for a, n in tg.most_common(3)) + f" | pct {pcts}")
                self.batches.append({"t": t, "bot": self.bot_of[pl], "n": len(cur), "ok": okn, "dump": dump, "bal0": b0, "bal1": b1, "targets": dict(tg), "pcts": pcts})
        self.p(f"  多令批 {n_multi} 个，其中清仓批 {n_dump} 个；下面列出清仓批和 ≥6 条的批：")
        for x in lines:
            self.p(x)
        noop = Counter()
        for pl in self.sqids:
            for c in self.cmds.get(pl, ()):
                if c[2] == 1 and not c[5]:
                    noop[(self.bot_of[pl], self.nm(min(c[4], NEUTRAL)))] += 1
        if noop:
            self.p("  空令（进攻指令到达时无法生成前线：目标已不相邻/已无中立地；不扣费）：" + " ".join(f"{b}→{q}×{n}" for (b, q), n in noop.most_common(10)))
        # 本地指令数 vs 执行数（按 90 拍快照）
        gaps = []
        for b, pl in self.sq.items():
            rows = self.traj.get(b, [])
            for r0, r1 in zip(rows, rows[1:]):
                dc = r1["cmds"] - r0["cmds"]
                ex = sum(1 for c in self.cmds.get(pl, ()) if c[2] in (1, 2, 3, 4) and r0["t"] <= c[0] < r1["t"])
                if dc >= 8 and ex == 0:
                    gaps.append((b, r0["t"], r1["t"], dc))
        if gaps:
            agg = defaultdict(list)
            for b, t0, t1, dc in gaps:
                agg[b].append((t0, t1, dc))
            self.p("  本地连发却一条都没落地的 90 拍窗（号: 窗口数, 首-末, 本地指令合计）：" + " ".join(f"{b}:{len(v)}窗,{v[0][0]}-{v[-1][1]},{sum(x[2] for x in v)}条" for b, v in sorted(agg.items())))

    def sec_opponents(self):
        R = self.R
        self.p()
        self.p("[K] 对本队伤害最大的对手（整局：打掉本队的格数、打掉的余额；本队回敬的烧兵）与他们的成长")
        dmg = defaultdict(lambda: [0, 0, 0, 0, 10 ** 9, 0])
        for pl in self.sqids:
            for t, att, de, tiles, burnt, dB, dS, n in self.pair_def.get(pl, ()):
                x = dmg[att]
                x[0] += tiles; x[1] += dB; x[2] += burnt
                x[4] = min(x[4], t - 30); x[5] = max(x[5], t)
            for t, att, de, tiles, burnt, dB, dS, n in self.pair_att.get(pl, ()):
                if de < NEUTRAL:
                    dmg[de][3] += burnt
        ticks = [t for t in (630, 1530, 2130, 2700, 3300, 4200, 5100, 6300, 7500) if t <= R["endTick"]]
        for q, x in sorted(dmg.items(), key=lambda kv: -(kv[1][0] * 2 + kv[1][1]))[:8]:
            if x[0] < 100 and x[1] < 3000:
                continue
            grow = " ".join(f"{t}:{100 * self.terr(q, t) / self.land:.1f}%/{k(self.bal(q, t))}" for t in ticks) if q < self.H else ""
            self.p(f"  {self.nm(q):<20} 打掉本队 {x[0]:>6} 格 / {k(x[1]):>6} 兵（自烧 {k(x[2])}），{x[4]}-{x[5]} 拍；本队对它烧 {k(x[3])} | {grow}")

    def sec_total(self):
        """本队整局兵力去向总账：每个号只算我方控制期间（开局 → 离线或灭亡）。"""
        R = self.R
        self.p()
        self.p("[L] 本队整局兵力去向总账（每个号只算我方控制期间：开局→离线/灭亡；重放精确值。烧=进攻中真正消耗的兵；对消=进攻兵与对方打过来的兵在槽内 1:1 抵掉）")
        self.p("  号       到拍 |   利息 | 烧:中立     AI   真人 真人对消 | 攻击费 | 挨打掉兵 反击槽被消 | 捐出到账    税   收捐 | 船出兵  船费 靠队友岸 | 末余额 在途 | 被真人吃:格 对方烧 每格")
        keys = ("inc", "burnN", "burnAI", "burnH", "netH", "atkFee", "defBal", "defSlot", "donOut", "donTax", "donIn", "donOutNonSquad", "boatOut", "boatFee", "boatToMate", "boatToOutside", "boatOnEnemy", "balEnd", "outEnd", "lostTiles", "lostBurn", "tilesN", "tilesAI", "tilesH")
        tot = {x: 0 for x in keys}
        per = {}
        for b, pl in sorted(self.sq.items(), key=lambda x: x[1]):
            end = self.left[pl] if self.left[pl] >= 0 else self.alive_until(pl)
            d = self.ledger(pl, 0, end)
            r = {x: 0 for x in keys}
            r["end"] = end
            r["husk"] = self.left[pl] >= 0
            r["inc"] = d["inc"]
            for t, att, de, tiles, burnt, dB, dS, n in self.pair_att.get(pl, ()):
                if t > end + 30:
                    continue
                cl = self.cls(de, t)
                if cl == "N":
                    r["burnN"] += burnt; r["tilesN"] += tiles
                elif cl == "AI":
                    r["burnAI"] += burnt; r["tilesAI"] += tiles
                else:
                    r["burnH"] += burnt - dS; r["netH"] += dS; r["tilesH"] += tiles
            r["atkFee"] = sum(s[1] for s in d["sent"].values())
            r["defBal"] = d["def_bal"]
            r["defSlot"] = sum(x[2] for x in d["lost"].values())
            r["donOut"], r["donTax"] = d["don_out"][0], d["don_out"][1]
            r["donOutNonSquad"] = sum(v for q, v in d["don_to"].items() if q not in self.bot_of)
            r["donIn"] = d["don_in"]
            r["boatOut"], r["boatFee"] = d["boat"][0], d["boat"][1]
            # 船靠在别的真人席位的地上：同队 = 整船兵移交给对方（受对方硬上限限制）；敌队 = 登陆进攻。
            # boatToOutside = 靠在「不归编队控制」的队友地上的那部分（编队外的队友，或已离线的编队号空壳）。
            for (t, p, tg, tr, got, q0, cap) in R["landings"]:
                if p != pl or not (0 <= tg < self.H) or tg == pl or t > min(end, R["endTick"]):
                    continue
                if self.team_game and R["teams"][tg] == R["teams"][pl]:
                    r["boatToMate"] += tr
                    if tg not in self.bot_of or 0 <= self.left[tg] <= t:
                        r["boatToOutside"] += tr
                else:
                    r["boatOnEnemy"] += tr
            r["balEnd"], r["outEnd"] = d["bal1"], d["out1"]
            r["giftIn"] = sum(g[3] for g in R.get("botGifts", ()) if g[2] == pl and g[0] <= end)
            for t, att, de, tiles, burnt, dB, dS, n in self.pair_def.get(pl, ()):
                if t > end + 30 or att >= self.H:
                    continue
                r["lostTiles"] += tiles; r["lostBurn"] += burnt
            per[b] = {x: int(v) if not isinstance(v, bool) else v for x, v in r.items()}
            for x in keys:
                tot[x] += r[x]
            per_tile = f"{r['lostBurn'] / r['lostTiles']:.0f}" if r["lostTiles"] else "—"
            self.p(f"  {b:<7} {end:>5}{'*' if r['husk'] else ' '}| {k(r['inc']):>6} | {k(r['burnN']):>6} {k(r['burnAI']):>6} {k(r['burnH']):>6} {k(r['netH']):>6} | {k(r['atkFee']):>6} | {k(r['defBal']):>6} {k(r['defSlot']):>6} | {k(r['donOut']):>6} {k(r['donTax']):>6} {k(r['donIn']):>6} | {k(r['boatOut']):>6} {k(r['boatFee']):>5} {k(r['boatToMate']):>6} | {k(r['balEnd']):>6} {k(r['outEnd']):>5} | {r['lostTiles']:>6} {k(r['lostBurn']):>6} {per_tile:>4}")
        per_tile = f"{tot['lostBurn'] / tot['lostTiles']:.0f}" if tot["lostTiles"] else "—"
        self.p(f"  合计          | {k(tot['inc']):>6} | {k(tot['burnN']):>6} {k(tot['burnAI']):>6} {k(tot['burnH']):>6} {k(tot['netH']):>6} | {k(tot['atkFee']):>6} | {k(tot['defBal']):>6} {k(tot['defSlot']):>6} | {k(tot['donOut']):>6} {k(tot['donTax']):>6} {k(tot['donIn']):>6} | {k(tot['boatOut']):>6} {k(tot['boatFee']):>5} {k(tot['boatToMate']):>6} | {k(tot['balEnd']):>6} {k(tot['outEnd']):>5} | {tot['lostTiles']:>6} {k(tot['lostBurn']):>6} {per_tile:>4}")
        inc = max(1, tot["inc"])
        fees = tot["atkFee"] + tot["donTax"] + tot["boatFee"]
        self.p(f"  占总利息：打中立 {100 * tot['burnN'] / inc:.1f}% 打AI {100 * tot['burnAI'] / inc:.1f}% 打真人 {100 * (tot['burnH'] + tot['netH']) / inc:.1f}%（其中对消 {100 * tot['netH'] / inc:.1f}%） | 三种手续费 {100 * fees / inc:.1f}%（攻击费 {100 * tot['atkFee'] / inc:.1f}% 捐款税 {100 * tot['donTax'] / inc:.1f}% 船费 {100 * tot['boatFee'] / inc:.1f}%） | 挨打掉兵 {100 * tot['defBal'] / inc:.1f}% | 送给编队外 {100 * (tot['donOutNonSquad'] + tot['boatToOutside']) / inc:.1f}%（捐款 {k(tot['donOutNonSquad'])} + 船靠编队外队友/空壳的岸 {k(tot['boatToOutside'])}）| 船靠编队内队友岸 {k(tot['boatToMate'] - tot['boatToOutside'])}，登陆敌方真人 {k(tot['boatOnEnemy'])} | 离线/灭亡时还在手里 {100 * (tot['balEnd'] + tot['outEnd']) / inc:.1f}%")
        self.p(f"  得地：中立 {tot['tilesN']} 格（{tot['burnN'] / max(1, tot['tilesN']):.1f} 兵/格） AI {tot['tilesAI']} 格（{tot['burnAI'] / max(1, tot['tilesAI']):.1f} 兵/格） 真人 {tot['tilesH']} 格（{tot['burnH'] / max(1, tot['tilesH']):.1f} 兵/格，不含对消）；带 * 的号是掉线后交给内置 AI（末余额即移交给 AI 的兵）")
        gifts = [g for g in R.get("botGifts", ()) if g[2] in self.bot_of]
        gift_tot = sum(per[b].get("giftIn", 0) for b in per)
        if gifts:
            by_bot = sorted(((per[b].get("giftIn", 0), b) for b in per if per[b].get("giftIn", 0) > 0), reverse=True)
            big = sorted(gifts, key=lambda g: -g[3])[:6]
            self.p(f"  表外进项：内置 AI / 离线空壳队友送来的兵（引擎 botDonate→botGive，不是玩家指令，不占受捐额度，只受对方硬上限限制）合计 {k(gift_tot)}（= 总利息的 {100 * gift_tot / inc:.1f}%）："
                   + " ".join(f"{b} {k(v)}" for v, b in by_bot))
            self.p("    最大的几笔：" + "；".join(f"{g[0]} 拍 {self.nm(g[1])} → {self.bot_of[g[2]]} {k(g[3])}（送出方原有 {k(g[5])}）" for g in big))
        self.squad_ledger = {"perBot": per, "total": {x: int(v) for x, v in tot.items()}, "giftIn": int(gift_tot),
                             "gifts": [[g[0], self.nm(g[1]), self.bot_of[g[2]], g[3], g[4]] for g in sorted(gifts, key=lambda g: -g[3])[:12]]}

    def sec_donnet(self):
        """全场捐款网络：重放里所有真人的成交捐款（回放只含成交的捐款），按阵营汇总。"""
        R = self.R
        self.donnet = None
        if not self.team_game:
            return
        teams = R["teams"]

        def cls(p):
            if p in self.bot_of:
                return "本编队"
            return ("本队路人" if teams[p] == self.my_team else f"队{teams[p]}")

        bands = ((0, 2142, "<2142"), (2142, 3213, "2142~3212"), (3213, 4284, "3213~4283"), (4284, 10 ** 9, "≥4284"))
        by_cls = defaultdict(lambda: {"n": 0, "got": 0, "tax": 0, "toHusk": 0, "bands": {b[2]: 0 for b in bands}})
        recv = defaultdict(lambda: {"n": 0, "got": 0, "from": defaultdict(int), "t0": 10 ** 9, "t1": 0})
        pairs = defaultdict(lambda: {"n": 0, "got": 0, "tax": 0, "t0": 10 ** 9, "t1": 0})
        husk = defaultdict(lambda: {"n": 0, "got": 0, "tax": 0, "t0": 10 ** 9, "t1": 0})
        gifts = []
        for c in R["cmdLog"]:
            if c[2] != 2 or not c[5] or c[1] >= self.H or c[4] >= self.H:
                continue
            t, p, q, got, tax = c[0], c[1], c[4], c[6], c[7]
            x = by_cls[cls(p)]
            x["n"] += 1; x["got"] += got; x["tax"] += tax
            for a, b, name in bands:
                if a <= t < b:
                    x["bands"][name] += got
            r = recv[q]
            r["n"] += 1; r["got"] += got; r["from"][p] += got; r["t0"] = min(r["t0"], t); r["t1"] = max(r["t1"], t)
            pr = pairs[(p, q)]
            pr["n"] += 1; pr["got"] += got; pr["tax"] += tax; pr["t0"] = min(pr["t0"], t); pr["t1"] = max(pr["t1"], t)
            if 0 <= self.left[q] < t:
                x["toHusk"] += got
                h = husk[(p, q)]
                h["n"] += 1; h["got"] += got; h["tax"] += tax; h["t0"] = min(h["t0"], t); h["t1"] = max(h["t1"], t)
            if c[3] >= 900 and 0 <= self.left[p] - t <= 120:
                gifts.append({"t": t, "from": self.nm(p, t), "to": self.nm(q, t), "got": got, "leftT": self.left[p]})
        if not by_cls:
            return
        self.p()
        self.p("[N] 全场捐款网络（重放里全部真人的成交捐款；回放只记成交的捐款）")
        for name, x in sorted(by_cls.items(), key=lambda kv: -kv[1]["got"]):
            self.p(f"  {name:<5} {x['n']:>3} 笔 到账 {k(x['got']):>6} 税 {k(x['tax']):>6} | 分段到账 " + " ".join(f"{b}:{k(v)}" for b, v in x["bands"].items()) + (f" | 其中捐给已离线的队友（空壳，免额度）{k(x['toHusk'])}" if x["toHusk"] else ""))
        self.p("  收捐最多的 8 个：")
        top = sorted(recv.items(), key=lambda kv: -kv[1]["got"])[:8]
        for q, r in top:
            fr = " ".join(f"{self.nm(p)}:{k(v)}" for p, v in sorted(r["from"].items(), key=lambda kv: -kv[1])[:4])
            self.p(f"    {self.nm(q):<22}{'（' + str(self.left[q]) + ' 拍已离线）' if self.left[q] >= 0 else ''} {r['n']:>3} 笔 {k(r['got']):>6}（{r['t0']}~{r['t1']} 拍）← {fr}")
        if husk:
            self.p("  捐给空壳（已离线、由内置 AI 托管的队友）：")
            for (p, q), h in sorted(husk.items(), key=lambda kv: -kv[1]["got"])[:6]:
                self.p(f"    {self.nm(p)} → {self.nm(q)} {h['n']} 笔 到账 {k(h['got'])} 税 {k(h['tax'])}（{h['t0']}~{h['t1']} 拍）")
        for g in sorted(gifts, key=lambda g: -g["got"])[:5]:
            self.p(f"  离场前清仓捐款：{g['t']} 拍 {g['from']} → {g['to']} {k(g['got'])}（{g['leftT']} 拍离线）")
        # 内置 AI / 离线空壳给队友送兵（不是玩家指令，上面的捐款统计里没有）
        bot_gifts = [g for g in R.get("botGifts", ()) if g[2] < self.H]
        bg_pairs = defaultdict(lambda: {"n": 0, "got": 0, "fee": 0, "t0": 10 ** 9, "t1": 0})
        bg_team = defaultdict(int)
        for t, p, q, got, fee, b0, l0 in bot_gifts:
            x = bg_pairs[(p, q)]
            x["n"] += 1; x["got"] += got; x["fee"] += fee; x["t0"] = min(x["t0"], t); x["t1"] = max(x["t1"], t)
            bg_team[cls(q)] += got
        if bg_pairs:
            self.p("  表外：内置 AI / 离线空壳把余额送给队友（引擎 botDonate，手续费 64/1024，不占额度；按接收方阵营合计）："
                   + " ".join(f"{n}:{k(v)}" for n, v in sorted(bg_team.items(), key=lambda kv: -kv[1])))
            for (p, q), x in sorted(bg_pairs.items(), key=lambda kv: -kv[1]["got"])[:8]:
                self.p(f"    {self.nm(p)}{'（' + str(self.left[p]) + ' 拍离线）' if p < self.H and self.left[p] >= 0 else ''} → {self.nm(q)} {x['n']} 次 到账 {k(x['got'])} 费 {k(x['fee'])}（{x['t0']}~{x['t1']} 拍）")
        self.donnet = {
            "botGiftsByClass": {n: int(v) for n, v in bg_team.items()},
            "botGiftPairs": [{"from": self.nm(p), "fromLeft": self.left[p] if p < self.H and self.left[p] >= 0 else None, "to": self.nm(q), "n": x["n"], "delivered": int(x["got"]), "fee": int(x["fee"]), "t0": x["t0"], "t1": x["t1"]} for (p, q), x in sorted(bg_pairs.items(), key=lambda kv: -kv[1]["got"])[:8]],
            "byClass": {n: {"n": x["n"], "delivered": int(x["got"]), "tax": int(x["tax"]), "toHusk": int(x["toHusk"]), "bands": {b: int(v) for b, v in x["bands"].items()}} for n, x in by_cls.items()},
            "topReceivers": [{"who": self.nm(q), "left": self.left[q] if self.left[q] >= 0 else None, "n": r["n"], "delivered": int(r["got"]), "t0": r["t0"], "t1": r["t1"], "from": [{"who": self.nm(p), "delivered": int(v)} for p, v in sorted(r["from"].items(), key=lambda kv: -kv[1])[:4]]} for q, r in top],
            "toHusks": [{"from": self.nm(p), "to": self.nm(q), "n": h["n"], "delivered": int(h["got"]), "tax": int(h["tax"]), "t0": h["t0"], "t1": h["t1"]} for (p, q), h in sorted(husk.items(), key=lambda kv: -kv[1]["got"])[:6]],
            "leaveGifts": sorted(gifts, key=lambda g: -g["got"])[:5],
        }

    def sec_teamfall(self, step=300, min_drop=2.5, top_windows=4):
        """本队整队掉地最猛的窗口：掉的是谁的地（在控的号 / 空壳 / 路人，路人里又分在线和已离线），被谁吃的。"""
        R = self.R
        self.teamfall = None
        if not self.team_game:
            return
        end = R["endTick"]
        teams = R["teams"]
        mt = self.my_team
        nT = R["nTeams"]
        self.p()
        self.p("[O] 各队离线情况与本队掉地窗口（空壳=已离线、由内置 AI 托管的真人；份额为占全图陆地 %）")
        ticks = [t for t in (1530, 3060, 4500, 6000, 7500, 9000, 10800, 12600) if t < end]
        self.p("     t | " + " | ".join(f"队{i}：在线 号/地%  空壳 号/地%" for i in range(1, nT + 1)))
        husk_rows = []
        for t in ticks:
            i = self.ix(t)
            terr = R["snapTerr"][i]
            cells = []
            row = {"t": t}
            for tm in range(1, nT + 1):
                on = [q for q in range(self.H) if teams[q] == tm and terr[q] > 0 and not (0 <= self.left[q] <= t)]
                hs = [q for q in range(self.H) if teams[q] == tm and terr[q] > 0 and 0 <= self.left[q] <= t]
                a, b = sum(terr[q] for q in on), sum(terr[q] for q in hs)
                cells.append(f"      {len(on):>3}/{100 * a / self.land:5.1f}      {len(hs):>3}/{100 * b / self.land:5.1f}")
                row[f"T{tm}"] = {"online": len(on), "onlineSharePct": round(100 * a / self.land, 1), "husks": len(hs), "huskSharePct": round(100 * b / self.land, 1)}
            husk_rows.append(row)
            self.p(f"{t:>6} | " + " | ".join(cells))
        # 本队掉地最猛的窗口
        grid = list(range(0, end, step)) + [end]
        share = [R["teamLand"][self.ix(t)][mt] for t in grid]
        wins = []
        for j in range(1, len(grid)):
            d = 100 * (share[j] - share[j - 1]) / self.land
            if d <= -min_drop:
                wins.append((d, grid[j - 1], grid[j]))
        wins = sorted(wins)[:top_windows]
        out_w = []
        for d, a, b in sorted(wins, key=lambda w: w[1]):
            ia, ib = self.ix(a), self.ix(b)
            ta, tb_ = R["snapTerr"][ia], R["snapTerr"][ib]
            ba = R["snapBal"][ia]
            lost_by = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # 守方 -> 攻方 -> [格, 攻方烧兵]
            for t, att, de, tiles, burnt, dB, dS, n in R["pairLog"]:
                if a < t <= b + 29 and de < self.H and teams[de] == mt and tiles > 0 and (att >= self.H or teams[att] != mt):
                    x = lost_by[de][att]
                    x[0] += tiles; x[1] += burnt
            cls_tot = {"在控的号": 0, "本队空壳": 0, "路人在线": 0, "路人已离线": 0}
            rows = []
            for q in range(self.H):
                if teams[q] != mt:
                    continue
                dl = tb_[q] - ta[q]
                gone = 0 <= self.left[q] <= b
                if q in self.bot_of:
                    c = "本队空壳" if gone else "在控的号"
                else:
                    c = "路人已离线" if gone else "路人在线"
                cls_tot[c] += dl
                if dl < 0:
                    rows.append((dl, q, c))
            rows.sort()
            self.p(f"  掉地窗口 {a}~{b}：本队 {100 * share[grid.index(a)] / self.land:.1f}% → {100 * share[grid.index(b)] / self.land:.1f}%（{d:+.1f} 点）| 净变化：" + " ".join(f"{c} {100 * v / self.land:+.2f}" for c, v in cls_tot.items()))
            ws = {"t0": a, "t1": b, "teamShare0": round(100 * share[grid.index(a)] / self.land, 1), "teamShare1": round(100 * share[grid.index(b)] / self.land, 1), "netByClassPct": {c: round(100 * v / self.land, 2) for c, v in cls_tot.items()}, "losers": []}
            for dl, q, c in rows[:6]:
                st = f"{self.left[q]} 拍离线" if self.left[q] >= 0 else "在线"
                if 0 <= self.death[q] <= b + 30:
                    st += f"，{self.death[q]} 拍灭亡"
                atk = sorted(lost_by[q].items(), key=lambda kv: -kv[1][0])[:3]
                at = " ".join(f"{self.nm(p)}:{x[0]}格/烧{k(x[1])}" for p, x in atk)
                self.p(f"    {self.nm(q):<22} {c} {st}：地 {ta[q]}→{tb_[q]}（{100 * dl / self.land:+.2f} 点），窗口起点兵 {k(ba[q])}（密 {ba[q] / max(1, ta[q]):.0f}）| 被吃 [{at}]")
                ws["losers"].append({"who": self.nm(q), "class": c, "leftT": self.left[q] if self.left[q] >= 0 else None, "deathT": self.death[q] if self.death[q] >= 0 else None, "terr0": ta[q], "terr1": tb_[q], "bal0": ba[q], "attackers": [{"who": self.nm(p), "tiles": x[0], "burn": int(x[1])} for p, x in atk]})
            out_w.append(ws)
        self.teamfall = {"husks": husk_rows, "windows": out_w}

    def sec_interest(self):
        """利息效率：利息 = 利率 × 余额，余额到软上限（100×地）时最多，超过后递减，到硬上限（150×地）为 0。
        对每个号、每个阶段统计：超软上限 / 贴硬上限的拍数、实得收入、同样的地一直握在软上限能得的收入。"""
        R = self.R
        T = self.T
        end = R["endTick"]
        phases = [(600, 1500), (1500, 4284), (4284, end)]
        phases = [(a, min(b, end)) for a, b in phases if a < end]
        self.p()
        self.p("[P] 利息效率（只算我方在控期间；软上限=100×地，硬上限=150×地；「满额」=同样的地、余额一直等于软上限时的收入；超软=余额>软上限的拍数，贴硬=余额≥149×地的拍数）")
        self.p("  号       | " + " | ".join(f"{a}~{b}: 均密 超软 贴硬  实得   满额  比例" for a, b in phases))
        out = {}
        tot = [[0, 0, 0, 0, 0, 0] for _ in phases]
        for b_, pl in sorted(self.sq.items(), key=lambda x: x[1]):
            stop = self.left[pl] if self.left[pl] >= 0 else self.alive_until(pl)
            cells = []
            out[b_] = []
            for k_, (a, b) in enumerate(phases):
                over = hard = n = 0
                got = bench = dsum = 0
                over_loss = 0
                for i in range(len(T) - 1):
                    t = T[i]
                    if t < a or t >= b or t >= stop:
                        continue
                    terr, bal = R["snapTerr"][i][pl], R["snapBal"][i][pl]
                    if terr <= 0:
                        continue
                    cap = L.soft_cap(terr)
                    step = T[i + 1] - t
                    inc = R["snapInc"][i + 1][pl] - R["snapInc"][i][pl]
                    tt = t + 9
                    full = L.g0(L.interest_rate(tt, terr, cap, self.land) * cap, 10000) + (terr if tt % 100 == 99 else 0)
                    if step != 10:
                        full = full * step // 10
                    n += step; got += inc; bench += full; dsum += step * bal / terr
                    if bal > cap:
                        over += step
                        over_loss += max(0, full - inc)
                    if bal >= 149 * terr:
                        hard += step
                if n == 0:
                    cells.append(" " * 44)
                    out[b_].append(None)
                    continue
                cells.append(f"{dsum / n:5.0f} {over:>5} {hard:>5} {k(got):>6} {k(bench):>6} {100 * got / max(1, bench):4.0f}%")
                out[b_].append({"from": a, "to": b, "ticks": n, "meanDensity": round(dsum / n, 1), "ticksOverSoftCap": over, "ticksAtHardCap": hard, "income": int(got), "incomeAtSoftCap": int(bench), "lostWhileOverSoftCap": int(over_loss)})
                x = tot[k_]
                x[0] += n; x[1] += over; x[2] += hard; x[3] += got; x[4] += bench; x[5] += over_loss
            self.p(f"  {b_:<8} | " + " | ".join(cells))
        self.p("  合计     | " + " | ".join(f"      {x[1]:>5} {x[2]:>5} {k(x[3]):>6} {k(x[4]):>6} {100 * x[3] / max(1, x[4]):4.0f}%" for x in tot))
        self.p("  其中余额在软上限以上那些拍上少拿的利息：" + " ".join(f"{a}~{b}: {k(x[5])}" for (a, b), x in zip(phases, tot)))
        self.interest = {"phases": [{"from": a, "to": b, "botTicks": x[0], "ticksOverSoftCap": x[1], "ticksAtHardCap": x[2], "income": int(x[3]), "incomeAtSoftCap": int(x[4]), "lostWhileOverSoftCap": int(x[5])} for (a, b), x in zip(phases, tot)], "perBot": out}

    def sec_map(self, ticks):
        R = self.R
        for t in ticks:
            m = R["maps"].get(str(t))
            if not m:
                continue
            rows = m["rows"]
            # 裁到本队包围盒附近
            ys = [i for i, r in enumerate(rows) if re.search(r"[a-j]", r)]
            xs = [j for r in rows for j, ch in enumerate(r) if "a" <= ch <= "j"]
            if ys:
                y0, y1 = max(0, min(ys) - 4), min(len(rows), max(ys) + 5)
                x0, x1 = max(0, min(xs) - 8), min(len(rows[0]), max(xs) + 9)
            else:
                y0, y1, x0, x1 = 0, len(rows), 0, len(rows[0])
            self.p()
            self.p(f"[M] t={t} 占地图（每格 {m['cell']}px；a-j=本队号 {json.dumps(m['legend'], ensure_ascii=False)}；+=路人队友 数字=敌队 :=AI _=中立地 空格=水；显示列 {x0}-{x1} 行 {y0}-{y1}）")
            for r in rows[y0:y1]:
                self.p("  " + r[x0:x1])

    def facts(self):
        """给复盘 JSON 用的机器可读事实。"""
        R = self.R
        oc = self.card.get("outcome", {})
        end = oc.get("endTick") or R["endTick"]
        f = {"matchId": self.mid, "land": self.land, "humans": self.H, "nTeams": R["nTeams"], "nTeamsHeader": R["nTeamsHeader"], "teamSizes": R["teamSizes"], "myTeam": self.my_team, "squadInRoom": sorted(self.sq), "foreign": self.foreign, "version": version_of(self.mid)}
        tl = []
        for t in sorted(set([90, 180, 270, 630, 1080, 1530, 2130, 2700, 3060, 3600, 4500, 5400, 6300, 7200, 8100, 9000, 10800, 12600] + list(getattr(self, "extra_tl", [])) + [end])):
            if t > end:
                continue
            (tt, tland, bl, neu, ta, tb, sq_t, sq_b, sq_n, husk) = self.team_rows([t])[0]
            row = {"t": t, "alive": sq_n, "sqTerr": sq_t, "sqSharePct": round(100 * sq_t / self.land, 2), "sqBal": sq_b, "sqDens": round(sq_b / max(1, sq_t), 1)}
            if husk[0]:
                row["husks"] = {"n": husk[0], "terr": husk[1], "sharePct": round(100 * husk[1] / self.land, 2), "bal": husk[2]}
            if self.team_game:
                row["teamOnlineBal"] = {f"T{i}": int(tb[i]) for i in range(1, R["nTeams"] + 1)}
                row["teamOnlineHumans"] = {f"T{i}": ta[i] for i in range(1, R["nTeams"] + 1)}
            if self.team_game:
                row["teamSharePct"] = {f"T{i}": round(100 * tland[i] / self.land, 1) for i in range(1, R["nTeams"] + 1)}
                row["aiSharePct"] = round(100 * bl / self.land, 1)
                row["neutralSharePct"] = round(100 * neu / self.land, 1)
            tl.append(row)
        f["timeline"] = tl
        deaths = []
        dmap = {}
        for d in R["deaths"]:
            if d["p"] in self.bot_of:
                dmap.setdefault(d["p"], d)
        for b, pl in sorted(self.sq.items(), key=lambda x: (self.alive_until(x[1]), x[1])):
            ex = self.exit.get(b, {})
            d = dmap.get(pl)
            peak_t, peak_v = 0, 0
            for i, t in enumerate(self.T):
                v = R["snapTerr"][i][pl]
                if v > peak_v:
                    peak_v, peak_t = v, t
            row = {"bot": b, "event": ex.get("event"), "localTick": ex.get("tick"), "lastLogTick": int(self.traj[b][-1]["t"]) if self.traj.get(b) else None, "leftServerTick": self.left[pl] if self.left[pl] >= 0 else None, "deathServerTick": self.death[pl] if self.death[pl] >= 0 else None, "peakTerr": peak_v, "peakTick": peak_t}
            if d:
                lo = max(0, d["t"] - 500)
                ld = self.ledger(pl, lo, d["t"] + 1)
                row.update({"terrAtDeath": d["terr"], "balAtDeath": d["bal"], "attackersAtDeath": [{"who": self.nm(a, d["t"]), "troops": tr} for a, tr in sorted(d["attackers"], key=lambda x: -x[1])[:4]],
                            "last500": {"terr0": ld["terr0"], "bal0": ld["bal0"], "tilesLost": sum(x[0] for x in ld["lost"].values()), "balLostDefending": int(ld["def_bal"]), "lostTo": [{"who": self.nm(q, lo), "tiles": x[0], "bal": int(x[1])} for q, x in sorted(ld["lost"].items(), key=lambda x: -(2 * x[1][0] + x[1][1]))[:3]],
                                        "donatedOut": int(ld["don_out"][0]), "donationTax": int(ld["don_out"][1]), "received": int(ld["don_in"] + ld["boat_in"]), "attackSent": int(sum(v[0] for v in ld["sent"].values()))}})
            deaths.append(row)
        f["deaths"] = deaths
        f["drops"] = getattr(self, "drops", [])
        f["drop30CountCard"] = getattr(self, "drop_count_card", None)
        f["donations"] = getattr(self, "don_stats", {})
        f["dumpBatches"] = [b for b in getattr(self, "batches", []) if b["dump"]]
        f["squadLedger"] = getattr(self, "squad_ledger", None)
        f["boatHandovers"] = getattr(self, "boat_handovers", [])
        f["donationNetwork"] = getattr(self, "donnet", None)
        f["teamFall"] = getattr(self, "teamfall", None)
        f["interest"] = getattr(self, "interest", None)
        return f

    def run(self, map_ticks=(), ledger_step=300):
        self.sec_header()
        self.sec_teams()
        end = self.R["endTick"]
        self.sec_top([t for t in (630, 1530, 2400, 3300, 4500, 6000, 8100) if t < end] + [end])
        self.sec_roster()
        self.sec_ledger(ledger_step)
        self.sec_pairs()
        self.sec_deaths()
        self.sec_donations()
        self.sec_drops()
        self.sec_batches()
        self.sec_opponents()
        self.sec_total()
        self.sec_donnet()
        self.sec_teamfall()
        self.sec_interest()
        self.sec_map(map_ticks)
        return "\n".join(self.out) + "\n"


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    mid = args[0]
    maps = []
    if "--map" in args:
        maps = [int(x) for x in args[args.index("--map") + 1].split(",")]
    step = int(args[args.index("--step") + 1]) if "--step" in args else 300
    d = Dossier(mid)
    if "--tl" in args:
        d.extra_tl = [int(x) for x in args[args.index("--tl") + 1].split(",")]
    text = d.run(maps, step)
    os.makedirs(OUTDIR, exist_ok=True)
    open(os.path.join(OUTDIR, f"{mid}.txt"), "w").write(text)
    json.dump(d.facts(), open(os.path.join(OUTDIR, f"{mid}-facts.json"), "w"), ensure_ascii=False, indent=1)
    if "--quiet" not in args:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
