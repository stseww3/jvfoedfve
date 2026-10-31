using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Text;
var compOpts = new Guid("B5FEEC05-8CD0-4A83-96DA-466284BB4BD8");
var compRefs = new Guid("7E4D4708-096E-4C5C-AEDA-CB10BA6A740D");
var srcLink = new Guid("CC110556-A091-4D38-9FEC-25AB9A351A6A");
foreach (var p in args) {
    using var prov = MetadataReaderProvider.FromPortablePdbStream(File.OpenRead(p));
    var md = prov.GetMetadataReader();
    var kinds = new List<string>();
    foreach (var h in md.GetCustomDebugInformation(EntityHandle.ModuleDefinition)) {
        var cdi = md.GetCustomDebugInformation(h);
        var k = md.GetGuid(cdi.Kind);
        var blob = md.GetBlobBytes(cdi.Value);
        if (k == compOpts) {
            var parts = Encoding.UTF8.GetString(blob).Split('\0');
            var sb = new StringBuilder();
            for (int i = 0; i + 1 < parts.Length; i += 2) sb.Append(parts[i]).Append('=').Append(parts[i + 1].Length > 3000 ? parts[i + 1][..3000] + "..." : parts[i + 1]).Append(" | ");
            kinds.Add("CompilationOptions: " + sb);
        } else if (k == compRefs) kinds.Add($"CompilationMetadataReferences ({blob.Length} bytes)");
        else if (k == srcLink) kinds.Add("SourceLink");
        else kinds.Add(k.ToString());
    }
    Console.WriteLine($"== {Path.GetFileName(p)}: {(kinds.Count == 0 ? "(no module CDI)" : string.Join("\n   ", kinds))}");
}
