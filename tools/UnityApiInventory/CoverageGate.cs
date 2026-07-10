using System.Text.Json;

namespace UnityApiInventory;

internal static class CoverageGate
{
    private static readonly HashSet<string> AllowedClassifications =
    [
        "typed",
        "generic",
        "public_unwrapped",
        "no_public_api",
        "external_dependency",
        "obsolete",
        "explicit_non_goal",
    ];

    public static int Run(CoverageOptions options)
    {
        HashSet<string> snapshotIds = ReadSnapshotIds(options.Snapshot);
        RegistryReadResult registry = ReadRegistry(options.Registry);
        string[] unclassified = snapshotIds
            .Except(registry.ValidIds)
            .Order(StringComparer.Ordinal)
            .ToArray();
        string[] removed = registry.ValidIds
            .Except(snapshotIds)
            .Order(StringComparer.Ordinal)
            .ToArray();
        bool complete = unclassified.Length == 0
            && removed.Length == 0
            && registry.InvalidRecords.Count == 0;
        var report = new CoverageReport(
            InventoryRunner.SchemaVersion,
            snapshotIds.Count,
            registry.RecordCount,
            snapshotIds.Intersect(registry.ValidIds).Count(),
            unclassified,
            removed,
            registry.InvalidRecords,
            complete);
        JsonFiles.WriteJson(options.Output, report);
        return complete ? 0 : 3;
    }

    private static HashSet<string> ReadSnapshotIds(string path)
    {
        var identifiers = new HashSet<string>(StringComparer.Ordinal);
        foreach (var record in JsonFiles.ReadJsonLines(path))
        {
            string id = record["symbol_id"]?.GetValue<string>()
                ?? throw new CliException("Snapshot record is missing 'symbol_id'.");
            if (!identifiers.Add(id))
            {
                throw new CliException($"Snapshot contains duplicate symbol_id '{id}'.");
            }
        }

        return identifiers;
    }

    private static RegistryReadResult ReadRegistry(string path)
    {
        using JsonDocument document = JsonDocument.Parse(File.ReadAllText(path));
        JsonElement records = document.RootElement.GetProperty("records");
        var validIds = new HashSet<string>(StringComparer.Ordinal);
        var seenIds = new HashSet<string>(StringComparer.Ordinal);
        var invalid = new List<string>();
        int index = 0;
        foreach (JsonElement record in records.EnumerateArray())
        {
            ValidateRecord(record, index, seenIds, validIds, invalid);
            index++;
        }

        return new RegistryReadResult(validIds, invalid, index);
    }

    private static void ValidateRecord(
        JsonElement record,
        int index,
        HashSet<string> seenIds,
        HashSet<string> validIds,
        List<string> invalid)
    {
        string? id = StringProperty(record, "symbol_id");
        string? classification = StringProperty(record, "classification");
        string? rationale = StringProperty(record, "rationale");
        if (id is null || !seenIds.Add(id))
        {
            invalid.Add($"records[{index}]: missing or duplicate symbol_id");
            return;
        }

        if (classification is null || !AllowedClassifications.Contains(classification))
        {
            invalid.Add($"records[{index}]: invalid classification");
            return;
        }

        if (string.IsNullOrWhiteSpace(rationale))
        {
            invalid.Add($"records[{index}]: rationale is required");
            return;
        }

        validIds.Add(id);
    }

    private static string? StringProperty(JsonElement element, string name)
    {
        return element.TryGetProperty(name, out JsonElement value)
            && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;
    }

    private sealed record RegistryReadResult(
        HashSet<string> ValidIds,
        IReadOnlyList<string> InvalidRecords,
        int RecordCount);

    private sealed record CoverageReport(
        string SchemaVersion,
        int SnapshotSymbolCount,
        int RegistryRecordCount,
        int ClassifiedCount,
        IReadOnlyList<string> UnclassifiedSymbolIds,
        IReadOnlyList<string> RemovedRegistrySymbolIds,
        IReadOnlyList<string> InvalidRegistryRecords,
        bool IsComplete);
}
