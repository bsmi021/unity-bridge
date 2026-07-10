using System.Runtime.InteropServices;

namespace UnityApiInventory;

internal sealed record InventoryOptions(
    string UnityRoot,
    string UnityVersion,
    string UnityRevision,
    string CaptureTime,
    string HostOs,
    string BuildTarget,
    string ApiCompatibility,
    IReadOnlyList<string> Defines,
    IReadOnlyList<string> Assemblies,
    IReadOnlyList<string> AssemblyRoots,
    string? ProjectRoot,
    string? TocJs,
    string DocumentationBaseUrl,
    string Output,
    string Summary)
{
    public static InventoryOptions From(CliArguments args)
    {
        string captureTime = args.RequireSingle("--capture-time");
        if (!DateTimeOffset.TryParse(captureTime, out _))
        {
            throw new CliException("Option '--capture-time' must be an ISO-8601 timestamp.");
        }

        return new InventoryOptions(
            args.RequireSingle("--unity-root"),
            args.RequireSingle("--unity-version"),
            args.RequireSingle("--unity-revision"),
            captureTime,
            NormalizeHostOs(),
            args.RequireSingle("--build-target"),
            args.RequireSingle("--api-compatibility"),
            args.Values("--define").Order(StringComparer.Ordinal).ToArray(),
            args.Values("--assembly"),
            args.Values("--assembly-root"),
            Optional(args, "--project-root"),
            Optional(args, "--toc-js"),
            args.SingleOrDefault(
                "--documentation-base-url",
                $"https://docs.unity3d.com/{VersionChannel(args.RequireSingle("--unity-version"))}/Documentation/ScriptReference"),
            args.RequireSingle("--output"),
            args.RequireSingle("--summary"));
    }

    private static string? Optional(CliArguments args, string option)
    {
        IReadOnlyList<string> values = args.Values(option);
        return values.Count switch
        {
            0 => null,
            1 => values[0],
            _ => throw new CliException($"Option '{option}' may be supplied only once."),
        };
    }

    private static string VersionChannel(string version)
    {
        string[] parts = version.Split('.');
        return parts.Length >= 2 ? $"{parts[0]}.{parts[1]}" : version;
    }

    private static string NormalizeHostOs()
    {
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows)) return "windows";
        if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX)) return "macos";
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux)) return "linux";
        return "unknown";
    }
}

internal sealed record DiffOptions(string Before, string After, string Output)
{
    public static DiffOptions From(CliArguments args) => new(
        args.RequireSingle("--before"),
        args.RequireSingle("--after"),
        args.RequireSingle("--output"));
}

internal sealed record CoverageOptions(string Snapshot, string Registry, string Output)
{
    public static CoverageOptions From(CliArguments args) => new(
        args.RequireSingle("--snapshot"),
        args.RequireSingle("--registry"),
        args.RequireSingle("--output"));
}

internal sealed record RegistryBuildOptions(
    string Snapshot,
    string Summary,
    string? Overrides,
    string? GenericProof,
    string Output)
{
    public static RegistryBuildOptions From(CliArguments args) => new(
        args.RequireSingle("--snapshot"),
        args.RequireSingle("--summary"),
        Optional(args.Values("--overrides"), "--overrides"),
        Optional(args.Values("--generic-proof"), "--generic-proof"),
        args.RequireSingle("--output"));

    private static string? Optional(IReadOnlyList<string> values, string option)
    {
        return values.Count switch
        {
            0 => null,
            1 => values[0],
            _ => throw new CliException($"Option '{option}' may be supplied only once."),
        };
    }
}
