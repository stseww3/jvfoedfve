import fs from 'node:fs';

let code = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldReady = `  const allReadyInRoom0 =
    !avoidC110Collision &&
    timerSpreadOk &&
    (headlessOnly
      ? (headlessInRoom0 === HEADLESS_BOTS.length || (headlessInRoom0 >= HEADLESS_BOTS.length - 2 && minStartsIn <= 12))
      : wantTenForCurrentLobby
        ? (readyCountInRoom0 === 10 || (readyCountInRoom0 >= 8 && minStartsIn <= 8))
        : (chromeInRoom0 === 5 || (chromeInRoom0 >= 4 && minStartsIn <= 8)));`;

const newReady = `  const allReadyInRoom0 =
    !avoidC110Collision &&
    timerSpreadOk &&
    minStartsIn >= 5 &&
    (headlessOnly
      ? (headlessInRoom0 === HEADLESS_BOTS.length || (headlessInRoom0 >= HEADLESS_BOTS.length - 1 && minStartsIn >= 5 && minStartsIn <= 14))
      : wantTenForCurrentLobby
        ? (readyCountInRoom0 === 10 || (readyCountInRoom0 >= 9 && minStartsIn >= 5 && minStartsIn <= 12))
        : (chromeInRoom0 === 5 || (chromeInRoom0 >= 4 && minStartsIn <= 8)));`;

if (code.includes(oldReady)) {
  code = code.replace(oldReady, newReady);
  console.log('Fixed allReadyInRoom0: require minStartsIn >= 5 so squad never splits across countdown boundary!');
}

code = code.replace(
  'const delayMs = 450 + ((${c.slot} * 380) % 2400) + Math.floor(Math.random() * 850);',
  'const delayMs = 120 + ((${c.slot} * 140) % 900) + Math.floor(Math.random() * 250);'
);

fs.writeFileSync('tsb-apex-squad.mjs', code, 'utf8');
