namespace UnityApiInventory;

internal static class InventoryRunner
{
    public const string SchemaVersion = "1.0";
    public const string ExtractorVersion = "1.0.0";

    public static int Run(InventoryOptions options)
    {
        CaptureContext context = Context(options);
        ProjectMetadataIndex projectMetadata = ProjectMetadataIndex.Load(options.ProjectRoot);
        var assemblies = new List<AssemblyRecord>();
        var skippedAssemblies = new List<SkippedAssembly>();
        var records = new List<ApiRecord>();
        foreach (string path in AssemblyDiscovery.Discover(options))
        {
            string displayPath = AssemblyDiscovery.DisplayPath(path, options.UnityRoot);
            try
            {
                ExtractionResult result = MetadataExtractor.Extract(
                    path,
                    displayPath,
                    options,
                    context,
                    projectMetadata);
                assemblies.Add(result.Assembly);
                records.AddRange(result.Records);
            }
            catch (BadImageFormatException)
            {
                skippedAssemblies.Add(new SkippedAssembly(displayPath, "not_managed_assembly"));
            }
        }

        DocumentationIndex documentation = DocumentationIndex.Load(options);
        documentation.Apply(records);

        ApiRecord[] orderedRecords = records
            .OrderBy(record => record.SymbolId, StringComparer.Ordinal)
            .ThenBy(record => record.CanonicalSignature, StringComparer.Ordinal)
            .ToArray();
        byte[] snapshot = JsonFiles.SerializeJsonLines(orderedRecords);
        JsonFiles.WriteBytes(options.Output, snapshot);
        InventorySummary summary = Summary(
            options,
            assemblies,
            skippedAssemblies,
            projectMetadata,
            documentation,
            orderedRecords,
            snapshot);
        JsonFiles.WriteJson(options.Summary, summary);
        return 0;
    }

    private static CaptureContext Context(InventoryOptions options)
    {
        return new CaptureContext(
            new UnityIdentity(options.UnityVersion, options.UnityRevision),
            options.HostOs,
            options.BuildTarget,
            options.Defines,
            options.ApiCompatibility,
            ExtractorVersion,
            options.CaptureTime);
    }

    private static InventorySummary Summary(
        InventoryOptions options,
        IReadOnlyList<AssemblyRecord> assemblies,
        IReadOnlyList<SkippedAssembly> skippedAssemblies,
        ProjectMetadataIndex projectMetadata,
        DocumentationIndex documentation,
        IReadOnlyList<ApiRecord> records,
        byte[] snapshot)
    {
        var counts = records
            .GroupBy(record => record.MemberKind, StringComparer.Ordinal)
            .OrderBy(group => group.Key, StringComparer.Ordinal)
            .ToDictionary(group => group.Key, group => group.Count(), StringComparer.Ordinal);
        AssemblyRecord[] orderedAssemblies = assemblies
            .OrderBy(assembly => assembly.Name, StringComparer.Ordinal)
            .ThenBy(assembly => assembly.Path, StringComparer.Ordinal)
            .ToArray();
        return new InventorySummary(
            SchemaVersion,
            ExtractorVersion,
            options.CaptureTime,
            options.HostOs,
            new UnityIdentity(options.UnityVersion, options.UnityRevision),
            options.BuildTarget,
            options.Defines,
            options.ApiCompatibility,
            orderedAssemblies.Length,
            records.Count,
            counts,
            JsonFiles.Sha256(snapshot),
            orderedAssemblies,
            skippedAssemblies.OrderBy(item => item.Path, StringComparer.Ordinal).ToArray(),
            documentation.JoinInfo(options, records),
            projectMetadata.Summary(orderedAssemblies),
            PlaybackModuleScanner.Scan(options.UnityRoot));
    }
}
