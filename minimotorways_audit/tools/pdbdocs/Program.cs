using System.Reflection.Metadata;
var sha256 = new Guid("8829d00f-11b8-4213-878b-770e8597ac16");
var sha1 = new Guid("ff1816ec-aa5e-4d10-87f7-6f4963833460");
foreach (var p in args) {
    using var prov = MetadataReaderProvider.FromPortablePdbStream(File.OpenRead(p));
    var md = prov.GetMetadataReader();
    foreach (var dh in md.Documents) {
        var d = md.GetDocument(dh);
        var alg = md.GetGuid(d.HashAlgorithm);
        string a = alg == sha256 ? "sha256" : alg == sha1 ? "sha1" : alg.ToString();
        bool embedded = false;
        foreach (var cdi in md.GetCustomDebugInformation(dh)) if (md.GetGuid(md.GetCustomDebugInformation(cdi).Kind) == new Guid("0E8A571B-6926-466E-B4AD-8AB04611F5FE")) embedded = true;
        Console.WriteLine($"{Path.GetFileName(p)}\t{a}\t{Convert.ToHexString(md.GetBlobBytes(d.Hash)).ToLower()}\t{(embedded ? "EMBEDDED" : "-")}\t{md.GetString(d.Name)}");
    }
}
