import fs from 'node:fs';

let code = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const old4577 = `      if (s.lobby.stopped.includes('4591') || s.lobby.stopped.includes('4577') || s.lobby.stopped.includes('4215') || s.lobby.stopped.includes('1006')) {
        clients[idx].freshToken = false;
        clients[idx].enteredLobbyAt = 0;
      }`;

const new4577 = `      if (s.lobby.stopped.includes('4591') || s.lobby.stopped.includes('4577') || s.lobby.stopped.includes('4215') || s.lobby.stopped.includes('1006')) {
        clients[idx].freshToken = false;
        clients[idx].enteredLobbyAt = 0;
        if (s.lobby.stopped.includes('4577')) {
          rotateSocksSession(clients[idx].socksPort);
        }
      }`;

if (code.includes(old4577)) {
  code = code.replace(old4577, new4577);
  console.log('Added auto-rotateSocksSession on 4577 in tsb-apex-squad.mjs!');
}

// Also rotate when worker console logs "error 4577"
const oldConsole = `    if (msg.type === 'console') {
      console.log(\`[\${this.name}] \${msg.text}\`);
      return;
    }`;

const newConsole = `    if (msg.type === 'console') {
      console.log(\`[\${this.name}] \${msg.text}\`);
      if (typeof msg.text === 'string' && msg.text.includes('error 4577')) {
        rotateSocksSession(this.socksPort);
        this.freshToken = false;
        this.enteredLobbyAt = 0;
      }
      return;
    }`;

if (code.includes(oldConsole)) {
  code = code.replace(oldConsole, newConsole);
  console.log('Added worker console error 4577 auto-rotateSocksSession!');
}

fs.writeFileSync('tsb-apex-squad.mjs', code, 'utf8');
