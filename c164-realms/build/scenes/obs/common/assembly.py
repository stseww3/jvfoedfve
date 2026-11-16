"""Auto-discovery of a category's work-package modules.

A work package is a module in a category subpackage (build/scenes/obs/<category>/<package>.py). It
may define any of:

    build(canvas, origin) -> int        place blocks and display entities, return the entity count
    models()              -> {name: Model}
    pack(pack_dir)        -> [str]

The category's __init__.py calls category(__name__) and forwards build/models/pack to it. Adding a
package is just adding a module -- two workers never edit a shared list, so they never conflict
(S2-integrator 3.1).

Order: where two packages write the same cell the later one wins, so a package that has to come
after another (a facade over the massing, a room inside a shell) sets ORDER = <number> at the top
of its module. Modules run by ORDER (50 when not set), then by name.

Modules whose name starts with "_" and the module named "mood" (the look lives there) are skipped.
"""
import importlib
import pkgutil

SKIP = {"mood"}
DEFAULT_ORDER = 50


def _parts(package_name):
    pkg = importlib.import_module(package_name)
    names = sorted(info.name for info in pkgutil.iter_modules(pkg.__path__)
                   if not info.ispkg and not info.name.startswith("_") and info.name not in SKIP)
    mods = [importlib.import_module(f"{package_name}.{n}") for n in names]
    return sorted(mods, key=lambda m: (getattr(m, "ORDER", DEFAULT_ORDER), m.__name__))


def _built(canvas, module, first):
    """What the assembly does once a package has built. The package's view band: a module that sets
    VIEW (artkit.models.NEAR, MID, ...) has every display entity it placed brought down to that
    range, but for the models named in VIEW_KEEP (artkit.models.band). And a note of which
    entities are the package's own, canvas.entity_owners = [(first, end, 'interiors/chartroom'), ...],
    from which tools/check.py tells whose entities a board view counts."""
    view = getattr(module, "VIEW", None)
    if view is not None:
        from artkit import models as M
        M.band(canvas, first, float(view), keep=tuple(getattr(module, "VIEW_KEEP", ())))
    owners = getattr(canvas, "entity_owners", None)
    if owners is None:
        owners = canvas.entity_owners = []
    owners.append((first, len(canvas.entities), "/".join(module.__name__.split(".")[-2:])))


class Category:
    def __init__(self, package_name):
        self.package_name = package_name

    def parts(self):
        return _parts(self.package_name)

    def build(self, canvas, origin=(0, 0, 0)):
        n = 0
        for m in self.parts():
            f = getattr(m, "build", None)
            if f is not None:
                first = len(canvas.entities)
                n += int(f(canvas, origin) or 0)
                _built(canvas, m, first)
        return n

    def models(self):
        out = {}
        for m in self.parts():
            f = getattr(m, "models", None)
            if f is None:
                continue
            for key, model in (f() or {}).items():
                if key in out:
                    raise ValueError(f"model name {key!r} is defined twice in {self.package_name}")
                out[key] = model
        return out

    def pack(self, pack_dir):
        out = []
        for m in self.parts():
            f = getattr(m, "pack", None)
            if f is not None:
                out += list(f(pack_dir) or [])
        return out


def category(package_name):
    return Category(package_name)
