"""Interiors (L7 / plan section 8): the five rooms of the observatory.

Each room is a builder ``build_<room>(c, origin, roles=B, *, version=...)`` that draws into a passed
Canvas with the room's reference corner at ``origin``. ``origin`` is the world position of the
room's local (0, 0, 0): the north-west corner of the floor layer. S2 calls these from the master
scene at each room's world position; the ``obs_int_<room>`` test scenes call them inside a stand-in
box shell (``shell.build_box``) until the main-building line (c178) hands over the real shells.

Skeleton numbers come from plan/reviews/R1-first-designs.md (0.3) and the A3 shell write-up
(plan/parts/A3-mainbuilding.md 4.6). They live as constants in ``shell.py`` until
``scenes.obs.common.skeleton`` is published, then move there. Heavy machines (A5) and modelled props
(c179) are stand-ins here (``stubs.py``); the real models drop onto the same anchor points without
changing this code.
"""
from . import shell, stubs, starhall
from .starhall import build_starhall

__all__ = ["shell", "stubs", "starhall", "build_starhall"]
