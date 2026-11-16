"""The lamps of the ways in the grand stair hall: the two flights, their landings, the mezzanine
and the cross gallery before them. Surveyed by astro (c360) on the master scene, block light cell
by cell (#79627): with these every cell one can stand on up there has 5 at the feet or at the
head, and of what the door's view sees through the three arches behind the pier nothing is
brighter than before (the brightest face 7, the pier's own east face 10).

Rows as lights.ROOF_WAYS: the block a caged lamp is fixed to, the way its face looks, the level
of its source (in the cell before that face), what it lights. A row that looks "down" names the
cell of a drop light's glass instead.
"""
LAMPS = [
    ((-3, 9, 0), "down", 10, "the mezzanine and the heads of both flights: a drop light on the axis, under the brass "
                             "beam, where the pier hides it from the door"),
    ((-2, 8, -6), "south", 10, "the north flight of the grand stair and the north end of the cross gallery"),
    ((-2, 8, 6), "north", 10, "the south flight of the grand stair and the south end of the cross gallery"),
]
