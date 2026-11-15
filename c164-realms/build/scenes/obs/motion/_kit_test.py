"""The arithmetic of _kit.py against itself, without the game (from build/):

    python -m scenes.obs.motion._kit_test

Not a work package (the name starts with "_"). It answers what can be answered without a client:
a turned part keeps its anchor on the entity and turns the right way round, a connecting rod
stays on its crank pin, the steps are the ones the parts file promises, and the files written are
the files the functions name. What the client does with them is plan/parts/motion.md section 10.
"""
import json
import math
import os
import shutil
import tempfile

from . import _kit as MK


class _Canvas:
    def __init__(self):
        self.entities = []

    def add_entity(self, x, y, z, nbt):
        self.entities.append((x, y, z, nbt))


def _display(name, yaw=0.0, turn=None, scale=(1.0, 1.0, 1.0), anchor=(0.0, 0.0, 0.0)):
    """NBT as artkit.models.display writes it, for a model whose anchor lies `anchor` blocks from
    the middle of its box; turn is (model axis as a vector, degrees)."""
    q = MK._IDENT if turn is None else MK._about(turn[0], turn[1])
    q = (-q[0], q[1], -q[2], q[3])
    flipped = (-anchor[0] * scale[0], anchor[1] * scale[1], -anchor[2] * scale[2])
    t = MK._qrot(q, flipped)
    return {"id": "minecraft:item_display",
            "item": {"id": "minecraft:stick", "count": 1, "components": {"minecraft:item_model": f"c164:{name}"}},
            "transformation": {"left_rotation": list(q), "right_rotation": [0.0, 0.0, 0.0, 1.0],
                               "scale": list(scale), "translation": [-t[0], -t[1], -t[2]]},
            "Rotation": [(180.0 + yaw) % 360.0, 0.0], "Tags": ["c164art"]}


def _world(part, left, shift, m):
    """Where the game shows the model's point m (blocks from the middle of its box), as an offset
    from the entity, in world axes."""
    v = (-m[0] * part.scale[0], m[1] * part.scale[1], -m[2] * part.scale[2])
    p = MK._qrot(left, v)
    x, y, z = (shift[i] + p[i] for i in range(3))
    a = math.radians(-part.yaw)
    c, s = math.cos(a), math.sin(a)
    return (x * c + z * s, y, -x * s + z * c)


def _close(a, b, eps=1e-6):
    return all(abs(a[i] - b[i]) <= eps for i in range(len(a)))


def _last(canvas):
    return canvas.motion.parts[-1]


def test_ticks():
    assert MK._ticks(48, 4) == [0, 12, 24, 36, 48]
    assert MK._ticks(40, 8) == [0, 5, 10, 15, 20, 25, 30, 35, 40]
    assert MK._ticks(10, 3) == [0, 3, 7, 10]
    assert MK._num(87) == "87.0" and MK._num(79.5) == "79.5" and MK._num(-0.00001) == "0.0"
    assert MK._floats((0.0, -0.5, 1.0)) == "[0.0f,-0.5f,1.0f]"


def test_anchor_stays():
    """Whatever the yaw, the turns and the scale: the anchor stays on the entity and a point on the
    axis does not move."""
    c = _Canvas()
    anchor = (0.3, -0.2, 0.5)
    c.add_entity(4.5, 70.0, -2.5, _display("mot_a", yaw=37.0, turn=((0.6, 0.0, 0.8), 25.0), scale=(1.0, 2.0, 0.5),
                                           anchor=anchor))
    MK.spin(c, "y", 240)
    part = _last(c)
    on_axis = (anchor[0], anchor[1] + 1.0, anchor[2])
    rest = _world(part, part.left, part.shift, on_axis)
    assert _close(_world(part, part.left, part.shift, anchor), (0.0, 0.0, 0.0))
    for _tick, _ticks, turn, slide in part.steps:
        left, shift = part.pose(turn, slide)
        assert _close(_world(part, left, shift, anchor), (0.0, 0.0, 0.0)), turn
        assert _close(_world(part, left, shift, on_axis), rest), turn


def test_right_handed():
    """Placed with yaw 0 and no turns, the model's axes are the world's: a quarter turn about "y"
    takes what points east to the north (counter-clockwise seen from above)."""
    c = _Canvas()
    c.add_entity(0.5, 64.0, 0.5, _display("mot_b"))
    MK.spin(c, "y", 48)
    part = _last(c)
    left, shift = part.pose(90.0, 0.0)
    assert _close(_world(part, left, shift, (1.0, 0.0, 0.0)), (0.0, 0.0, -1.0))
    assert _close(part.local("x"), part.local((1, 0, 0)))
    c.add_entity(2.5, 64.0, 0.5, _display("mot_c", yaw=90.0))
    MK.spin(c, "x", 48)
    part = _last(c)
    assert _close(part.local("x"), part.local((0, 0, 1)))      # yaw 90 points the model's +x south
    left, shift = part.pose(90.0, 0.0)
    assert _close(_world(part, left, shift, (0.0, 0.0, -1.0)), (0.0, 1.0, 0.0))    # east goes up


def test_steps():
    c = _Canvas()
    c.add_entity(0.5, 64.0, 0.5, _display("mot_wheel", yaw=90.0, scale=(2.0, 2.0, 2.0)))
    MK.spin(c, "x", MK.ENGINE_REV)
    part = _last(c)
    assert [(t, d, round(a, 6)) for t, d, a, _s in part.steps] == [(0, 14, 105.0), (12, 14, 195.0),
                                                                   (24, 14, 285.0), (36, 14, 375.0)]
    assert part.lead == MK.LEAD and part.stray == 0.0
    # a long arm that turns slowly: many small steps, still aimed ahead, within a quarter pixel
    c.add_entity(3.5, 64.0, 0.5, _display("mot_arm", anchor=(1.75, 0.0, 0.0)))
    MK.spin(c, "y", MK.ORRERY["mercury"])
    part = _last(c)
    assert abs(part.arm() - 1.75) < 1e-9
    assert 20 <= len(part.steps) <= 30 and part.lead == MK.LEAD and part.stray <= MK.WOBBLE, len(part.steps)
    # a crank arm that is not a disc, at the engine's speed: 16 steps, not aimed ahead
    c.add_entity(6.5, 64.0, 0.5, _display("mot_crank", anchor=(0.5, 0.0, 0.0)))
    MK.spin(c, "z", MK.ENGINE_REV)
    part = _last(c)
    assert len(part.steps) == 16 and part.lead == 0 and part.stray <= MK.WOBBLE, (len(part.steps), part.lead)
    # too fast for an arm: refused, with the reason
    c.add_entity(9.5, 64.0, 0.5, _display("mot_fast", anchor=(1.75, 0.0, 0.0)))
    try:
        MK.spin(c, "y", 24)
    except ValueError as e:
        assert "too fast" in str(e)
    else:
        raise AssertionError("an arm of 1.75 blocks that turns in 24 ticks was not refused")
    # a pendulum: 8 poses there and back, back in the middle at the end
    c.add_entity(12.5, 64.0, 0.5, _display("mot_pendulum", anchor=(0.0, 0.5, 0.0)))
    MK.swing(c, "z", 5.0, MK.PENDULUM)
    part = _last(c)
    assert len(part.steps) == 8 and part.lead == MK.LEAD
    assert abs(part.steps[1][2] - 5.0 * (math.sin(math.pi / 4) + (1.0 - math.sin(math.pi / 4)) * 7.0 / 5.0)) < 1e-9


def test_rod_on_pin():
    """A rod 4 long on a crank of 1: at every pose its far end is on the crank pin."""
    c = _Canvas()
    c.add_entity(0.5, 64.0, 0.5, _display("mot_rod", anchor=(2.0, 0.0, 0.0)))
    MK.crank(c, (0, 0, 1), (1, 0, 0), 1.0, 4.0, MK.ENGINE_REV, lead=0)
    part = _last(c)
    assert len(part.steps) == 12
    for tick, ticks, tilt, slide in part.steps:
        a = 2.0 * math.pi * (tick + ticks) / MK.ENGINE_REV
        left, shift = part.pose(tilt, slide)
        assert _close(_world(part, left, shift, (-2.0, 0.0, 0.0)), (-5.0 + math.cos(a), math.sin(a), 0.0)), tick
        assert abs(_world(part, left, shift, (2.0, 0.0, 0.0))[1]) < 1e-9          # the crosshead pin keeps to its line
    c.add_entity(0.5, 64.0, 0.5, _display("mot_crosshead"))
    MK.crank(c, (0, 0, 1), (1, 0, 0), 1.0, 4.0, MK.ENGINE_REV, turn=False, lead=0)
    head = _last(c)
    assert [round(s[3], 9) for s in head.steps] == [round(s[3], 9) for s in part.steps]
    assert all(s[2] == 0.0 for s in head.steps) and abs(min(s[3] for s in head.steps) + 2.0) < 1e-9


def test_slide():
    c = _Canvas()
    c.add_entity(0.5, 64.0, 0.5, _display("mot_pen"))
    MK.slide(c, "x", [(0, 0.5, 1200), (1200, 0.0, 1200)], MK.DRUM_REV)
    part = _last(c)
    assert len(part.steps) == 12
    assert part.steps[5] == (1000, 200, 0.0, 0.5) and part.steps[11] == (2200, 200, 0.0, 0.0)
    assert part.steps[0][1] == 202 and abs(part.steps[0][3] - 0.5 / 6.0 * 1.01) < 1e-9
    try:
        MK.slide(c, "x", [(0, 0.5, 10)], 40, model="mot_pen", name="again")
    except ValueError as e:
        assert "registered already" in str(e)
    else:
        raise AssertionError("one entity was registered twice")


def test_write():
    c = _Canvas()
    c.add_entity(0.5, 64.0, 0.5, _display("mot_wheel", yaw=90.0))
    MK.spin(c, "x", MK.ENGINE_REV)
    c.add_entity(3.5, 65.0, 0.5, _display("mot_pendulum", anchor=(0.0, 0.5, 0.0)))
    MK.swing(c, "z", 5.0, MK.PENDULUM)
    c.add_entity(6.5, 64.0, 0.5, _display("mot_lamp"))
    MK.blink(c, "mot_lamp_dark", *MK.BLINK)
    MK.sound(c, (3.5, 65.0, 0.5), "minecraft:block.note_block.hat", MK.PENDULUM, at=(10, 30), volume=0.3)
    MK.puff(c, (9.0, 70.0, 0.0), "campfire_signal_smoke", 10, count=0, spread=(0.0, 0.07, 0.0), speed=1.0, far=True)
    assert MK.registered(c) == (3, 2)
    assert "m.mot_wheel" in c.entities[0][3]["Tags"]
    status, summary, details = MK.check(c)
    assert status == "PASS", (status, summary, details)
    tmp = tempfile.mkdtemp(prefix="c164-motion-test-")
    try:
        assert MK.write(c, tmp, "t", at=(10, 64, -3)) == ["function c164art:t-motion/start"]
        root = os.path.join(tmp, "data", "c164art", "function", "t-motion")
        have = set()
        for d, _dirs, names in os.walk(root):
            for n in names:
                have.add(os.path.relpath(os.path.join(d, n), root).replace(os.sep, "/")[:-len(".mcfunction")])
        assert {"start", "stop", "rest", "halt", "load", "watch", "c10/0", "c40/0", "c48/0", "c60/0"} <= have, have

        def lines(rel):
            with open(os.path.join(root, *rel.split("/")) + ".mcfunction", encoding="utf-8") as fh:
                return fh.read().splitlines()

        named = set()
        for rel in have:
            for line in lines(rel):
                for word in line.split():
                    if word.startswith("c164art:t-motion/"):
                        named.add(word.split("/", 1)[1])
        assert named <= have, named - have                     # every function a line names is written
        assert have - named == {"stop", "load"}, have - named   # and all but the two entries are named
        first = lines("c10/0")
        assert first[0].startswith("execute unless score #run c164m matches ") and first[0].endswith("t-motion/halt")
        assert first[1] == "schedule function c164art:t-motion/c10/0 10t replace"
        assert first[2] == "scoreboard players set #t c164m 1"
        assert first[3] == "particle minecraft:campfire_signal_smoke 19.0 134.0 -3.0 0.0 0.07 0.0 1.0 0 force"
        assert any("x=10.5,y=128.0,z=-2.5,distance=..0.05,tag=m.mot_wheel,limit=1]" in ln for ln in lines("c48/0"))
        assert any(ln.startswith("playsound minecraft:block.note_block.hat block @a[x=13.5,y=129.0,z=-2.5,"
                                 "distance=..16.0] 13.5 129.0 -2.5 0.3 1.0") for ln in lines("c40/2"))
        assert sum(1 for ln in lines("rest") if ln.startswith("data merge entity ")) == 3
        with open(os.path.join(tmp, "data", "minecraft", "tags", "function", "load.json"), encoding="utf-8") as fh:
            assert json.load(fh) == {"values": [{"id": "c164art:t-motion/load", "required": False}]}
        assert MK.write(_Canvas(), tmp, "t") == []
        assert not os.path.exists(root)
        assert not os.path.exists(os.path.join(tmp, "data", "minecraft", "tags", "function", "load.json"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_same_spot():
    c = _Canvas()
    for _ in range(2):
        c.add_entity(0.5, 64.0, 0.5, _display("mot_wheel"))
        MK.spin(c, "y", 48)
    status, _summary, details = MK.check(c)
    assert status == "FAIL" and "one spot" in details[0], details
    c = _Canvas()
    c.add_entity(0.5, 64.0, 0.5, _display("mot_wheel"))
    MK.spin(c, "y", 48)
    c.add_entity(0.5, 64.0, 0.5, _display("mot_wheel"))
    MK.spin(c, "y", -48, name="mot_wheel.b")
    assert MK.check(c)[0] == "PASS"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("ok", test.__name__)
    print(f"{len(tests)} tests passed")
