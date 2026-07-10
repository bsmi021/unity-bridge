namespace UnityApiInventory;

internal static class ProvenanceClassifier
{
    public static ProvenanceInfo Classify(string path)
    {
        string normalized = path.Replace('\\', '/');
        string lower = normalized.ToLowerInvariant();
        string name = Path.GetFileNameWithoutExtension(path);
        if (lower.Contains("/playbackengines/")) return new("playback_module");
        if (name.StartsWith("UnityEditor", StringComparison.Ordinal)) return new("unity_editor");
        if (name.StartsWith("UnityEngine", StringComparison.Ordinal)) return new("unity_runtime");
        if (lower.Contains("/packages/")) return new("package_unresolved");
        if (lower.Contains("/assets/plugins/")) return new("vendor_plugin");
        if (lower.Contains("/assets/")) return new("project");
        if (lower.Contains("/library/scriptassemblies/"))
        {
            return name.Contains("test", StringComparison.OrdinalIgnoreCase)
                ? new("test")
                : new("project_or_package_unresolved");
        }

        return new("unknown");
    }

    public static AvailabilityInfo Availability(
        ProvenanceInfo provenance,
        InventoryOptions options)
    {
        bool runtime = provenance.Classification is not "unity_editor";
        string defines = string.Join(",", options.Defines);
        string key = string.Join(
            "|",
            provenance.Classification,
            options.BuildTarget,
            defines,
            options.ApiCompatibility);
        return new AvailabilityInfo(
            key,
            Editor: true,
            Runtime: runtime,
            options.BuildTarget,
            options.Defines,
            options.ApiCompatibility);
    }
}
