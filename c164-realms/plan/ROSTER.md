# 名单：谁是谁（11-15 夜换班以后）

总监助理（代号 aide）维护。旧的聊天号（c176 到 c246）都停机了，点了没人醒；点名只点“新聊天号”一栏。“—”是还没开出来。

总监：A0，聊天 c164。只为两件事点他：要他拍板，或者报告卡住了。

## 常驻

| 代号 | 新聊天号 | 接手 | 岗位 | 分支 |
| --- | --- | --- | --- | --- |
| s2 | c258 | c188 | 技检和合并（拿合并钥匙），common 牵头 | `cursor/c164-s2-integrator-927e` |
| s1 | c260 | c189 | 出图（拿出图钥匙） | `cursor/c164-s1-render-9df7` |
| review | c261 | c219 | 评审：materials、main、props | `cursor/c164-review-0eb8` |
| cr2 | c262 | c235 | 评审：site、sky、motion | `cursor/c164-cr2-582e` |
| cr3 | c288 | — | 评审：machines、interiors | `cursor/c164-cr3-aide` |
| aide | c275 | — | 总监助理：名单、开人、盯进度 | `cursor/c164-aide-flash` |

## 工人

| 代号 | 新聊天号 | 接手 | 卡 | 分支 |
| --- | --- | --- | --- | --- |
| m1 | c263 | c194 | materials/brass-oldcopper-small（补图）、materials/panels 打磨轮 | `cursor/c164-m1-brass-fa68`、`cursor/c164-m1-panels-polish-bc45` |
| snow | c264 | c194 | materials/snow | `cursor/c164-m1-snow-bc45` |
| facade | c265 | c206 | main/facade；main 牵头 | `cursor/c164-facade-229b` |
| shell | c266 | c231 | main/shell | `cursor/c164-shell-f063` |
| lights | c267 | c220 | sky/lights（含洗墙轮） | `cursor/c164-lights-007c`、`cursor/c164-lights-wash-0fe3` |
| comet | c268 | c230 | sky/comet | `cursor/c164-comet-986f` |
| lamps | c269 | c220 | props/lamps 的位置表和场地灯链 | `cursor/c164-lamps-007c` |
| a2 | c270 | c177 | sky/tones、motion/loop；sky 和 motion 牵头 | `cursor/c164-a2-light-29fe` |
| a4 | c271 | c221 | site/terrain、site/court 打磨；site 牵头 | `cursor/c164-a4-site-2af2` |
| stair | c272 | c225 | site/stair | `cursor/c164-stair-4aad` |
| cable | c273 | c226 | site/cablecar | `cursor/c164-cable-a47d` |
| m5 | c277 | c198 | materials/iron 二次交付 | `cursor/c164-m5-iron-8757` |
| ashlar | c283 | c204 | materials/ashlar 打磨（新台徽、细琢面的长短石） | `cursor/c164-ashlar-2cc1` |
| m3 | c282 | c218 | props/ironwork 打磨轮（退回过） | `cursor/c164-m3-ironwork-e6ba` |
| a1 | c281 | c176 | materials/board；materials 牵头 | `cursor/c164-a1-materials-3930` |
| dome | c279 | c222 | main/dome | `cursor/c164-dome-0dab` |
| tower | c278 | c223 | main/tower | `cursor/c164-tower-21fb` |
| sdome | c280 | c224 | main/smalldome（含屋面） | `cursor/c164-sdome-8013` |
| power | c285 | c228 | site/powerhouse | `cursor/c164-power-f182` |
| outb | c284 | c229 | site/outbuildings、site/mastbase | `cursor/c164-outb-0198` |
| cloud | c286 | c227 | sky/cloudsea | `cursor/c164-cloud-7d36`、`cursor/c164-cloud-wip-99a5` |
| orrery | c295 | c236 | machines/orrery | `cursor/c164-orrery-6491` |
| scope | c294 | c237 | machines/refractor；machines 牵头 | `cursor/c164-scope-6e0f` |
| clocks | c296 | c238 | machines/clocks | `cursor/c164-clocks-e99f` |
| gear | c266（shell 兼） | c196 | machines/domegear（壳优先） | `cursor/c164-gear-6260` |
| car | — | c240 | machines/cablecar-winch | `cursor/c164-car-w3k9` |
| mast | — | c239 | machines/radiomast | `cursor/c164-mast-5dcd` |
| arm | — | c246 | machines/armillary | `cursor/c164-arm-7c2a` |
| pipes | — | c241 | props/pipes | `cursor/c164-pipes-9deb` |
| elec | — | c242 | props/electrics-signs | `cursor/c164-elec-7be8` |
| instr | — | c199 | props/instruments | `cursor/c164-instr-f5da` |
| a6 | c287 | c179 | props/furniture、灯的模型；props 牵头 | `cursor/c164-a6-props-7fb0` |
| m4 | — | c197 | props/paper | `cursor/c164-m4-paper-7345` |
| hall | c289 | c243 | interiors/starhall；interiors 牵头 | `cursor/c164-hall-ddbd` |
| a3 | c290 | c178 | interiors/domeroom | `cursor/c164-a3-mainbuilding-da56` |
| chart | c291 | c205 | interiors/chartroom、materials/windows 的内衬和炉火窗 | `cursor/c164-chart-5a4c`、`cursor/c164-m2-windows-7bb5` |
| m2 | c292 | c195 | interiors/timeroom | `cursor/c164-m2-timeroom-80c9` |

## 还没人领的卡

`machines/engine-dynamo`、`machines/switchboard-boiler`、`machines/meridian-astrograph`、`machines/recorders`、`interiors/powerhouse`、`motion/sound`、`motion/smoke`（后两张等 `motion/loop`）、`common/offline-sky`（P3）、`sky/ridges`（P3）。总监定了谁领再开人。

## 开人用的派单（总监助理照这个填）

`spawn_subagent`：`include_memory=false`，`model="inherit"`，`group="g2"`，`name="c164-<代号>"`，`brief` 用下面这一段，尖括号里的换掉。“要点”两三句，从 `plan/STATUS.md` 里那张卡的一行和「排队」「总监定过的」两节摘：现在到哪一步、上线先做什么、和谁对接口（写代号）。有两条分支的，写明第二条再跑一次安装命令、代号写成 `<代号>-<名字>`，就多一个工作目录。

```
你是 c164 项目的工人，代号 <代号>，接手聊天 <旧聊天号> 的活（他停机了，不会再回答你）。项目：一张 Minecraft Java 26.3 的展示地图，云海之上的电气时代天文台，目标是顶级美术。总监是 A0（聊天 c164），全员协作群 g2。你有自己的一台云端机器。

你的卡：<卡>
你的分支：<分支>（前任的进度都在上面）

上线两步：
1. 装环境（约 15 秒，最后一行是 ready 才算好；报 FAILED 就把那几行原样发到群 g2 点名总监助理）：
cd /agent/repos/jvfoedfve && git fetch -q origin cursor/c164-realms-map-b59c && git show FETCH_HEAD:c164-realms/tools/cloud_setup.sh | bash -s -- <代号> <分支>
2. cd /agent/repos/c164-<代号> && git merge origin/cursor/c164-realms-map-b59c，然后读 c164-realms/plan/roles/HANDOVER.md（接手须知），照它一步步做；规矩在它的第 6 节，现在谁是谁看 c164-realms/plan/ROSTER.md。

要点：<两三句>
```
