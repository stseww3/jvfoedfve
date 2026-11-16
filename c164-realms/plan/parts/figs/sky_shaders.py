#!/usr/bin/env python3
"""Checks of the shaders that carry the look (build/scenes/obs/sky/_shaders.py; card sky/safe-look).

    python plan/parts/figs/sky_shaders.py [--glslc <glslc or glslang command>] [--keep <dir>]
        [--panorama <png>] [--camera-y 201.62] [--look blue]

1. Writing the files proves that every patch still finds its place in this game's own text.
2. The arithmetic, on the numpy twin: the closed form of the afterglow fan against the fan's mesh
   as SkyRenderer builds it; the zenith and the horizon are the look's; sky, far sea and what
   things fade to meet at the horizon; a block of the cloud sea shows the colour of the painted
   sea behind it; how much fog lies on the front in V1 and on the building in V12.
3. Compiled as the game compiles: with the game's own build of shaderc, fetched from Mojang like
   the client jar (sky_shaderc.py), or with a glslc or glslang command (--glslc, C164_GLSLC);
   skipped with a note when neither is to be had. Every pipeline's pair of shaders under its
   defines with our files in place, with and without the macros the device adds. Ours has to
   compile wherever the game's own text compiles, and every fragment input needs a vertex output
   of the same type at its location (the game refuses the pipeline otherwise). The pipelines are
   the table read off RenderPipelines of 26.3 (PAIRS); the three passes of the game's transparency
   are added for every shader that includes oit.glsl.
4. --panorama: the sky all round as the shaders paint it, seen from --camera-y.

It prints what it finds and ends with `result: PASS` or `result: FAIL`. The game alone proves that
a shader links and draws: this is what can be known before a trip to the real machine.
"""
import argparse
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJECT, "build"))
sys.path.insert(0, os.path.join(PROJECT, "tools"))
sys.path.insert(0, HERE)

from scenes.obs.sky import _shaders as S  # noqa: E402
from scenes.obs.sky import mood  # noqa: E402

# (vertex shader, fragment shader, defines) of every pipeline of RenderPipelines (26.3)
PAIRS = """
animate_sprite animate_sprite_blit
animate_sprite animate_sprite_interpolate
block block
block block ALPHA_CUTOUT
clouds clouds
debug_point position_color
entity entity
entity entity ALPHA_CUTOUT
entity entity ALPHA_CUTOUT,APPLY_TEXTURE_MATRIX,NO_OVERLAY,NO_CARDINAL_LIGHTING
entity entity ALPHA_CUTOUT,EMISSIVE,NO_OVERLAY,NO_CARDINAL_LIGHTING
entity entity ALPHA_CUTOUT,EMISSIVE,NO_OVERLAY,NO_CARDINAL_LIGHTING,APPLY_TEXTURE_MATRIX
entity entity ALPHA_CUTOUT,EMISSIVE,NO_OVERLAY,NO_CARDINAL_LIGHTING,APPLY_TEXTURE_MATRIX,OIT_ADDITIVE
entity entity ALPHA_CUTOUT,NO_OVERLAY
entity entity ALPHA_CUTOUT,NO_OVERLAY,PER_FACE_LIGHTING
entity entity ALPHA_CUTOUT,PER_FACE_LIGHTING
entity entity ALPHA_CUTOUT,PER_FACE_LIGHTING,DISSOLVE
entity entity EMISSIVE,ALPHA_CUTOUT,PER_FACE_LIGHTING
entity entity EMISSIVE,NO_OVERLAY,NO_CARDINAL_LIGHTING
entity entity GLINT
entity entity GLINT,ALPHA_CUTOUT,NO_OVERLAY,PER_FACE_LIGHTING
entity entity NO_OVERLAY
glint glint
gui gui
item item ALPHA_CUTOUT
item item GLINT,ALPHA_CUTOUT
item item GLINT,GLINT_SPECIAL,ALPHA_CUTOUT
panorama panorama
particle particle
position_color position_color
position_tex_color position_tex_color
position_tex position_tex
rendertype_beacon_beam rendertype_beacon_beam
rendertype_crumbling rendertype_crumbling
rendertype_end_portal rendertype_end_portal PORTAL_LAYERS
rendertype_entity_shadow rendertype_entity_shadow
rendertype_leash rendertype_leash
rendertype_lightning rendertype_lightning
rendertype_lightning rendertype_lightning OIT_ADDITIVE
rendertype_lines rendertype_lines
rendertype_outline rendertype_outline
rendertype_water_mask rendertype_water_mask
screenquad blit_depth
screenquad blit_screen
screenquad integrate_depth
screenquad lightmap
screenquad oit_composite OIT,OIT_WAVELET_RANK,OIT_COEFF_COUNT,OIT_COEFF_ATTACHMENT_COUNT
screenquad oit_depth_bounds_cull OIT,OIT_WAVELET_RANK,OIT_COEFF_COUNT,OIT_COEFF_ATTACHMENT_COUNT
sky sky
stars stars
terrain terrain
terrain terrain ALPHA_CUTOUT
terrain terrain ALPHA_CUTOUT,MULTIDRAW_TERRAIN
terrain terrain MULTIDRAW_TERRAIN
text text
text text IS_GRAYSCALE
text text IS_GRAYSCALE,IS_SEE_THROUGH
text text IS_GUI
text text IS_GUI,IS_GRAYSCALE
text text IS_SEE_THROUGH
world_border world_border
world_border world_border OIT_ADDITIVE
"""
VALUES = {"ALPHA_CUTOUT": "0.1", "PORTAL_LAYERS": "15", "OIT_WAVELET_RANK": "3", "OIT_COEFF_COUNT": "8",
          "OIT_COEFF_ATTACHMENT_COUNT": "2"}
OIT = ["OIT", "OIT_WAVELET_RANK", "OIT_COEFF_COUNT", "OIT_COEFF_ATTACHMENT_COUNT"]
OIT_PASSES = (["OIT_ACCUMULATE"], ["OIT_ALPHA_ONLY", "OIT_DEPTH_BOUNDS"], ["OIT_ALPHA_ONLY", "OIT_TRANSMITTANCE"])
# what the game's compiler is given (GlslCompiler): Vulkan 1.2, bindings handed out, no optimising
OPTIONS = ["--target-env=vulkan1.2", "-fauto-bind-uniforms", "-g", "-O0"]
MACROS = ("RENDERPEARL_DEPTH_IS_ZERO_TO_ONE", "RENDERPEARL_EXPLICIT_DEPTH_INVARIANCE",
          "RENDERPEARL_INSTANCE_INDEX_INCLUDES_BASE_INSTANCE")
INTERFACE = re.compile(r"layout\s*\(\s*location\s*=\s*(\d+)\s*\)\s*((?:flat|smooth|noperspective)\s+)?(in|out)\s+(\w+)\s+(\w+)")


def pairs():
    out = []
    for line in PAIRS.strip().splitlines():
        parts = line.split()
        out.append((parts[0], parts[1], parts[2].split(",") if len(parts) > 2 else []))
    return out


# ---- the arithmetic ------------------------------------------------------------------------------
def fan_mesh(twin, d):
    """The share of the afterglow at directions d on the fan as SkyRenderer builds it: the apex 100
    out on the afterglow's side with the colour's alpha, 16 rim points 120 out with none, the rim
    lifted by 40 * alpha towards the apex's side."""
    a = twin.n["glow_alpha"]
    west, north = twin.west, twin.north
    up = np.array([0.0, 1.0, 0.0])
    apex = 100.0 * west
    rim = [120.0 * math.cos(t) * west + 40.0 * a * math.cos(t) * up + 120.0 * math.sin(t) * north
           for t in np.linspace(0.0, 2.0 * math.pi, 17)]
    out = np.zeros(len(d))
    for p, q in zip(rim[:-1], rim[1:]):
        # the ray s * d meets the triangle apex, p, q where s * d = apex + u (p - apex) + v (q - apex)
        m = np.stack([p - apex, q - apex], axis=1)                      # 3 x 2
        for i, ray in enumerate(d):
            sol, *_ = np.linalg.lstsq(np.column_stack([m, -ray]), -apex, rcond=None)
            u, v, s = sol
            if s > 0.0 and u >= -1e-9 and v >= -1e-9 and u + v <= 1.0 + 1e-9 \
                    and np.allclose(apex + m @ sol[:2], s * ray, atol=1e-6):
                out[i] = max(out[i], a * (1.0 - u - v))
    return out


def directions(azimuths, elevations):
    """Unit vectors: azimuth in degrees from west towards north, elevation in degrees."""
    out = []
    for az in azimuths:
        for el in elevations:
            ca, sa, ce, se = (math.cos(math.radians(az)), math.sin(math.radians(az)),
                              math.cos(math.radians(el)), math.sin(math.radians(el)))
            out.append((-ca * ce, se, -sa * ce))
    return np.array(out)


def arithmetic(twin, camera_y):
    ok = True
    n = twin.n
    print(f"look {n['look']}: sky {mood._hex(n['sky'])} fog {mood._hex(n['fog'])} share {n['share']:.4f} "
          f"glow {mood._hex(n['glow'])} x {n['glow_alpha']}, sea {mood._hex(n['sea'])} at y {n['sea_y']:.0f}")
    # 1. the fan
    d = directions((0, 10, 30, 60, 85, 120, 180), (-60, -20, -5, -1, 0.5, 2, 4, 6, 8))
    closed, mesh = twin.fan(d), fan_mesh(twin, d)
    worst = float(np.max(np.abs(closed - mesh)))
    good = worst < 0.02
    ok &= good
    print(f"[{'ok' if good else 'FAIL'}] afterglow fan, closed form against the mesh: {len(d)} directions, "
          f"largest difference {worst:.4f} (the mesh has 16 flat sides)")
    # 2. the seen colours of the look
    up = twin.sky_at(np.array([[0.0, 1.0, 0.0]]), camera_y)[0]
    east = twin.sky_at(directions((180,), (0.01,)), camera_y)[0]
    v = mood.look(n["look"])
    for name, got, want in (("zenith", up, v["zenith"]), ("horizon away from the west", east, v["horizon"])):
        gap = float(np.max(np.abs(got - np.array(mood._rgb(want)))))
        good = gap < 1.5 / 255.0
        ok &= good
        print(f"[{'ok' if good else 'FAIL'}] {name}: painted {mood._hex(got)}, the look states {want}")
    # 3. no step at the horizon: the sky, the far sea, what blocks fade to and what the edge of the view fades to
    for az in (0, 20, 45, 90, 180):
        hi, lo = directions((az,), (0.001,)), directions((az,), (-0.001,))
        sky, sea = twin.sky_at(hi, camera_y)[0], twin.sky_at(lo, camera_y)[0]
        band_hi, band_lo = twin.band(hi)[0], twin.band(lo)[0]
        behind_hi, behind_lo = twin.behind(hi, camera_y)[0], twin.behind(lo, camera_y)[0]
        gap = max(float(np.max(np.abs(x - sky))) for x in (sea, band_hi, band_lo, behind_hi, behind_lo))
        good = gap < 1.0 / 255.0
        ok &= good
        print(f"[{'ok' if good else 'FAIL'}] horizon, {az:3d} degrees from west: sky {mood._hex(sky)} | sea {mood._hex(sea)} "
              f"| things fade to {mood._hex(band_hi)} above, {mood._hex(band_lo)} below")
    # 4. the block sea and the painted sea are one: a block of the sea's colour at any distance shows the
    #    colour painted behind it, with or without the game's fog at the edge of the view
    eye = camera_y - n["sea_y"]
    worst = 0.0
    for el in (-60, -30, -11, -5, -2, -0.5):
        d = directions((0, 60, 180), (el,))
        reach = eye / np.maximum(-d[:, 1], 1e-9)
        painted = twin.sky_at(d, camera_y)
        for edge in (0.0, 0.5, 1.0):
            block = twin.apply(twin.sea_colour, reach, d, camera_y, edge)
            worst = max(worst, float(np.max(np.abs(block - painted))))
    good = worst < 0.5 / 255.0
    ok &= good
    print(f"[{'ok' if good else 'FAIL'}] a sea block where the painted sea begins: largest difference {worst * 255.0:.2f} of 255")
    # 4b. what lies on the sea is gone into the painted sea before the blocks end, whatever its own colour,
    #     and what stands on the hilltop takes none of it
    worst, rim = 0.0, mood.FOG_END
    for height in (0.0, 4.0, mood.LEVEL_FULL):
        for az in (0, 60, 180):
            drop = eye - height
            away = math.hypot(rim, drop)
            d = np.array([[-math.cos(math.radians(az)) * rim / away, -drop / away, -math.sin(math.radians(az)) * rim / away]])
            for colour in ((1.0, 1.0, 1.0), (0.0, 0.0, 0.0)):
                worst = max(worst, float(np.max(np.abs(twin.apply(colour, away, d, camera_y) - twin.sky_at(d, camera_y)))))
    good = worst < 0.5 / 255.0
    ok &= good
    print(f"[{'ok' if good else 'FAIL'}] white and black things on the sea (0, 4, {mood.LEVEL_FULL:.0f} above its top) {rim:.0f} blocks away on the map: "
          f"largest difference to the painted sea {worst * 255.0:.2f} of 255 (the blocks end at 160)")
    # 5. how much fog lies on what (the director's marks, #68701: the front in V1 0.10 at most, the
    #    building in V12 0.25 at most)
    import boardshots
    from scenes.obs.common import skeleton as SK
    views = {key: shot for (shot, _, _), (_, _, key, _) in zip(boardshots.views(), boardshots.VIEWS)}
    front = (SK.WALL_E + 2.0, 9.0, SK.AXIS_Z)
    marks = (("V1", "the front, mid-height", front, 0.10), ("V1", "the dome's apex", (SK.DOME_AXIS[0], SK.DOME_APEX, SK.DOME_AXIS[1]), 0.10),
             ("V12", "the front, mid-height", front, 0.25), ("V12", "the dome's apex", (SK.DOME_AXIS[0], SK.DOME_APEX, SK.DOME_AXIS[1]), 0.25),
             ("V12", "the sunset platform", (SK.SUNSET_PLATFORM["centre"][0] - 18.0, 0.0, 0.5), 0.25))
    for key, what, point, most in marks:
        pos = np.array(views[key]["pos"], dtype=float)
        ray = np.array(point, dtype=float) - pos
        dist = float(np.linalg.norm(ray))
        share = float(twin.fogged(dist, pos[1] + mood.GROUND_Y, ray[1] / dist))
        before = min(1.0, max(0.0, (dist - mood.FOG_START) / (mood.REGISTRY_FOG_END - mood.FOG_START)))
        if float(np.max(mood.levelled(math.hypot(ray[0], ray[2]), pos[1] + mood.GROUND_Y + ray[1] - n["sea_y"]))) > 0.0:
            good = False
        good = share <= most
        ok &= good
        print(f"[{'ok' if good else 'FAIL'}] {key}, {what}: {dist:5.1f} blocks from an eye {pos[1] + mood.GROUND_Y - n['sea_y']:5.1f} above the sea: "
              f"fog {share:.3f} (at most {most:.2f}; the registry look's {before:.2f})")
    print(f"       the far sea from y {camera_y:.0f} ({eye:.0f} above it): the share of the horizon band at")
    for el in (-30, -11, -5, -2, -1, -0.3):
        reach = eye / math.sin(math.radians(-el))
        share = float(twin.fogged(reach, camera_y, math.sin(math.radians(el))))
        print(f"         {el:6.1f} degrees: {reach:7.0f} blocks out, {share:.2f}")
    return ok


def panorama(twin, path, camera_y, width=1440, height=480):
    """The whole sky: west in the middle, north to its right; 60 degrees below to 90 above."""
    from PIL import Image
    az = (np.arange(width) + 0.5) / width * 360.0 - 180.0
    el = 90.0 - (np.arange(height) + 0.5) / height * 150.0
    a, e = np.meshgrid(np.radians(az), np.radians(el))
    d = np.stack([-np.cos(a) * np.cos(e), np.sin(e), -np.sin(a) * np.cos(e)], axis=-1).reshape(-1, 3)
    img = (np.clip(twin.sky_at(d, camera_y), 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).reshape(height, width, 3)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    Image.fromarray(img).save(path)
    print(f"panorama ({width} x {height}, west in the middle, from y {camera_y:.0f}) -> {path}")


# ---- the compilers -------------------------------------------------------------------------------
def _macros(macros, defines):
    return {d: VALUES.get(d, "") for d in list(macros) + list(defines)}


class Glslc:
    """glslc (shaderc's command) or glslang (its front end) as a command."""

    def __init__(self, command, work):
        self.command, self.work = command, work
        self.cache = {}

    def describe(self):
        version = subprocess.run([self.command, "--version"], capture_output=True, text=True).stdout.strip().splitlines()
        return version[0] if version else self.command

    def tree(self, name, texts):
        """A folder holding the shaders: core/<file> and include files under the names the game's
        #include <minecraft:x.glsl> asks for."""
        root = os.path.join(self.work, name)
        os.makedirs(os.path.join(root, "core"))
        os.makedirs(os.path.join(root, "inc"))
        for rel, text in texts.items():
            folder, _, base = rel.partition("/")
            path = os.path.join(root, "core", base) if folder == "core" else os.path.join(root, "inc", "minecraft:" + base)
            with open(path, "w") as fh:
                fh.write(text)
        return root

    def run(self, root, shader, defines, preprocess=False, macros=MACROS):
        """(ok, output). shader is core/<name>.vsh or .fsh."""
        key = (root, shader, tuple(defines), preprocess, tuple(macros))
        if key not in self.cache:
            vertex = shader.endswith(".vsh")
            flags = [f"-D{k}={v}" if v else f"-D{k}" for k, v in _macros(macros, defines).items()]
            if os.path.basename(self.command).startswith("glslang"):
                # glslang's own command: the same front end without shaderc around it. It takes
                # #include only when the extension is asked for, which shaderc does by itself.
                cmd = [self.command, "--target-env", "vulkan1.2", "--auto-map-bindings", "-S", "vert" if vertex else "frag",
                       "-P#extension GL_GOOGLE_include_directive : enable", f"-I{os.path.join(root, 'inc')}", *flags]
                cmd += ["-E"] if preprocess else ["-V", "-o", os.path.join(self.work, "out.spv")]
            else:
                cmd = [self.command, *OPTIONS, f"-fshader-stage={'vertex' if vertex else 'fragment'}",
                       "-I", os.path.join(root, "inc"), *flags]
                cmd += ["-E"] if preprocess else ["-o", os.path.join(self.work, "out.spv")]
            done = subprocess.run(cmd + [os.path.join(root, shader)], capture_output=True, text=True)
            good = done.returncode == 0
            self.cache[key] = (good, done.stdout if preprocess and good else done.stdout + done.stderr)
        return self.cache[key]


class Game:
    """The game's own build of shaderc, called as the game calls it (sky_shaderc.py)."""

    def __init__(self, library, spvc=None):
        import sky_shaderc
        self.shaderc = sky_shaderc.Shaderc(library)
        self.spvc = sky_shaderc.Spvc(spvc) if spvc else None
        self.cache = {}

    def describe(self):
        return f"the game's own shaderc ({self.shaderc.version()}), with the game's options"

    def tree(self, name, texts):
        return name, dict(texts)

    def run(self, root, shader, defines, preprocess=False, macros=MACROS):
        name, texts = root
        key = (name, shader, tuple(defines), preprocess, tuple(macros))
        if key not in self.cache:
            def include(wanted):
                space, _, rest = wanted.partition(":")
                return texts.get("include/" + rest) if space == "minecraft" else None
            good, out = self.shaderc.compile(texts[shader], shader.endswith(".fsh"), shader, _macros(macros, defines),
                                             include, preprocess)
            self.cache[key] = (good, out if isinstance(out, str) else "")
        return self.cache[key]

    def opengl(self, root, shader, defines, macros=MACROS):
        """(ok, message, extensions): the shader as the OpenGL backend treats it. The SPIR-V goes
        back to GLSL 330 through the game's SPIRV-Cross with the game's options; that text is
        then compiled by the same strict front end under OpenGL's rules, as a driver would."""
        name, texts = root
        key = ("gl", name, shader, tuple(defines), tuple(macros))
        if key not in self.cache:
            def include(wanted):
                space, _, rest = wanted.partition(":")
                return texts.get("include/" + rest) if space == "minecraft" else None
            fragment = shader.endswith(".fsh")
            good, spirv = self.shaderc.compile(texts[shader], fragment, shader, _macros(macros, defines), include, spirv=True)
            if not good:
                self.cache[key] = (False, "no SPIR-V: " + spirv, ())
                return self.cache[key]
            good, text = self.spvc.glsl(spirv)
            if not good:
                self.cache[key] = (False, "SPIRV-Cross: " + text, ())
                return self.cache[key]
            extensions = tuple(sorted(set(re.findall(r"^\s*#extension\s+(\w+)", text, flags=re.M))))
            version = re.search(r"^\s*#version\s+(.+)$", text, flags=re.M)
            good, out = self.shaderc.compile(text, fragment, shader + " as GLSL 330", {}, lambda wanted: None, opengl=True)
            message = "" if good else "the GLSL 330 is refused: " + str(out)
            if good and (version is None or version.group(1).strip() != "330"):
                good, message = False, f"the text is not #version 330 but {version.group(1) if version else 'nothing'}"
            self.cache[key] = (good, message, extensions)
            if os.environ.get("C164_KEEP_GLSL"):
                path = os.path.join(os.environ["C164_KEEP_GLSL"], name, shader.replace("/", "_") + "." + "_".join(list(defines) + list(macros))[:80] + ".glsl")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as fh:
                    fh.write(text)
        return self.cache[key]


def interface(c, root, shader, defines, macros=MACROS):
    """{(in or out, location): (type, flat)} of a shader's inputs and outputs."""
    good, text = c.run(root, shader, defines, preprocess=True, macros=macros)
    if not good:
        return None
    return {(io, int(loc)): (kind, bool(q and q.strip() == "flat")) for loc, q, io, kind, _ in INTERFACE.findall(text)}


def with_includes(texts):
    """texts and every file they include that is not among them, from the game."""
    out = dict(texts)
    pending = list(out.values())
    while pending:
        for inc in re.findall(r"#include\s*<minecraft:([\w.]+)>", pending.pop()):
            if "include/" + inc not in out:
                out["include/" + inc] = S.vanilla("include/" + inc)
                pending.append(out["include/" + inc])
    return out


def compiled(c, look):
    ours = S.files(look)
    names = sorted({f"core/{v}.vsh" for v, _, _ in pairs()} | {f"core/{f}.fsh" for _, f, _ in pairs()})
    game = with_includes({name: S.vanilla(name) for name in names})
    mine = with_includes(dict(game, **ours))
    touched = set(ours) | {name for name, text in game.items() if "<minecraft:fog.glsl>" in text}
    before, after = c.tree("game", game), c.tree("ours", mine)
    ok, done, skipped, failures = True, 0, [], []
    for vsh, fsh, defines in pairs():
        v, f = f"core/{vsh}.vsh", f"core/{fsh}.fsh"
        if v not in touched and f not in touched:
            continue
        sets = [defines]
        if "oit.glsl" in game[f] and "OIT" not in defines:
            sets += [defines + OIT + extra for extra in OIT_PASSES]
        for ds in sets:
            for macros in (MACROS, ()):
                label = f"{vsh} + {fsh} [{','.join(ds)}]{'' if macros else ' without the device macros'}"
                if not (c.run(before, v, ds, macros=macros)[0] and c.run(before, f, ds, macros=macros)[0]):
                    skipped.append(label)           # not a combination the game's own text compiles under
                    continue
                done += 1
                for shader in (v, f):
                    good, text = c.run(after, shader, ds, macros=macros)
                    if not good:
                        ok = False
                        failures.append(f"{label}: {shader} does not compile\n" + "\n".join("         " + line for line in text.strip().splitlines()[:12]))
                out, into = interface(c, after, v, ds, macros), interface(c, after, f, ds, macros)
                if out is None or into is None:
                    continue
                for (io, loc), (kind, flat) in sorted(into.items()):
                    if io != "in":
                        continue
                    match = out.get(("out", loc))
                    if match is None:
                        ok = False
                        failures.append(f"{label}: the fragment shader reads location {loc} ({kind}) and the vertex shader writes nothing there")
                    elif match != (kind, flat):
                        ok = False
                        failures.append(f"{label}: location {loc} is {match} in the vertex shader and {(kind, flat)} in the fragment shader")
    print(f"[{'ok' if ok else 'FAIL'}] compiled with {c.describe()}: {done} pipelines' pairs with our "
          f"{len(ours)} files in place ({len(touched)} of the game's shaders are touched: they include fog.glsl or are replaced)")
    if getattr(c, "spvc", None) is not None:
        ok &= opengl(c, before, after, touched)
    else:
        print("[--] the OpenGL backend's path (SPIR-V back to GLSL 330 by the game's SPIRV-Cross) was not run: "
              "that library is not to be had here")
    seen = set()
    for line in failures:
        if line not in seen:
            print("  FAIL " + line)
        seen.add(line)
    if skipped:
        print(f"       {len(skipped)} combinations the game's own text does not compile under here were left out "
              f"(the transparency passes' defines are guessed): {'; '.join(skipped[:6])}{' ...' if len(skipped) > 6 else ''}")
    return ok


def opengl(c, before, after, touched):
    """The OpenGL backend's path for every touched shader, ours beside the game's own text: where
    the game's own does not get through this check, the check cannot judge ours either."""
    ok, done, blind, failures, ext_game, ext_ours = True, 0, [], [], set(), set()
    seen = set()
    for vsh, fsh, defines in pairs():
        sets = [defines]
        if "oit.glsl" in before[1][f"core/{fsh}.fsh"] and "OIT" not in defines:
            sets += [defines + OIT + extra for extra in OIT_PASSES]
        for ds in sets:
            for macros in (MACROS, ()):
                for shader in (f"core/{vsh}.vsh", f"core/{fsh}.fsh"):
                    key = (shader, tuple(ds), tuple(macros))
                    if shader not in touched or key in seen:
                        continue
                    seen.add(key)
                    if not c.run(before, shader, ds, macros=macros)[0]:
                        continue                    # not a combination the game's own text compiles under
                    label = f"{shader} [{','.join(ds)}]{'' if macros else ' without the device macros'}"
                    game_ok, game_message, game_ext = c.opengl(before, shader, ds, macros)
                    our_ok, our_message, our_ext = c.opengl(after, shader, ds, macros)
                    ext_game |= set(game_ext)
                    ext_ours |= set(our_ext)
                    if our_ok:
                        done += 1
                    elif game_ok:
                        ok = False
                        failures.append(f"{label}: {our_message}")
                    else:
                        blind.append(f"{label}: ours: {our_message.splitlines()[0][:160] if our_message else ''} | the game's: {game_message.splitlines()[0][:160] if game_message else ''}")
    more = sorted(ext_ours - ext_game)
    if more:
        ok = False
    print(f"[{'ok' if ok else 'FAIL'}] the OpenGL backend's path: {done} shader variants of ours go back to GLSL 330 through the game's "
          f"SPIRV-Cross ({c.spvc.version()}, the game's options) and that text compiles under OpenGL's rules "
          f"(the same strict front end, target OpenGL 4.5); extensions the text asks for: ours {sorted(ext_ours) or 'none'}, "
          f"the game's own {sorted(ext_game) or 'none'}")
    for line in failures[:12]:
        print("  FAIL " + "\n         ".join(line.splitlines()[:10]))
    if more:
        print(f"  FAIL our text asks for extensions the game's own does not: {more}")
    if blind:
        print(f"       {len(blind)} variants this check cannot judge (the game's own text does not get through it either): "
              f"{'; '.join(blind[:3])}{' ...' if len(blind) > 3 else ''}")
    return ok


def compiler(args):
    """(compiler, note): glslc when one is named, else the game's own shaderc, else nothing."""
    if args.glslc:
        work = args.keep or tempfile.mkdtemp(prefix="c164_shaders_")
        if args.keep:
            shutil.rmtree(args.keep, ignore_errors=True)
            os.makedirs(args.keep)
        return Glslc(args.glslc, work), None
    try:
        import json
        import zipfile
        import sky_shaderc
        with zipfile.ZipFile(S.jar()) as z:
            version = json.loads(z.read("version.json"))["id"]
        try:
            spvc = sky_shaderc.library(version, name="spvc", inner_name="libspirv-cross.so")
        except Exception as exc:  # the OpenGL path is then left out, and said so
            print(f"       (the game's SPIRV-Cross is not to be had here: {type(exc).__name__}: {exc})")
            spvc = None
        return Game(sky_shaderc.library(version), spvc), None
    except Exception as exc:  # no compiler is a note, not a failure
        return None, f"{type(exc).__name__}: {exc}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--look", default=mood.DEFAULT)
    ap.add_argument("--glslc", default=os.environ.get("C164_GLSLC"), help="a glslc or glslang command instead of the game's own shaderc")
    ap.add_argument("--keep", help="with --glslc: leave the two shader trees and the compiler's work here")
    ap.add_argument("--panorama")
    ap.add_argument("--camera-y", type=float, default=float(mood.GROUND_Y) + 1.62, help="world y of the eye (default: on the terrace)")
    args = ap.parse_args()

    written = S.files(args.look)
    print(f"[ok] {len(written)} files written from the game's own text: every patch found its place "
          f"({', '.join(sorted(written))})")
    twin = S.Twin(args.look)
    ok = arithmetic(twin, args.camera_y)
    c, note = compiler(args)
    if c is not None:
        ok &= compiled(c, args.look)
    else:
        print(f"[--] nothing was compiled: no --glslc, and the game's own shaderc is not to be had here ({note}). "
              f"The stage macros, the includes and the interface between the stages are then only proved by the game")
    if args.panorama:
        panorama(twin, args.panorama, args.camera_y)
    print(f"result: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
