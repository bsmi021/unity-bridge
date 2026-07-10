using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using System.Text.Json.Serialization.Metadata;

namespace UnityApiInventory;

internal static class JsonFiles
{
    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DictionaryKeyPolicy = null,
        DefaultIgnoreCondition = JsonIgnoreCondition.Never,
        TypeInfoResolver = new DefaultJsonTypeInfoResolver(),
        WriteIndented = false,
    };

    public static byte[] SerializeJsonLines<T>(IEnumerable<T> records)
    {
        var builder = new StringBuilder();
        foreach (T record in records)
        {
            builder.Append(JsonSerializer.Serialize(record, Options));
            builder.Append('\n');
        }

        return Encoding.UTF8.GetBytes(builder.ToString());
    }

    public static void WriteBytes(string path, byte[] contents)
    {
        EnsureParent(path);
        File.WriteAllBytes(path, contents);
    }

    public static void WriteJson<T>(string path, T value)
    {
        byte[] contents = JsonSerializer.SerializeToUtf8Bytes(value, Options);
        WriteBytes(path, [.. contents, (byte)'\n']);
    }

    public static void WriteNode(string path, JsonNode value)
    {
        string json = value.ToJsonString(Options) + "\n";
        WriteBytes(path, Encoding.UTF8.GetBytes(json));
    }

    public static IReadOnlyList<JsonObject> ReadJsonLines(string path)
    {
        return File.ReadLines(path)
            .Where(line => !string.IsNullOrWhiteSpace(line))
            .Select(ParseObject)
            .ToArray();
    }

    public static string Sha256(byte[] contents)
    {
        return Convert.ToHexString(SHA256.HashData(contents)).ToLowerInvariant();
    }

    private static JsonObject ParseObject(string line)
    {
        return JsonNode.Parse(line)?.AsObject()
            ?? throw new CliException("Snapshot contains a non-object JSON line.");
    }

    private static void EnsureParent(string path)
    {
        string? parent = Path.GetDirectoryName(Path.GetFullPath(path));
        if (parent is not null) Directory.CreateDirectory(parent);
    }
}
