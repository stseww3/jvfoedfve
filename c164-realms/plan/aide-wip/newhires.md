# 新开的六人（总监 11-16 08:36；总控 08:36 独占了节点）

到岗（【领卡】）时各告诉一句：

- c356 rec：machines/recorders，node101。对口：clocks（c345，母钟和记录仪怎么接）。审批人 cr3（c347）。
- c357 smoke：motion/smoke，node102。牵头 a2（c322，MK 的循环和登记）。审批人 cr2（c333）。
- c358 vault：interiors/platevault，node103。对口：m1（c335，仪器、配电板）、shell（c325，空腔和门洞）。审批人 cr4（c337）。
- c359 clkrm：interiors/clockroom，node104。搭档 tower（c327：井 5×5、沉格背板、窗后光源、开口，他在备）。审批人 cr4。
- c360 astro：简报写的是 astroroom，改做 interiors/batteryroom，node105，分支 cursor/c164-astro-batteryroom-f3-<后缀>（从总装头开）。
  卡 plan/packages/interiors/batteryroom.md；前任 stair 的草图在 cursor/c164-stair-batteryroom-f3-b330 @ 0aae4ace
  （plan/packages/interiors/batteryroom-sketch.md 交接说明，plan/parts/figs/int-batteryroom-sketch.png，int_batteryroom_sketch.py）。
  三处对口：hall（c348）的 aisle_doors() 读 interiors.batteryroom.HALL_DOOR=(7,-6)，名字要留；
  m2（c351）的 timeroom.py 两根立管在 x 6、x 9 上来，草图画的是 6.5、9.5，要对一下；shell（c325）开空腔的门洞和楼板。
  搭档 mast（c346）：配电板和铜排他在做（和 machines/board 一家：石板、黄铜圈、米色表盘，绿只在刻度和针上）。
  snow 给总监报过的默认：地下窗里侧整块铁百叶挡光，ext_base 有房没房并排比。审批人 cr4。
- c361 sound：motion/sound，node106。牵头 a2。审批人 cr2。

后四个（n7 到 n10）总控说先别开（没机器）。
