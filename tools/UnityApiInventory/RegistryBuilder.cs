using System.Text.Json;
using System.Text.Json.Nodes;

namespace UnityApiInventory;

internal static class RegistryBuilder
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

    public static int Run(RegistryBuildOptions options)
    {
        byte[] snapshotBytes = File.ReadAllBytes(options.Snapshot);
        SnapshotIdentity identity = ReadIdentity(options.Summary);
        string actualHash = JsonFiles.Sha256(snapshotBytes);
        if (actualHash != identity.Sha256)
        {
            throw new CliException("Snapshot SHA-256 does not match the supplied summary.");
        }

        IReadOnlyDictionary<string, RegistryOverride> overrides = ReadOverrides(options.Overrides);
        IReadOnlyDictionary<AssemblyProofKey, RegistryOverride> genericProof =
            ReadGenericProof(options.GenericProof, identity);
        IReadOnlyList<JsonObject> snapshot = JsonFiles.ReadJsonLines(options.Snapshot);
        EnsureOverridesExist(snapshot, overrides);
        var records = new JsonArray();
        foreach (JsonObject record in snapshot.OrderBy(SymbolId, StringComparer.Ordinal))
        {
            string id = SymbolId(record);
            RegistryOverride classification = overrides.TryGetValue(id, out RegistryOverride? value)
                ? value
                : Default(record, genericProof);
            Validate(record, classification);
            records.Add(ToJson(id, classification));
        }

        JsonFiles.WriteNode(options.Output, Registry(identity, records));
        return 0;
    }

    private static SnapshotIdentity ReadIdentity(string summaryPath)
    {
        using JsonDocument document = JsonDocument.Parse(File.ReadAllText(summaryPath));
        JsonElement root = document.RootElement;
        string sha = root.GetProperty("snapshot_sha256").GetString()
            ?? throw new CliException("Summary is missing snapshot_sha256.");
        string version = root.GetProperty("unity").GetProperty("version").GetString()
            ?? throw new CliException("Summary is missing unity.version.");
        return new SnapshotIdentity(sha, version);
    }

    private static IReadOnlyDictionary<string, RegistryOverride> ReadOverrides(string? path)
    {
        var overrides = new Dictionary<string, RegistryOverride>(StringComparer.Ordinal);
        if (path is null) return overrides;
        using JsonDocument document = JsonDocument.Parse(File.ReadAllText(path));
        foreach (JsonElement record in document.RootElement.GetProperty("records").EnumerateArray())
        {
            string id = RequiredString(record, "symbol_id");
            string classification = RequiredString(record, "classification");
            string rationale = RequiredString(record, "rationale");
            string[] proof = record.GetProperty("proof").EnumerateArray()
                .Select(item => item.GetString() ?? string.Empty)
                .ToArray();
            if (!overrides.TryAdd(id, new RegistryOverride(classification, rationale, proof)))
                throw new CliException($"Duplicate override symbol_id '{id}'.");
        }

        return overrides;
    }

    private static IReadOnlyDictionary<AssemblyProofKey, RegistryOverride> ReadGenericProof(
        string? path,
        SnapshotIdentity identity)
    {
        var proofs = new Dictionary<AssemblyProofKey, RegistryOverride>();
        if (path is null) return proofs;
        using JsonDocument document = JsonDocument.Parse(File.ReadAllText(path));
        JsonElement root = document.RootElement;
        JsonElement snapshot = root.GetProperty("snapshot");
        if (RequiredString(snapshot, "sha256") != identity.Sha256
            || RequiredString(snapshot, "unity_version") != identity.UnityVersion)
        {
            throw new CliException(
                "Generic proof snapshot SHA-256 and Unity version must match the supplied summary.");
        }
        foreach (JsonElement assembly in root.GetProperty("assemblies").EnumerateArray())
        {
            AssemblyProofKey key = ProofKey(assembly);
            string[] proof = assembly.GetProperty("proof").EnumerateArray()
                .Select(item => item.GetString() ?? string.Empty)
                .ToArray();
            var value = new RegistryOverride(
                "generic",
                "Exact loaded assembly identity passed the generic-host compile and live probe.",
                proof);
            if (!HasProof(value, "csharp_compile:") || !HasProof(value, "live_positive:"))
            {
                throw new CliException(
                    "Generic assembly proof requires csharp_compile and live_positive proof.");
            }
            if (!proofs.TryAdd(key, value))
                throw new CliException($"Duplicate generic proof assembly '{key.Name}'.");
        }
        return proofs;
    }

    private static void EnsureOverridesExist(
        IReadOnlyList<JsonObject> snapshot,
        IReadOnlyDictionary<string, RegistryOverride> overrides)
    {
        var ids = snapshot.Select(SymbolId).ToHashSet(StringComparer.Ordinal);
        string[] missing = overrides.Keys.Except(ids).Order(StringComparer.Ordinal).ToArray();
        if (missing.Length > 0)
            throw new CliException($"Override symbols are absent from snapshot: {string.Join(", ", missing)}");
    }

    private static RegistryOverride Default(
        JsonObject record,
        IReadOnlyDictionary<AssemblyProofKey, RegistryOverride> genericProof)
    {
        bool obsolete = record["obsolete"]?["is_obsolete"]?.GetValue<bool>() is true;
        if (obsolete)
        {
            return new RegistryOverride(
                "obsolete",
                "Classified obsolete from pinned assembly metadata.",
                ["metadata:obsolete_attribute"]);
        }
        AssemblyProofKey? key = RecordProofKey(record);
        if (key is not null && genericProof.TryGetValue(key, out RegistryOverride? proof))
            return proof;
        return new RegistryOverride(
            "public_unwrapped",
            "No verified typed or generic reachable path is registered.",
            []);
    }

    private static AssemblyProofKey ProofKey(JsonElement assembly)
    {
        string name = RequiredString(assembly, "name");
        string mvid = RequiredString(assembly, "mvid");
        string sha256 = RequiredString(assembly, "sha256").ToLowerInvariant();
        if (!Guid.TryParse(mvid, out Guid parsed) || !IsSha256(sha256))
            throw new CliException($"Generic proof assembly identity is invalid: {name}.");
        return new AssemblyProofKey(name, parsed.ToString("D"), sha256!);
    }

    private static AssemblyProofKey? RecordProofKey(JsonObject record)
    {
        JsonObject? assembly = record["assembly"] as JsonObject;
        if (assembly is null) return null;
        string? name = assembly["name"]?.GetValue<string>();
        string? mvid = assembly["mvid"]?.GetValue<string>();
        string? sha256 = assembly["sha256"]?.GetValue<string>()?.ToLowerInvariant();
        if (name is null || !Guid.TryParse(mvid, out Guid parsed) || !IsSha256(sha256))
            return null;
        return new AssemblyProofKey(name, parsed.ToString("D"), sha256!);
    }

    private static bool IsSha256(string? value)
    {
        return value?.Length == 64 && value.All(Uri.IsHexDigit);
    }

    private static void Validate(JsonObject record, RegistryOverride value)
    {
        if (!AllowedClassifications.Contains(value.Classification))
            throw new CliException($"Invalid coverage classification '{value.Classification}'.");
        if (string.IsNullOrWhiteSpace(value.Rationale))
            throw new CliException("Coverage classification rationale is required.");
        if (value.Classification == "typed" && value.Proof.Count == 0)
            throw new CliException("typed classification requires proof.");
        if (value.Classification == "generic"
            && (!HasProof(value, "csharp_compile:") || !HasProof(value, "live_positive:")))
        {
            throw new CliException(
                "generic classification requires csharp_compile and live_positive proof.");
        }

        bool obsolete = record["obsolete"]?["is_obsolete"]?.GetValue<bool>() is true;
        if (value.Classification == "obsolete" && !obsolete)
            throw new CliException("obsolete classification requires obsolete assembly metadata.");
    }

    private static bool HasProof(RegistryOverride value, string prefix)
    {
        return value.Proof.Any(item => item.StartsWith(prefix, StringComparison.Ordinal));
    }

    private static JsonObject ToJson(string id, RegistryOverride value)
    {
        var proof = new JsonArray();
        foreach (string item in value.Proof) proof.Add(item);
        return new JsonObject
        {
            ["symbol_id"] = id,
            ["classification"] = value.Classification,
            ["rationale"] = value.Rationale,
            ["proof"] = proof,
        };
    }

    private static JsonObject Registry(SnapshotIdentity identity, JsonArray records)
    {
        return new JsonObject
        {
            ["$schema"] = "coverage-registry.schema.json",
            ["schema_version"] = InventoryRunner.SchemaVersion,
            ["snapshot"] = new JsonObject
            {
                ["sha256"] = identity.Sha256,
                ["unity_version"] = identity.UnityVersion,
            },
            ["records"] = records,
        };
    }

    private static string SymbolId(JsonObject record)
    {
        return record["symbol_id"]?.GetValue<string>()
            ?? throw new CliException("Snapshot record is missing symbol_id.");
    }

    private static string RequiredString(JsonElement record, string name)
    {
        return record.GetProperty(name).GetString()
            ?? throw new CliException($"Override is missing {name}.");
    }

    private sealed record SnapshotIdentity(string Sha256, string UnityVersion);
    private sealed record AssemblyProofKey(string Name, string Mvid, string Sha256);
    private sealed record RegistryOverride(
        string Classification,
        string Rationale,
        IReadOnlyList<string> Proof);
}
