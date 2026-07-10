using System;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal static class ExecuteScriptReflectionPolicy
    {
        private static readonly string[] InternalReflectionTokens =
        {
            "BindingFlags.NonPublic",
            ".GetTypes()",
            ".DefinedTypes",
            ".Assembly.GetType(",
            "System.Reflection.Emit",
        };

        public static bool Validate(
            string code, bool allowInternalReflection, out string message)
        {
            message = "";
            if (allowInternalReflection)
                return true;

            foreach (var token in InternalReflectionTokens)
            {
                if ((code ?? "").IndexOf(token, StringComparison.Ordinal) < 0)
                    continue;
                message = "Internal/private reflection is disabled. "
                    + "Set allowInternalReflection=true explicitly to use it.";
                return false;
            }
            return true;
        }
    }
}
