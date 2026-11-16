"""The game's own shader compiler, for the checks of plan/parts/figs/sky_shaders.py.

The 26.3 client compiles every shader with shaderc (com.mojang.renderpearl's GlslCompiler, through
LWJGL's binding). Its build of the library is one of the game's own files, like the client jar:
the version's list of libraries at Mojang names it (org.lwjgl:lwjgl-shaderc:<version>:natives-linux).
library() fetches that one file, SHA-1 checked, into a folder under the temp directory and takes
libshaderc.so out of it; nothing is installed. Shaderc calls it the way GlslCompiler does:

    target Vulkan 1.2, bindings handed out, none preserved, debug info, no optimising, entry "main",
    #include <namespace:name> resolved to the file of that id, the defines of the pipeline.
"""
import ctypes as C
import hashlib
import io
import json
import os
import platform
import tempfile
import time
import urllib.request
import zipfile

MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
VULKAN, VULKAN_1_2 = 0, (1 << 22) | (2 << 12)
VERTEX, FRAGMENT = 0, 1


def _get(url, tries=4):
    last = None
    for attempt in range(tries):
        if attempt:
            time.sleep(2 ** attempt)
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                return resp.read()
        except Exception as exc:  # retried, then reported
            last = exc
    raise IOError(f"cannot fetch {url}: {last}")


def library(version, folder=None):
    """The path of the game's libshaderc.so for this machine; fetched on the first call."""
    folder = folder or os.environ.get("C164_SHADERC_DIR") or os.path.join(tempfile.gettempdir(), "c164_shaderc")
    path = os.path.join(folder, f"libshaderc-{version}.so")
    if os.path.isfile(path):
        return path
    machine = platform.machine().lower()
    suffix = {"x86_64": ":natives-linux", "amd64": ":natives-linux", "aarch64": ":natives-linux-arm64"}.get(machine)
    if suffix is None or platform.system() != "Linux":
        raise IOError(f"no build of the game's shaderc is looked up for {platform.system()} {machine}")
    entry = next((v for v in json.loads(_get(MANIFEST))["versions"] if v["id"] == version), None)
    if entry is None:
        raise IOError(f"Mojang's manifest lists no version {version}")
    libraries = json.loads(_get(entry["url"]))["libraries"]
    found = [lib for lib in libraries if "shaderc" in lib["name"] and lib["name"].endswith(suffix)]
    if not found:
        raise IOError(f"version {version} lists no library *shaderc*{suffix}")
    artifact = found[0]["downloads"]["artifact"]
    data = _get(artifact["url"])
    if hashlib.sha1(data).hexdigest() != artifact["sha1"]:
        raise IOError(f"{artifact['url']}: the SHA-1 is not the one Mojang lists")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        inner = [n for n in z.namelist() if n.endswith("libshaderc.so")]
        if not inner:
            raise IOError(f"{found[0]['name']} holds no libshaderc.so")
        os.makedirs(folder, exist_ok=True)
        with open(path + ".part", "wb") as fh:
            fh.write(z.read(inner[0]))
    os.replace(path + ".part", path)
    return path


class _Include(C.Structure):
    _fields_ = [("source_name", C.c_char_p), ("source_name_length", C.c_size_t),
                ("content", C.c_char_p), ("content_length", C.c_size_t), ("user_data", C.c_void_p)]


_RESOLVE = C.CFUNCTYPE(C.c_void_p, C.c_void_p, C.c_char_p, C.c_int, C.c_char_p, C.c_size_t)
_RELEASE = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p)


class Shaderc:
    def __init__(self, path):
        self.path = path
        lib = self.lib = C.CDLL(path)
        p, s, i = C.c_void_p, C.c_size_t, C.c_int
        for name, res, args in (
                ("shaderc_compiler_initialize", p, []),
                ("shaderc_compiler_release", None, [p]),
                ("shaderc_compile_options_initialize", p, []),
                ("shaderc_compile_options_release", None, [p]),
                ("shaderc_compile_options_set_target_env", None, [p, i, C.c_uint32]),
                ("shaderc_compile_options_set_auto_bind_uniforms", None, [p, C.c_bool]),
                ("shaderc_compile_options_set_preserve_bindings", None, [p, C.c_bool]),
                ("shaderc_compile_options_set_generate_debug_info", None, [p]),
                ("shaderc_compile_options_set_optimization_level", None, [p, i]),
                ("shaderc_compile_options_add_macro_definition", None, [p, C.c_char_p, s, C.c_char_p, s]),
                ("shaderc_compile_options_set_include_callbacks", None, [p, _RESOLVE, _RELEASE, p]),
                ("shaderc_compile_into_spv", p, [p, C.c_char_p, s, i, C.c_char_p, C.c_char_p, p]),
                ("shaderc_compile_into_preprocessed_text", p, [p, C.c_char_p, s, i, C.c_char_p, C.c_char_p, p]),
                ("shaderc_result_get_compilation_status", i, [p]),
                ("shaderc_result_get_length", s, [p]),
                ("shaderc_result_get_bytes", p, [p]),
                ("shaderc_result_get_error_message", C.c_char_p, [p]),
                ("shaderc_result_release", None, [p])):
            fn = getattr(lib, name)
            fn.restype, fn.argtypes = res, args
        self.compiler = lib.shaderc_compiler_initialize()
        if not self.compiler:
            raise OSError(f"{path}: shaderc_compiler_initialize() gave nothing")

    def version(self):
        return os.path.basename(self.path)

    def compile(self, text, fragment, name, macros, include, preprocess=False):
        """(ok, output): the SPIR-V's length in bytes, the preprocessed text, or the compiler's
        message. macros: {name: value}; include(id) -> the text of the included file or None."""
        lib = self.lib
        live = {}

        def resolve(_user, requested, _kind, _requesting, _depth):
            wanted = requested.decode("utf-8")
            found = include(wanted)
            source = wanted.encode("utf-8") if found is not None else b""
            content = found.encode("utf-8") if found is not None else b"not found"
            result = _Include(source, len(source), content, len(content), None)
            address = C.addressof(result)
            live[address] = (result, source, content)
            return address

        def release(_user, address):
            live.pop(address, None)

        resolver, releaser = _RESOLVE(resolve), _RELEASE(release)
        options = lib.shaderc_compile_options_initialize()
        try:
            lib.shaderc_compile_options_set_target_env(options, VULKAN, VULKAN_1_2)
            lib.shaderc_compile_options_set_auto_bind_uniforms(options, True)
            lib.shaderc_compile_options_set_preserve_bindings(options, False)
            lib.shaderc_compile_options_set_generate_debug_info(options)
            lib.shaderc_compile_options_set_optimization_level(options, 0)
            for key, value in macros.items():
                k, v = key.encode("utf-8"), str(value).encode("utf-8")
                lib.shaderc_compile_options_add_macro_definition(options, k, len(k), v, len(v))
            lib.shaderc_compile_options_set_include_callbacks(options, resolver, releaser, None)
            source = text.encode("utf-8")
            call = lib.shaderc_compile_into_preprocessed_text if preprocess else lib.shaderc_compile_into_spv
            result = call(self.compiler, source, len(source), FRAGMENT if fragment else VERTEX,
                          name.encode("utf-8"), b"main", options)
            try:
                if lib.shaderc_result_get_compilation_status(result) != 0:
                    return False, (lib.shaderc_result_get_error_message(result) or b"").decode("utf-8", "replace")
                length = lib.shaderc_result_get_length(result)
                if preprocess:
                    return True, C.string_at(lib.shaderc_result_get_bytes(result), length).decode("utf-8", "replace")
                return True, length
            finally:
                lib.shaderc_result_release(result)
        finally:
            lib.shaderc_compile_options_release(options)
