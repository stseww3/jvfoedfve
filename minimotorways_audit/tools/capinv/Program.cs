using System.Collections.Immutable;
using System.Reflection;
using System.Reflection.Emit;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Text;
using System.Text.RegularExpressions;

var ops = new Dictionary<short, OpCode>();
foreach (var f in typeof(OpCodes).GetFields(BindingFlags.Public | BindingFlags.Static)) { var o = (OpCode)f.GetValue(null)!; ops[o.Value] = o; }

var cats = new (string Cat, Regex Re)[] {
    ("NET", new Regex(@"^System\.Net\.|^UnityEngine\.Networking\.|^UnityEngine\.WWW|^System\.Net\.Http|Sockets\.|::.*Socket")),
    ("PROC", new Regex(@"^System\.Diagnostics\.Process(StartInfo)?::")),
    ("LOAD", new Regex(@"^System\.Reflection\.Assembly::(Load|LoadFrom|LoadFile|UnsafeLoadFrom|LoadWithPartialName|GetType|CreateInstance)|^System\.AppDomain::(Load|ExecuteAssembly|CreateInstance|DefineDynamicAssembly)|^System\.Reflection\.Emit\.|DynamicMethod|Marshal::GetDelegateForFunctionPointer|^System\.Activator::CreateInstance|^System\.Type::GetType\(|::Invoke\(System\.Object,System\.Object\[\]\)|^System\.Delegate::CreateDelegate|^System\.Type::InvokeMember|^System\.Type::(GetMethod|GetField|GetProperty)\(System\.String")),
    ("FILE", new Regex(@"^System\.IO\.(File|FileInfo|Directory|DirectoryInfo|FileStream|StreamWriter|BinaryWriter)::(Write|Append|Create|Copy|Move|Delete|Open|Replace|\.ctor|SetAttributes|GetFiles|EnumerateFiles|GetDirectories)|^System\.Environment::GetFolderPath|^System\.IO\.Path::GetTemp")),
    ("REG", new Regex(@"^Microsoft\.Win32\.Registry")),
    ("ENV", new Regex(@"^System\.Environment::(GetEnvironmentVariable|SetEnvironmentVariable|get_UserName|get_MachineName|GetCommandLineArgs|get_CommandLine|get_UserDomainName|ExpandEnvironmentVariables)|SystemInfo::get_(deviceUniqueIdentifier|deviceName)")),
    ("CLIP", new Regex(@"systemCopyBuffer|Clipboard")),
    ("SCREEN", new Regex(@"^UnityEngine\.ScreenCapture::|Texture2D::ReadPixels|::EncodeTo(PNG|JPG|EXR|TGA)")),
    ("URL", new Regex(@"Application::OpenURL")),
    ("CRYPTO", new Regex(@"^System\.Security\.Cryptography\.")),
    ("ENC", new Regex(@"Convert::FromBase64String|GZipStream|DeflateStream")),
    ("NATIVEPTR", new Regex(@"Marshal::(Copy|WriteByte|WriteInt16|WriteInt32|WriteInt64|WriteIntPtr)\(|VirtualProtect|VirtualAlloc")),
    ("PRIVACY", new Regex(@"^UnityEngine\.(Microphone|WebCamTexture|LocationService|Windows\.Speech\.|Windows\.WebCam\.)|^UnityEngine\.Input::get_(location|compass|gyro)|Application::RequestUserAuthorization|^UnityEngine\.Handheld::")),
    ("UFILE", new Regex(@"^UnityEngine\.Windows\.(File|Directory|Crypto)::|MemoryProfiler::TakeSnapshot|^UnityEngine\.Diagnostics\.Utils::")),
    ("FNPTR", new Regex(@"NativeLibrary::|Marshal::GetFunctionPointerForDelegate|Marshal::GetDelegateForFunctionPointer|Marshal::Prelink|AppDomain::(add_AssemblyResolve|add_TypeResolve|add_ResourceResolve)")),
    ("THREAD", new Regex(@"^System\.Threading\.Thread::\.ctor|^System\.Threading\.ThreadPool::(QueueUserWorkItem|UnsafeQueueUserWorkItem)|^System\.Threading\.Timer::\.ctor")),
};
var strRes = new (string Cat, Regex Re)[] {
    ("S-URL", new Regex(@"(?i)\b(https?|ftp|wss?|tcp|udp)://")),
    ("S-IP", new Regex(@"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
    ("S-DOMAIN", new Regex(@"(?i)\b[a-z0-9-]{2,}\.(com|net|org|io|ru|cn|xyz|top|club|info|me|co|app|dev|cc|tk|su|biz|onion|link|site|online|pw|in|de|uk|jp|kr|au)\b")),
    ("S-B64", new Regex(@"^[A-Za-z0-9+/]{80,}={0,2}$")),
    ("S-EXEC", new Regex(@"(?i)\.(exe|bat|cmd|ps1|vbs|scr|hta|lnk|msi)\b|powershell|cmd\.exe|rundll|regsvr|schtasks|wscript|cscript|mshta|certutil|bitsadmin")),
    ("S-PERSIST", new Regex(@"(?i)CurrentVersion\\\\?Run|\\Startup|RunOnce|Winlogon|Image File Execution")),
    ("S-STEAL", new Regex(@"(?i)Login Data|Cookies|wallet|discord|leveldb|Local State|\btoken\b|password|keylog|metamask|exodus|electrum")),
};

var results = new List<string>();
foreach (var path in args) {
    var name = Path.GetFileName(path);
    using var fs = File.OpenRead(path);
    using var pe = new PEReader(fs);
    if (!pe.HasMetadata) { Console.WriteLine($"=== {name}: not managed"); continue; }
    var md = pe.GetMetadataReader();
    var prov = new Prov();
    var hits = new SortedDictionary<string, SortedSet<string>>();
    void Add(string k, string caller) { if (!hits.TryGetValue(k, out var s)) hits[k] = s = new SortedSet<string>(); s.Add(caller); }

    var pinvokes = new Dictionary<MethodDefinitionHandle, string>();
    foreach (var mh in md.MethodDefinitions) {
        var m = md.GetMethodDefinition(mh);
        var imp = m.GetImport();
        if (!imp.Module.IsNil) {
            var mod = md.GetString(md.GetModuleReference(imp.Module).Name);
            pinvokes[mh] = mod + "!" + md.GetString(imp.Name);
            Add("PINVOKE-DECL | " + mod + "!" + md.GetString(imp.Name), Prov.MethodKey(md, mh, prov));
        }
    }
    foreach (var mh in md.MethodDefinitions) {
        var m = md.GetMethodDefinition(mh);
        if (m.RelativeVirtualAddress == 0) continue;
        string caller = Prov.MethodKey(md, mh, prov);
        var il = pe.GetMethodBody(m.RelativeVirtualAddress).GetILBytes()!;
        int i = 0;
        while (i < il.Length) {
            short v;
            if (il[i] == 0xFE) { v = (short)(0xFE00 | il[i + 1]); i += 2; } else { v = il[i]; i += 1; }
            if (!ops.TryGetValue(v, out var op)) break;
            if (op.Value == OpCodes.Calli.Value) Add("CALLI | indirect call through raw function pointer", caller);
            switch (op.OperandType) {
                case OperandType.InlineNone: break;
                case OperandType.ShortInlineBrTarget: case OperandType.ShortInlineI: case OperandType.ShortInlineVar: i += 1; break;
                case OperandType.InlineVar: i += 2; break;
                case OperandType.InlineI8: case OperandType.InlineR: i += 8; break;
                case OperandType.InlineSwitch: int n = BitConverter.ToInt32(il, i); i += 4 + 4 * n; break;
                case OperandType.InlineBrTarget: case OperandType.InlineI: case OperandType.ShortInlineR: i += 4; break;
                default: {
                    int tok = BitConverter.ToInt32(il, i); i += 4;
                    if ((uint)tok >> 24 == 0x70) {
                        string s;
                        try { s = md.GetUserString(MetadataTokens.UserStringHandle(tok & 0xFFFFFF)); } catch { break; }
                        foreach (var (c, re) in strRes) if (re.IsMatch(s)) Add(c + " | " + (s.Length > 160 ? s[..160] + "..." : s).Replace("\n", "\\n"), caller);
                        break;
                    }
                    if ((uint)tok >> 24 == 0x06) {
                        var th = (MethodDefinitionHandle)MetadataTokens.EntityHandle(tok);
                        if (pinvokes.TryGetValue(th, out var pi)) Add("PINVOKE-CALL | " + pi, caller);
                    }
                    var t = prov.Token(md, tok);
                    foreach (var (c, re) in cats) if (re.IsMatch(t)) { Add(c + " | " + t, caller); break; }
                    break;
                }
            }
        }
    }
    // Unity auto-run hooks
    foreach (var cah in md.CustomAttributes) {
        var ca = md.GetCustomAttribute(cah);
        string ctor = ca.Constructor.Kind == HandleKind.MemberReference
            ? prov.Token(md, MetadataTokens.GetToken(ca.Constructor))
            : prov.Token(md, MetadataTokens.GetToken(ca.Constructor));
        if (ctor.Contains("RuntimeInitializeOnLoadMethod") || ctor.Contains("ModuleInitializer")) {
            string target = ca.Parent.Kind == HandleKind.MethodDefinition ? Prov.MethodKey(md, (MethodDefinitionHandle)ca.Parent, prov) : ca.Parent.Kind.ToString();
            Add("AUTORUN | " + ctor.Split("::")[0], target);
        }
    }
    foreach (var th in md.TypeDefinitions) {
        var td = md.GetTypeDefinition(th);
        if (md.GetString(td.Name) == "<Module>") foreach (var mh in td.GetMethods()) if (md.GetString(md.GetMethodDefinition(mh).Name) == ".cctor") Add("AUTORUN | <Module>.cctor (module initializer)", Prov.MethodKey(md, mh, prov));
    }
    Console.WriteLine($"=== {name}: {hits.Count} distinct sensitive items");
    foreach (var (k, callers) in hits) {
        Console.WriteLine("  " + k + "   [" + callers.Count + " caller(s)]");
        foreach (var c in callers.Take(6)) Console.WriteLine("      <- " + c);
        if (callers.Count > 6) Console.WriteLine("      <- ... +" + (callers.Count - 6) + " more");
    }
}

class Prov : ISignatureTypeProvider<string, object?> {
    public string GetArrayType(string e, ArrayShape s) => e + "[" + new string(',', s.Rank - 1) + "]";
    public string GetByReferenceType(string e) => e + "&";
    public string GetFunctionPointerType(MethodSignature<string> s) => "fnptr(" + string.Join(",", s.ParameterTypes) + ")" + s.ReturnType;
    public string GetGenericInstantiation(string gt, ImmutableArray<string> a) => gt + "<" + string.Join(",", a) + ">";
    public string GetGenericMethodParameter(object? c, int i) => "!!" + i;
    public string GetGenericTypeParameter(object? c, int i) => "!" + i;
    public string GetModifiedType(string m, string u, bool r) => u;
    public string GetPinnedType(string e) => e;
    public string GetPointerType(string e) => e + "*";
    public string GetPrimitiveType(PrimitiveTypeCode t) => t switch { PrimitiveTypeCode.String => "System.String", PrimitiveTypeCode.Object => "System.Object", _ => t.ToString() };
    public string GetSZArrayType(string e) => e + "[]";
    public string GetTypeFromDefinition(MetadataReader r, TypeDefinitionHandle h, byte k) => DefName(r, h);
    public string GetTypeFromReference(MetadataReader r, TypeReferenceHandle h, byte k) => RefName(r, h);
    public string GetTypeFromSpecification(MetadataReader r, object? c, TypeSpecificationHandle h, byte k) => r.GetTypeSpecification(h).DecodeSignature(this, c);
    public static string DefName(MetadataReader r, TypeDefinitionHandle h) {
        var t = r.GetTypeDefinition(h);
        var dt = t.GetDeclaringType();
        if (!dt.IsNil) return DefName(r, dt) + "/" + r.GetString(t.Name);
        var ns = r.GetString(t.Namespace); return (ns.Length > 0 ? ns + "." : "") + r.GetString(t.Name);
    }
    public static string RefName(MetadataReader r, TypeReferenceHandle h) {
        var t = r.GetTypeReference(h);
        if (t.ResolutionScope.Kind == HandleKind.TypeReference) return RefName(r, (TypeReferenceHandle)t.ResolutionScope) + "/" + r.GetString(t.Name);
        var ns = r.GetString(t.Namespace); return (ns.Length > 0 ? ns + "." : "") + r.GetString(t.Name);
    }
    public static string MethodKey(MetadataReader md, MethodDefinitionHandle mh, Prov p) {
        var m = md.GetMethodDefinition(mh);
        try {
            var sig = m.DecodeSignature(p, null);
            return DefName(md, m.GetDeclaringType()) + "::" + md.GetString(m.Name) + (sig.GenericParameterCount > 0 ? "`" + sig.GenericParameterCount : "") + "(" + string.Join(",", sig.ParameterTypes) + ")" + sig.ReturnType;
        } catch { return DefName(md, m.GetDeclaringType()) + "::" + md.GetString(m.Name) + "(?)"; }
    }
    public string Token(MetadataReader md, int tok) {
        try {
            if ((uint)tok >> 24 == 0x70) return "\"" + md.GetUserString(MetadataTokens.UserStringHandle(tok & 0xFFFFFF)) + "\"";
            var h = MetadataTokens.EntityHandle(tok);
            switch ((uint)tok >> 24) {
                case 0x01: return RefName(md, (TypeReferenceHandle)h);
                case 0x02: return DefName(md, (TypeDefinitionHandle)h);
                case 0x1B: return md.GetTypeSpecification((TypeSpecificationHandle)h).DecodeSignature(this, null);
                case 0x04: { var f = md.GetFieldDefinition((FieldDefinitionHandle)h); return DefName(md, f.GetDeclaringType()) + "::" + md.GetString(f.Name); }
                case 0x06: return MethodKey(md, (MethodDefinitionHandle)h, this);
                case 0x0A: {
                    var mr = md.GetMemberReference((MemberReferenceHandle)h);
                    string parent = mr.Parent.Kind switch {
                        HandleKind.TypeReference => RefName(md, (TypeReferenceHandle)mr.Parent),
                        HandleKind.TypeDefinition => DefName(md, (TypeDefinitionHandle)mr.Parent),
                        HandleKind.TypeSpecification => md.GetTypeSpecification((TypeSpecificationHandle)mr.Parent).DecodeSignature(this, null),
                        HandleKind.MethodDefinition => MethodKey(md, (MethodDefinitionHandle)mr.Parent, this),
                        _ => "?" };
                    if (mr.GetKind() == MemberReferenceKind.Method) { var s = mr.DecodeMethodSignature(this, null); return parent + "::" + md.GetString(mr.Name) + (s.GenericParameterCount > 0 ? "`" + s.GenericParameterCount : "") + "(" + string.Join(",", s.ParameterTypes) + ")" + s.ReturnType; }
                    return parent + "::" + md.GetString(mr.Name);
                }
                case 0x2B: { var ms = md.GetMethodSpecification((MethodSpecificationHandle)h); var inst = ms.DecodeSignature(this, null); return Token(md, MetadataTokens.GetToken(ms.Method)) + "<" + string.Join(",", inst) + ">"; }
                case 0x11: return "sig";
            }
        } catch { }
        return "tok" + ((uint)tok >> 24).ToString("x2");
    }
}
