using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal static class ExecuteScriptDiagnostics
    {
        private static readonly Regex DiagnosticPattern = new Regex(
            @"^(?:(?<location>.*?):\s*)?(?<severity>error|warning)\s+" +
            @"(?<code>[A-Za-z]{2}\d+):\s*(?<message>.*)$",
            RegexOptions.Compiled | RegexOptions.IgnoreCase);

        public static List<ExecuteScriptDiagnostic> Parse(string report)
        {
            var diagnostics = new List<ExecuteScriptDiagnostic>();
            var lines = (report ?? "").Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');
            foreach (var rawLine in lines)
            {
                var line = rawLine.Trim();
                if (line.Length == 0)
                    continue;
                diagnostics.Add(ParseLine(line));
            }
            return diagnostics;
        }

        public static bool HasErrors(IEnumerable<ExecuteScriptDiagnostic> diagnostics)
        {
            foreach (var diagnostic in diagnostics ?? Array.Empty<ExecuteScriptDiagnostic>())
            {
                if (string.Equals(
                    diagnostic?.severity, "error", StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }
            return false;
        }

        private static ExecuteScriptDiagnostic ParseLine(string line)
        {
            var match = DiagnosticPattern.Match(line);
            if (!match.Success)
            {
                return new ExecuteScriptDiagnostic
                {
                    severity = "info",
                    message = line,
                    raw = line,
                };
            }

            return new ExecuteScriptDiagnostic
            {
                severity = match.Groups["severity"].Value.ToLowerInvariant(),
                code = match.Groups["code"].Value.ToUpperInvariant(),
                message = match.Groups["message"].Value,
                location = match.Groups["location"].Value,
                raw = line,
            };
        }
    }
}
