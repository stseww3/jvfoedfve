with open("v27-team-live.js", "r", encoding="utf-8") as f:
    s = f.read()

old_emoji = """      const d = window.dictionary;
      const bBCmd = (d && window[d.sbCommands]) || window.bB;
      const b1Net = (d && window[d.sbNet]) || window.b1;
      if (bBCmd?.gv && typeof bBCmd.gv.rJ === "function") {
        bBCmd.gv.rJ(1015, bossId);
      } else if (b1Net?.qo && typeof b1Net.qo.rK === "function") {
        b1Net.qo.rK(1015, bossId);
      }
    } catch {}"""

new_emoji = """      const d = window.dictionary;
      const b1Net = (d && window[d.sbNet]) || window.b1;
      if (b1Net?.qo && typeof b1Net.qo.rK === "function") {
        b1Net.qo.rK(1015, bossId);
        if (slot === 0 && window.__hlLog) {
          window.__hlLog(`[HL-EMOJI] t=${g.t} sent private scales emoji (1015) -> boss=${bossId}(${g.names?.[bossId] || ""})`);
        }
      }
    } catch (e) {
      if (slot === 0 && window.__hlLog) {
        window.__hlLog(`[HL-EMOJI-ERR] ${e?.message || e}`);
      }
    }"""

assert old_emoji in s, "old_emoji not found"
s = s.replace(old_emoji, new_emoji, 1)

old_style_pick = """      const need = this.elimCost(g, q) + g.attackTroopsOn(q, me) - g.attackTroopsOn(me, q);
      if (need <= 0) continue;"""
new_style_pick = """      const need = this.elimCost(g, q) + g.attackTroopsOn(q, me) - g.attackTroopsOn(me, q);
      if (need <= 0) continue;
      if (!this.person(g, q) && g.hasAttack(me, q) && (!g.hasAttack(q, me) || g.attackTroopsOn(me, q) >= 0.35 * need)) continue;"""
if new_style_pick not in s:
    assert old_style_pick in s, "old_style_pick not found"
    s = s.replace(old_style_pick, new_style_pick, 1)

old_v17_buy = """      const want = 1.25 * need + 3 * this.cnt[q];
      const x = Math.min(B - fee - keep, want);
      if (x <= 0 || (x < want && (x < P.chunk * B || (P.pplKill > 0 && person)))) continue;"""
new_v17_buy = """      if (!person && g.hasAttack(me, q) && (!g.hasAttack(q, me) || g.attackTroopsOn(me, q) >= 0.35 * need)) continue;
      const want = 1.25 * need + 3 * this.cnt[q];
      const x = Math.min(B - fee - keep, want);
      if (x < this.minCmd(g) || (x < want && (x < P.chunk * B || (P.pplKill > 0 && person)))) continue;"""
if new_v17_buy not in s:
    assert old_v17_buy in s, "old_v17_buy not found"
    s = s.replace(old_v17_buy, new_v17_buy, 1)

old_gen_send = """  send(g, target, troops) {
    const bal = g.bal[this.me];
    if (bal <= 0 || troops <= 0) return false;"""
new_gen_send = """  send(g, target, troops) {
    const bal = g.bal[this.me];
    if (bal <= 0 || troops <= 0) return false;
    if (g.online && target !== NEUTRAL) {
      if (!this._lastTargetSendTick) this._lastTargetSendTick = new Map();
      if (g.t - (this._lastTargetSendTick.get(target) ?? -999) < 15) return false;
      this._lastTargetSendTick.set(target, g.t);
    }"""
if new_gen_send not in s:
    assert old_gen_send in s, "old_gen_send not found"
    s = s.replace(old_gen_send, new_gen_send, 1)

with open("v27-team-live.js", "w", encoding="utf-8") as f:
    f.write(s)

print("Successfully patched v27-team-live.js on d3! Size:", len(s))
