"""The models of the machines/domegear test scene: the gear's own, and those of whatever else of
the dome room is in the tree (the refractor, the room's ironwork and the furniture it borrows)."""
from scenes.obs import interiors, machines, props


def build_models():
    out = {}
    for line in (machines, interiors, props):
        out.update(line.models() or {})
    return out
