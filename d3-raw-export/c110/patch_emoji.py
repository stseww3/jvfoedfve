with open("v27-team-live.js", "r", encoding="utf-8") as f:
    s = f.read()

emoji_fn = """  tryPrivateBossEmoji(g) {
    if (typeof window === "undefined" || !g.online) return;
    const me = this.me;
    if (!g.alive[me] || g.terr[me] <= 0) return;
    const slot = ((typeof window.__tsbSquadSlot === "number" ? window.__tsbSquadSlot : me) | 0) % 20;
    if (g.t < 25 + slot * 4) return;
    if (g.t - (this._lastBossEmojiTick ?? -999) < 180) return;
    let bossId = -1;
    for (let p = 0; p < g.humans; p++) {
      if (this.isBossNpl(g, p) && g.alive[p] && g.terr[p] > 0) {
        bossId = p;
        break;
      }
    }
    if (bossId < 0) return;
    this._lastBossEmojiTick = g.t;
    try {
      const d = window.dictionary;
      const bBCmd = (d && window[d.sbCommands]) || window.bB;
      const b1Net = (d && window[d.sbNet]) || window.b1;
      if (bBCmd?.gv && typeof bBCmd.gv.rJ === "function") {
        bBCmd.gv.rJ(1015, bossId);
      } else if (b1Net?.qo && typeof b1Net.qo.rK === "function") {
        b1Net.qo.rK(1015, bossId);
      }
    } catch {}
  }

  // AUTO PEACE VOTE CALL & ACCEPT:"""

if "tryPrivateBossEmoji" not in s:
    assert "  // AUTO PEACE VOTE CALL & ACCEPT:" in s
    s = s.replace("  // AUTO PEACE VOTE CALL & ACCEPT:", emoji_fn, 1)
    old_act = "    if (g.t < P.coreFrom) {\n      this.analyze(g);"
    new_act = "    this.tryPrivateBossEmoji(g);\n    if (g.t < P.coreFrom) {\n      this.analyze(g);"
    assert old_act in s
    s = s.replace(old_act, new_act, 1)
    with open("v27-team-live.js", "w", encoding="utf-8") as f:
        f.write(s)

print("Patched v27-team-live.js! Size:", len(s), "hasEmoji:", "tryPrivateBossEmoji" in s)
