with open("tsb-team-squad.mjs", "r", encoding="utf-8") as f:
    s = f.read()

old_boss = """          const bossExplicitQuit = !!(window.__quitPlayers && bossIdx >= 0 && window.__quitPlayers.has(bossIdx));
          s.bossActiveInGame = bossIdx >= 0 && !bossExplicitQuit;"""
new_boss = """          s.bossActiveInGame = bossIdx >= 0;"""
if old_boss in s:
    s = s.replace(old_boss, new_boss, 1)

old_room1 = "const targetRoomNow = bq?.sH?.sH?.find?.(r => r && r.vz >= 0 && r.vz <= 3);"
new_room1 = "const targetRoomNow = ${waitMode ? 'bq?.sH?.sH?.[0]' : 'bq?.sH?.sH?.find?.(r => r && r.vz >= 0 && r.vz <= 3)'};"
if old_room1 in s:
    s = s.replace(old_room1, new_room1, 1)

old_room2 = "if (isInLobbyNow && bq?.sH && typeof bq.sH.select === \"function\" && bq.sH.wF && (!targetRoomNow || bq.sH.wF !== targetRoomNow.id))"
new_room2 = "if (!${waitMode ? 'true' : 'false'} && isInLobbyNow && bq?.sH && typeof bq.sH.select === \"function\" && bq.sH.wF && (!targetRoomNow || bq.sH.wF !== targetRoomNow.id))"
if old_room2 in s:
    s = s.replace(old_room2, new_room2, 1)

old_room3 = "const targetRoom = bq.sH.sH.find(r => r && r.vz >= 0 && r.vz <= 3);"
new_room3 = "const targetRoom = ${waitMode ? 'bq.sH.sH[0]' : 'bq.sH.sH.find(r => r && r.vz >= 0 && r.vz <= 3)'};"
if old_room3 in s:
    s = s.replace(old_room3, new_room3, 1)

with open("tsb-team-squad.mjs", "w", encoding="utf-8") as f:
    f.write(s)

print("Patched tsb-team-squad.mjs! Size:", len(s))
