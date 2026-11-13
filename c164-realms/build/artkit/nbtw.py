"""Small NBT writer, just enough for structure templates.

Python values map to tags by type: bool/Byte -> byte, Short, int -> int, Long, Float, float -> double,
str -> string, dict -> compound, list/tuple -> list (all items of one type), IntArray -> int array.
"""
import gzip
import struct


class Byte(int):
    pass


class Short(int):
    pass


class Long(int):
    pass


class Float(float):
    pass


class IntArray(list):
    pass


def _name(s):
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def _tag(v):
    if isinstance(v, (bool, Byte)):
        return 1
    if isinstance(v, Short):
        return 2
    if isinstance(v, Long):
        return 4
    if isinstance(v, int):
        return 3
    if isinstance(v, Float):
        return 5
    if isinstance(v, float):
        return 6
    if isinstance(v, str):
        return 8
    if isinstance(v, IntArray):
        return 11
    if isinstance(v, (list, tuple)):
        return 9
    if isinstance(v, dict):
        return 10
    raise TypeError(f"cannot encode {type(v).__name__} as NBT")


def _payload(v, out):
    t = _tag(v)
    if t == 1:
        out += struct.pack(">b", int(v))
    elif t == 2:
        out += struct.pack(">h", v)
    elif t == 3:
        out += struct.pack(">i", v)
    elif t == 4:
        out += struct.pack(">q", v)
    elif t == 5:
        out += struct.pack(">f", v)
    elif t == 6:
        out += struct.pack(">d", v)
    elif t == 8:
        out += _name(v)
    elif t == 11:
        out += struct.pack(">i", len(v))
        out += struct.pack(f">{len(v)}i", *v)
    elif t == 9:
        item = _tag(v[0]) if v else 0
        out.append(item)
        out += struct.pack(">i", len(v))
        for x in v:
            if _tag(x) != item:
                raise TypeError("NBT lists must hold a single type")
            _payload(x, out)
    else:
        for k, x in v.items():
            out.append(_tag(x))
            out += _name(k)
            _payload(x, out)
        out.append(0)


def encode(value):
    """Encode a dict as a nameless-root compound payload (without the leading tag and name)."""
    out = bytearray()
    _payload(value, out)
    return bytes(out)


def write_template(path, size, palette, blocks, entities=(), data_version=5023):
    """Write a structure template.

    palette  list of (block_id, {property: value})
    blocks   list of (x, y, z, palette_index) or (x, y, z, palette_index, block_entity_nbt_dict)
    entities list of (x, y, z, nbt_dict); positions relative to the template origin
    """
    out = bytearray()
    out += b"\x0a" + _name("")
    out += b"\x03" + _name("DataVersion") + struct.pack(">i", data_version)
    out += b"\x09" + _name("size") + b"\x03" + struct.pack(">iiii", 3, *size)

    out += b"\x09" + _name("palette") + (b"\x0a" if palette else b"\x00") + struct.pack(">i", len(palette))
    for block_id, props in palette:
        entry = {"id": block_id}
        if props:
            entry["properties"] = {k: str(v) for k, v in sorted(props.items())}
        _payload(entry, out)

    out += b"\x09" + _name("blocks") + (b"\x0a" if blocks else b"\x00") + struct.pack(">i", len(blocks))
    pos_head = b"\x09" + _name("pos") + b"\x03" + struct.pack(">i", 3)
    state_head = b"\x03" + _name("state")
    nbt_head = b"\x0a" + _name("nbt")
    pack = struct.Struct(">iii").pack
    pack_i = struct.Struct(">i").pack
    for blk in blocks:
        out += pos_head
        out += pack(blk[0], blk[1], blk[2])
        out += state_head
        out += pack_i(blk[3])
        if len(blk) > 4 and blk[4] is not None:
            out += nbt_head
            _payload(blk[4], out)
        out.append(0)

    out += b"\x09" + _name("entities") + (b"\x0a" if entities else b"\x00") + struct.pack(">i", len(entities))
    for x, y, z, nbt in entities:
        _payload({
            "pos": [float(x), float(y), float(z)],
            "blockPos": [int(x // 1), int(y // 1), int(z // 1)],
            "nbt": nbt,
        }, out)
    out.append(0)

    with gzip.open(path, "wb", compresslevel=6) as fh:
        fh.write(out)


def snbt(v):
    """Text form of a value, for use inside commands."""
    t = _tag(v)
    if t == 1:
        return f"{int(v)}b"
    if t == 2:
        return f"{int(v)}s"
    if t == 3:
        return str(int(v))
    if t == 4:
        return f"{int(v)}L"
    if t == 5:
        return f"{float(v):.6g}f"
    if t == 6:
        return f"{float(v):.6g}d"
    if t == 8:
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if t == 11:
        return "[I;" + ",".join(str(int(x)) for x in v) + "]"
    if t == 9:
        return "[" + ",".join(snbt(x) for x in v) + "]"
    return "{" + ",".join(f'"{k}":{snbt(x)}' for k, x in v.items()) + "}"
