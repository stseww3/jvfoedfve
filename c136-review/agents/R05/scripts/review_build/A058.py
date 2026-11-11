# A058.py — 组装 reviews/A058.json。机械数字取自 review_skel.py 的骨架（/tmp/c136-r05/skel/A058.json），
# 其余数字逐条来自 truth_digest.py / shadow.mjs / border_owners.mjs / cmd_bursts.mjs 的输出（见 scripts 字段）。
# 用法：python3 scripts/review_build/A058.py
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import skel, pick_timeline, dump, check, accounts, account_scripts

M = 'A058'
S = skel(M)
ACC = accounts(M)   # 广播 0007 的三本账（延迟 / 好地 / 600–1500 决策拍归因）+ 配额闸计数，原样取自脚本输出
SRC = 'src/strategy/v27-team-c116-vb.js'

notes = {
    90: '10 号全部落子；首轮中立扩张已发（[HL-OPENING] t=65 cyc=0 rings=7 spend=362/759）',
    180: '第二轮扩张（t=170 cyc=1 rings=6）；三队各约 0.5%',
    360: '我方号地中位 480，对在场真人中位 511（t=300）；zero_7、leo_tx 的最后一条日志就在 t=360',
    600: '我方号地中位 1958，对真人 2498（−22%）；已执行指令的陈旧度从约 10 拍升到 60–150 拍；首批同拍连发（ryan_m t=609×4）',
    900: '机器人占图 48.8%（峰值）；我方 8/10 在线；alex_k/riku_x/kaito9 每 5 拍发一条打机器人指令但几乎不落地',
    1200: '队伍名次 2→3；我方 7 号在线，地中位 4517 对真人 9997；存兵密度 15.6 对真人 5.9（兵没花出去）',
    1500: '机器人占图只剩 9.3%：900–1500 分掉 39.5% 的图，我方只多了 1.0%；地中位 4796 对真人 12166',
    1800: '在线 5 号；noah88 四周 100% 是队友（63% 在线 + 37% 已离线），每 25 拍发一次调度但全部不落地',
    2100: '在线 3 号（talon5、sora_w、noah88）；sora_w 在 t=2030、2093 各 9 条同拍连发，兵 418k→3k',
    2400: '编队总兵 2445k→978k（noah88 八笔捐兵 + talon5/sora_w 两轮连发清仓）；份额 8.6%→9.3%',
    3000: 'noah88 阵亡（2984）；talon5 四周 0% 敌人、73% 是已离线队友的地，开始 900 拍空转',
    3600: 'T3 领先 39.5%；talon5 存兵 1313k 仍无接触面；sora_w 开始分批打 Serial [kilr]',
    4200: '已离线的 5 个僵尸号在 3476–4028 被 Serial 与 [UZB] 吃光；编队只剩 talon5、sora_w（+zero_7 僵尸号）',
    4800: 'talon5 打完 SYFER 一轮（4540–4765）；T1 32.6% 排第二',
    5400: 'talon5 密度 93–117（5100–6900 段因超过软上限少拿利息 1237k）',
    6000: 'T1 27.9% 掉到第三；Furry 112873 格、存兵 10.9M',
    6300: 'talon5↔sora_w 在 6202–6447 互捐 8 笔，税烧掉 1866k',
    6600: 'T2 40.9% 领先；talon5 开始吃已离线的 [UZB] Full send',
    6900: 'T1 33.1%（本局最高 34.6% 在 7080）；talon5 59584 格',
    7200: '编队份额 17.5%（峰值 17.6% 在 7260），几乎全是 talon5（112400 格）；Furry 263485 格/22.6M',
    7500: 'sora_w（7404）、zero_7 僵尸号（7413）已死；Furry 开始连续 8 次进攻 talon5',
    7800: 'talon5 76043 格/5974k，对面 Furry 359571 格/28.0M',
    8010: 'talon5 于 7994 阵亡；T1 只剩 NAH 一人在线',
    8250: '终局：T2 98.3%',
}

phases = {
    'spawn_0_90': {
        'facts': [
            '10 号全部分到 T1（黑），和同房另一支编队 B039 的 2 个号同队；选点是一个紧凑方阵：质心 (138,290)、最远号离质心 128 格（协调器 r0/r1/r2 = 28/82/136）。',
            '方阵范围内只有 1 个非我方真人（Terri#3，T2，离 sora_w 15 格，t=435 掉线）。',
            '10 个号最后一条 [HL-SPAWN*] 日志里的指定点都不等于实际出生点（spawn_truth.mjs）。',
        ],
        'problems': [
            '方阵把内圈号围在队友中间：noah88 在 t=900 时 72% 的陆上邻格是队友，t=1500 起 100%（border_owners.mjs），整局没有过对敌接触面。',
        ],
    },
    'opening_90_630': {
        'facts': [
            't=300：我方号地中位 480、密度 2.8；在场 44 名真人（不含两支编队）地中位 511、密度 3.8——开局中立扩张基本持平（−6%）。',
            't=600：我方 1958 对真人 2498（上四分位 3057），落后 22%。',
            '指令陈旧度（已执行指令对上的那次影子决策到执行的拍数）：t<300 中位 10–14 拍；600–900 段 49–146 拍（各号不等）。',
            'zero_7、leo_tx 在本地 t=360 之后再无日志与指令（各只发过 3 条指令），t=785 被标离线。',
        ],
        'problems': [
            '客户端从 t≈560 起开始落后，首批同拍连发出现在 t=609–721（ryan_m×4、kaito9×5、zexos1×7、riku_x×8、sora_w×6）：同一决策的多份拷贝一拍内全落地，例：riku_x t=693 花掉 89% 存兵（首条只想花 23%）。',
            'sora_w 在本地 t=561 把 isNoFullSend 误锁为真（上一条指令 10 拍后落地造成的扣款被算在新指令头上）；到 t=1019 共 7/10 个号被锁。',
        ],
    },
    'midgame_630_3500': {
        'facts': [
            't=900→1500：机器人占图 48.8%→9.3%，三支队伍合计 47.4%→89.3%；我方编队 5.3%→6.3%。t=1500 我方号地中位 4796 对真人 12166（−61%），密度 43.7 对 9.5。',
            '下发对账（全程）：策略自报发出 666 条指令（影子策略复算 680 条，逐窗口几乎一致），录像里真正执行 338 条（51%）；陆攻/出船 617→310，捐兵 49→28。',
            '已执行指令里 75 条陈旧度 ≥90 拍、22 条 ≥300 拍；900–1500 段多数号的中位在 215–509 拍。',
            '7 个号先后失联并被标离线：785、785、1121、1681、1681、1905、1905；离线瞬间这 7 个号共握 1,686,717 兵、29341 格。同房 B039 的 20 个号 t≤2000 掉了 12 个，44 名真人只掉 6 个。',
            '幸存 3 号：noah88（全程无接触面的银行）、sora_w（对 holyfcklois 一线）、talon5（西侧）。2400 拍以后 talon5、sora_w 的陈旧度回到 4–14 拍（个别窗口 26）。',
        ],
        'problems': [
            '「机器人锁」：805–1405 七个采样拍里，有相邻机器人的 51 个（号×拍）样本中 38 个没有任何机器人目标能通过留底（24 个留底 ≥ 全部存兵），其中 33 个的留底是由「同一个机器人的另一个邻居＝我方队友」定出来的。',
            'alex_k、riku_x、kaito9 没被锁、每 5 拍都在发打机器人的指令（alex_k 900–1080 发 34 条、落地 0 条），是指令没送到。',
            'noah88 29 笔调度有 21 笔没执行（t<2142 时单笔花费超过受赠方整个配额上限）；随后 2205–2247 的 42 拍内 8 笔一起落地，兵 447k→7.5k。',
            'sora_w t=2030×9、t=2093×9 与 talon5 t=2296×9、t=2324×8 四批连发把各自存兵打到 2–7%。',
            'talon5 在 t=3000–3900 四周没有敌人：73% 的邻格属于已离线队友（ryan_m 226、zero_7 81、zexos1 79 格），存兵 774k→1383k 空转。',
        ],
    },
    'endgame_3500_plus': {
        'facts': [
            '已离线的 alex_k、leo_tx、kaito9、ryan_m、zexos1 在 3476–4028 被 Serial [kilr]（T3）和 [UZB]（T3）吃光：Serial 从我方号手里共拿 41956 格。',
            'talon5 3950 起分批打已离线/失血的邻居（Serial、SYFER、[UZB] Full send），地 25430→45148（6600）→112400（7200）→峰值 122457（7458，占图 16.1%）。',
            'sora_w 4113 达峰 18584 格后被围成银行，4872–7161 向 talon5 捐 13 笔共 7,143,833 兵（税 1,426,851）。',
            'T1 在 7080 达到全局最高 34.6%，此时 T2 已 47%；Furry（T2）7357 一击打死 sora_w，7525–7945 八次进攻共 3179 万兵打死 talon5。',
        ],
        'problems': [
            '6202–6447 talon5 与 sora_w 互捐 8 笔（各 4 笔，间隔 14–21 拍）：到账 4544k/3367k，税 1195k/671k，245 拍烧掉 1866k。',
            'talon5 5100–6900 密度 93–117，因超软上限少拿利息 1237k。',
            'talon5 7392、7707 各两条 pct≈120 的进攻打 Furry（合计 4587k 对 Furry 存兵 25–28M）。',
        ],
    },
}

turning = [
    {
        'id': 'TP1', 't0': 900, 't1': 1500, 'shareBefore': 15.2, 'shareAfter': 25.9, 'shareOf': 'T1（我方队伍）',
        'rankBefore': 2, 'rankAfter': 3, 'squadShareBefore': 5.3, 'squadShareAfter': 6.3,
        'what': '机器人的地被分完的 600 拍：T2 17.2→34.9、T3 15.0→28.5、T1 15.2→25.9（由第二掉到末位，落后榜首 2.0→9.0 个点）；我方 10 号只从 5.3% 涨到 6.3%。',
        'evidence': [
            '机器人占图 48.8%（t=900）→9.3%（t=1500）；我方号地中位 4827→4796，在场真人中位 5525→12166（review_skel.py 的 cmp 表）。',
            '同一窗口我方存兵 225k→1606k、密度 5.6→33.5（真人密度中位 9.5）：兵攒着没变成地。',
            '影子策略逐拍复算：805–1405 有相邻机器人的 51 个（号×拍）样本里 38 个没有任何机器人目标过得了留底，33 个的留底由我方队友定出（shadow.mjs --cold --floor）。',
            '下发对账：alex_k 900–1080 发 34 条打机器人指令、落地 0 条；riku_x 990–1260 发 45 条、落地 0 条；sora_w 1260–1530 发 48 条、落地 0 条（shadow.mjs --match；策略自报 cmds= 与影子逐窗口一致）。',
            '已执行指令陈旧度：alex_k 900–1200 段中位 434 拍，riku_x 1200–1500 段 509 拍，talon5 1200–1500 段 502 拍。',
        ],
        'priorDecisions': [
            {'t': '600–900', 'bot': 'talon5/sora_w/ryan_m/noah88/zexos1', 'what': '打机器人的可用兵 = 存兵 − 留底；留底取 winFloor，其中一项 safeFinite = 相邻机器人「最弱的其它邻居」的存兵。两个我方号共用一个机器人邻居时，各自的留底≈对方的全部存兵 → pickTarget 第 1161 行 continue。',
             'codePath': f'{SRC}: Style.pickTarget L1161 ← V13.floorFor0 L2233-2241 ← Policy.winFloor L4562-4569 ← V17/V13.safeFinite L2757-2768/L2500-2510 ← Strategy.threatOf L417-443'},
            {'t': '600–900', 'bot': 'alex_k/riku_x/kaito9/zexos1', 'what': '指令发出后不记「在途」，下个决策拍（5 拍后）照原样再发；客户端落后时这些指令成批迟到或丢失。',
             'codePath': f'{SRC}: Policy.act L4838（只按 t%5 设闸）→ V13.act → General.act L752-810 → Strategy.send L479-487（accept 即 cmds++，无在途登记）'},
        ],
        'statementType': 'inferred',
        'note': '留底部分是影子策略（零延迟视角）的推断；落地/陈旧度部分是录像与日志的直接观察。两者谁占多大比例没有拆开（见 unknowns）。',
    },
    {
        'id': 'TP2', 't0': 1500, 't1': 2400, 'shareBefore': 25.9, 'shareAfter': 30.1, 'shareOf': 'T1（我方队伍）',
        'rankBefore': 3, 'rankAfter': 3, 'squadShareBefore': 6.3, 'squadShareAfter': 9.3,
        'what': '编队在线数 7→3，编队总兵 1606k→2558k（1800）→978k（2400）：兵在 2030–2330 的四批连发和一串捐兵里花光，换来 3 个点的图。T1 仍是末位，T3 在 1860 超过 T2 成为榜首。',
        'evidence': [
            'alex_k、zexos1 于 1681，ryan_m、riku_x 于 1905 被标离线，离线瞬间四号共握 1,560,269 兵、23089 格（review_skel.py deathsSkel）。',
            'sora_w t=2030 九条打 holyfcklois（pct 353,243,242,238,238,299,299,299,298）＝它本地 t=1580–1635 的九次决策按相反顺序落地（陈旧 395–450 拍），存兵 418k→29k；t=2093 又九条，29k→3k。',
            'noah88 t=2205×3、2233×4、2247×1 共 8 笔捐兵：447k→7.5k，到账 371k、税 72k；其中 2233 的四笔是本地 2130/2155/2180/2205 四条调度反序落地。',
            'talon5 t=2296×9、2324×8：首条想花 20% 存兵，整批花掉 76%；770k→11k（DROP30 2250–2340：打真人 −757k、捐出 −37k）。',
            'sora_w 打 holyfcklois 合计出兵 537k、拿 8168 格、又被反推 4364 格（地 5051→9122@2160→4944@2400）。',
        ],
        'priorDecisions': [
            {'t': '1575–2030（本地）', 'bot': 'sora_w', 'what': '每个决策拍都对 holyfcklois 下一条通用整额进攻（want = 1.25×need + 3×接触格），前一条没落地就再下一条。',
             'codePath': f'{SRC}: Policy.buyLand L5342-5619，通用分支 return this.send(...) L5616；Policy.send L3838-3925'},
            {'t': '1530–2230（本地）', 'bot': 'noah88', 'what': '每 25 拍一笔 pct=320/380 的调度（offense_dispatch/defense），不看受赠方配额也不看上一笔是否到账。',
             'codePath': f'{SRC}: Policy.tryDonateToTeammate L4325-4518（闸 L4329/L4331，B 类 L4474-4495，发出 L4508）'},
            {'t': '2160–2295（本地）', 'bot': 'talon5', 'what': '对已离线的 Maple Leaf 走「非真人一次打满」分支，连续 16 个决策拍重复下单。',
             'codePath': f'{SRC}: Policy.buyLand L5449-5454（return this.send L5453）'},
        ],
        'statementType': 'observed',
    },
    {
        'id': 'TP3', 't0': 6990, 't1': 7980, 'shareBefore': 33.6, 'shareAfter': 14.1, 'shareOf': 'T1（我方队伍）',
        'rankBefore': 2, 'rankAfter': 2, 'squadShareBefore': 12.5, 'squadShareAfter': 4.7,
        'what': 'T2 的 Furry 先吃 T3（6000–6600）再转头吃 T1：T1 33.6%→14.1%，T2 47.0%→72.0%。T1 此时在线的只剩 2–5 人。',
        'evidence': [
            'Furry 各 600 拍从真人手里拿的地：6600 段 10.3%、7200 段 13.9%、7800 段 22.8%（占全图）；7200 段里 talon5 6.5%、NAH 5.3%、sora_w 1.9%。',
            't=7200：Furry 263485 格/22.6M 兵；talon5 112400 格/9.0M；NAH 114652 格/5.9M。T1 在线真人 3 人。',
            'sora_w：6846–7161 向 talon5 捐 3 笔（到账 1251k）后剩 1024k/18584 格，t=7357 被 Furry 一条 2031k 的进攻拿走 14252 格，7404 阵亡。',
            'talon5：7392 两条 pct=119（1390k+1211k）、7707 两条 pct=122（1063k+923k）打 Furry；Furry 7525–7945 八次进攻共 31,789,305 兵，talon5 丢 99115 格，7994 阵亡。',
        ],
        'priorDecisions': [
            {'t': '6835–7135', 'bot': 'sora_w', 'what': '被围的银行号按 B 类调度把兵送给 talon5（offense_dispatch pct=263–320），自己密度从 150 降到 55。',
             'codePath': f'{SRC}: Policy.tryDonateToTeammate L4474-4508'},
            {'t': '7380–7385、7695–7700', 'bot': 'talon5', 'what': '对榜首 Furry 走失血/分批分支各下两条约 12% 存兵的进攻。',
             'codePath': f'{SRC}: Policy.buyLand L5585（t≥3800 nearCollapse/bleeding 分支）、L5607（pulseMode 分支）'},
        ],
        'statementType': 'observed',
    },
]

D = {d['bot']: d for d in S['deathsSkel']}


def death(bot, cause, chain):
    d = dict(D[bot])
    d['cause'] = cause
    d['chain'] = chain
    return d


deaths = [
    death('zero_7', '客户端失联：本地 t=360 之后再无日志与指令，t=785 被引擎标为离线；之后是引擎托管的僵尸号，7413 被 Furry 吃掉。',
          '只发过 3 条指令（全部落地，陈旧 10–12 拍）→ 360 后静默 → 785 离线时 718 格/29,630 兵 → 托管 AI 把它养到 3008 格（2520）→ Furry 拿 1765 格、holyfcklois 拿 1038 格 → 7413 阵亡。无队友捐兵。'),
    death('leo_tx', '客户端失联：本地 t=360 之后静默，t=785 被标离线；僵尸号 3824 被 Serial [kilr] 吃掉。',
          '3 条指令全部落地 → 静默 → 离线时 684 格/27,203 兵 → Serial 出 129,050 兵拿 1386 格 → 3824 阵亡。'),
    death('kaito9', '客户端失联：最后一条日志在本地 t=720，最后一条落地指令 t=896，t=1121 被标离线；僵尸号 3832 被 Serial 吃掉。',
          '600–900 段指令陈旧度中位 74 拍，t=658 五条连发 → 影子在 900–1170 仍想发 36 条打机器人指令，落地 0 → 离线时 4850 格/69,615 兵 → Serial 出 124,662 兵拿 6930 格 → 3832 阵亡。'),
    death('alex_k', '客户端失联：本地 t=1080 后无日志，t=1681 被标离线，离线时空握 307,128 兵；僵尸号 3476 被 Serial 三次进攻吃掉。',
          '630–1080 每 5 拍发一条打机器人的指令（策略自报 83 条，落地 15 条；陈旧度 600–900 段 146 拍、900–1200 段 434 拍）；t=1134 九条连发是本地 t≈700 的决策 → 1225 后无指令落地，118 格机器人接触面闲置，兵 115k→314k → 离线后托管 AI 涨到 16653 格（3149）→ Serial 3178/3248/3416 共 378,678 兵拿 11662 格，[UZB] 拿 1717 格 → 3476 阵亡。'),
    death('zexos1', '客户端失联：本地 t=1170 后无日志，t=1681 被标离线，离线时空握 497,850 兵；僵尸号 4028 被 [UZB] 吃掉。',
          '810–990 发 22 条落地 1 条（陈旧度 390 拍）；990–1260 被机器人锁（留底由 ryan_m/talon5 通过机器人#161 定出）→ 离线时 7239 格 → 托管 AI 涨到 18322 格（3569）→ [UZB] 出 574,258 兵拿 11580 格、Serial 拿 3364 格 → 4028 阵亡。'),
    death('ryan_m', '客户端失联：本地 t=1350 后无日志，t=1905 被标离线，离线时空握 435,570 兵；僵尸号 3984 被 Serial 吃掉。',
          '900–1170 被机器人锁（发 0 条）；1260–1350 发 9 条落地 0 条 → 离线时 4796 格 → Serial 出 218,673 兵拿 6847 格 → 3984 阵亡。'),
    death('riku_x', '客户端失联：本地 t=1260 后无日志，t=1905 被标离线，离线时空握 319,721 兵；僵尸号 2857 被 Serial 吃掉。',
          '策略自报 89 条、落地 25 条；连发 t=693×8、868×9（花掉 85% 存兵）、1309×6（本地 t=800 的决策，陈旧 509 拍）→ 990–1260 发 45 条落地 0 → 离线时 4020 格 → Serial 出 41,203 兵拿 3323 格 → 2857 阵亡。'),
    death('noah88', '全程在线但从 t≈1200 起被队友围死（无接触面）；2205–2247 的 8 笔连发捐兵把 447k 兵捐到只剩 7.5k；Serial 吃穿已离线队友的地后，t=2821 一条 98k 的进攻拿走它 3293 格中的 2551 格，2984 阵亡。',
          '峰值 3368 格（843）→ 1530–2230 每 25 拍一笔调度共 29 笔、21 笔没执行（配额不够），密度一路涨到 136 → 2205×3（给 talon5）、2233×4、2247×1（给 sora_w）→ 2400 时 17k 兵 → 2821 被打时 43k 兵（13/格）→ 死前没有收到任何捐兵（DROP30 2880–2970：被打 −35k）。'),
    death('sora_w', '后期被围成银行号，6846–7161 连捐 3 笔后密度 55；Furry t=7357 一条 2,031k 的进攻（对它 1,024k/18,584 格）拿走 14252 格，7404 阵亡。',
          '2030/2093 两批连发打 holyfcklois（418k→3k，拿 8168 格又丢 4364 格）→ 3540–4065 分批打 Serial，地 5683→18584（4113 峰值）→ 四周变成队友 → 4872–7161 向 talon5 捐 13 笔 7.14M（税 1.43M）→ 7290–7380 DROP30：被打 −586k → 阵亡。'),
    death('talon5', '编队最后一个号、T1 第二大户；Furry 7525–7945 八次进攻共 3179 万兵（它峰值存兵 1101 万）拿走 99115 格，7994 阵亡。',
          '2296/2324 连发吃已离线的 Maple Leaf（9896 格）→ 3000–3900 被已离线队友的地围住空转 → 3950 起分批打 Serial/SYFER/Full send → 6600–7200 地 45148→112400 → 7392、7707 四条进攻打 Furry（共 4587k）→ 7830–7920 DROP30：被打 −2803k → 阵亡。死前 300 拍没有收到捐兵（sora_w 已死）。'),
]


def dec(i, t, bots, what, code, ev, verdict, key, stype='observed', why=''):
    return {'id': f'D{i:02d}', 't': t, 'bots': bots, 'what': what, 'why': why, 'codePath': code, 'evidence': ev,
            'verdict': verdict, 'patternId': 'NEW', 'patternKey': key, 'statementType': stype}


decisions = [
    dec(1, '0–90', '全部', '协调器把 10 号排成紧凑方阵（r0/r1/r2 = 28/82/136，最远号离质心 128 格）。',
        'src/strategy/spawn-coordinator-c116-vb.mjs: solve() L790 起，方阵半径 L1074-1077（minReqSep/r0/r1/r2 的 clamp）',
        ['t=600 我方号地中位 1958 对真人 2498（−22%）', 'noah88 陆上邻格里队友占比：t=900 72%、t=1200 80%、t=1500 起 100%；riku_x t=900 63%', '方阵内除 Terri 外没有别的真人，外圈号的地把内圈号的中立地和机器人邻居都隔开了'],
        'error', 'SP-ENCLOSED', 'observed', '内圈号（INNER_ARC_BANK 角色）按设计就是后排；本局后排号再没有获得过接触面。'),
    dec(2, '65–300', '全部', '开局按 DP 表每个百拍周期发一条中立扩张。',
        f'{SRC}: V13.expandNeutral L2373 → V13.dpNeutral L2383-2412（[HL-OPENING]）',
        ['t=300 我方号地中位 480 对真人 511（−6%）', '此段指令陈旧度中位 10–14 拍、无连发、每号 3 条指令全部落地'],
        'good', 'OP-DP-PAR'),
    dec(3, '805–1405', 'talon5/sora_w/ryan_m/noah88/zexos1/riku_x', '身边有便宜机器人（每格 2.0–12.4，其中几个 0 兵）却不打：可用兵 = 存兵 − 留底 ≤ 0。',
        f'{SRC}: Style.pickTarget L1161 ← V13.floorFor0 L2235-2236 ← Policy.winFloor L4562-4569 ← safeFinite L2757-2768/L2500-2510 ← Strategy.threatOf L417-443',
        ['51 个（号×拍）样本里 38 个没有任何机器人目标过留底，33 个的留底由我方队友定出', '例：sora_w t=905 存兵 24293、留底 25781（由机器人#188 的另一邻居 noah88 的存兵定出），五个机器人邻居全部在 L1161 被跳过',
         '佐证：talon5 策略自报 cmds 在 900–1530 每 90 拍只加 0–3，noah88 加 0–2'],
        'error', 'AT-BOTLOCK', 'inferred', 'winFloor 把「机器人反咬时它最弱的其它邻居有多少兵」当作自己要留的兵；这个「最弱邻居」恰好是队友时，两个号互相把对方锁住。'),
    dec(4, '600–2330', 'alex_k/riku_x/sora_w/talon5 等', '指令发出后不登记在途：5 拍后局面没变就再发一条同样的；客户端落后时，同一决策的多份拷贝在同一个服务器帧里反序落地，每条按当时余额重新计价。',
        f'{SRC}: Policy.act L4838（t%5 闸）；Strategy.send L479-487；Policy.send L3838-3925（无在途表）',
        ['334 条已执行陆攻/出船里 135 条落在 ≥3 条的同拍批里，5 批满 9 条（cmd_bursts.mjs）', 'riku_x t=868×9 打中立：花掉 85% 存兵，首条只想花 9%', 'sora_w t=2030×9：花 95%（首条 35%）；talon5 t=2296×9：花 76%（首条 20%）',
         '策略自报 666 条、落地 338 条；影子策略按每拍受理 1 条复算 669 条（不限条数时 680 条）',
         '不落后时也成立（volleys.py）：2400 拍后两号打真人 69 条，按「同一目标、间隔 ≤21 拍」归成 27 轮，每轮中位 3 条；首条花批前存兵 13%，整轮 27%（≥3 条的 15 轮中位 33%）',
         '同拍被中立最小额指令（pct=47）挤掉 27 条，其中打真人 5 条（sora_w 3600–3899 四条 272k 打 Serial）'],
        'error', 'IO-BATCH9', 'observed'),
    dec(5, '561（sora_w）–1019', 'sora_w/alex_k/noah88/riku_x/zexos1/kaito9/talon5', 'isNoFullSend 被误锁：新指令发出后 7 拍内余额下降就认定「引擎没给足兵」，而那次下降其实是上一条指令落地的扣款。',
        f'{SRC}: Policy.updateShadowQuota L3821-3833；Policy.send L3844-3862、L3879',
        ['sora_w：t=550 发 pct=87 打机器人#198（t=560 落地，扣 466）；t=560 发 pct=468 打中立（want 2189，bal0 4780）；t=561 余额 < bal0−fee → actualSent 记为 410 → want ≥ 1.12×410 → 置真',
         '影子复算的首次置真拍：sora_w 561、alex_k 659、noah88 742、riku_x 825、zexos1 834、kaito9 872、talon5 1019；zero_7/leo_tx/ryan_m 没触发', '置真后 send 在 L3858/L3861 拒发共 34 次（talon5 16、sora_w 7）；L4549、L5164、L5262-5266、L5430 这些带 !isNoFullSend 的条件此后恒假'],
        'error', 'EC-NOFULLSEND-LOCK', 'inferred', '置真拍是影子复算（影子与真实策略的发令数逐窗口一致，故可信度高）；真实客户端没有直接日志。'),
    dec(6, '1530–2230', 'noah88', '29 笔调度（给 talon5 20 笔、给 sora_w 9 笔），21 笔没有执行。',
        f'{SRC}: Policy.tryDonateToTeammate L4474-4508（B 类 offense_dispatch；无配额模型）',
        ['t<2142 时一笔 pct=320 的捐兵花费（例 170 点）超过受赠方整个配额上限（115 点）：19 笔在四个试算拍上全部被配额拒', 'noah88 存兵 195k→447k、密度 59→136（硬上限 150），四周 100% 是队友',
         '录像里这 5 局的 843 条捐兵指令没有一条是无效的——被拒的捐兵根本不进录像，策略侧却记为已发（cmds++、lastDonateTick 更新）'],
        'error', 'DN-QUOTA-BLIND'),
    dec(7, '2205–2247', 'noah88', '42 拍内 8 笔捐兵一起落地：447k→7.5k（到账 371k、税 72k）。',
        f'{SRC}: Policy.tryDonateToTeammate L4329（t−lastDonateTick<12 的闸按本地拍计）、L4508',
        ['t=2205×3 给 talon5（余额 446618→278701→173917）是本地 t≤2030 的调度，陈旧 ≥175 拍', 't=2233×4 给 sora_w 是本地 2130/2155/2180/2205 四条反序落地', '此后 noah88 13 兵/格，t=2821 被 Serial 一条 98k 的进攻打穿'],
        'error', 'DN-BURST-DRAIN'),
    dec(8, '2030–2400', 'sora_w', '对 holyfcklois（T2，t=1500 时 23774 格）下通用整额进攻。',
        f'{SRC}: Policy.buyLand 通用分支 L5616',
        ['出兵 537k、拿 8168 格、打掉对方 210k 兵，又被反推 4364 格；holyfcklois 2710 阵亡（talon5 也出了 258k 拿 7525 格）', '两批连发后 sora_w 兵剩 3k（0.4 兵/格），地 9122（2160）→4944（2400）'],
        'unclear', 'AT-GENERIC-FULL', 'observed', '目标本身不差（对方最终被打死），坏在 18 份拷贝一次清仓；零延迟下这条分支每次只花约 25–35%。'),
    dec(9, '2160–2700', 'talon5', '吃已离线的 Maple Leaf（同房 B039 的号，在 T2，59k 兵/12866 格）：走非真人一次打满分支。',
        f'{SRC}: Policy.buyLand L5449-5454（L5453 返回）',
        ['拿 9896 格，出兵 627k、收回 463k（净花 164k，约 17 兵/格）', '同一窗口还拿 holyfcklois 7525 格（258k）和中立 5869 格；地 6453→24097'],
        'good', 'AT-CHEAP-LEFT'),
    dec(10, '3000–3900', 'talon5', '编队最大的号 900 拍没有任何动作：四周 0% 敌人，73% 是已离线队友的地；不发船，只在 3458、3731 给 sora_w 各捐一笔。',
        f'{SRC}: Policy.buyLand L5618（无报价）；Policy.idleBoats L5031（有兄弟在陆上接敌且自己密度<115 → return）；Policy.tryDonateToTeammate L4331/L4498',
        ['border_owners.mjs：t=3000–3900 talon5 陆上邻格 526，其中已离线队友 386（ryan_m 226、zero_7 81、zexos1 79）、在线队友 140、敌人 0', '存兵 774k→1383k（密度 30→54）；同期 T3 36.7%→39.5%', '两笔捐兵到账 788k、税 193k'],
        'error', 'DF-ZOMBIE-WALL'),
    dec(11, '3540–4065', 'sora_w', '对被多家围攻的 Serial [kilr] 分批进攻（先 pulse 分支，后失血分支）。',
        f'{SRC}: Policy.buyLand L5607（pulseMode）、L5585（t≥3800 nearCollapse/bleeding）',
        ['地 5683（3300）→6593（3600）→12306（3900）→18584（4113 峰值）', '这一段指令陈旧度中位 7–11 拍、无连发'],
        'good', 'AT-PULSE-BLEED'),
    dec(12, '3950–6950', 'talon5', '分批打失血/已离线的邻居：Serial（3950–4105）、SYFER（4540–4765）、[UZB] Full send（5180–6950）。',
        f'{SRC}: Policy.buyLand L5585、L5607',
        ['6600–7200：拿 Full send 35617 格（出兵 2455k）、Serial 14605 格、中立 11729 格，地 45148→112400', '峰值 122457 格（7458）＝全图 16.1%'],
        'good', 'AT-PULSE-BLEED'),
    dec(13, '4872–7161', 'sora_w', '被围的银行号向前线号 talon5 捐 13 笔。',
        f'{SRC}: Policy.tryDonateToTeammate L4474-4508',
        ['到账 7,143,833、税 1,426,851（税/到账 20.0%）', '全编队 28 笔捐兵：到账 12.88M、税 2.89M'],
        'unclear', 'DN-TAX', 'observed', '方向对（无接触面的号把兵送去前线），但每笔都按捐出方全部存兵抽 6.25%，折合到账额的两成。'),
    dec(14, '6202–6447', 'talon5/sora_w', '两个号互相捐：talon5→sora_w 4 笔，sora_w→talon5 4 笔，交替进行。',
        f'{SRC}: Policy.tryDonateToTeammate L4474-4495（yield_opt_dispatch；两边 boxedIn=true）',
        ['talon5→sora_w 到账 4,543,865、税 1,194,876；sora_w→talon5 到账 3,367,310、税 671,364；245 拍烧掉 1,866,240 兵，约为两号 6180 拍时合计存兵（4853k）的 38%',
         'sora_w 当时卡在硬上限（150×18584=2,787,600），talon5 后两笔到账被受赠方余量截断（到账 850k、税 298k）', '日志：talon5 6195（dMe 111、dAlly 41）、sora_w 6210（dMe 127、dAlly 72）、talon5 6295（105/87）、sora_w 6310（150/76）……'],
        'error', 'DN-PINGPONG'),
    dec(15, '7380–7700', 'talon5', '对榜首 Furry 下四条进攻（7392 两条 pct=119，7707 两条 pct=122）。',
        f'{SRC}: Policy.buyLand L5585、L5607',
        ['共 4587k 兵；7392 时 talon5 11.9M 对 Furry 25.2M/298963 格（密度 84）', 'Furry 在 7357 已先打了 sora_w；7525 起八次进攻共 31.8M 兵'],
        'unclear', 'EG-GIANT-POKE'),
]

new_patterns = [
    {'key': 'IO-LAG-STALE', 'prefix': 'IO', 'name': '客户端落后：指令按旧局面决策、迟到落地',
     'definition': '把每条已执行指令（目标、比例）对到影子策略最近一次相同决策，陈旧度 = 执行拍 − 决策拍；某号 300 拍窗口内陈旧度中位 ≥90 拍记一次。', 'detector': 'scripts/shadow.mjs --match'},
    {'key': 'IO-BATCH9', 'prefix': 'IO', 'name': '同拍连发批（≤9 条、反序、逐条重新计价）',
     'definition': '同一号在同一拍执行 ≥3 条陆攻/出船指令；附：整批花掉的余额占比 vs 首条想花的占比。', 'detector': 'scripts/cmd_bursts.mjs'},
    {'key': 'IO-LOST-CMD', 'prefix': 'IO', 'name': '发了没落地的指令',
     'definition': '策略自报 cmds=（[HL-TICK]）减去调度日志条数 = 陆攻/出船已发数；与录像实际执行数之差 ≥20% 的对局/号。', 'detector': 'scripts/review_skel.py（delivery 字段）'},
    {'key': 'EX-CLIENT-DROP', 'prefix': 'EX', 'name': '客户端失联 → 被标离线的僵尸号',
     'definition': '我方号在录像里出现 leave 事件；附最后一条日志拍、离线瞬间握有的兵与地、之后被谁吃掉。', 'detector': 'scripts/review_skel.py（deathsSkel）'},
    {'key': 'EX-PEER-SQUAD', 'prefix': 'EX', 'name': '同房另有一支我方编队',
     'definition': 'card.sameMatchPeer 非空；按 identity-map 统计对方号落在哪些队、两支编队与其余真人各自 t≤2000 的离线率。', 'detector': 'scripts/match_truth.mjs（peer 字段）'},
    {'key': 'AT-BOTLOCK', 'prefix': 'AT', 'name': '机器人锁：留底被队友的存兵顶到 ≥ 自己的存兵',
     'definition': 't<1500，某号有相邻 AI 机器人但没有任何非真人目标满足 pickTarget L1161（可用兵 > max(minShare×兵, minCmd)），且 safeFinite 的取值来自「该机器人的另一个邻居 = 我方号」。', 'detector': 'scripts/shadow.mjs --cold --floor 805,905,...'},
    {'key': 'SP-ENCLOSED', 'prefix': 'SP', 'name': '方阵内圈号被队友围死',
     'definition': 't≤1500 时某号陆上邻格 ≥70% 属于队友。', 'detector': 'scripts/border_owners.mjs'},
    {'key': 'DF-ZOMBIE-WALL', 'prefix': 'DF', 'name': '在线号被已离线队友的地围住',
     'definition': '在线号连续 ≥300 拍对敌接触为 0，且陆上邻格 ≥50% 属于已离线队友。', 'detector': 'scripts/border_owners.mjs'},
    {'key': 'DN-QUOTA-BLIND', 'prefix': 'DN', 'name': '配额不够也照发的调度',
     'definition': '[HL-DISPATCH] 已记日志、录像里无对应执行，且按日志拍 +0/7/14/21 试算均被受赠方配额拒绝。', 'detector': 'scripts/match_truth.mjs（dispatch[].sim）'},
    {'key': 'DN-BURST-DRAIN', 'prefix': 'DN', 'name': '连发捐兵清仓',
     'definition': '同一捐出方 50 拍内 ≥3 笔捐兵落地且余额下降 ≥60%。', 'detector': 'scripts/donation_bursts.mjs'},
    {'key': 'DN-PINGPONG', 'prefix': 'DN', 'name': '互捐',
     'definition': 'A→B 与 B→A 的捐兵在 150 拍内各出现 ≥1 笔；计双向税额。', 'detector': 'scripts/donation_ledger.mjs'},
    {'key': 'DN-TAX', 'prefix': 'DN', 'name': '捐兵税占比',
     'definition': '某号全局捐兵 税/到账 ≥20%（单笔比例低或到账被受赠方余量截断时更高）。', 'detector': 'scripts/donation_ledger.mjs'},
    {'key': 'EC-NOFULLSEND-LOCK', 'prefix': 'EC', 'name': 'isNoFullSend 误锁',
     'definition': '影子策略里 isNoFullSend 由假变真的那一拍，前 14 拍内有另一条自己的指令落地。', 'detector': 'scripts/shadow.mjs --match（lockT）'},
    {'key': 'AT-CHEAP-LEFT', 'prefix': 'AT', 'name': '吃已离线账号的地（有效）',
     'definition': '目标 state=2 且每格净花费 < 自己密度；经 buyLand L5453。', 'detector': 'scripts/truth_digest.py --win'},
    {'key': 'AT-PULSE-BLEED', 'prefix': 'AT', 'name': '分批打失血/濒死邻居（有效）',
     'definition': 'buyLand 经 L5585/L5607 返回且 600 拍内地增 ≥30%。', 'detector': 'scripts/shadow.mjs'},
    {'key': 'AT-GENERIC-FULL', 'prefix': 'AT', 'name': '通用整额分支被重复下单',
     'definition': 'buyLand 经 L5616 返回的进攻在同一拍落地 ≥3 条。', 'detector': 'scripts/shadow.mjs + cmd_bursts.mjs'},
    {'key': 'EG-GIANT-POKE', 'prefix': 'EG', 'name': '后期对存兵 ≥2 倍的榜首小额进攻',
     'definition': 't≥6000，目标存兵 ≥2×自己，单条出兵 ≤15% 自己存兵。', 'detector': 'scripts/truth_digest.py --win'},
    {'key': 'OP-DP-PAR', 'prefix': 'OP', 'name': '开局中立扩张与真人持平（有效）',
     'definition': 't=300 我方号地中位 ≥ 0.9×在场真人地中位。', 'detector': 'scripts/review_skel.py（cmp）'},
]

doc = {
    'matchId': M, 'reviewer': 'R05', 'protocol': 'v2.0',
    'context': dict(S['context'], note='74 名「真人」里 30 个是我方的号：本编队 10 个全在 T1；同房 B039（squad20）20 个号分在 T1×2、T2×7、T3×11。'),
    'outcome': S['outcome'],
    'timeline': pick_timeline(S, notes),
    'phases': phases,
    'turningPoints': turning,
    'deaths': deaths,
    'drop30': {'windows': S['drop30'], 'mainSinkCounts': S['drop30MainSink'],
               'note': '17 个 DROP30 窗口逐笔对平（残差 0）：打真人 7、捐出 4、被打 3、打机器人 2、打中立 1。最大的四笔：talon5 2250–2340（连发，−757k）、sora_w 1980–2070（连发，−398k）、noah88 2160–2250（连发捐兵，−443k）、sora_w 6840–6930（捐兵，−1147k）。'},
    'dispatchAudit': S['dispatch'],
    'delivery': S['delivery'],
    'shadow': S['shadow'],
    **ACC,
    'squadVsRealHumans': S['cmp'],
    'decisions': decisions,
    'newPatterns': new_patterns,
    'lossArchetype': 'external',
    'archetypeNote': '主因在策略之外：7/10 个客户端失联，其余 3 个在 900–2300 拍落后服务器 130–500 拍；同房另一支编队的 20 个号同样大面积掉线，真人没有。次要分型 never-grew（编队份额到 t=6900 之前没超过 10.6%）。',
    'winnerNotes': 'T2 的真人 Furry🦊 [Corgi]#9 一人拿到全图 78.8%。t=1500 时它 25635 格已是全图最大的号，之后到 t=3000 地不动（25.6–26.6k）只攒兵 240k→2351k（密度 9→88）；3000 起吃 T3 的小号，6000–6600 吃 TITAN（4.8%），6600 起转向 T1：NAH 15.4%、talon5 13.0%、HRE、LMAOOOO。它收到队友捐兵 Cute Catboy 18 笔 7.5M、Yolo 13 笔 4.0M。T3 在 1860–6210 领先，随后 Serial [kilr]（6140）、[UZB]（6672）掉线，T3 的地被 T1（NAH、talon5）和 T2 分食。T1 没有两线作战的问题：整局的地主要来自 T3 的离线号，输在最后没有任何一个号的存兵能和 Furry 同量级（7200 拍 22.6M 对 talon5 9.0M、NAH 5.9M）。',
    'wentWell': [
        '开局 300 拍中立扩张与真人持平（480 对 511）。',
        'talon5 用一次打满分支吃已离线的 Maple Leaf：净花 164k 拿 9896 格。',
        'talon5、sora_w 在客户端恢复同步后（2400 拍起陈旧度 4–14 拍）的分批进攻有效：sora_w 5683→18584 格，talon5 25430→122457 格。',
        '被围的 sora_w 把兵送给前线的 talon5（方向正确）。',
    ],
    'unknowns': [
        '客户端为什么落后/失联：日志里没有主机负载或网络指标；只看到同房两支编队的 30 个号一起恶化，而 44 名真人里 t≤2000 只掉 6 个。',
        '指令从策略到服务器之间在哪里丢的：引擎的发送函数是直接 WebSocket.send，没有本地队列；每帧每号最多 9 条、反序落地的规则出自哪一层（服务器？接入层？）没有源码。',
        'TP1 里「机器人锁」和「指令没落地」各占多少：被锁的号（talon5、noah88、ryan_m）几乎不发令，没被锁的号（alex_k、riku_x、kaito9）发了不落地，两者同时存在，没有做反事实重演。',
        'noah88 t=2205 那三笔给 talon5 的捐兵对应哪三条日志（推测是本地 1980/2005/2030），以及本地 2055–2105 三条给 sora_w 的调度为什么没有痕迹（推测被配额在源头拒掉）。',
        '真实客户端里 isNoFullSend 的置真拍没有直接日志，只有影子复算。',
    ],
    'mechanicsQuestions': [
        '服务器是否对每个玩家每帧的指令数设了 9 条上限？超出的丢弃还是顺延？帧内执行顺序是否为到达顺序的逆序？',
        '捐兵/出船指令被引擎判无效时是否根本不发往服务器（5 局录像里 843 条捐兵、1693 条出船零无效，而陆攻 13878 条里有 692 条无效）？若是，接入层的 g.donate 返回 true 的条件是什么？',
        '客户端落后多少、多久会被服务器判离线（本局从最后一条日志到 left 相隔 225–645 拍）？',
        '离线账号由引擎 AI 托管后还留在原队伍：它的地对队友不可进攻、不可穿过——有没有任何机制（投票踢人、并地）能让队友接手？',
    ],
    'scripts': [
        *account_scripts(M),
        'scripts/sim_replay.mjs（逐拍精确重放；A058 校验 100%）', 'scripts/match_truth.mjs A058 → /tmp/c136-r05/truth/A058.json', 'scripts/review_skel.py A058 → 骨架（时间线、阵亡骨架、DROP30、调度对账、落地率、真人对照、赢家）',
        'scripts/truth_digest.py A058 [--win bot,t0,t1]', 'scripts/shadow_prep.cjs vb；scripts/shadow.mjs A058 --quiet --match（下发对账与陈旧度）', 'scripts/shadow.mjs A058 --cold --quiet --t0 790 --t1 1410 --floor 805,905,1005,1105,1205,1305,1405（机器人锁）',
        'scripts/shadow.mjs A058 --bots talon5,sora_w,noah88 --t0 1500（各窗口出口行）', 'scripts/border_owners.mjs A058 --at 600,900,...,3900（邻格构成）', 'scripts/cmd_bursts.mjs（全量连发统计）', 'scripts/volleys.py A058 --t0 2400（连续下单）', 'scripts/review_build/A058.py（本文件）',
    ],
    'confidenceOverall': {'level': 'high', 'note': '时间线、阵亡、DROP30、调度、连发、落地率均来自 100% 对齐的逐拍重放；陈旧度是下界估计；机器人锁与 isNoFullSend 为影子策略推断（影子按每拍受理 1 条时发令数 669，对真实 cmds= 666）。'},
}

dump(M, doc)
check(M)
