"""lined() with the delivered shell's room_at() against the table it replaces (ROOM_BAYS)."""
from scenes.obs.materials import windows as W
from scenes.obs.main import shell, facade

table = [w for w in facade.windows() if W.lining_of(w["glass"])]
print("lit windows of the facade:", len(table))
real, by_table = [], []
for w in table:
    cells, (dx, dz), (y0, y1) = w["cells"], w["inward"], w["y"]
    x, z = cells[len(cells) // 2]
    room = shell.room_at(x + dx, (y0 + y1) // 2, z + dz)
    in_table = w["bay"] in W.ROOM_BAYS.get((w["front"], w["storey"]), ())
    mark = "" if (room is not None) == in_table else "   <-- differs"
    print(f"  {w['front']:5} {w['storey']:5} bay {w['bay']:3}  glass {str(w['glass'])[:28]:28} inside ({x + dx}, {(y0 + y1) // 2}, {z + dz}) "
          f"room_at: {room!s:12} table: {in_table}{mark}")
    real.append(room is not None)
    by_table.append(in_table)
print("lined by room_at:", sum(real), " by the table:", sum(by_table))
print("lined():", len(W.lined()), "windows")
