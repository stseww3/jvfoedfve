"""The game's own pictures and shapes, read the way the game reads them.

Assets looks a file up in the resource packs given to it and then in the client jar, so what comes
out is what the game would show with those packs on: block states pick models, models inherit from
their parents, faces name textures. Nothing here draws; render.py does.

Coordinates of a model are in blocks (the files count in sixteenths). Face order everywhere is the
game's: down, up, north, south, west, east.
"""
import io
import json
import math
import os
import zipfile

import numpy as np
from PIL import Image

FACES = ("down", "up", "north", "south", "west", "east")
NORMALS = np.array([(0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0)], dtype=float)
CENTRE = np.array([0.5, 0.5, 0.5])


def split(ref):
    ns, sep, path = ref.partition(":")
    return (ns, path) if sep else ("minecraft", ref)


def rot(axis, degrees):
    """Right-handed turn about one axis as a 3x3 matrix."""
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=float)
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=float)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)


def nearest_face(normal):
    """Index of the face direction a normal is closest to (what the game calls the quad's direction)."""
    return int(np.argmax(NORMALS @ np.asarray(normal, dtype=float)))


class Element:
    """One box of a model, placed: `inv` and `off` take a point of the block (or of the item's
    unit cube) into the box's own frame, where it lies between lo and hi."""

    __slots__ = ("lo", "hi", "inv", "off", "tex", "uv", "uvrot", "tint", "cull", "override", "emit", "world_uv", "aligned")

    def __init__(self):
        self.tex = [None] * 6      # texture reference per face, None where the box has no face
        self.uv = np.zeros((6, 4))
        self.uvrot = [0] * 6
        self.tint = [-1] * 6
        self.cull = [-1] * 6       # the neighbour (direction number, as placed) that can hide the face
        self.override = -1         # face index whose shade is used for every face, or -1
        self.emit = 0
        self.world_uv = False      # uvlock: the picture keeps its attitude when the model is turned
        self.aligned = True

    def faces_out(self):
        """Per face: the direction it looks in once placed, as a unit vector."""
        m = self.inv.T                              # normals go with the inverse transpose
        out = []
        for n in NORMALS:
            v = m @ n
            out.append(v / np.linalg.norm(v))
        return out


def default_uv(lo, hi, face):
    """The picture area a face shows when the model does not say (sixteenths)."""
    fx, fy, fz = (lo * 16.0)
    tx, ty, tz = (hi * 16.0)
    return {
        0: (fx, 16 - tz, tx, 16 - fz), 1: (fx, fz, tx, tz),
        2: (16 - tx, 16 - ty, 16 - fx, 16 - fy), 3: (fx, 16 - ty, tx, 16 - fy),
        4: (fz, 16 - ty, tz, 16 - fy), 5: (16 - tz, 16 - ty, 16 - fz, 16 - fy),
    }[face]


class Assets:
    def __init__(self, jar, packs=()):
        self.zip = zipfile.ZipFile(jar)
        self.names = set(self.zip.namelist())
        self.packs = [p for p in packs if p]
        self._json, self._model, self._tex = {}, {}, {}

    # ---- files -------------------------------------------------------------------------------
    def read(self, path):
        for p in self.packs:
            f = os.path.join(p, path)
            if os.path.isfile(f):
                with open(f, "rb") as fh:
                    return fh.read()
        if path in self.names:
            return self.zip.read(path)
        return None

    def json(self, path):
        if path not in self._json:
            raw = self.read(path)
            self._json[path] = None if raw is None else json.loads(raw)
        return self._json[path]

    def texture(self, ref):
        """RGBA picture (h, w, 4) of a texture reference; the first frame of an animated one."""
        ns, path = split(ref)
        key = f"{ns}:{path}"
        if key not in self._tex:
            raw = self.read(f"assets/{ns}/textures/{path}.png")
            if raw is None:
                img = np.zeros((16, 16, 4), dtype=np.uint8)
                img[..., :] = (248, 0, 248, 255)
                img[:8, :8] = img[8:, 8:] = (0, 0, 0, 255)
            else:
                img = np.array(Image.open(io.BytesIO(raw)).convert("RGBA"))
                meta = self.json(f"assets/{ns}/textures/{path}.png.mcmeta") or {}
                if "animation" in meta:
                    w = meta["animation"].get("width", min(img.shape[0], img.shape[1]))
                    h = meta["animation"].get("height", w)
                    img = img[:h, :w]
            self._tex[key] = img
        return self._tex[key]

    # ---- models ------------------------------------------------------------------------------
    def model(self, ref):
        """A model with everything it inherits: {"textures", "elements", "ao"}."""
        ns, path = split(ref)
        key = f"{ns}:{path}"
        hit = self._model.get(key)
        if hit is None:
            data = self.json(f"assets/{ns}/models/{path}.json") or {}
            hit = {"textures": {}, "elements": None, "ao": True}
            if "parent" in data:
                par = self.model(data["parent"])
                hit = {"textures": dict(par["textures"]), "elements": par["elements"], "ao": par["ao"]}
            for k, v in data.get("textures", {}).items():
                hit["textures"][k] = v["sprite"] if isinstance(v, dict) else v
            if "elements" in data:
                hit["elements"] = data["elements"]
            if "ambientocclusion" in data:
                hit["ao"] = bool(data["ambientocclusion"])
            self._model[key] = hit
        return hit

    @staticmethod
    def _texture_of(model, name):
        for _ in range(16):
            if not name.startswith("#"):
                return name
            name = model["textures"].get(name[1:])
            if name is None:
                return None
        return None

    def elements(self, ref, x=0, y=0, uvlock=False):
        """The boxes of a model turned as a block state turns it (x, y in degrees)."""
        model = self.model(ref)
        turn = rot("y", -y) @ rot("x", -x)
        out = []
        for el in model["elements"] or []:
            e = Element()
            e.lo = np.array(el["from"], dtype=float) / 16.0
            e.hi = np.array(el["to"], dtype=float) / 16.0
            own, origin = np.eye(3), CENTRE
            r = el.get("rotation")
            if r:
                origin = np.array(r["origin"], dtype=float) / 16.0
                if "axis" in r or "angle" in r:
                    own = rot(r["axis"], r.get("angle", 0.0))
                else:
                    own = rot("z", r.get("z", 0.0)) @ rot("y", r.get("y", 0.0)) @ rot("x", r.get("x", 0.0))
                if r.get("rescale") and not np.allclose(own, np.eye(3)):
                    own = own @ np.diag([1.0 / np.abs(own[:, i]).max() for i in range(3)])
            back = np.linalg.inv(own)
            e.inv = back @ turn.T
            e.off = origin + back @ (CENTRE - origin) - e.inv @ CENTRE
            e.aligned = bool(np.allclose(np.abs(e.inv).max(axis=1), 1.0, atol=1e-6) and np.allclose(np.abs(e.inv).sum(axis=1), 1.0, atol=1e-6))
            e.world_uv = bool(uvlock and (x % 360 or y % 360))
            e.emit = int(el.get("light_emission", 0))
            if "shade_direction_override" in el:
                e.override = FACES.index(el["shade_direction_override"])
            elif el.get("shade") is False:
                e.override = 1
            for name, face in el["faces"].items():
                f = FACES.index(name)
                e.tex[f] = self._texture_of(model, face["texture"])
                e.uv[f] = face.get("uv") or default_uv(e.lo, e.hi, f)
                e.uvrot[f] = int(face.get("rotation", 0)) // 90 % 4
                e.tint[f] = int(face.get("tintindex", -1))
                if "cullface" in face:
                    e.cull[f] = nearest_face(turn @ NORMALS[FACES.index(face["cullface"])])
            out.append(e)
        return out, model["ao"]

    # ---- block states ------------------------------------------------------------------------
    @staticmethod
    def _matches(when, props):
        if "OR" in when:
            return any(Assets._matches(w, props) for w in when["OR"])
        if "AND" in when:
            return all(Assets._matches(w, props) for w in when["AND"])
        return all(str(props.get(k)) in str(v).split("|") for k, v in when.items())

    def parts(self, name, props):
        """What a block state shows: a list of parts, each a list of weighted choices
        (weight, model, x, y, uvlock). Empty when the block has no model of its own."""
        data = self.json(f"assets/minecraft/blockstates/{name}.json")
        if data is None:
            return []

        def choices(apply):
            items = apply if isinstance(apply, list) else [apply]
            return [(int(a.get("weight", 1)), a["model"], int(a.get("x", 0)), int(a.get("y", 0)), bool(a.get("uvlock", False)))
                    for a in items]

        if "variants" in data:
            for key, apply in data["variants"].items():
                conds = [c.partition("=") for c in key.split(",") if c]
                if all(str(props.get(k)) == v for k, _, v in conds):
                    return [choices(apply)]
            return []
        return [choices(part["apply"]) for part in data["multipart"] if "when" not in part or self._matches(part["when"], props)]

    def multipart(self, name):
        """Is the block put together from parts that each pick their own variant?"""
        return "multipart" in (self.json(f"assets/minecraft/blockstates/{name}.json") or {})

    def item_model(self, ref):
        """The model an item definition points at (plain "minecraft:model" definitions only)."""
        ns, path = split(ref)
        data = self.json(f"assets/{ns}/items/{path}.json") or {}
        model = data.get("model", {})
        while model.get("type", "").endswith("composite") and model.get("models"):
            model = model["models"][0]
        return model.get("model")
