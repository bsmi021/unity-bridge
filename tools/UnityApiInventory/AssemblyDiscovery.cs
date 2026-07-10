namespace UnityApiInventory;

internal static class AssemblyDiscovery
{
    public static IReadOnlyList<string> Discover(InventoryOptions options)
    {
        string unityRoot = Path.GetFullPath(options.UnityRoot);
        if (!Directory.Exists(unityRoot))
        {
            throw new CliException($"Unity root does not exist: {unityRoot}");
        }

        var assemblies = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        AddUnityManagedAssemblies(unityRoot, assemblies);
        AddExplicitAssemblies(options.Assemblies, assemblies);
        AddAssemblyRoots(options.AssemblyRoots, assemblies);
        if (assemblies.Count == 0)
        {
            throw new CliException("No assemblies were found for the requested inventory.");
        }

        return assemblies.Order(StringComparer.OrdinalIgnoreCase).ToArray();
    }

    public static string DisplayPath(string path, string unityRoot)
    {
        string fullPath = Path.GetFullPath(path);
        string relative = Path.GetRelativePath(Path.GetFullPath(unityRoot), fullPath);
        string display = relative.StartsWith("..", StringComparison.Ordinal)
            ? fullPath
            : relative;
        return display.Replace('\\', '/');
    }

    private static void AddUnityManagedAssemblies(string root, HashSet<string> assemblies)
    {
        string managed = Path.Combine(root, "Editor", "Data", "Managed");
        AddFiles(
            Path.Combine(managed, "UnityEngine"),
            "UnityEngine.*Module.dll",
            SearchOption.TopDirectoryOnly,
            assemblies);
        AddFiles(
            Path.Combine(managed, "UnityEngine"),
            "UnityEditor.*Module.dll",
            SearchOption.TopDirectoryOnly,
            assemblies);
        foreach (string fileName in new[] { "UnityEditor.Graphs.dll" })
        {
            string path = Path.Combine(managed, fileName);
            if (File.Exists(path)) assemblies.Add(Path.GetFullPath(path));
        }
    }

    private static void AddExplicitAssemblies(
        IReadOnlyList<string> paths,
        HashSet<string> assemblies)
    {
        foreach (string path in paths)
        {
            string fullPath = Path.GetFullPath(path);
            if (!File.Exists(fullPath)) throw new CliException($"Assembly does not exist: {fullPath}");
            assemblies.Add(fullPath);
        }
    }

    private static void AddAssemblyRoots(
        IReadOnlyList<string> roots,
        HashSet<string> assemblies)
    {
        foreach (string root in roots)
        {
            string fullRoot = Path.GetFullPath(root);
            if (!Directory.Exists(fullRoot))
            {
                throw new CliException($"Assembly root does not exist: {fullRoot}");
            }

            AddFiles(fullRoot, "*.dll", SearchOption.AllDirectories, assemblies);
        }
    }

    private static void AddFiles(
        string directory,
        string pattern,
        SearchOption search,
        HashSet<string> assemblies)
    {
        if (!Directory.Exists(directory)) return;
        foreach (string path in Directory.EnumerateFiles(directory, pattern, search))
        {
            assemblies.Add(Path.GetFullPath(path));
        }
    }
}
