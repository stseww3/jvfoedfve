export const HELP = `teamgate-v2.mjs — 高保真组队模拟器与断面反事实评测器

都在 c136-review/agents/R06 下，经重计算闸门跑：
  HEAVY_TIMEOUT=110 timeout 120 bash ../../tools/run-heavy.sh node sim-v2/teamgate-v2.mjs --mode <模式> …

--mode verify       物理底座自检
    --match <局>            对局包编号（B021 …；B038 / B039 自动改读同一场的 A057 / A058 录像）
    --to <拍>               只放到这一拍（缺省放完）
    --clone-at <拍> --clone-len <拍数>   clone 分叉自检的位置和长度

--mode checkpoint   真局断面反事实（历史臂 + 对照臂 + 处理臂，三个世界逐拍同步）
    --match <局> --t0 <拍> [--len 900]          断面拍、窗口长度
    --baseline <策略>       对照臂（缺省 vb）。简写：c110 / vb / va / vc(=c116) / g09，或策略文件路径
    --candidate <策略文件>  处理臂；不给就只跑对照臂（校准用）
    --base-params / --cand-params '<JSON>'      覆盖策略 PARAMS 的开关
    --arm baseline|candidate|both               只跑其中一臂（省时间；之后用 --mode pair 合）
    --warmup full|<拍数>    断面前影子热身多少拍（缺省 full = 从第 0 拍）
    --seats 27,28,…         只接管这些席位（缺省：这一局全部我方席位）
    --channel <档>          C0 | C1 | C2 | C3 | C4，可带参数：C3:w0=600,w1=2100,lagMin=150,lagMax=400,burstMin=20,burstMax=60,speed=1.45
                            C1:dMin=10,dMax=12   C2:fill=linear|upper|lower   C4:gain=4,window=100
    --trace-from <局>       C2 借用别的局的实录阶梯（按席位次序对上）
    --seed <n>              通道抖动、反应补丁的随机种子（两臂相同）
    --keep first|last       超过 9 条顶时留最早 / 最晚发出的（缺省 first）
    --order lifo|fifo       同一回合内的执行次序（缺省 lifo：后发先执行）
    --cap 9 --cap-rounds 3  连续几个回合最多执行几条
    --multi                 一个决策拍允许受理多条（缺省只受理第 1 条）
    --donate-submit always|quote   捐款提交时恒返回 true（缺省，线上口径）| 提交时就按配额判（旧门禁口径）
    --ao-id off|<0~1023>    是否提供界面侧的捐款预检 window.ao.iD（缺省 off；数值 = 界面滑杆的档）
    --inflight-guard <拍>   发出一条后多少拍内不再调策略（缺省 0）
    --fallback cheapest|engine|drop   其余真人的陆攻目标已出局 / 不接壤时：改打身边最便宜的内置 AI / 无主地（缺省）| 原样交给引擎 | 作废
    --our-leaves replay|ignore        接管后我方席位在录像里的离场（掉线 / 被移出）照放（缺省）| 不放
    --react off|first|thin|first,thin 对手反应补丁（缺省 off）
    --budget-ms 95000       墙钟预算：超了就在当前拍截断，三个世界停在同一拍
    --out <文件>            结果 JSON；--dump-cmds <文件> 每条指令的流水；--keep-logs --dump-logs <文件> 策略日志

--mode arena        闭环多原型对抗（见 --mode arena --help-arena）
--mode pair         汇总若干结果文件：--in a.json,b.json,… 或 --dir <目录>，出各指标成对差的中位数 / P10 / 胜负场数
`;
