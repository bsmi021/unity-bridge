namespace UnityApiInventory;

internal sealed class CliException(string message) : Exception(message);

internal sealed class CliArguments
{
    private readonly Dictionary<string, List<string>> _values;

    private CliArguments(Dictionary<string, List<string>> values)
    {
        _values = values;
    }

    public static CliArguments Parse(string[] args)
    {
        var values = new Dictionary<string, List<string>>(StringComparer.Ordinal);
        for (int index = 0; index < args.Length; index += 2)
        {
            string option = args[index];
            if (!option.StartsWith("--", StringComparison.Ordinal) || index + 1 >= args.Length)
            {
                throw new CliException($"Expected '--option value', received '{option}'.");
            }

            if (!values.TryGetValue(option, out List<string>? entries))
            {
                entries = [];
                values.Add(option, entries);
            }

            entries.Add(args[index + 1]);
        }

        return new CliArguments(values);
    }

    public string RequireSingle(string option)
    {
        IReadOnlyList<string> entries = Values(option);
        return entries.Count == 1
            ? entries[0]
            : throw new CliException($"Option '{option}' must be supplied exactly once.");
    }

    public string SingleOrDefault(string option, string defaultValue)
    {
        IReadOnlyList<string> entries = Values(option);
        return entries.Count switch
        {
            0 => defaultValue,
            1 => entries[0],
            _ => throw new CliException($"Option '{option}' may be supplied only once."),
        };
    }

    public IReadOnlyList<string> Values(string option)
    {
        return _values.TryGetValue(option, out List<string>? entries) ? entries : [];
    }
}

internal static class CliHelp
{
    public const string Text = """
        UnityApiInventory commands:
          inventory --unity-root PATH --unity-version VERSION --unity-revision REVISION
                    --capture-time ISO8601 --build-target TARGET --api-compatibility LEVEL
                    --output SNAPSHOT.jsonl --summary SUMMARY.json
                    [--define SYMBOL] [--assembly FILE] [--assembly-root DIRECTORY]
                    [--project-root UNITY_PROJECT]
                    [--toc-js FILE] [--documentation-base-url URL]
          diff --before SNAPSHOT.jsonl --after SNAPSHOT.jsonl --output DIFF.json
          coverage-gate --snapshot SNAPSHOT.jsonl --registry REGISTRY.json --output REPORT.json
          registry-build --snapshot SNAPSHOT.jsonl --summary SUMMARY.json
                         [--overrides OVERRIDES.json]
                         [--generic-proof GENERIC_PROOF.json] --output REGISTRY.json
        """;
}
