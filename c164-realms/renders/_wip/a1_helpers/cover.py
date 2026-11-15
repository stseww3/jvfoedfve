import sys
sys.path.insert(0, ".")
from scenes.obs.common import blocks as B
from scenes.obs.materials import _standin as S0
import scenes.obs_mat_board as S
c = S.build()
placed = {s.partition("[")[0].replace("minecraft:", "") for s in c.b.values()}
rep = [b.replace("minecraft:", "") for b in B.ids(B.REPAINTED)]
van = [b.replace("minecraft:", "") for b in B.ids(B.VANILLA)]
print("repainted", len(rep), "on board", sum(b in placed for b in rep))
print("repainted not on board:", [b for b in rep if b not in placed])
print("vanilla", len(van), "on board", sum(b in placed for b in van))
print("vanilla not on board:", [b for b in van if b not in placed])
print("placed not in table:", sorted(placed - set(rep) - set(van)))
left = S0.left()
print("still stand-ins:", len(left), sorted(left) if not isinstance(left, dict) else sorted(left))
