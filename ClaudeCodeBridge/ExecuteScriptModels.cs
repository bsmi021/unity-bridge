using System;
using System.Collections.Generic;

namespace BWS.Editor.ClaudeCodeBridge
{
    [Serializable]
    public class ExecuteScriptParams
    {
        public string expression;
        public bool returnValue = true;
        public ExecuteScriptManifest manifest = new ExecuteScriptManifest();
    }

    [Serializable]
    public class ExecuteScriptManifest
    {
        public string intent = "read-only";
        public List<string> expectedAssemblies = new List<string>();
        public List<ExecuteScriptAssemblyRequest> expectedAssemblyIdentities =
            new List<ExecuteScriptAssemblyRequest>();
        public List<string> declaredObjectIds = new List<string>();
        public List<string> declaredFilePaths = new List<string>();
        public int timeoutMs = 30000;
        public string undoLabel = "";
        public string returnSchema = "auto";
        public bool allowInternalReflection;
    }

    [Serializable]
    public class ExecuteScriptAssemblyRequest
    {
        public string name;
        public string fullName;
        public string mvid;
        public string path;
    }

    [Serializable]
    public class ExecuteScriptAssemblyIdentity
    {
        public string name;
        public string fullName;
        public string mvid;
        public string path;
    }

    [Serializable]
    public class ExecuteScriptAssemblyResolutionIssue
    {
        public string code;
        public string message;
        public ExecuteScriptAssemblyRequest request;
        public List<ExecuteScriptAssemblyIdentity> candidates =
            new List<ExecuteScriptAssemblyIdentity>();
    }

    [Serializable]
    public class ExecuteScriptResult
    {
        public bool success;
        public string result;
        public string resultType;
        public bool resultSet;
        public ExecuteScriptValue value;
        public long executionTimeMs;
        public string message;
        public List<ExecuteScriptDiagnostic> compilerDiagnostics =
            new List<ExecuteScriptDiagnostic>();
        public List<ExecuteScriptLogEntry> unityLogs = new List<ExecuteScriptLogEntry>();
        public List<string> referencedAssemblies = new List<string>();
        public List<ExecuteScriptAssemblyIdentity> resolvedAssemblies =
            new List<ExecuteScriptAssemblyIdentity>();
        public List<ExecuteScriptAssemblyResolutionIssue> assemblyResolutionIssues =
            new List<ExecuteScriptAssemblyResolutionIssue>();
        public ExecuteScriptMutationReport mutation = new ExecuteScriptMutationReport();
    }

    [Serializable]
    public class ExecuteScriptValue
    {
        public string kind;
        public string type;
        public string stringValue;
        public bool boolValue;
        public List<ExecuteScriptValue> items = new List<ExecuteScriptValue>();
        public List<ExecuteScriptDictionaryEntry> entries =
            new List<ExecuteScriptDictionaryEntry>();
        public List<ExecuteScriptNamedValue> fields = new List<ExecuteScriptNamedValue>();
        public ExecuteScriptUnityObject unityObject;
    }

    [Serializable]
    public class ExecuteScriptDictionaryEntry
    {
        public ExecuteScriptValue key;
        public ExecuteScriptValue value;
    }

    [Serializable]
    public class ExecuteScriptNamedValue
    {
        public string name;
        public ExecuteScriptValue value;
    }

    [Serializable]
    public class ExecuteScriptUnityObject
    {
        public string objectId;
        public string name;
        public string type;
        public string assetPath;
        public string globalObjectId;
    }

    [Serializable]
    public class ExecuteScriptDiagnostic
    {
        public string severity;
        public string code;
        public string message;
        public string location;
        public string raw;
    }

    [Serializable]
    public class ExecuteScriptLogEntry
    {
        public string message;
        public string stackTrace;
        public string logType;
    }

    [Serializable]
    public class ExecuteScriptMutationReport
    {
        public bool governed;
        public bool reverted;
        public int undoGroup = -1;
        public string undoLabel;
        public List<string> declaredObjectIds = new List<string>();
        public List<string> declaredFilePaths = new List<string>();
        public List<ExecuteScriptChangedObject> changedObjects =
            new List<ExecuteScriptChangedObject>();
        public List<ExecuteScriptFileChange> changedProjectFiles =
            new List<ExecuteScriptFileChange>();
    }

    [Serializable]
    public class ExecuteScriptChangedObject
    {
        public string objectId;
        public string name;
        public string type;
        public string assetPath;
        public string globalObjectId;
    }

    [Serializable]
    public class ExecuteScriptFileChange
    {
        public string path;
        public string change;
    }

    internal class ExecuteScriptOutcome
    {
        public bool Success;
        public string Message;
        public object Value;
        public bool ResultSet;
        public List<ExecuteScriptDiagnostic> Diagnostics =
            new List<ExecuteScriptDiagnostic>();
        public List<ExecuteScriptAssemblyIdentity> ResolvedAssemblies =
            new List<ExecuteScriptAssemblyIdentity>();
        public List<ExecuteScriptAssemblyResolutionIssue> AssemblyResolutionIssues =
            new List<ExecuteScriptAssemblyResolutionIssue>();
    }
}
