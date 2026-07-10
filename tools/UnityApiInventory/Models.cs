namespace UnityApiInventory;

internal sealed record ObsoleteInfo(bool IsObsolete, string? Message, bool IsError);

internal sealed record ProvenanceInfo(
    string Classification,
    string? PackageId = null,
    string? Asmdef = null,
    string? PackageSource = null,
    string? PackageVersion = null,
    string? SourceRoot = null,
    int? SourceFileCount = null,
    string? ManifestPath = null,
    string? PackageLockPath = null,
    VariantEvidence? VariantEvidence = null,
    string Resolution = "path_heuristic");

internal sealed record VariantEvidence(
    IReadOnlyList<string> IncludePlatforms,
    IReadOnlyList<string> ExcludePlatforms,
    IReadOnlyList<string> DefineConstraints,
    IReadOnlyList<string> OptionalUnityReferences,
    bool AutoReferenced);

internal sealed record AvailabilityInfo(
    string Key,
    bool Editor,
    bool Runtime,
    string BuildTarget,
    IReadOnlyList<string> Defines,
    string ApiCompatibility);

internal sealed record CaptureContext(
    UnityIdentity Unity,
    string HostOs,
    string BuildTarget,
    IReadOnlyList<string> Defines,
    string ApiCompatibility,
    string ExtractorVersion,
    string CaptureTime);

internal sealed record UnityIdentity(string Version, string Revision);

internal sealed record AssemblyRecord(
    string Name,
    string Path,
    string Mvid,
    string Sha256,
    ProvenanceInfo Provenance);

internal sealed record SkippedAssembly(string Path, string Reason);

internal sealed record DocumentationJoinInfo(
    string Status,
    string? SourcePath,
    string? SourceSha256,
    string BaseUrl,
    int TocEntryCount,
    int IndexedEntryCount,
    int IgnoredEntryCount,
    int AmbiguousIdentityCount,
    int MatchedTypeCount,
    int UnmatchedTypeCount);

internal sealed record ProjectMetadataInfo(
    string Status,
    string? ProjectRoot,
    string? ManifestPath,
    string? ManifestSha256,
    string? PackagesLockPath,
    string? PackagesLockSha256,
    int AsmdefCount,
    int MatchedAssemblyCount,
    IReadOnlyList<string> UnresolvedAssemblyNames,
    IReadOnlyList<AssemblySourceMap> SourceMaps);

internal sealed record AssemblySourceMap(
    string AssemblyName,
    string Asmdef,
    IReadOnlyList<string> SourceFiles);

internal sealed record PlaybackModuleEvidence(
    string Name,
    string Path,
    int GenericManagedAssemblyCount,
    IReadOnlyList<string> Variations);

internal sealed class ApiRecord
{
    public string SchemaVersion { get; init; } = InventoryRunner.SchemaVersion;
    public required string SymbolId { get; init; }
    public required string CanonicalSignature { get; init; }
    public required string RecordKind { get; init; }
    public required string MemberKind { get; init; }
    public string? TypeKind { get; init; }
    public string? DeclaringType { get; init; }
    public string Visibility { get; init; } = "public";
    public bool IsStatic { get; init; }
    public int GenericArity { get; init; }
    public required ObsoleteInfo Obsolete { get; init; }
    public required AvailabilityInfo Availability { get; init; }
    public required ProvenanceInfo Provenance { get; init; }
    public required AssemblyRecord Assembly { get; init; }
    public required CaptureContext Context { get; init; }
    public IReadOnlyList<string> CapabilityTags { get; init; } = [];
    public string? DocumentationUrl { get; set; }
    public string? SourceUrl { get; init; }
    public string? CoverageClassification { get; init; }
}

internal sealed record InventorySummary(
    string SchemaVersion,
    string ExtractorVersion,
    string CaptureTime,
    string HostOs,
    UnityIdentity Unity,
    string BuildTarget,
    IReadOnlyList<string> Defines,
    string ApiCompatibility,
    int AssemblyCount,
    int SymbolCount,
    IReadOnlyDictionary<string, int> RecordCounts,
    string SnapshotSha256,
    IReadOnlyList<AssemblyRecord> Assemblies,
    IReadOnlyList<SkippedAssembly> SkippedAssemblies,
    DocumentationJoinInfo DocumentationJoin,
    ProjectMetadataInfo ProjectMetadata,
    IReadOnlyList<PlaybackModuleEvidence> PlaybackModules);

internal sealed record ExtractionResult(AssemblyRecord Assembly, IReadOnlyList<ApiRecord> Records);
