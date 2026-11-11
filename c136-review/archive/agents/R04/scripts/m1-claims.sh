#!/usr/bin/env bash
# m1-claims.sh — M1《已知机制清单》里引用的每个常数 / 规则，在模拟器源码和旧工具里的出处行。
# 用法：bash c136-review/agents/R04/scripts/prep.sh && bash c136-review/agents/R04/scripts/m1-claims.sh > c136-review/agents/R04/out/m1-claims.txt
# 输入：/tmp/c136-r04/c117/territorial-sim/sim（fdvg cursor/c117-sim-teams-96f2 @97124c5c）
#       /tmp/c136-r04/c58/territorial-sim（fdvg cursor/c58-v24-95b7 @2d3bbd36）
set -u
S=/tmp/c136-r04/c117/territorial-sim/sim
C58=/tmp/c136-r04/c58/territorial-sim
FDVG="${FDVG:-/agent/repos/fdvg}"
C58SHA=2d3bbd365638421fe43ed9e6aee415d8aba8334f

show() { # show <标签> <文件> <正则>
  echo "## $1"
  timeout 30 grep -nE "$3" "$2" | sed -E 's/^([0-9]+):\s*/  L\1: /' | cut -c1-230
  echo
}

echo "# M1 引用核对（模拟器 c117 版 sim/，行号针对 97124c5c）"
echo
show "A1 组队局判定注释 / teams 数组"            $S/game.js  'Team games \(live|this\.teams = new|this\.donCap = 15'
show "A2 AI 轮流入队"                            $S/game.js  'teams\[p\] = 1 \+ \(p % this\.nTeams\)'
show "A3 isEnemy / isEnemyOf / isTeammate"       $S/game.js  'return this\.teams\[p\] === 0 \|\||return p !== q && \(this\.teams|return p !== q && this\.teams'
show "A4 不能陆攻队友"                           $S/game.js  'no land attack on a teammate|!this\.isEnemy\(p, target\)\) return false'
show "A5 边界判定 hostileTo（队友像素也算）"     $S/game.js  'return v === T_LAND \|\| \(v >= P_INNER && this\.own\[p\] !== player\)'
show "A7 领先队 / 存活队数"                      $S/game.js  'leadingTeam\(\) \{|teamsAlive\(\) \{|teamMembers\(team\) \{'
show "B1 捐款手续费 64/1024"                     $S/game.js  'iV\(64 \* B, 1024\)'
show "B2 接收方余量 150x / 1.5e9"                $S/game.js  'this\.terr\[q\] \* 150 - b|1\.5e9 - b'
show "B3 配额成本分段"                           $S/game.js  't >= 3213|t < 357|t < 714|t < 1071\) return|t < 2142\) return|100 \* uw'
show "B3 配额上限增长"                           $S/game.js  'this\.donCap \+= '
show "B3 免配额条件"                             $S/game.js  'this\.t >= 4284 \|\| this\.isBot\(q\)'
show "B7 船到队友岸边交兵"                       $S/boats.js 'hands its|receiverRoom\(target, troops\)'
show "B8 AI 捐款"                                $S/bots.js  'botDonate\(p, dn, diff, cap\) \{|if \(p < this\.humans\) dn = B|diff === 5 && B < cap|this\.recentWar\[q\]\) return this\.botGive|this\.boatCount\[q\] && q !== p'
show "C1 发船手续费 32/1024、最少 60 兵"          $S/boats.js 'this\.quote\(p, pct, 32\)|if \(troops < 60\)'
show "C1 陆攻手续费 12/1024"                     $S/game.js  'this\.quote\(p, pct, 12\)|iV\(12 \* this\.bal\[p\], 1024\)'
show "C2 船数上限"                               $S/boats.js 'const MAX_BOATS|const PLAYER_BOATS|const MAX_ROUTES'
show "C3 航速"                                   $S/boats.js 'const speed = '
show "C4 海上损耗"                               $S/boats.js 'this\.t % 5 === 3|Math\.max\(1, v >> 7\)'
show "C5 船战"                                   $S/boats.js 'const FIGHT_RANGE2|this\.t % 2 === 1|const dmg = '
show "C6 登陆"                                   $S/boats.js 'landAt\(p, troops, c, at\) \{|this\.hasAttack\(p, target\) \|\| this\.hasFreeSlot\(p\)'
show "C7 召回"                                   $S/boats.js 'if \(type % 64 === 5\) return false'
show "C8 追船"                                   $S/boats.js 'if \(pct === 849\) pct = 850|limit && 120 < dist'
show "C9 进攻槽"                                 $S/game.js  'this\.slotsHuman = |this\.slotsBot = '
show "D1 难度表 / 初始兵"                        $S/game.js  'BOT_START_BALANCE = |HUMAN_START_BALANCE = |timerSpeed:|boatPct:|weakestPct:|boatLimit:|interceptPermille:'
show "D2 AI 决策节拍"                            $S/bots.js  'this\.botTimer\[p\] = iV\(this\.botPeriod\[p\], 10\)|this\.botAttack\(p, iV\(this\.botPct\[p\] \* this\.bal\[p\], 1e3\)\)'
show "D3 AI 选目标"                              $S/bots.js  'botAttackTeam\(p, dn, diff, cap\) \{|rng\.chance\(DIFFICULTY\.weakestPct\[diff\]\)|this\.anyBotTarget\(\) && rng\.chance'
show "D4 AI 组队局：陆攻 > 船 > 山 > 捐"          $S/bots.js  'if \(this\.botBoat\(p\)\) return;|if \(this\.botMountain\(p\)\) return;|this\.botDonate\(p, dn, diff, cap\);'
show "D6 离开的真人按难度 6 运行"                $S/game.js  'difficulty 6: a send every 80 ticks|leave\(p\) \{|this\.state\[p\] = 2'
show "D7 AI 拦船"                                $S/bots.js  'this\.t % 51 !== 45|return len <= 60'
show "D9 领先队占 80% 后的追猎"                  $S/game.js  'this\.t % 109 !== 9|iV\(8 \* this\.land, 10\)'
show "E1 出生格"                                 $S/game.js  'const SPAWN_CELL|const SPAWN_BLOCK'
show "E2 出生形状（4x4 去四角）"                 $S/game.js  'if \(!\(\(fb < x && x < fb \+ 3\) \|\| \(fc < y && y < fc \+ 3\)\)\) continue'
show "E3 选点：点击处向外最多 20 圈"             $S/game.js  'for \(let r = 0; r < 20; r\+\+\)'
show "F1 胜利判定"                               $S/game.js  'if \(this\.leaderLand < this\.land\) return|if \(this\.enemyBoatsOf\(this\.rank\[0\]\) > 0\) return|this\.winnerTeam = '
show "F2 淘汰：领土 <= 峰值/4"                   $S/game.js  'if \(bx <= iV\(jP, 4\)\) this\.collapse\(p\)|this\.peak\[p\] = jP - Math\.max\(1, iV\(jP - bx, 1e3\)\)'

echo "# 录像解码器（fdvg c58 tools/c102-replay-lib.mjs @2d3bbd36）"
echo
timeout 30 git -C "$FDVG" show "$C58SHA:territorial-sim/tools/c102-replay-lib.mjs" > /tmp/c136-r04/c102-replay-lib.mjs
show "G1 头部字段"                               /tmp/c136-r04/c102-replay-lib.mjs 'numberTeams|teamPlayerCount|botDifficultyTeam|i2\(12\); i2\(12\); i2\(31\)'
show "G2 指令编码"                               /tmp/c136-r04/c102-replay-lib.mjs 'const id = i2\(4\), player = i2\(9\)|if \(id === 0\) dX = i2|else if \(id === [0-9]+\)|id === 5 \|\| id === 6'
show "G3 出生阶段帧数"                           /tmp/c136-r04/c102-replay-lib.mjs 'const jJ = '
show "G4 旧工具里多人局 AI 难度的假设"           /tmp/c136-r04/c102-replay-lib.mjs 'difficulty: H > 1 \? 0'

echo "# 海洋笔记 / c6 笔记"
echo
show "N1 船手续费、船战距离的旧说法"             $C58/NOTES-c22-ocean.md '32/1024|7\.5 像素|每 5 tick|最多 8 艘'
show "N2 单人局逐拍吻合的旧说法"                 $C58/NOTES-c6.md 'tick for tick'
