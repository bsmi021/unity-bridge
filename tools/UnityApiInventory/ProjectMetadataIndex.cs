using System.Text.Json;

namespace UnityApiInventory;

internal sealed class ProjectMetadataIndex
{
    private readonly string? _projectRoot;
    private readonly IReadOnlyDictionary<string, AsmdefInfo> _asmdefs;
    private readonly IReadOnlySet<string> _ambiguousNames;
    private readonly IReadOnlyDictionary<string, PackageLockEntry> _lockEntries;
    private readonly int _asmdefCount;
    private readonly string? _manifestPath;
    private readonly string? _lockPath;

    private ProjectMetadataIndex(
        string? projectRoot,
        IReadOnlyDictionary<string, AsmdefInfo> asmdefs,
        IReadOnlySet<string> ambiguousNames,
        IReadOnlyDictionary<string, PackageLockEntry> lockEntries,
        int asmdefCount,
        string? manifestPath,
        string? lockPath)
    {
        _projectRoot = projectRoot;
        _asmdefs = asmdefs;
        _ambiguousNames = ambiguousNames;
        _lockEntries = lockEntries;
        _asmdefCount = asmdefCount;
        _manifestPath = manifestPath;
        _lockPath = lockPath;
    }

    public static ProjectMetadataIndex Load(string? projectRoot)
    {
        if (projectRoot is null) return Empty();
        string root = Path.GetFullPath(projectRoot);
        if (!Directory.Exists(root)) throw new CliException($"Project root does not exist: {root}");
        string manifest = Path.Combine(root, "Packages", "manifest.json");
        string lockFile = Path.Combine(root, "Packages", "packages-lock.json");
        IReadOnlyDictionary<string, PackageLockEntry> lockEntries = ReadLock(lockFile);
        (Dictionary<string, AsmdefInfo> asmdefs, HashSet<string> ambiguous, int count) =
            ReadAsmdefs(root, lockEntries, lockFile);
        return new ProjectMetadataIndex(
            root,
            asmdefs,
            ambiguous,
            lockEntries,
            count,
            File.Exists(manifest) ? manifest : null,
            File.Exists(lockFile) ? lockFile : null);
    }

    public ProvenanceInfo Classify(
        string assemblyPath,
        string assemblyName,
        ProvenanceInfo fallback)
    {
        if (_projectRoot is null) return fallback;
        if (_ambiguousNames.Contains(assemblyName))
        {
            return fallback with { Resolution = "ambiguous_asmdef" };
        }

        if (_asmdefs.TryGetValue(assemblyName, out AsmdefInfo? asmdef))
        {
            return asmdef.Provenance;
        }

        if (IsUnderProject(assemblyPath) && assemblyName.StartsWith("Assembly-CSharp", StringComparison.Ordinal))
        {
            return new ProvenanceInfo("project", Resolution: "default_project_assembly");
        }

        return fallback;
    }

    public ProjectMetadataInfo Summary(IReadOnlyList<AssemblyRecord> assemblies)
    {
        if (_projectRoot is null)
        {
            return new ProjectMetadataInfo(
                "not_requested", null, null, null, null, null, 0, 0, [], []);
        }

        string status = _manifestPath is not null && _lockPath is not null
            ? "joined"
            : "joined_with_gaps";
        string[] unresolved = assemblies
            .Where(item => IsUnderProject(item.Path))
            .Where(item => item.Provenance.Resolution is not "asmdef" and not "default_project_assembly")
            .Select(item => item.Name)
            .Distinct(StringComparer.Ordinal)
            .Order(StringComparer.Ordinal)
            .ToArray();
        AssemblySourceMap[] sourceMaps = assemblies
            .Where(item => item.Provenance.Resolution == "asmdef")
            .Select(item => SourceMap(item.Name))
            .Where(item => item is not null)
            .Cast<AssemblySourceMap>()
            .OrderBy(item => item.AssemblyName, StringComparer.Ordinal)
            .ToArray();
        return new ProjectMetadataInfo(
            status,
            Normalize(_projectRoot),
            RelativeOrNull(_manifestPath),
            HashOrNull(_manifestPath),
            RelativeOrNull(_lockPath),
            HashOrNull(_lockPath),
            _asmdefCount,
            assemblies.Count(item => item.Provenance.Resolution == "asmdef"),
            unresolved,
            sourceMaps);
    }

    private static ProjectMetadataIndex Empty()
    {
        return new ProjectMetadataIndex(
            null,
            new Dictionary<string, AsmdefInfo>(),
            new HashSet<string>(),
            new Dictionary<string, PackageLockEntry>(),
            0,
            null,
            null);
    }

    private static (
        Dictionary<string, AsmdefInfo> Asmdefs,
        HashSet<string> Ambiguous,
        int Count) ReadAsmdefs(
            string root,
            IReadOnlyDictionary<string, PackageLockEntry> lockEntries,
            string lockPath)
    {
        var asmdefs = new Dictionary<string, AsmdefInfo>(StringComparer.Ordinal);
        var ambiguous = new HashSet<string>(StringComparer.Ordinal);
        int count = 0;
        foreach (string searchRoot in AsmdefRoots(root).Where(Directory.Exists))
        {
            foreach (string path in Directory.EnumerateFiles(searchRoot, "*.asmdef", SearchOption.AllDirectories))
            {
                AsmdefInfo info = ReadAsmdef(root, path, lockEntries, lockPath);
                count++;
                if (!asmdefs.TryAdd(info.Name, info)) ambiguous.Add(info.Name);
            }
        }

        return (asmdefs, ambiguous, count);
    }

    private static IEnumerable<string> AsmdefRoots(string root)
    {
        yield return Path.Combine(root, "Assets");
        yield return Path.Combine(root, "Packages");
        yield return Path.Combine(root, "Library", "PackageCache");
    }

    private static AsmdefInfo ReadAsmdef(
        string projectRoot,
        string path,
        IReadOnlyDictionary<string, PackageLockEntry> lockEntries,
        string lockPath)
    {
        using JsonDocument document = JsonDocument.Parse(File.ReadAllText(path));
        JsonElement root = document.RootElement;
        string name = RequiredString(root, "name", path);
        PackageIdentity package = PackageFor(projectRoot, path, lockEntries);
        string sourceRoot = Path.GetDirectoryName(path)!;
        string[] sourceFiles = Directory.EnumerateFiles(sourceRoot, "*.cs", SearchOption.AllDirectories)
            .Select(item => Relative(projectRoot, item))
            .Order(StringComparer.Ordinal)
            .ToArray();
        string[] optional = Strings(root, "optionalUnityReferences");
        bool isTest = optional.Contains("TestAssemblies", StringComparer.Ordinal)
            || name.EndsWith(".Tests", StringComparison.Ordinal);
        var variants = new VariantEvidence(
            Strings(root, "includePlatforms"),
            Strings(root, "excludePlatforms"),
            Strings(root, "defineConstraints"),
            optional,
            !root.TryGetProperty("autoReferenced", out JsonElement auto) || auto.GetBoolean());
        var provenance = new ProvenanceInfo(
            isTest ? "test" : package.Id is null ? "project" : "package",
            package.Id,
            Relative(projectRoot, path),
            package.Source,
            package.Version,
            Relative(projectRoot, sourceRoot),
            sourceFiles.Length,
            RelativeOrNull(projectRoot, package.ManifestPath),
            package.Id is not null && File.Exists(lockPath) ? Relative(projectRoot, lockPath) : null,
            variants,
            "asmdef");
        return new AsmdefInfo(name, provenance, sourceFiles);
    }

    private static PackageIdentity PackageFor(
        string root,
        string asmdefPath,
        IReadOnlyDictionary<string, PackageLockEntry> lockEntries)
    {
        string relative = Relative(root, asmdefPath);
        string? packageRoot = null;
        string? packageId = null;
        if (relative.StartsWith("Packages/", StringComparison.Ordinal))
        {
            packageId = relative.Split('/')[1];
            packageRoot = Path.Combine(root, "Packages", packageId);
        }
        else if (relative.StartsWith("Library/PackageCache/", StringComparison.Ordinal))
        {
            string folder = relative.Split('/')[2];
            int separator = folder.LastIndexOf('@');
            packageId = separator > 0 ? folder[..separator] : folder;
            packageRoot = Path.Combine(root, "Library", "PackageCache", folder);
        }

        return ReadPackage(packageId, packageRoot, lockEntries);
    }

    private static PackageIdentity ReadPackage(
        string? packageId,
        string? packageRoot,
        IReadOnlyDictionary<string, PackageLockEntry> lockEntries)
    {
        if (packageId is null || packageRoot is null) return new PackageIdentity(null, null, null, null);
        string manifest = Path.Combine(packageRoot, "package.json");
        string? version = null;
        if (File.Exists(manifest))
        {
            using JsonDocument document = JsonDocument.Parse(File.ReadAllText(manifest));
            version = OptionalString(document.RootElement, "version");
            packageId = OptionalString(document.RootElement, "name") ?? packageId;
        }

        lockEntries.TryGetValue(packageId, out PackageLockEntry? entry);
        string source = entry?.Source
            ?? (packageRoot.Contains($"{Path.DirectorySeparatorChar}Packages{Path.DirectorySeparatorChar}")
                ? "embedded"
                : "unresolved");
        return new PackageIdentity(packageId, version ?? entry?.Version, source, manifest);
    }

    private static IReadOnlyDictionary<string, PackageLockEntry> ReadLock(string path)
    {
        var entries = new Dictionary<string, PackageLockEntry>(StringComparer.Ordinal);
        if (!File.Exists(path)) return entries;
        using JsonDocument document = JsonDocument.Parse(File.ReadAllText(path));
        if (!document.RootElement.TryGetProperty("dependencies", out JsonElement dependencies))
            return entries;
        foreach (JsonProperty property in dependencies.EnumerateObject())
        {
            entries[property.Name] = new PackageLockEntry(
                OptionalString(property.Value, "version"),
                OptionalString(property.Value, "source"));
        }

        return entries;
    }

    private static string RequiredString(JsonElement element, string name, string path)
    {
        return OptionalString(element, name)
            ?? throw new CliException($"Missing '{name}' in asmdef: {path}");
    }

    private static string? OptionalString(JsonElement element, string name)
    {
        return element.TryGetProperty(name, out JsonElement value)
            && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;
    }

    private static string[] Strings(JsonElement element, string name)
    {
        if (!element.TryGetProperty(name, out JsonElement values)
            || values.ValueKind != JsonValueKind.Array) return [];
        return values.EnumerateArray()
            .Where(value => value.ValueKind == JsonValueKind.String)
            .Select(value => value.GetString()!)
            .Order(StringComparer.Ordinal)
            .ToArray();
    }

    private bool IsUnderProject(string path)
    {
        if (_projectRoot is null) return false;
        string fullPath = Path.GetFullPath(path);
        string relative = Path.GetRelativePath(_projectRoot, fullPath);
        return relative != ".."
            && !relative.StartsWith($"..{Path.DirectorySeparatorChar}", StringComparison.Ordinal);
    }

    private string? RelativeOrNull(string? path)
    {
        return path is null || _projectRoot is null ? null : Relative(_projectRoot, path);
    }

    private static string? RelativeOrNull(string root, string? path)
    {
        return path is null ? null : Relative(root, path);
    }

    private static string? HashOrNull(string? path)
    {
        return path is null ? null : JsonFiles.Sha256(File.ReadAllBytes(path));
    }

    private static string Relative(string root, string path)
    {
        return Normalize(Path.GetRelativePath(root, Path.GetFullPath(path)));
    }

    private static string Normalize(string path) => path.Replace('\\', '/');

    private AssemblySourceMap? SourceMap(string assemblyName)
    {
        if (!_asmdefs.TryGetValue(assemblyName, out AsmdefInfo? info)
            || info.Provenance.Asmdef is null) return null;
        return new AssemblySourceMap(assemblyName, info.Provenance.Asmdef, info.SourceFiles);
    }

    private sealed record AsmdefInfo(
        string Name,
        ProvenanceInfo Provenance,
        IReadOnlyList<string> SourceFiles);
    private sealed record PackageLockEntry(string? Version, string? Source);
    private sealed record PackageIdentity(
        string? Id,
        string? Version,
        string? Source,
        string? ManifestPath);
}
