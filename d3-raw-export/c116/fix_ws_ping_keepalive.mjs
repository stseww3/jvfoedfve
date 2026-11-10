import fs from 'node:fs';

let hb = fs.readFileSync('headless-bot.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldUpgrade = `          upgraded = true;
          state = 1;
          emit('open');`;

const newUpgrade = `          upgraded = true;
          state = 1;
          try { tlsSock.setKeepAlive(true, 10000); } catch {}
          const pingTimer = setInterval(() => {
            if (state !== 1) { clearInterval(pingTimer); return; }
            try { sendFrame(0x09, Buffer.alloc(0)); } catch {}
          }, 12000);
          if (pingTimer.unref) pingTimer.unref();
          emit('open');`;

if (hb.includes(oldUpgrade)) {
  hb = hb.replace(oldUpgrade, newUpgrade);
  fs.writeFileSync('headless-bot.mjs', hb, 'utf8');
  console.log('Added 12s WebSocket Ping + TCP KeepAlive in headless-bot.mjs so GProxy never drops silent connections!');
}
