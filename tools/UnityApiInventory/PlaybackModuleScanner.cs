namespace UnityApiInventory;

internal static class PlaybackModuleScanner
{
    public static IReadOnlyList<PlaybackModuleEvidence> Scan(string unityRoot)
    {
        string playback = Path.Combine(
            Path.GetFullPath(unityRoot),
            "Editor",
            "Data",
            "PlaybackEngines");
        if (!Directory.Exists(playback)) return [];

        return Directory.EnumerateDirectories(playback)
            .Select(Module)
            .OrderBy(module => module.Name, StringComparer.Ordinal)
            .ToArray();
    }

    private static PlaybackModuleEvidence Module(string path)
    {
        string variations = Path.Combine(path, "Variations");
        string[] names = Directory.Exists(variations)
            ? Directory.EnumerateDirectories(variations)
                .Select(Path.GetFileName)
                .Where(name => name is not null)
                .Cast<string>()
                .Order(StringComparer.Ordinal)
                .ToArray()
            : [];
        string managed = Path.Combine(variations, "mono", "Managed");
        int count = Directory.Exists(managed)
            ? Directory.EnumerateFiles(managed, "*.dll").Count()
            : 0;
        return new PlaybackModuleEvidence(
            Path.GetFileName(path),
            path.Replace('\\', '/'),
            count,
            names);
    }
}
