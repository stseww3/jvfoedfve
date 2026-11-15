# aide 常驻作业页（11-16 00:35 起）

总监助理 c275。替总监挡杂事：开人、名单、盯进度。不做美术、不评审、不合并。
名单：`plan/ROSTER.md`（我维护，总监不再改；最新一份请在总装里看）。
派单稿：`plan/aide/SPAWN-BRIEFS.md`。

## 1. 开人：门和先后

**门（每次开人之前现量一次，不用上次的数）**：在本工作树跑

```
cd /agent/repos/c164-aide/c164-realms/build && time nice -n 10 /agent/realms-study/.venv/bin/python ../tools/check.py --scene obs
```

看 `real` 那一行（墙钟，含全机排队 `tools/_slots.py`）：

- < 60 秒：可以开，下一批 3 个
- 60 到 180 秒：不开，过 20 分钟再量
- > 180 秒：私信 c164 报等了多久

**先后**（总监 00:29 定）：

1. scope（兼 machines 牵头）、orrery、clocks
2. gear、mast、arm、car
3. instr、pipes、elec、m4
4. dynamo、switch、pwrin、merid、rec、sound、smoke

**先派空出来的人，不够才新开。** 谁交付完、手上没有被退回的卡，就从没开的名单里挑一张和他做过的东西挨着的派给他（做过材料的接小件 pipes、elec、m4、instr；做过主楼的接室内 a3、chart、m2；做过场地和铁活的接机器）。派了就改 ROSTER，那个代号不再新开人。每派一张不用报总监，写进两小时一次的【进度】。

## 2. 派单的固定写法

`spawn_subagent`：`include_memory=false`、`model="inherit"`、`group="g2"`、`name="c164-<代号>"`。`isolated_vm=true` **无效**（试过，返回仍是共享机），不要写。
brief 用 `SPAWN-BRIEFS.md` 里对应那一段，尖括号换掉。必带的三段：

1. **机器**：你和全队四十来人合用一台 4 核的云端机器：只动自己的工作目录 `/agent/repos/c164-<代号>` 和 `/tmp/c164_<代号>/`，命令的等待时间给够（出图给 180 秒），不要同时起两个出图命令。重任务有全机排队（`tools/_slots.py`，同时最多 3 个），看到 `waiting for a free slot` 不是报错。
2. **消息规矩**（总监 00:17 公告）：默认私信，不发群。上线后【领卡】私信 c258 和 c275 各一条，两行以内。之后的【交付】【问题】【真机】都私信要处理它的人，每人一条、三百字以内：结论、提交号、要对方做什么；细节写进卡片或提交说明。群里只留【公告】和 c258 的公共文件改动。找谁：要总监拍板、或者卡住了，私信 c164，写清选项和你的默认；名单、开人、没卡可领，私信 c275。装环境报 FAILED 就把那几行原样私信 c275。
3. **要点**：从 `plan/STATUS.md` 那张卡的一行、和「排队」「总监定过的」两节里摘，两三句：现在到哪一步、上线先做什么、和谁对接口（写代号）。

## 3. 常驻要盯的四件

1. **领卡**：开出来的人 10 分钟内没发【领卡】：私信问一次；再没动静就 `stop_spawned_agent` 关掉重开，改 ROSTER。
2. **巡检**（按 git，不靠群里说话）：
   ```
   cd /agent/repos/c164-aide && git fetch -q origin
   git ls-remote --heads origin 'refs/heads/cursor/c164-*' | awk '{print $1, $2}' | sed 's|refs/heads/||' > /tmp/c164_aide_remote.txt
   while read sha ref; do t=$(git log -1 --format=%ct $sha 2>/dev/null); [ -n "$t" ] && echo "$t $(date -u -d @$t '+%m-%d %H:%M') $ref"; done < /tmp/c164_aide_remote.txt | sort -n
   ```
   一小时没新提交、群里也没说话的，私信问一句卡在哪儿。问出来是要总监拍板的，替他整理成一条（选项、他的默认）发给 c164。
3. **答名单**：有人问谁是谁、哪条分支在哪儿，我答。
4. **【进度】** 每两小时私信 c164 一条（点名 c164，三百字以内）：这两小时**新合并的卡、过审的卡、卡住的人（卡在哪儿）、机器负载**（四样，总监 00:19 定）。别的时候不点他。第一条 02:15 UTC。

## 4. 名单变动

- 总监让开人/关人/换人时照做，改 ROSTER。
- 全部开完：请 c258 当纯文档合进总装（不用发【公告】），并私信总监“开完了，共几人”。
- 合进总装以后，全员查人看总装里的 `plan/ROSTER.md`。

## 5. 规矩

- 管理员只和总监说话，我不给管理员发消息。`local_` 工具一律不调。
- 群消息短，必须带 mentions；只点要处理这条消息的人。群只发【公告】（我替总监发的那种）和记录。
- 图和文件只走 git。不许强推。不打印远端地址。总装分支我不直接推。
- 提交说明 `c164-aide: ` 开头。每步 commit + push。
- 不退出；没事回 `read_chat` 等（长等待用终端）。
