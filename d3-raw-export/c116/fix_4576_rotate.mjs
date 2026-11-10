import fs from 'node:fs';

let hb = fs.readFileSync('headless-bot.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldErrBlock = `      if (msg.text.includes('error 4591') || msg.text.includes('error 4215') || msg.text.includes('error 4577') || msg.text.includes('error 4229')) {
        client.freshToken = false;
        client.enteredLobbyAt = 0;
        if (msg.text.includes('error 4577')) {`;

const newErrBlock = `      if (msg.text.includes('error 4591') || msg.text.includes('error 4215') || msg.text.includes('error 4577') || msg.text.includes('error 4576') || msg.text.includes('error 4229')) {
        client.freshToken = false;
        client.enteredLobbyAt = 0;
        if (msg.text.includes('error 4577') || msg.text.includes('error 4576')) {
          if (socksPort) {
            const s = net.connect(socksPort, '127.0.0.1');
            let stg = 0, b = Buffer.alloc(0);
            s.on('error', () => {});
            s.on('connect', () => s.write(Buffer.from([0x05, 0x01, 0x00])));
            s.on('data', (c) => {
              b = Buffer.concat([b, c]);
              if (stg === 0 && b.length >= 2) {
                stg = 1;
                const hb = Buffer.from('rotate.proxy.local', 'utf8');
                const req = Buffer.alloc(4 + 1 + hb.length + 2);
                req[0] = 0x05; req[1] = 0x01; req[2] = 0x00; req[3] = 0x03;
                req[4] = hb.length; hb.copy(req, 5); req.writeUInt16BE(80, 5 + hb.length);
                s.write(req);
              } else if (stg === 1 && b.length >= 10) {
                try { s.destroy(); } catch {}
              }
            });
          }
        }
        if (msg.text.includes('error 4577')) {`;

if (!hb.includes(oldErrBlock)) {
  console.error('Could not find oldErrBlock in headless-bot.mjs!');
  process.exit(1);
}
hb = hb.replace(oldErrBlock, newErrBlock);
fs.writeFileSync('headless-bot.mjs', hb, 'utf8');
console.log('Successfully added error 4576 / 4577 automatic SOCKS5 session rotation to headless-bot.mjs!');
