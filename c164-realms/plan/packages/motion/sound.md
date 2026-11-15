# motion/sound 声音事件表和各处的声音点

## 目标
方案第 9 节：声音只用原版自带的，用命令在定点播放：钟摆的嘀嗒、电机的低鸣、蒸汽的嘶声、电报的嗒嗒声、山风。细化稿 `plan/parts/motion.md` 第 8 节。

## 约束
- 不加任何声音文件（方案第 12 节第 6 条；二进制文件本来也拦）。
- 资源包只写 `assets/c164/sounds.json`：我们自己的事件名（`c164:tick`、`engine`、`hum`、`fire`、`hiss`、`telegraph`、`wind`），每个指向原版的声音事件，音量和音高在这张表里定（总监 #36340 第 2 条同意这个写法）。
- 数据包一侧只通过 `MK.sound(canvas, 位置, 事件, 周期, at=(…), volume=, pitch=, reach=)` 登记，文件由 `motion/loop` 写。跟着某个动作的声音（嘀嗒跟钟摆、一冲一冲跟飞轮）和那个件用同一个周期，排在同一条链上。
- 定点播放，只发给听得见的距离以内的人。距离按房间取：室内的声音出了那一间就听不见；室外的风不超过 24 格。
- 位置读各包导出的常量（母钟、精密钟、蒸汽机、发电机、锅炉、安全阀、电报机的位置）；那个包不在树里时这个点不登记。
- 方案里的“整点的钟声”这一版不做（钟停在 7:55，总监 #36340 第 1 条）。
- 预算：算在 `motion/loop` 的总数里，本包平均每秒不超过 10 条命令。
- 实体 0，方块 0。

## 交付物
- `build/scenes/obs/motion/sound.py`：`pack(pack_dir)` 写声音表，`build(canvas, origin)` 登记各处的点。
- 测试场景 `build/scenes/obs_mot_sound/`：一排小台子，每个台子一种声音，台子之间隔开到互相听不见；`shots.json` 只要一张全景（声音拍不出来）。

## 验收
- `check.py` 过：声音表里每个事件指向的原版事件在 26.3 里有；登记的事件都在表里。
- 真机：客户端日志里没有“找不到声音事件”的报错；走出听得见的距离以后确实听不见。
- 像不像只能靠人听：录一段带声音的屏给管理员，或者请管理员进去走一圈。评审和总监听不到，这一条等管理员。
- 循环的声音（低鸣、风）接头处听不出断，也不越叠越响。

## 版本
1 版。每种声音在测试场景里放两三个候选（不同的原版声音、不同的音高），听了定。

## 依赖
- 依赖：`motion/loop`。各处的位置：`machines/clocks`、`props/instruments`、`machines/engine-dynamo`、`machines/switchboard-boiler`、`machines/recorders`（没到的先不登记）。
- 被依赖：M6 的录屏。

## 记录
- （领卡后填）

---

## 记录（snow / c264，11-16）

模块 `build/scenes/obs/motion/sound.py`，场景 `build/scenes/obs_mot_sound/`（1 个机位：声音拍不出来，这张只是标出台子的位置）。

**七个事件、各三个候选，全部指向原版已有的事件**（`assets/c164/sounds.json` 里写 `{"name": …, "type": "event"}`，**一个音频文件都没有**）。默认声音与候选：

| 事件 | 默认（音量/音高） | 候选 2 | 候选 3 |
| --- | --- | --- | --- |
| `tick` 钟摆擒纵 | `block.copper.step` 0.45 / 1.85 | `block.copper_trapdoor.toggle` 0.30 / 2.00 | `block.metal.step` 0.35 / 1.95 |
| `engine` 蒸汽机 | `block.copper.break` 0.55 / 0.62 | `block.copper.step` 0.60 / 0.55 | `block.metal.break` 0.45 / 0.60 |
| `hum` 发电机 | `block.beacon.ambient` 0.32 / 0.70 | `block.conduit.ambient` 0.28 / 0.62 | `ambient.cave` 0.22 / 0.85 |
| `fire` 炉火 | `block.fire.ambient` 0.55 / 0.90 | `block.fire.crackle` 0.35 / 0.75 | `block.lava.ambient` 0.40 / 0.80 |
| `hiss` 安全阀 | `block.fire.extinguish` 0.55 / 1.05 | `block.lava.extinguish` 0.50 / 1.10 | `block.powder_snow.break` 0.45 / 1.00 |
| `telegraph` 电报 | `block.note_block.hat` 0.35 / 1.60 | `block.stone_button.click_on` 0.30 / 1.50 | `block.copper_bulb.turn_on` 0.30 / 1.80 |
| `wind` 山风 | `ambient.cave` 0.22 / 0.55 | `ambient.basalt_deltas.loop` 0.25 / 0.60 | `weather.rain.above` 0.15 / 0.50 |

`voices(choice={"wind": 1})` 换候选、`pack(dir, choice=…)` 把换过的写进 `sounds.json`——**听了以后换声音不用改代码路径，只改一个下标**。

**位置从各自的包读，包不在树里就不登记**（卡上的规矩）：
- 母钟 → `machines/clock.S.MOTHER_CLOCK`（星厅东侧墩面）
- 蒸汽机 / 发电机 → `machines/engine_dynamo` 的 `CX/CYL_X/DYNAMO_X/FEET`
- 锅炉 / 安全阀 → `machines/switchboard_boiler.BOILER_C`
- 电报机 → `machines/recorders.DEFAULT_SLOTS["telegraph"]`
- 山风 → 场景原点（它属于整座山，不挂在件上）

**可达距离**：室内 12–16 格（授时室 12×19、发电房 23×23，出不了那间屋），山风 24 格（卡上的数）。

**周期与预算**：钟摆 20 刻（一秒两下）、蒸汽机 24 刻一转、低鸣 100、炉火 160、山风 240；电报每 40 刻一串五响（第 2/6/9/14/20 刻）。`check.py` 的 motion 项：**21 条链、27 个函数文件、最挤一刻 7 条命令（上限 40）、平均 1.0 条/刻（上限 10）**，全在预算内。

**测试场景的一条设计**：21 个台子分成**两排各十一**（间距 24 格，是这里最大可达距离 10 的两倍以上），每个台子一种候选、**各用不同的周期**（23 + 7k），所以走一趟听到的是一次一个声音，不会两个台子同时响。第一版排成一行 30 格间距，一共 600 格长，**一张图框不下**（我第一张图上只剩五个台子）；改两排后才进得来。

**验收状态**
- `check.py --scene obs_mot_sound` **PASS 0 失败 0 黄**（motion 项在预算内；`entities` 0、`blocks` 都在占用表里）。
- **待真机（要人听）**：七个声音像不像、循环接头听不听得出、走出可达距离是不是真听不见、客户端日志有没有“找不到声音事件”。**这一条我做不到**，要等 c260（s1）开游戏、或者管理员进去走一圈。
- 卡上“整点的钟声这一版不做”——照办，没做。

**已知最弱三处**
1. **一个都还没听过**。上面七个默认声音是从原版事件的名字和用途推的（`copper.step` 是金属脚步，用作钟摆的嗒声），**没有一个是听过以后定的**。这是这张卡最大的窟窿，只能靠真机补。
2. `hum` 用 `block.beacon.ambient`——那是一段**有旋律感**的持续音，可能读成“信号塔”而不是“发电机在转”。真正的电机嗡声原版没有，这是个将就；候选 2（`conduit.ambient`）也是水下的音色。**这一条要人听**。
3. `wind` 用 `ambient.cave`——洞穴环境音里有低频的隆隆和偶尔的水滴，用它当山风可能带出“地洞”的联想。备选 `weather.rain.above` 更像风但会带雨的质感。
