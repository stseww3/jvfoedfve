with open("headless-bot.mjs", "r", encoding="utf-8") as f:
    hb = f.read()

hb = hb.replace(
    "while(this.ae7.length>0&&this.ae5<this.aIt*7&&aE.a2G!==2){n8()}if(this.ae7.length===0){return}",
    "while(this.ae7.length>0&&this.ae5<this.aIt*7&&aE.a2G===1&&bi.a3I===this){n8()}if(this.ae7.length===0||aE.a2G!==1||bi.a3I!==this){return}"
).replace(
    "while(this.af3.length>0&&this.af1<this.aK3*7&&aE.a38!==2){n8()}if(this.af3.length===0){return}",
    "while(this.af3.length>0&&this.af1<this.aK3*7&&aE.a38===1&&bi.a3I===this){n8()}if(this.af3.length===0||aE.a38!==1||bi.a3I!==this){return}\n    )\n    .replace(\n      'if(aE.a38===2){break}if(this.af3.length>0){for(aC=this.af4-2;aC>=0;aC--){n8();if(aE.a38===2){break loop}}}',\n      'if(aE.a38!==1||bi.a3I!==this){break}if(this.af3.length>0){for(aC=this.af4-2;aC>=0;aC--){n8();if(aE.a38!==1||bi.a3I!==this){break loop}}}'"
).replace(
    "while(bi.eZ>=this.eZ&&_steps++<35){this.eZ+=42;if(aE.a38===2){n6();break}this.af6();if(this.af1===this.aK3*7&&this.af3.length===0){this.eZ=bi.eZ;break}}",
    "while(bi.eZ>=this.eZ&&_steps++<35&&bi.a3I===this){this.eZ+=42;if(aE.a38!==1){if(aE.a38===2)n6();break}this.af6();if(aE.a38!==1||bi.a3I!==this||(this.af1===this.aK3*7&&this.af3.length===0)){this.eZ=bi.eZ;break}}"
)

old_raf = """  const rafs = [];
  setInterval(() => {
    const batch = rafs.splice(0, rafs.length);
    const now = performance.now();
    for (const fn of batch) {
      try { fn(now); } catch {}
    }
  }, 16);"""

new_raf = """  const rafs = [];
  let lastIdleRafAt = 0;
  setInterval(() => {
    const now = performance.now();
    const inGameNow = typeof sandbox === 'object' && sandbox.aE && sandbox.aE.a38 === 1;
    if (!inGameNow && now - lastIdleRafAt < 115) return;
    lastIdleRafAt = now;
    const batch = rafs.splice(0, rafs.length);
    for (const fn of batch) {
      try { fn(now); } catch {}
    }
  }, 16);"""

if old_raf in hb:
    hb = hb.replace(old_raf, new_raf, 1)

with open("headless-bot.mjs", "w", encoding="utf-8") as f:
    f.write(hb)

print("Updated headless-bot.mjs on d3! Size:", len(hb))
