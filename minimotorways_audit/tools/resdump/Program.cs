using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;

var outDir = args[0];
Directory.CreateDirectory(outDir);
foreach (var path in args.Skip(1)) {
    var name = Path.GetFileName(path);
    var bytes = File.ReadAllBytes(path);
    using var pe = new PEReader(new MemoryStream(bytes));
    if (!pe.HasMetadata) continue;
    var md = pe.GetMetadataReader();
    var cor = pe.PEHeaders.CorHeader!;
    int resRva = cor.ResourcesDirectory.RelativeVirtualAddress;
    int count = 0;
    foreach (var rh in md.ManifestResources) {
        var r = md.GetManifestResource(rh);
        var rname = md.GetString(r.Name);
        count++;
        if (!r.Implementation.IsNil) { Console.WriteLine($"{name}\tLINKED\t{rname}\t{r.Implementation.Kind}"); continue; }
        pe.PEHeaders.TryGetDirectoryOffset(cor.ResourcesDirectory, out int resOff);
        long off = resOff + r.Offset;
        int len = BitConverter.ToInt32(bytes, (int)off);
        var data = bytes.AsSpan((int)off + 4, len).ToArray();
        var dst = Path.Combine(outDir, name + "__" + rname);
        File.WriteAllBytes(dst, data);
        string magic = BitConverter.ToString(data.Take(8).ToArray());
        Console.WriteLine($"{name}\tEMBEDDED\t{rname}\t{len}\t{magic}");
    }
    if (count == 0) Console.WriteLine($"{name}\tNONE");
}
