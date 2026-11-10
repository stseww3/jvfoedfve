with open("v27-team-live.js", "r", encoding="utf-8") as f:
    s = f.read()

old_hook = """    const ensureLobbyHook = () => {
      const sH = window.bq?.sH;
      if (!sH || typeof sH.select !== "function") return;
      if (!sH.__origSelect) {
        sH.__origSelect = sH.select.bind(sH);
        sH.select = function(id) {
          if (id > 0) {
            if (!isBossReadyInLobby()) {
              if (this.wF > 0) return this.__origSelect(0);
              return;
            }
            const firstId = this.sH?.[0]?.id || id;
            if (this.wF === firstId) return;
            return this.__origSelect(firstId);
          }
          if (this.wF > 0) return this.__origSelect(0);
        };
      }
      if (window.bq?.f6 !== 1) return;
      const bossReady = isBossReadyInLobby();"""

new_hook = """    const ensureLobbyHook = () => {
      window.__tsbFollowLeader = "kazerd183";
      window.__tsbWaitForLeader = true;
      const lobMenu = window.u?.a8B?.(29);
      if (lobMenu && !lobMenu.__patchedA5C) {
        lobMenu.__patchedA5C = true;
        lobMenu.a5C = function(ej) {
          if (ej === 2) {
            if (window.bq?.sH?.wF > 0) window.bq.sH.select(0);
            return;
          }
          if (ej < 2 && isBossReadyInLobby()) {
            window.bq?.sH?.click?.(0);
          }
        };
      }
      if (window.bq?.f6 !== 1) {
        const gState = window.aE ? (window.aE.a38 | 0) : 0;
        const mState = window.ab?.a4H ? (window.ab.a4H() | 0) : 0;
        if (gState === 0 && mState !== 6 && mState !== 8 && mState !== 10 && window.u?.z?.a7v) {
          const nowMs = Date.now();
          const slot = window.__tsbSquadSlot | 0;
          if (!window.__lastAutoEnterLobbyAt || nowMs - window.__lastAutoEnterLobbyAt > 6000 + slot * 180) {
            window.__lastAutoEnterLobbyAt = nowMs;
            try {
              if (window.b1?.z && !window.b1.z.ef?.(0) && typeof window.b1.z.aJc === "function") {
                window.b1.z.aJc(0, 0, 0);
              }
              if (window.b1?.z) window.b1.z.f7 = 1;
              if (window.bm?.buffer?.data) {
                if (window.__tsbPlayerName) window.bm.buffer.data[122].value = window.__tsbPlayerName;
                window.bm.buffer.data[121].value = 4095;
                window.bm.buffer.data[158].value = 0;
              }
              window.u.z.a7v(1);
            } catch {}
          }
        }
        return;
      }
      const sH = window.bq?.sH;
      if (!sH || typeof sH.select !== "function") return;
      if (!sH.__origSelect) {
        sH.__origSelect = sH.select.bind(sH);
        sH.select = function(id) {
          if (id > 0) {
            if (!isBossReadyInLobby()) {
              if (this.wF > 0) return this.__origSelect(0);
              return;
            }
            const firstId = this.sH?.[0]?.id || id;
            if (this.wF === firstId) return;
            return this.__origSelect(firstId);
          }
          if (this.wF > 0) return this.__origSelect(0);
        };
      }
      const bossReady = isBossReadyInLobby();"""

assert old_hook in s, "old_hook not found"
s = s.replace(old_hook, new_hook, 1)

with open("v27-team-live.js", "w", encoding="utf-8") as f:
    f.write(s)

print("Successfully patched lobby hook on d3! Size:", len(s))
