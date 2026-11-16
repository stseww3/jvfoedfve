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
OPENGL, OPENGL_4_5 = 1, 450
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


def library(version, folder=None, name="shaderc", inner_name="libshaderc.so"):
    """The path of the game's libshaderc.so for this machine; fetched on the first call. With
    name="spvc", inner_name="libspirv-cross.so": its build of SPIRV-Cross, which the OpenGL
    backend uses."""
    folder = folder or os.environ.get("C164_SHADERC_DIR") or os.path.join(tempfile.gettempdir(), "c164_shaderc")
    path = os.path.join(folder, f"{inner_name.rsplit('.', 1)[0]}-{version}.so")
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
    found = [lib for lib in libraries if name in lib["name"] and lib["name"].endswith(suffix)]
    if not found:
        raise IOError(f"version {version} lists no library *{name}*{suffix}")
    artifact = found[0]["downloads"]["artifact"]
    data = _get(artifact["url"])
    if hashlib.sha1(data).hexdigest() != artifact["sha1"]:
        raise IOError(f"{artifact['url']}: the SHA-1 is not the one Mojang lists")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        inner = [n for n in z.namelist() if n.endswith(inner_name)]
        if not inner:
            raise IOError(f"{found[0]['name']} holds no {inner_name} (it holds {', '.join(z.namelist()[:12])})")
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
                ("shaderc_compile_options_set_auto_map_locations", None, [p, C.c_bool]),
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

    def compile(self, text, fragment, name, macros, include, preprocess=False, spirv=False, opengl=False):
        """(ok, output): the SPIR-V's length in bytes (the SPIR-V itself with spirv=True), the
        preprocessed text, or the compiler's message. macros: {name: value}; include(id) -> the
        text of the included file or None. opengl=True: not the game's call but the same front
        end under OpenGL's rules (target OpenGL 4.5, locations and bindings handed out), for the
        GLSL 330 the OpenGL backend hands to the driver."""
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
            if opengl:
                lib.shaderc_compile_options_set_target_env(options, OPENGL, OPENGL_4_5)
                lib.shaderc_compile_options_set_auto_map_locations(options, True)
            else:
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
                return True, (C.string_at(lib.shaderc_result_get_bytes(result), length) if spirv else length)
            finally:
                lib.shaderc_result_release(result)
        finally:
            lib.shaderc_compile_options_release(options)


class Spvc:
    """The game's own build of SPIRV-Cross, called as its OpenGL backend calls it
    (com.mojang.renderpearl's GlPipelineRecompiler): the SPIR-V of a shader back to GLSL 330, which
    the driver then compiles. The options are the game's, by their numbers in spirv_cross_c.h:
    GLSL version 330, no 420pack, push constants as a uniform buffer, base instance as the device
    has it, and (outside the game's shader debug mode) two common ones. The game also renames the
    stages' inputs and outputs by their locations; names do not change what is valid and are left."""
    GLSL, COPY = 1, 0
    UINTS = ((0x2000008, 330),)
    BOOLS = ((0x2000007, False), (0x2000021, True), (0x1000036, True), (0x1000002, True))
    BASE_INSTANCE = 0x2000005

    def __init__(self, path):
        self.path = path
        lib = self.lib = C.CDLL(path)
        p, s, i = C.c_void_p, C.c_size_t, C.c_int
        for name, res, args in (
                ("spvc_context_create", i, [C.POINTER(p)]),
                ("spvc_context_destroy", None, [p]),
                ("spvc_context_get_last_error_string", C.c_char_p, [p]),
                ("spvc_context_parse_spirv", i, [p, C.c_void_p, s, C.POINTER(p)]),
                ("spvc_context_create_compiler", i, [p, i, p, i, C.POINTER(p)]),
                ("spvc_compiler_create_compiler_options", i, [p, C.POINTER(p)]),
                ("spvc_compiler_options_set_uint", i, [p, i, C.c_uint]),
                ("spvc_compiler_options_set_bool", i, [p, i, C.c_ubyte]),
                ("spvc_compiler_install_compiler_options", i, [p, p]),
                ("spvc_compiler_compile", i, [p, C.POINTER(C.c_char_p)])):
            fn = getattr(lib, name)
            fn.restype, fn.argtypes = res, args

    def version(self):
        return os.path.basename(self.path)

    def glsl(self, spirv, base_instance=False):
        """(ok, text): the GLSL 330 of this SPIR-V, or SPIRV-Cross's message."""
        lib = self.lib
        context = C.c_void_p()
        if lib.spvc_context_create(C.byref(context)) != 0:
            return False, "spvc_context_create() failed"

        def check(code, what):
            if code != 0:
                raise ValueError(f"{what}: {(lib.spvc_context_get_last_error_string(context) or b'').decode('utf-8', 'replace')}")
        try:
            words = (C.c_uint32 * (len(spirv) // 4)).from_buffer_copy(spirv)
            ir, compiler, options, source = C.c_void_p(), C.c_void_p(), C.c_void_p(), C.c_char_p()
            check(lib.spvc_context_parse_spirv(context, words, len(words), C.byref(ir)), "parse")
            check(lib.spvc_context_create_compiler(context, self.GLSL, ir, self.COPY, C.byref(compiler)), "create the compiler")
            check(lib.spvc_compiler_create_compiler_options(compiler, C.byref(options)), "create the options")
            for key, value in self.UINTS:
                check(lib.spvc_compiler_options_set_uint(options, key, value), f"option {key:#x}")
            for key, value in self.BOOLS + ((self.BASE_INSTANCE, base_instance),):
                check(lib.spvc_compiler_options_set_bool(options, key, 1 if value else 0), f"option {key:#x}")
            check(lib.spvc_compiler_install_compiler_options(compiler, options), "install the options")
            check(lib.spvc_compiler_compile(compiler, C.byref(source)), "translate")
            return True, (source.value or b"").decode("utf-8", "replace")
        except ValueError as exc:
            return False, str(exc)
        finally:
            lib.spvc_context_destroy(context)
