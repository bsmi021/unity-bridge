namespace UnityApiInventory;

internal static class Program
{
    public static int Main(string[] args)
    {
        try
        {
            return Run(args);
        }
        catch (CliException exception)
        {
            Console.Error.WriteLine(exception.Message);
            return 2;
        }
        catch (Exception exception)
        {
            Console.Error.WriteLine(exception);
            return 2;
        }
    }

    private static int Run(string[] args)
    {
        if (args.Length == 0 || args[0] is "--help" or "-h" or "help")
        {
            Console.WriteLine(CliHelp.Text);
            return 0;
        }

        CliArguments options = CliArguments.Parse(args[1..]);
        return args[0] switch
        {
            "inventory" => InventoryRunner.Run(InventoryOptions.From(options)),
            "diff" => SnapshotDiffer.Run(DiffOptions.From(options)),
            "coverage-gate" => CoverageGate.Run(CoverageOptions.From(options)),
            "registry-build" => RegistryBuilder.Run(RegistryBuildOptions.From(options)),
            _ => throw new CliException($"Unknown command '{args[0]}'.\n{CliHelp.Text}"),
        };
    }
}
