# R08 假设卡索引

写卡的人：R08（局内复盘专员 8）。范围：我复盘的 16 局（G02、G05、G08、B043、B033、B034、B031、B049、B006、B030、B019、B009、B015、B029、B035、B027）里看到的失分模式，
每一条都写成了能在发现集 123 局上机械计数的脚本（`agents/R08/scripts/`），计数结果在 `agents/R08/out/_cross/`。验证集没有碰。

## 怎么读一张卡

每张卡固定八节：一句话 → 可证伪的陈述 → 机制（策略代码行、引擎代码行）→ 检测器（哪个脚本、口径）→ 计数（我的 16 局 / 发现集全量，分编队档）→
和结果的关系（含检验）→ 反证和混杂 → 证据等级，以及交给验证集（E3）和模拟器（E4）该怎么测。卡里不写补丁、不写参数取值——那是会审提案的事。

证据等级照 `PLAN.md` §2：E0 猜想、E1 单局个例、E2 发现集脚本统计显著、E3 验证集独立复现、E4 模拟器反事实配对消融。
一张卡常常要分开说两件事——「这个现象存在、有多频繁」和「它值多少地」——两件事的等级可以不一样，卡头分开标。

## 口径提醒（每张卡都适用）

- 编队档：squad10 = c116（发现集 75 局）、squad20 = c110（38 局）、squad8 = g09（10 局，发现集里没有录像）。
- 真值口径的数（来自录像逐拍重演）只覆盖有录像、且重演出来和日志逐行对得上的局：96 局对得上，其中 89 局有对局段、80 局录像到 1500 拍以后（`xtruth.txt` [XT-A]）。
  日志口径的数（`xscan.txt`）覆盖全部 123 局。
- 「own」= 本编队的号；「野人」= 同局里不是任何机器号的真人；「机器号」= own + [APEX] + 名字池。
- 逐局口径（每局先算一个比值，再取各局的中位）和合计口径（各局的条数 / 格数直接相加）会差很多：own 每局人头差不多，野人的人头集中在大房间，
  大房间人均地小，所以合计口径对 own 偏乐观。卡里的结论以逐局口径为准，合计口径只用来拆构成。
- 显著性：`xsig.txt` 一共 143 个检验，Bonferroni 门槛 0.05 ÷ 143 = 0.00035；置换检验 20000 次，能给出的最小 p 是 0.00005。「过门槛」指过这条线（过了的 57 个）。
- 「几乎不卡的局」= own 在 600~1500 落地的陆攻里没生效的 ≤5%（20 局）。

## 卡片一览

<!-- cards-table:begin -->
| 卡 | 现象 | 现象的等级 | 「值多少地」的等级 | 对应的模式编号 |
|---|---|---|---|---|
| [H01](H01-lag-wave.md) | 卡顿波：600~1500 拍机器号的指令晚到、成批落地、落空 | E2 | E2 | NEW-IO-01、NEW-IO-02、NEW-IO-03、NEW-IO-05、NEW-IO-14 |
| [H02](H02-fall-630-1500.md) | 630 拍持平，1500 拍人均地只剩野人的一半 | E2 | —（它本身就是结果量） | NEW-EC-06、NEW-EC-10 |
| [H03](H03-sb-lock.md) | 挨着白给的内置 AI 不出手：留底里的 AI 仇恨项取了编队友的余额，互锁 | E2 | E2 偏弱 | NEW-EC-05 |
| [H04](H04-reinforce-duplicates.md) | 打内置 AI 的兵有一半是续在已有进攻上的；同拍重复下单 | E2 | E1 | NEW-EX-01、NEW-EX-02、NEW-IO-02 |
| [H05](H05-few-and-small-targets.md) | 下手的 AI 少、下手时 AI 已经小了 | E2 | E2 | NEW-EC-06、NEW-EC-10 |
| [H06](H06-neutral-leftovers.md) | 600 拍以后的无主地只拿到野人的一半：一半是 AI 垮掉后的余地，一半是开局就没人占的地 | E2 | E1 | NEW-EC-06 |
| [H07](H07-spawn.md) | 出生点：贴边、扎堆、最后一条指派没执行 | E2 | E1 | NEW-SP-01、NEW-SP-02、NEW-SP-03、NEW-SP-05、NEW-SP-07、NEW-SP-08 |
| [H08](H08-softcap-expensive-buys.md) | 1500 拍后：余额顶在软上限以上，再出手就是高价 | E2 | E1 | NEW-EC-03、NEW-EC-09、NEW-AT-01、NEW-AT-03 |
| [H09](H09-boxed-by-squadmates.md) | 被自己人围住：没有可打的目标，地不动、兵空涨 | E2 | E1 | NEW-MT-09、NEW-MT-09L、NEW-MT-11、NEW-EC-02、NEW-EC-04、NEW-OP-01 |
| [H10](H10-passive-loss.md) | 挨打不还手：地在掉，一条打向进攻者的指令都没有 | E2 | E2 偏弱 | NEW-DF-01、NEW-DF-01w、NEW-DF-04、NEW-DF-06 |
| [H11](H11-quarter-line-bank.md) | 带着大笔兵被除名：地掉到峰值的四分之一，账上的兵清零 | E2 | E2 偏弱 | NEW-DF-08、NEW-DF-07 |
| [H12](H12-donations.md) | 捐款：4284 拍前发出的八成半没成交（主要是引擎的受捐额度）；成交的每送到 100 兵另付 38 兵的税 | E2 | E1 | NEW-DN-01、NEW-DN-02、NEW-DN-07、NEW-DN-12、NEW-DN-17 |
| [H13](H13-leave-with-land.md) | 带着地离开：号还有几千格就变成了没人管的空壳 | E2 | E1 | NEW-IO-04、NEW-IO-07、NEW-IO-13 |
| [H14](H14-more-enemies-after-buy.md) | 扩张以后邻居变多，接着被吃：选目标时不看目标背后是谁 | E2 | E2 偏弱 | NEW-AT-04、NEW-AT-02 |
| [H15](H15-post-1500-gates.md) | 1500 拍后剩下的内置 AI 地：挨着的时候出手只有野人的一半——c110 卡在最小指令门槛和留底上，c116 放行了但落不了地 | E2 | E1 | NEW-EC-07、NEW-EC-08 |
<!-- cards-table:end -->

这张表和 `cards.json` 由 `scripts/cardsjson.py` 从各卡的卡头生成（改了卡头要重跑）。

## 复现

```bash
cd /agent/repos/c136-r08
export PYTHONDONTWRITEBYTECODE=1
A=c136-review/agents/R08
# 日志口径（123 局，约 1 分钟）
timeout 120 python3 $A/scripts/xscan.py --quiet
# 指令流（107 份录像，只解码不模拟）、捐款按引擎额度换档的拍分段
bash c136-review/tools/run-heavy.sh node $A/scripts/replay_cmds.mjs --out-dir $A/out/_run/streams <局> …
timeout 120 python3 $A/scripts/xbatch.py
timeout 120 python3 $A/scripts/xdon.py --quiet
# 真值（逐拍重演到 1800 拍；12 局一批，每批几十秒）
bash c136-review/tools/run-heavy.sh node $A/scripts/xtruth.mjs <局> …
timeout 120 python3 $A/scripts/xtruth.py --quiet
# 真值，1500 拍以后（逐拍重演到 3000 拍；一次一局，后台跑完 80 局）
bash $A/scripts/xpost_batch.sh
timeout 120 python3 $A/scripts/xpost.py --quiet
# 剂量—反应、显著性、代码行号对照、五个策略档的生效参数
timeout 120 python3 $A/scripts/xdose.py --quiet
timeout 120 python3 $A/scripts/xsig.py --quiet
timeout 60 python3 $A/scripts/codemap.py --quiet
bash c136-review/tools/run-heavy.sh node $A/scripts/params_all.mjs
# 我的 16 局的跨局表（要先有各局的事实表）
timeout 120 python3 $A/scripts/crossmatch.py --quiet
timeout 120 python3 $A/scripts/flowcheck.py
# 卡片一览 / cards.json；文稿里的数字对不对得上脚本输出
python3 $A/scripts/cardsjson.py
timeout 120 python3 $A/scripts/numcheck.py
```

顺序有讲究：`xdose.py` 读 `xscan` / `xbatch` / `xtruth` 的 JSON，`xsig.py` 再读 `xdose` 和 `xpost` 的 JSON。
局号取自 `/agent/repos/c136-data/manifest.jsonl` 里 `split == "discovery"` 的行。跨局对比报告在 `../reports/CROSS-MATCH-SUMMARY.md`。
