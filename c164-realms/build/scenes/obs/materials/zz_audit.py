"""Runs last in the category (the name sorts it there): checks what the material packages have written
against the rules of the category, and stops the pack from being made if one is broken. See _kit.audit."""
from . import _kit as K

# vanilla pictures this category replaces outright, as paths under assets/minecraft/textures/. A block
# picture is only replaced when no block of the game that keeps its vanilla look shows it.
REPLACED = ()


def pack(pack_dir):
    return [K.audit(pack_dir, REPLACED)]
