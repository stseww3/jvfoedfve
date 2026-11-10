import fs from 'node:fs';

let code = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldReady = `  const allReadyInRoom0 =
    !avoidC110Collision &&
    timerSpreadOk &&
    minStartsIn >= 5 &&
    (headlessOnly
      ? (headlessInRoom0 === HEADLESS_BOTS.length || (headlessInRoom0 >= HEADLESS_BOTS.length - 1 && minStartsIn >= 5 && minStartsIn <= 14))
      : wantTenForCurrentLobby
        ? (readyCountInRoom0 === 10 || (readyCountInRoom0 >= 9 && minStartsIn >= 5 && minStartsIn <= 12))
        : (chromeInRoom0 === 5 || (chromeInRoom0 >= 4 && minStartsIn <= 8)));`;

const newReady = `  const allReadyInRoom0 =
    !avoidC110Collision &&
    timerSpreadOk &&
    (headlessOnly
      ? (headlessInRoom0 === HEADLESS_BOTS.length || (headlessInRoom0 >= HEADLESS_BOTS.length - 2 && minStartsIn <= 12))
      : wantTenForCurrentLobby
        ? (readyCountInRoom0 === 10 || (readyCountInRoom0 >= 8 && minStartsIn <= 8))
        : (chromeInRoom0 === 5 || (chromeInRoom0 >= 4 && minStartsIn <= 8)));`;

if (code.includes(oldReady)) {
  code = code.replace(oldReady, newReady);
  fs.writeFileSync('tsb-apex-squad.mjs', code, 'utf8');
  console.log('Restored allReadyInRoom0 (removed minStartsIn >= 5 bug)!');
}
