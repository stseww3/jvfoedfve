# 逐局精细复盘规程（v1）

> 适用：R07、R08、R09 从第一轮起；R03~R06 交完代码地图后加入。
> 目标：每局产出一份**细到拍、细到代码行、又能跨局汇总**的复盘。

## 0. 管理员的要求（原话）

> 「基本上要一局一局复盘 非常细的 跑满ai思考 大概分析12小时左右的量和深度」
> 「注意出方案是非常后期的事情 要分析清楚」
> 「对游戏代码理解也要nextlevel」

## 1. 原则

1. **复盘的对象是决策，不是结局。** 一局只有一个胜负，却有上千个决策。输了不代表每个决策都错，赢了不代表都对。逐个决策看它在当时的局面下好不好。
2. **本阶段只回答三件事：发生了什么、为什么、值多少。** 不提参数改动，不写补丁。看到「改成多少就好了」的念头，记到 `unknowns` 里，不展开。
3. **三种陈述分开写。** 观察：日志或全量真相里直接看得到的。推断：由引擎机制或代码推出来的，写明依据。猜测：没有依据的，标「待验证」。
4. **数字出自脚本。** 脚本放 `scripts/`，输出放 `out/`，复盘里引用路径。
5. **做对的也要记。** 新版不能把有效的东西改坏。
6. **解释不了就写「不知道」**，并写明查过什么。
7. **独立。** 写完自己的复盘之前，不看别人对同一局的复盘，也不看上一轮 S01~S10 对这一局的结论。

## 2. 输入：对局包

由 R01 发布（位置见 c136 的广播）。每局一个目录：

| 文件 | 内容 |
| :-- | :-- |
| `card.json` | 对局卡：对局编号、时间、小队、人数、策略版本、游戏版本、地图、队伍数、真人数、我方队伍、结果、数据完整度、污染标记 |
| `results.jsonl` | 我方每个号的结算记录 |
| `squad.log` | 这一局的小队日志切片（出生分配、开局检查、每 90 拍的状态快照、捐款 / 协防 / 拦截 / 调度事件、结算） |
| `traj.csv` | 从日志抽出的逐号轨迹：拍、领土、兵力、密度、邻居数等 |
| `truth/`（有录像才有，R02 发布） | 用引擎重放得到的全场数据：所有玩家和队伍的领土、兵力、出兵、阵亡 |

没有 `truth/` 的局照样复盘，但涉及对手的结论只能写成推断，并在 `context.dataCompleteness` 里如实标注。

对应的源码版本在 `card.json` 里；代码地图由 R05、R06 发布，引擎机制由 R03、R04 发布。它们还没发布时，直接读源码。

## 3. 步骤

1. **核对身份。** 读 `card.json`，确认小队、版本、队伍数、我方队伍、数据完整度。有污染标记（同房互打、掉线、不满编）的局照做，但在结论里单独说明影响。
2. **画全局时间线。** t≈180、600、1500、3000、4500、终局，以及中间每隔约 300~600 拍：我方存活人数、团队领土份额与排名、团队总兵力；有 `truth/` 时加上前两名对手队伍的份额。
3. **分阶段评估。** 出生与开局（t<600）、扩张（600~1500）、中盘（1500~4500）、终局（4500 以后）。每个阶段列事实和问题，不打总分。
4. **找转折点。** 我方份额或排名掉得最多的 1~3 个窗口；赢的局找拉开差距的窗口。每个窗口写：前后份额、涉及的我方号和对手、窗口**之前**我方做了哪些决策。
5. **死因链。** 我方每个阵亡的号：哪一拍、被谁打、死前 500 拍的密度变化、最后几个决策。
6. **决策审计。** 从转折点和死因链往回追，列出具体的决策实例：拍、号、动作、当时的局面、产生它的代码路径（文件 + 函数 + 触发条件）、判断（错 / 对 / 说不清）和理由、估计代价。
7. **大额出兵对账。** 任何一个号在 100 拍内兵力减少 30% 以上，都要说明兵去了哪里（进攻、捐款、船、被打）。
8. **对手和赢家。** 赢的是谁，它什么时候、用多大的兵力比打的我们；它的成长曲线和我们差在哪。
9. **归类。** 给输局选一个分型（见 §4 的 `lossArchetype`）；给每个决策实例打模式编号（见 §6）。
10. **写未解现象和机制疑问。**

## 4. 输出

放在自己的目录下：

```
c136-review/agents/RNN/reviews/<对局编号>.json    结构化结果（汇总用）
c136-review/agents/RNN/reviews/<对局编号>.md      叙述版，不超过 150 行
c136-review/agents/RNN/scripts/…                  用到的脚本
c136-review/agents/RNN/out/<对局编号>/…           脚本输出
```

JSON 结构：

```json
{
  "matchId": "对局编号（用 card.json 里的）",
  "reviewer": "R07",
  "protocol": "v1",
  "context": {
    "time": "", "squad": "c116|c110|nope8", "bots": 10,
    "strategyVersion": "文件哈希或 unknown", "gameVersion": "",
    "map": "", "mapLand": 0, "teams": 0, "humans": 0, "ourTeam": 0,
    "dataCompleteness": { "results": true, "squadLog": true, "truth": false },
    "contamination": []
  },
  "outcome": {
    "result": "won|lost|over", "ourTeamRank": 0, "winnerTeam": 0,
    "endTick": 0, "ourFinalShare": 0.0
  },
  "timeline": [
    { "t": 600, "alive": 10, "teamLandShare": 0.0, "teamRank": 0,
      "teamTroops": 0, "topEnemyTeam": 0, "topEnemyShare": 0.0 }
  ],
  "phases": {
    "opening":   { "facts": [], "issues": [] },
    "expansion": { "facts": [], "issues": [] },
    "midgame":   { "facts": [], "issues": [] },
    "endgame":   { "facts": [], "issues": [] }
  },
  "turningPoints": [
    { "t0": 0, "t1": 0, "what": "", "shareBefore": 0.0, "shareAfter": 0.0,
      "ourBots": [], "enemies": [], "evidence": ["日志原句或 truth 引用"],
      "priorDecisions": [ { "t": 0, "bot": "", "action": "", "logRef": "", "codePath": "" } ],
      "alternatives": "当时还有哪些可行动作，各自大概的后果",
      "statementType": "observed|inferred|guess", "confidence": "high|medium|low" }
  ],
  "deaths": [
    { "bot": "", "t": 0, "killers": [], "densityLast500": [], "lastDecisions": [],
      "cause": "", "patternIds": [] }
  ],
  "decisions": [
    { "t": 0, "bot": "", "kind": "spawn|expand|attack|keep|donate|assist|boat|idle|other",
      "verdict": "error|good|unclear", "state": "当时局面的关键数字",
      "codePath": "文件:函数:条件", "why": "", "estCost": "兵力、领土或份额",
      "patternId": "模式编号或 NEW", "evidenceRef": "" }
  ],
  "newPatterns": [
    { "name": "", "definition": "精确到可以写成检测脚本", "detectionSketch": "",
      "instances": [ { "t": 0, "bot": "" } ] }
  ],
  "lossArchetype": "early-wipe|never-grew|mid-collapse|lead-thrown|outscaled|external|win",
  "winnerNotes": "",
  "wentWell": [],
  "unknowns": [],
  "mechanicsQuestions": [],
  "scripts": ["路径@提交号"],
  "confidenceOverall": "high|medium|low"
}
```

`lossArchetype` 的含义：

| 值 | 含义 |
| :-- | :-- |
| `early-wipe` | t<1500 就减员过半或被打出局 |
| `never-grew` | 活着，但团队份额始终没进过前两名 |
| `mid-collapse` | 中盘份额尚可，随后在一个较短的窗口里崩掉 |
| `lead-thrown` | 团队份额曾排第一，最后没赢 |
| `outscaled` | 没有明显失误窗口，被体量更大的队慢慢压过 |
| `external` | 主要由外部因素决定：同房互打、掉线、不满编 |
| `win` | 赢了 |

## 5. 深度验收清单

复盘交上来之前自查，R10 抽查：

- [ ] 时间线不少于 8 个点，含 t≈180 / 600 / 1500 / 3000（打到了的话）和终局
- [ ] 每个阵亡的号都有死因链，或者写明「不知道」及查过什么
- [ ] 输局至少 1 个转折点，每个转折点至少 3 条日志或真相引用，窗口前的决策追到了代码路径
- [ ] 决策实例不少于 10 条，其中至少 2 条是「对」的
- [ ] 所有 100 拍内兵力减少 30% 以上的事件都对上了账
- [ ] 写了赢家是谁、怎么赢的
- [ ] 每条陈述标了观察 / 推断 / 猜测
- [ ] 所有数字能由 `scripts/` 重算
- [ ] 没有任何参数改动建议

## 6. 模式目录

- 目录在联络分支 `c136-review/ledger/PATTERNS.md`，由 c136 维护。
- 复盘时给每个决策实例打一个已有的模式编号；没有合适的就写 `NEW`，并在 `newPatterns` 里给出**能写成检测脚本的定义**。
- c136 合并去重后分配编号并广播。之后由检测脚本在**全部对局**上机械计数，得到每个模式的出现频率和代价。**单局里看到的东西，在计数之前都只是个例。**
- 编号前缀：`SP` 出生与阵型 ｜ `OP` 开局扩张 ｜ `EC` 经济与密度 ｜ `DN` 捐款与后勤 ｜ `AT` 进攻选择 ｜ `DF` 防守与留守 ｜ `SE` 海与船 ｜ `MT` 多队博弈与目标 ｜ `EG` 终局与收口 ｜ `IO` 执行（延迟、指令被拒）｜ `EX` 外部因素。

## 7. 双审与质检

- 约 15% 的局由两名复盘员各自独立复盘，c136 不告知是哪些局。R10 比对两份结果在分型、最大转折点、首要模式上的一致程度。
- R10 每轮抽查若干份复盘：从原始数据重算其中的数字，核对代码路径是否真的对应那条日志。
- 两名复盘员结论不一致的局，c136 指派第三人只看分歧点。
