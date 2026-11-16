"""The lamps of the ways in the time room (interiors/timeroom, m2 c351), for the cells of its floor
that the room's own lamps leave under 5. Surveyed by a3 (c349) on the room's lights as m2 fixed them
(his branch at 5a5fa8a0, #79918): the hood of the instrument wall 12, the floor before the console
11, the rating bench 12, the reading lamp of the message desk 9, the world clocks 10, the lamp over
the blueprint 11. Between those pools two patches of the floor are left at 2 to 4, at the feet and
at the head alike: thirteen cells along the east wall north of the telephone (x 10..13, z -20..-16)
and, east of the door, the corner behind the coat stand with the way from the door to the message
desk (x 9..13, z -10..-7).

Where the lamps hang is the room's word (m2): none on the east wall south of z -16, where the door's
view (V10) has the telephone's pier and the message desk at its right edge, none hanging in the
middle of the room; the east wall's northern piers and the whole south wall, which that view has
behind it, are free, at 11 at the most. So one lamp on the pier between the two northern windows of
the east wall, far up the room where the view has the instrument wall's own light beside it, and
one on the south wall east of the door, between the coat stand and the corner, the fellow of the
lamp over the blueprint west of the door. Both are a level under the instrument wall's own sources
(12 along its head and on its console), which stays the brightest thing of the room.

One cell these do not reach: (8, -11) on the room's axis, at 4. The only wall near it is the lintel
of the door, and that carries the door's bell on the axis; the cell is left to the room's own lamps.

The levels are reckoned from the sources' cells, a level less for every cell of the way, as the
game spreads light in a clear room (the same reckoning gives the audit's numbers, cell for cell,
for the room as the assembly had it before); the light audit of the master scene (sound, c361)
is the proof.

Rows as lights.ROOF_WAYS: the block a caged lamp is fixed to, the way its face looks, the level of
its source (in the cell before that face), what it lights.
"""
LAMPS = [
    ((14, 9, -18), "west", 11, "the time room's floor along the east wall north of the telephone, between the "
                               "pool before the console and the message desk's"),
    ((11, 9, -6), "north", 11, "the time room's corner east of its door, behind the coat stand, and the way "
                               "from the door to the message desk"),
]
