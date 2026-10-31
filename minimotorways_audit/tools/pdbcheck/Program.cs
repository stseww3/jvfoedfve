using System.Collections.Immutable;
using System.Reflection;
using System.Reflection.Emit;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;

var ops = new Dictionary<short, OpCode>();
foreach (var f in typeof(OpCodes).GetFields(BindingFlags.Public | BindingFlags.Static)) { var o = (OpCode)f.GetValue(null)!; ops[o.Value] = o; }

HashSet<int>? Boundaries(byte[] il) {
    var set = new HashSet<int>(); int i = 0;
    while (i < il.Length) {
        set.Add(i); short v;
        if (il[i] == 0xFE) { if (i + 1 >= il.Length) return null; v = (short)(0xFE00 | il[i + 1]); i += 2; } else { v = il[i]; i += 1; }
        if (!ops.TryGetValue(v, out var op)) return null;
        switch (op.OperandType) {
            case OperandType.InlineNone: break;
            case OperandType.ShortInlineBrTarget: case OperandType.ShortInlineI: case OperandType.ShortInlineVar: i += 1; break;
            case OperandType.InlineVar: i += 2; break;
            case OperandType.InlineI8: case OperandType.InlineR: i += 8; break;
            case OperandType.InlineSwitch: int n = BitConverter.ToInt32(il, i); i += 4 + 4 * n; break;
            default: i += 4; break;
        }
    }
    return i == il.Length ? set : null;
}

var dir = args[0];
Console.WriteLine($"{"assembly",-48} {"pdbId",-6} {"chksum",-7} {"methods dll/pdb",-16} {"seqpts checked",-15} {"bad",-4} docs  verdict");
foreach (var dll in Directory.GetFiles(dir, "*.dll").OrderBy(x => x)) {
    var pdbPath = Path.ChangeExtension(dll, ".pdb");
    if (!File.Exists(pdbPath)) continue;
    var name = Path.GetFileName(dll);
    using var fs = File.OpenRead(dll);
    using var pe = new PEReader(fs);
    var md = pe.GetMetadataReader();
    CodeViewDebugDirectoryData? cv = null; DebugDirectoryEntry cvE = default; var sums = new List<PdbChecksumDebugDirectoryData>();
    foreach (var e in pe.ReadDebugDirectory()) {
        if (e.Type == DebugDirectoryEntryType.CodeView) { cv = pe.ReadCodeViewDebugDirectoryData(e); cvE = e; }
        else if (e.Type == DebugDirectoryEntryType.PdbChecksum) sums.Add(pe.ReadPdbChecksumDebugDirectoryData(e));
    }
    var pdbBytes = File.ReadAllBytes(pdbPath);
    if (!(pdbBytes[0] == 'B' && pdbBytes[1] == 'S' && pdbBytes[2] == 'J' && pdbBytes[3] == 'B')) { Console.WriteLine($"{name,-48} (Windows-format PDB, skipped)"); continue; }
    using var prov = MetadataReaderProvider.FromPortablePdbImage(ImmutableArray.Create(pdbBytes));
    var pdb = prov.GetMetadataReader();
    var hdr = pdb.DebugMetadataHeader!;
    var id = hdr.Id.ToArray();
    var guid = new Guid(id.AsSpan(0, 16));
    uint stamp = BitConverter.ToUInt32(id, 16);
    bool idOk = cv.HasValue && cv.Value.Guid == guid && cvE.Stamp == stamp;
    string sumRes = "none";
    if (sums.Count > 0) {
        var copy = (byte[])pdbBytes.Clone();
        for (int k = 0; k < 20; k++) copy[hdr.IdStartOffset + k] = 0;
        sumRes = "BAD";
        foreach (var s in sums) {
            byte[] h = s.AlgorithmName switch { "SHA256" => SHA256.HashData(copy), "SHA384" => SHA384.HashData(copy), "SHA512" => SHA512.HashData(copy), _ => Array.Empty<byte>() };
            if (h.AsSpan().SequenceEqual(s.Checksum.AsSpan())) sumRes = "OK";
        }
    }
    int mDll = md.MethodDefinitions.Count, mPdb = pdb.MethodDebugInformation.Count;
    int checkedSp = 0, bad = 0; var badMethods = new List<string>();
    foreach (var mh in md.MethodDefinitions) {
        var mdef = md.GetMethodDefinition(mh);
        if (mdef.RelativeVirtualAddress == 0) continue;
        var dih = mh.ToDebugInformationHandle();
        if (MetadataTokens.GetRowNumber(dih) > mPdb) continue;
        var di = pdb.GetMethodDebugInformation(dih);
        if (di.SequencePointsBlob.IsNil) continue;
        var il = pe.GetMethodBody(mdef.RelativeVirtualAddress).GetILBytes()!;
        var b = Boundaries(il);
        foreach (var sp in di.GetSequencePoints()) {
            checkedSp++;
            if (b == null || sp.Offset >= il.Length || !b.Contains(sp.Offset)) {
                bad++;
                var t = md.GetTypeDefinition(mdef.GetDeclaringType());
                badMethods.Add($"{md.GetString(t.Namespace)}.{md.GetString(t.Name)}::{md.GetString(mdef.Name)}");
                break;
            }
        }
    }
    bool ok = idOk && sumRes != "BAD" && mDll == mPdb && bad == 0;
    Console.WriteLine($"{name,-48} {(idOk ? "OK" : "BAD"),-6} {sumRes,-7} {mDll + "/" + mPdb,-16} {checkedSp,-15} {bad,-4} {pdb.Documents.Count,-5} {(ok ? "UNMODIFIED" : "*** SUSPICIOUS ***")}");
    foreach (var bm in badMethods.Distinct().Take(10)) Console.WriteLine($"      bad sequence points in {bm}");
    using var docs = new StreamWriter(Path.Combine(args[1], name + ".sources.txt"));
    foreach (var dh in pdb.Documents) docs.WriteLine(pdb.GetString(pdb.GetDocument(dh).Name));
}
