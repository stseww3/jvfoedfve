---
from: R07
to: HUB
type: report
time: 2026-11-12T04:13:31Z
---

# v28 进度：指令出口、P8、P1 已提交；剩 P3/P4/P5/P6/P7/P2

还没到可审阅的程度，这条只是报进度并把已有提交推上来。写完六局自测和作者说明后再发 `v28-draft-ready`。

## 已提交（都在 `c136-review/agents/R07/` 下）

| 提交 | 内容 |
|---|---|
| `0acb7ab` | `v28/v28-team-organism.js` = Vc 原文，`v28/spawn-coordinator-v28.mjs` = c116 协调器原文 |
| `ad2e04d`、`b8d4649` | 自测工具 `scripts/v28_shadow.mjs`（影子重放 + 闭环接管）和 `scripts/v28_equiv.py`（指令流比对） |
| `23050c9` | 全部指令收拢到 7 个出口（`xAttack/xDonate/xBoatTo/xBoat/xRetreat/xChase/xRecall`），纯透传 |
| `be27b48` | P8，开关 `enableCollapseGuard` |
| `a552dd1` | P1，开关 `enableInflightLedger` |

每加一步都重跑一次「开关全关 ≡ Vc」：A070 全局影子指令 2241 条，逐条相同。

## P1 闭环小测（A070）

做法：t≥700 起屏蔽录像里我方 10 个号的指令，改由策略发令，指令经信道后才结算；对手照录像走。信道 C1 按圆桌 §二：延迟 10~18 拍后取整到 7 的倍数、每号 3 轮最多 9 条。跑到 t=2300。

「重复下单」= 同一个号对同一目标的上一条进攻还在信道里，又发了一条。

| 信道 | 开关 | 进攻条数 | 重复下单 | 期末地 | 期末兵 | 存活 |
|---|---|---|---|---|---|---|
| C0 | 全关 | 528 | 0 | 466,818 | 5,550,314 | 10 |
| C0 | 只开 P1 | 487 | 0 | 527,074 | 5,399,411 | 10 |
| C1 | 全关 | 567 | 314（55.4%） | 372,431 | 3,825,218 | 9 |
| C1 | 只开 P1 | 478 | 40（8.4%） | 468,950 | 5,068,965 | 10 |
| C1 + 卡顿（t 1200~1400 多延迟 150 拍） | 全关 | 740 | 493（66.6%） | 376,587 | 3,504,153 | 10 |
| C1 + 卡顿 | 只开 P1 | 469 | 92（19.6%） | 410,842 | 4,719,030 | 10 |

- C1 下全关的重复率 55.4%，和圆桌引用的实况数字 52% 接近，说明这个信道模型大体对路。
- P1 把重复率压到 8.4%，剩下 40 条全是打人机。这些是「需求大于在途量」的正常补单还是漏网，我还没逐条核，先不下结论。G2 门槛是 <8%，目前差一点。
- 卡顿段里 P1 仍有 19.6%：延迟 150 拍超过了账本的放弃时限（`p1DropAfter` = 84 拍），账本当作丢失后又补发。这是参数取舍，会写进作者说明。
- 这是机制核对，不是胜率证据：对手不会对我方的新动作做反应，地和兵的差距只能当方向参考。

## 复现

```
R="bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/v28_shadow.mjs"
$R A070 --label vc --src /agent/repos/c136-data/src/strategy/v27-team-c116.js
$R A070 --label off --modules none
python3 c136-review/agents/R07/scripts/v28_equiv.py A070 vc off
$R A070 --label tk_c1_none --modules none --takeover 700 --until 2300 --chan c1
$R A070 --label tk_c1_p1   --modules p1   --takeover 700 --until 2300 --chan c1
$R A070 --label tk_c1s_p1  --modules p1   --takeover 700 --until 2300 --chan c1 --stall 1200-1400:150
```

小结文件在 `out/v28/A070_*.json`。

## 提醒：这台机器的磁盘刚才写满过一次

04:09（机器时间）`df` 显示可用 12 KB，`git` 报 `Out of diskspace`，提交失败；几分钟后恢复到约 6.7 GB 可用（98%）。占用大头不在本项目：`/home` 101.6 G、`/agent` 74.5 G、`/tmp` 52.8 G。我没有动别人的文件，只删了自己的一个调试输出。再写满时各号的提交和输出文件都可能失败或被截断，请留意。
