using System.Collections.Immutable;
using System.Reflection;
using System.Reflection.Emit;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Text;

var ops = new Dictionary<short, OpCode>();
foreach (var f in typeof(OpCodes).GetFields(BindingFlags.Public | BindingFlags.Static)) { var o = (OpCode)f.GetValue(null)!; ops[o.Value] = o; }

Dictionary<string, string> Load(string path, out int total) {
    var res = new Dictionary<string, string>();
    var pe = new PEReader(File.OpenRead(path));
    var md = pe.GetMetadataReader();
    var prov = new Prov();
    total = 0;
    foreach (var mh in md.MethodDefinitions) {
        var m = md.GetMethodDefinition(mh);
        string key = Prov.MethodKey(md, mh, prov);
        string body = "<no body>";
        if (m.RelativeVirtualAddress != 0) {
            var il = pe.GetMethodBody(m.RelativeVirtualAddress).GetILBytes()!;
            body = Normalize(md, il, prov);
        }
        total++;
        res[key] = body;
    }
    return res;
}

string Normalize(MetadataReader md, byte[] il, Prov prov) {
    var sb = new StringBuilder(); int i = 0;
    while (i < il.Length) {
        short v;
        if (il[i] == 0xFE) { v = (short)(0xFE00 | il[i + 1]); i += 2; } else { v = il[i]; i += 1; }
        if (!ops.TryGetValue(v, out var op)) { sb.Append("??"); break; }
        sb.Append(op.Name);
        switch (op.OperandType) {
            case OperandType.InlineNone: break;
            case OperandType.ShortInlineBrTarget: case OperandType.ShortInlineI: case OperandType.ShortInlineVar: sb.Append(' ').Append(il[i]); i += 1; break;
            case OperandType.InlineVar: sb.Append(' ').Append(BitConverter.ToUInt16(il, i)); i += 2; break;
            case OperandType.InlineI8: case OperandType.InlineR: sb.Append(' ').Append(BitConverter.ToInt64(il, i)); i += 8; break;
            case OperandType.InlineSwitch: int n = BitConverter.ToInt32(il, i); i += 4; sb.Append(" sw").Append(n); for (int k = 0; k < n; k++) { sb.Append(',').Append(BitConverter.ToInt32(il, i)); i += 4; } break;
            case OperandType.InlineBrTarget: case OperandType.InlineI: case OperandType.ShortInlineR: sb.Append(' ').Append(BitConverter.ToInt32(il, i)); i += 4; break;
            default:
                int tok = BitConverter.ToInt32(il, i); i += 4;
                sb.Append(' ').Append(prov.Token(md, tok)); break;
        }
        sb.Append(';');
    }
    return sb.ToString();
}

var game = args[0];
var g = Load(game, out int gTotal);
string? bestRef = null; int bestSame = -1; Dictionary<string, string>? bestR = null; int bestTotal = 0;
foreach (var r in args.Skip(1)) {
    try {
        var rr = Load(r, out int rt);
        int same = g.Count(kv => rr.TryGetValue(kv.Key, out var b) && b == kv.Value);
        Console.WriteLine($"  vs {r}: {same}/{g.Count} game methods identical");
        if (same > bestSame) { bestSame = same; bestRef = r; bestR = rr; bestTotal = rt; }
    } catch (Exception e) { Console.WriteLine($"  vs {r}: error {e.Message}"); }
}
var added = g.Keys.Where(k => !bestR!.ContainsKey(k)).ToList();
var changed = g.Where(kv => bestR!.TryGetValue(kv.Key, out var b) && b != kv.Value).Select(kv => kv.Key).ToList();
Console.WriteLine($"RESULT {Path.GetFileName(game)}: methods={g.Count}, identical={bestSame}, ADDED(not in official)={added.Count}, CHANGED={changed.Count}, stripped-from-official={bestTotal - (g.Count - added.Count)}  [best ref: {bestRef}]");
bool showAll = Environment.GetEnvironmentVariable("ALLADDED") == "1";
foreach (var a in added.Take(showAll ? int.MaxValue : 25)) Console.WriteLine("   ADDED   " + a + (showAll ? "   BODY=" + g[a] : ""));
foreach (var c in changed.Take(25)) Console.WriteLine("   CHANGED " + c);
if (args.Length > 0 && Environment.GetEnvironmentVariable("DUMP") is string d && d.Length > 0) {
    using var w = new StreamWriter(d);
    foreach (var c in changed) { w.WriteLine("### " + c); w.WriteLine("GAME: " + g[c]); w.WriteLine("REF : " + bestR![c]); }
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
    public string GetPrimitiveType(PrimitiveTypeCode t) => t.ToString();
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
        var sig = m.DecodeSignature(p, null);
        return DefName(md, m.GetDeclaringType()) + "::" + md.GetString(m.Name) + (sig.GenericParameterCount > 0 ? "`" + sig.GenericParameterCount : "") + "(" + string.Join(",", sig.ParameterTypes) + ")" + sig.ReturnType;
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
