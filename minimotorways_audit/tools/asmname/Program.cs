using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
foreach (var p in Directory.EnumerateFiles(args[0])) {
    try {
        using var pe = new PEReader(File.OpenRead(p));
        if (!pe.HasMetadata) continue;
        var md = pe.GetMetadataReader();
        if (!md.IsAssembly) continue;
        var a = md.GetAssemblyDefinition();
        Console.WriteLine($"{Path.GetFileName(p)}\t{md.GetString(a.Name)}\t{a.Version}\t{md.MethodDefinitions.Count}");
    } catch { }
}
