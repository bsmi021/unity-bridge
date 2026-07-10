using System.Text.Json;

namespace UnityApiInventory;

internal sealed class DocumentationIndex
{
    private readonly TocCatalog _catalog;
    private readonly string _baseUrl;

    private DocumentationIndex(TocCatalog catalog, string baseUrl)
    {
        _catalog = catalog;
        _baseUrl = baseUrl.TrimEnd('/');
    }

    public static DocumentationIndex Load(InventoryOptions options)
    {
        if (options.TocJs is null) return new DocumentationIndex(TocCatalog.Empty, options.DocumentationBaseUrl);
        string path = Path.GetFullPath(options.TocJs);
        if (!File.Exists(path)) throw new CliException($"toc.js does not exist: {path}");
        return new DocumentationIndex(Parse(path), options.DocumentationBaseUrl);
    }

    public void Apply(IEnumerable<ApiRecord> records)
    {
        foreach (ApiRecord record in records)
        {
            string? typeName = TypeName(record);
            string? link = typeName is null ? null : FindLink(typeName);
            if (link is not null) record.DocumentationUrl = $"{_baseUrl}/{link}.html";
        }
    }

    public static string SourceSha256(string path)
    {
        return JsonFiles.Sha256(File.ReadAllBytes(Path.GetFullPath(path)));
    }

    private string? FindLink(string typeName)
    {
        string normalized = NormalizeTypeName(typeName);
        return _catalog.Links.TryGetValue(normalized, out string? link) ? link : null;
    }

    public DocumentationJoinInfo JoinInfo(
        InventoryOptions options,
        IReadOnlyList<ApiRecord> records)
    {
        if (options.TocJs is null)
        {
            return new DocumentationJoinInfo(
                "not_requested", null, null, _baseUrl, 0, 0, 0, 0, 0, 0);
        }

        int matched = records.Count(
            record => record.RecordKind == "type" && record.DocumentationUrl is not null);
        int unmatched = records.Count(
            record => record.RecordKind == "type" && record.DocumentationUrl is null);
        return new DocumentationJoinInfo(
            "joined",
            Path.GetFullPath(options.TocJs).Replace('\\', '/'),
            SourceSha256(options.TocJs),
            _baseUrl,
            _catalog.TotalEntries,
            _catalog.Links.Count,
            _catalog.IgnoredEntries,
            _catalog.AmbiguousIdentities,
            matched,
            unmatched);
    }

    private static TocCatalog Parse(string path)
    {
        string source = File.ReadAllText(path);
        int start = source.IndexOf('{');
        int end = source.LastIndexOf('}');
        if (start < 0 || end < start) throw new CliException("toc.js does not contain a JSON object.");
        using JsonDocument document = JsonDocument.Parse(source[start..(end + 1)]);
        var links = new Dictionary<string, string>(StringComparer.Ordinal);
        var ambiguous = new HashSet<string>(StringComparer.Ordinal);
        int total = 0;
        int ignored = 0;
        AddLinks(document.RootElement, null, links, ambiguous, ref total, ref ignored);
        return new TocCatalog(links, total, ignored, ambiguous.Count);
    }

    private static void AddLinks(
        JsonElement node,
        string? rootBranch,
        Dictionary<string, string> links,
        HashSet<string> ambiguous,
        ref int total,
        ref int ignored)
    {
        string? title = node.TryGetProperty("title", out JsonElement titleElement)
            ? titleElement.GetString()
            : null;
        string? activeBranch = rootBranch;
        if (node.TryGetProperty("link", out JsonElement linkElement))
        {
            string? link = linkElement.GetString();
            if (rootBranch is null && link == "null" && title is not null)
                activeBranch = title;
            if (!string.IsNullOrWhiteSpace(link) && link is not "null" and not "toc")
            {
                total++;
                string? identity = FullIdentity(activeBranch, link);
                if (identity is null) ignored++;
                else AddIdentity(identity, link, links, ambiguous);
            }
        }

        if (!node.TryGetProperty("children", out JsonElement children)
            || children.ValueKind != JsonValueKind.Array) return;
        foreach (JsonElement child in children.EnumerateArray())
            AddLinks(child, activeBranch, links, ambiguous, ref total, ref ignored);
    }

    private static string? TypeName(ApiRecord record)
    {
        if (record.RecordKind is "type" or "type_forwarder")
        {
            return AfterAssembly(record.CanonicalSignature);
        }

        return record.DeclaringType is null ? null : AfterAssembly(record.DeclaringType);
    }

    private static string AfterAssembly(string value)
    {
        int separator = value.IndexOf("::", StringComparison.Ordinal);
        return separator < 0 ? value : value[(separator + 2)..];
    }

    private static string NormalizeTypeName(string typeName)
    {
        string normalized = typeName.Replace('+', '.');
        int tick = normalized.IndexOf('`');
        while (tick >= 0)
        {
            int end = tick + 1;
            while (end < normalized.Length && char.IsDigit(normalized[end])) end++;
            normalized = normalized[..tick] + "_" + normalized[(tick + 1)..];
            tick = normalized.IndexOf('`');
        }

        return normalized;
    }

    private static string? FullIdentity(string? rootBranch, string link)
    {
        if (rootBranch == "Other") return null;
        if (rootBranch is "UnityEngine" or "UnityEditor" or "Unity")
        {
            string prefix = rootBranch + ".";
            return link.StartsWith(prefix, StringComparison.Ordinal) ? link : prefix + link;
        }

        return link;
    }

    private static void AddIdentity(
        string identity,
        string link,
        Dictionary<string, string> links,
        HashSet<string> ambiguous)
    {
        if (ambiguous.Contains(identity)) return;
        if (!links.TryGetValue(identity, out string? existing))
        {
            links.Add(identity, link);
            return;
        }

        if (existing == link) return;
        links.Remove(identity);
        ambiguous.Add(identity);
    }

    private sealed record TocCatalog(
        IReadOnlyDictionary<string, string> Links,
        int TotalEntries,
        int IgnoredEntries,
        int AmbiguousIdentities)
    {
        public static TocCatalog Empty { get; } = new(
            new Dictionary<string, string>(StringComparer.Ordinal), 0, 0, 0);
    }
}
