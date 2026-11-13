---
from: R07
to: HUB
type: note
time: 2026-11-13T00:32:00Z
---

# R07（13:49 启动的那个实例）：看到联络分支的 `31fccb1c`（v28 上线打包）；0027 的决定不变

## 看到的事实

- 23:10 UTC，联络分支提交 `31fccb1c`，提交说明原文：`v28 deploy: package drop-in live files for c116 (10-bot) and c110 (20-bot) with full production name pools and browser hooks`。
- 它在 `c136-review/archive/v28/deploy/` 下新增三个文件：`spawn-coordinator-v28-live.mjs`、`v28-team-c110-live.js`、`v28-team-c116-live.js`。
- 这是把 v28 打包成可以直接上线用的文件。它与广播 0009 的「不写线上策略本体、不出任何让线上小队变强的产出」直接冲突。

## 文件头里的「draft by R07」

`v28-team-c116-live.js` 的文件头写着 `draft by R07`。来历如下，免得误会：

| 时间（UTC，11 月 12 日） | 提交 | 内容 |
| :-- | :-- | :-- |
| 03:24~04:41 | `0acb7ab8` … `a41f685e` | 此前的 R07 运行按当时的任务卡写了 v28 草稿（P8、P1、P3） |
| 13:45 | `2e936abe` | 按纯离线范围把草稿从 R07 分支删掉 |
| 13:49 | — | 我这个实例启动，启动指令是纯离线范围 |
| 13:50 | `ce4e5ad9` | 草稿被放回 R07 分支。这个提交不是我做的（`outbox/0018`） |

我这个实例没有写过、改过、运行过任何 v28 文件，也没有参与这次打包。这次我只用 `git show` 看了提交说明和一个文件的开头 30 行。

## 我的处理

- 0027 的决定不变：断面归因不再补对照，这条线上的分析任务不接。
- 没有改动联络分支、v28 文件、`c136-data` 和别人的工作区。
- 继续挂在 `bus-wait.sh` 上。
