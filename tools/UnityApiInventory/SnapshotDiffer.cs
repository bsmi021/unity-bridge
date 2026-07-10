using System.Text.Json.Nodes;

namespace UnityApiInventory;

internal static class SnapshotDiffer
{
    private static readonly string[] ChangedProperties =
    [
        "canonical_signature",
        "record_kind",
        "member_kind",
        "type_kind",
        "declaring_type",
        "visibility",
        "is_static",
        "generic_arity",
        "provenance",
    ];

    public static int Run(DiffOptions options)
    {
        IReadOnlyDictionary<string, JsonObject> before = ReadById(options.Before);
        IReadOnlyDictionary<string, JsonObject> after = ReadById(options.After);
        JsonArray added = Records(after.Keys.Except(before.Keys), after);
        JsonArray removed = Records(before.Keys.Except(after.Keys), before);
        JsonArray changed = new();
        JsonArray obsolete = new();
        JsonArray availability = new();
        foreach (string id in before.Keys.Intersect(after.Keys).Order(StringComparer.Ordinal))
        {
            Categorize(before[id], after[id], changed, obsolete, availability);
        }

        JsonObject report = Report(added, removed, changed, obsolete, availability);
        JsonFiles.WriteNode(options.Output, report);
        return 0;
    }

    private static IReadOnlyDictionary<string, JsonObject> ReadById(string path)
    {
        var records = new Dictionary<string, JsonObject>(StringComparer.Ordinal);
        foreach (JsonObject record in JsonFiles.ReadJsonLines(path))
        {
            string id = record["symbol_id"]?.GetValue<string>()
                ?? throw new CliException("Snapshot record is missing 'symbol_id'.");
            if (!records.TryAdd(id, record))
            {
                throw new CliException($"Snapshot contains duplicate symbol_id '{id}'.");
            }
        }

        return records;
    }

    private static JsonArray Records(
        IEnumerable<string> identifiers,
        IReadOnlyDictionary<string, JsonObject> records)
    {
        var output = new JsonArray();
        foreach (string id in identifiers.Order(StringComparer.Ordinal))
        {
            output.Add(records[id].DeepClone());
        }

        return output;
    }

    private static void Categorize(
        JsonObject before,
        JsonObject after,
        JsonArray changed,
        JsonArray obsolete,
        JsonArray availability)
    {
        if (!PropertyEquals(before, after, "obsolete"))
        {
            obsolete.Add(after.DeepClone());
        }

        if (!PropertyEquals(before, after, "availability"))
        {
            availability.Add(after.DeepClone());
        }

        if (ChangedProperties.Any(property => !PropertyEquals(before, after, property)))
        {
            changed.Add(after.DeepClone());
        }
    }

    private static bool PropertyEquals(JsonObject before, JsonObject after, string property)
    {
        before.TryGetPropertyValue(property, out JsonNode? beforeValue);
        after.TryGetPropertyValue(property, out JsonNode? afterValue);
        return JsonNode.DeepEquals(beforeValue, afterValue);
    }

    private static JsonObject Report(
        JsonArray added,
        JsonArray removed,
        JsonArray changed,
        JsonArray obsolete,
        JsonArray availability)
    {
        return new JsonObject
        {
            ["schema_version"] = InventoryRunner.SchemaVersion,
            ["counts"] = new JsonObject
            {
                ["added"] = added.Count,
                ["removed"] = removed.Count,
                ["changed"] = changed.Count,
                ["obsolete"] = obsolete.Count,
                ["availability_changed"] = availability.Count,
            },
            ["added"] = added,
            ["removed"] = removed,
            ["changed"] = changed,
            ["obsolete"] = obsolete,
            ["availability_changed"] = availability,
        };
    }
}
