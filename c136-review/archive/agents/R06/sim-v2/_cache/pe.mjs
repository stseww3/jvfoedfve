import { loadMatch } from '../lib/match.mjs';
const M = loadMatch(process.argv[2]);
console.log('squad', M.squad.join(','));
console.log('pageEnd', JSON.stringify([...M.pageEnd]));
console.log('leaveT', JSON.stringify([...M.leaveT]));
console.log('lastCmd', JSON.stringify([...M.lastCmd].filter(([p]) => M.squad.includes(p))));
console.log('doomed', JSON.stringify([...M.doomed]), 'deathT', JSON.stringify(M.deathT));
console.log('names', M.squad.map((p) => p + ':' + M.names[p]).join(' '));
