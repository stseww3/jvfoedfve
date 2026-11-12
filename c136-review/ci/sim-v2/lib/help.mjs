export const HELP = `teamgate-v2.mjs — 离线组队模拟器（v2.1 纯离线范围）

用途只有两件：验收「模拟器把历史旧策略复现得对不对」；在历史断面上做指令通道延迟的反事实归因。
只装历史旧策略 va / vb / vc / c110（数据包 src/strategy 下的原文件，按内容散列核对），每一局只跑它当年线上那一版，
策略参数和桥接补丁用文件里的原样。不装载其他策略文件、不比较候选策略、不改房间（标签、队数、生成房间）、不接线上。
已停用、给了就报错的开关：--candidate --cand-params --base-params --arm --inflight-guard --tag --tag-name --room synth
  --squad-husks --teams --humans --squad --map --pool --clans，以及与本局版本不符的 --baseline。

都在 c136-review/agents/R06 下，经重计算闸门跑：
  HEAVY_TIMEOUT=110 timeout 120 bash ../../tools/run-heavy.sh node sim-v2/teamgate-v2.mjs --mode <模式> …

--mode verify       物理底座自检：整段重放录像，与真引擎重放的指纹逐断面核对；clone 分叉自检；日志快照核对；计时
    --match <局>            对局包编号（B021 …；B038 / B039 自动改读同一场的 A057 / A058 录像）
    --to <拍>               只放到这一拍（缺省放完）
    --clone-at <拍> --clone-len <拍数>   clone 分叉自检的位置和长度

--mode live         真局签名扫描：只放录像、不跑策略，按 metrics.mjs 的口径算每局当年真实的指令签名和席位结果
    --matches A018,B021 | --cohort vb,c110 | --cohort all    --windows 630:1530,1530:3210    --out-dir <目录>  --force  --budget-ms

--mode checkpoint   历史断面重演（历史臂 = 录像原样；复现臂 = 从 t0 起我方席位改由历史策略经通道下令；两个世界逐拍同步）
    --match <局> --t0 <拍> [--len 900]          断面拍、窗口长度
    --baseline <策略>       可不给：自动取这一局当年的版本（A001~A017 va，A018~A095 vb，A097~A099 vc，B 组 c110）
    --warmup full|<拍数>    断面前影子热身多少拍（缺省 full = 从第 0 拍）
    --seats 27,28,…         只接管这些席位（缺省：这一局全部我方席位）
    --channel <档>          C0 即时（旧门禁口径）| C1 正常线上 | C2 这一局的实录阶梯 | C3 合成卡顿波 | C4 自激
                            可带参数：C3:w0=600,w1=2100,lagMin=150,lagMax=400,burstMin=20,burstMax=60,speed=1.45
                            C1:dMin=10,dMax=12   C2:fill=linear|upper|lower   C4:gain=4,window=100
    --trace-from <局>       C2 借用别的局的实录阶梯（按席位次序对上）
    --seed <n>              通道抖动、反应补丁的随机种子
    --keep first|last       超过 9 条顶时留最早 / 最晚发出的（缺省 first）
    --order lifo|fifo       同一回合内的执行次序（缺省 lifo：后发先执行）
    --cap 9 --cap-rounds 3  连续几个回合最多执行几条
    --multi                 一个决策拍允许受理多条（旧门禁口径；缺省只受理第 1 条，线上口径）
    --donate-submit always|quote   捐款提交时恒返回 true（缺省，线上口径）| 提交时就按配额判（旧门禁口径）
    --ao-id off|<0~1023>    是否提供界面侧的捐款预检 window.ao.iD（缺省 off；数值 = 界面滑杆的档）
    --handover carry|clean  接管时影子已发出、按通道算还在路上的指令：照常落地（缺省）| 清掉
    --fallback cheapest|engine|drop   其余真人的陆攻目标已出局 / 不接壤时：改打身边最便宜的内置 AI / 无主地（缺省）| 原样交给引擎 | 作废
    --our-leaves replay|ignore        接管后我方席位在录像里的离场（掉线 / 被移出）照放（缺省）| 不放
    --react off|first|thin|first,thin 对手反应补丁（缺省 off）
    --budget-ms 95000       墙钟预算：超了就在当前拍截断，两个世界停在同一拍
    --out <文件>            结果 JSON；--dump-cmds <文件> 每条指令的流水；--keep-logs --dump-logs <文件> 策略日志

--mode arena        闭环对手模型标定（真局房间头 + 对手模型，和同一局录像的走势对照）
    --room <局>             房间头、所有真人的真实落点都取这一局；我方跑这一局当年的版本
    --len 4300              跑多少拍
    --channel <档>          同上；--squad-fate real  我方页面当年在哪一拍停摆 / 登记离场，照放（验收时要开）
    --spawn recorded|policy 我方落点照录像（缺省）| 由历史策略自己的选点函数选
    --others-replay-until T 前 T 拍其余真人照录像，T 拍起交给对手模型
    --husks real|model|off  其余真人变空壳的时间表：照当年（缺省）| 按画像抽 | 不变空壳
    --opp <配比> --clan-opp O2,O6 --opp-rate 1 --opp-rhythm … --opp-sigma … --opp-dens-from 1530 --opp-dens-rate --opp-ai-by count|human|share
                            对手模型的配比与标定开关（画像：calib/human-profile.json，由 tools/human_profile.mjs 从 20 局录像量出）
    --out <文件>            结果 JSON；--dump-onsquad <文件> 对手打我方的每一条
`;
