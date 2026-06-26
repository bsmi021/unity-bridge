using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Xml.Linq;
using UnityEditor;
using UnityEditor.PackageManager;
using UnityEditor.PackageManager.Requests;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Optional Unity Code Coverage utility. Uses reflection so projects without
    /// com.unity.testtools.codecoverage still compile and can inspect reports.
    /// </summary>
    public class CodeCoverageCommandHandler : ICommandHandler
    {
        private const string PackageName = "com.unity.testtools.codecoverage";
        private const int DefaultMaxResults = 50;

        private static AddRequest _installRequest;
        private static BridgeCommand _installCommand;
        private static bool _installPollRegistered;

        public string CommandType => "code-coverage";

        public BridgeResponse Execute(BridgeCommand command)
        {
            string operation = "availability";
            try
            {
                var p = JsonUtility.FromJson<CodeCoverageParams>(
                    command.parametersJson ?? "{}") ?? new CodeCoverageParams();
                operation = string.IsNullOrEmpty(p.operation)
                    ? "availability"
                    : p.operation.ToLowerInvariant();

                switch (operation)
                {
                    case "availability": return Reply(command, Availability(operation));
                    case "install": return StartInstall(command, p);
                    case "start-recording": return InvokeRecording(command, operation, "StartRecording");
                    case "pause-recording": return InvokeRecording(command, operation, "PauseRecording");
                    case "resume-recording": return InvokeRecording(command, operation, "UnpauseRecording");
                    case "stop-recording": return InvokeRecording(command, operation, "StopRecording");
                    case "find-reports": return Reply(command, FindReports(operation, p));
                    case "summarize": return Reply(command, Summarize(operation, p));
                    default:
                        return Reply(command, Fail(operation, "Unknown operation. Supported: "
                            + "availability, install, start-recording, pause-recording, "
                            + "resume-recording, stop-recording, find-reports, summarize"));
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Code Coverage error: {ex}");
                return Reply(command, Fail(operation, ex.ToString()));
            }
        }

        private static BridgeResponse Reply(BridgeCommand command, CodeCoverageResult result)
        {
            string json = JsonUtility.ToJson(result);
            if (result.success) return BridgeResponse.Success(command.commandId, command.commandType, json);
            return new BridgeResponse
            {
                commandId = command.commandId,
                commandType = command.commandType,
                status = "error",
                timestamp = DateTime.UtcNow.ToString("o"),
                dataJson = json,
                errorMessage = result.message,
            };
        }

        private static CodeCoverageResult Availability(string operation)
        {
            Type apiType = FindType("UnityEditor.TestTools.CodeCoverage.CodeCoverage");
            PackageInfo info = FindPackageInfo();
            var result = BaseResult(operation, apiType, info);
            result.message = result.apiAvailable
                ? "Unity Code Coverage API is available."
                : "Unity Code Coverage package/API is not available.";
            return result;
        }

        private static BridgeResponse StartInstall(BridgeCommand command, CodeCoverageParams p)
        {
            if (EditorApplication.isCompiling)
                return Reply(command, Fail("install", "Unity is compiling. Try again after compile."));
            if (_installRequest != null)
                return Reply(command, Fail("install", "A Code Coverage install is already in progress."));

            string identifier = string.IsNullOrEmpty(p.identifier) ? PackageName : p.identifier.Trim();
            _installRequest = Client.Add(identifier);
            _installCommand = command;
            if (!_installPollRegistered)
            {
                EditorApplication.update += PollInstall;
                _installPollRegistered = true;
            }

            var result = Availability("install");
            result.success = true;
            result.identifier = identifier;
            result.message = $"Installing {identifier}...";
            return BridgeResponse.Running(command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private static void PollInstall()
        {
            if (_installRequest == null) return;
            if (!_installRequest.IsCompleted) return;

            var result = Availability("install");
            result.identifier = _installRequest.Result?.packageId ?? PackageName;
            result.success = _installRequest.Status != StatusCode.Failure;
            result.message = result.success
                ? $"Installed {result.identifier}."
                : _installRequest.Error?.message ?? "Code Coverage install failed.";
            ClaudeUnityBridge.WriteResponseStatic(MakeResponse(_installCommand, result));
            _installRequest = null;
            _installCommand = null;
            EditorApplication.update -= PollInstall;
            _installPollRegistered = false;
        }

        private static BridgeResponse MakeResponse(BridgeCommand command, CodeCoverageResult result)
        {
            return result.success
                ? BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result))
                : BridgeResponse.Error(command.commandId, command.commandType, result.message);
        }

        private static BridgeResponse InvokeRecording(
            BridgeCommand command, string operation, string methodName)
        {
            Type apiType = FindType("UnityEditor.TestTools.CodeCoverage.CodeCoverage");
            PackageInfo info = FindPackageInfo();
            if (apiType == null) return Reply(command, Unavailable(operation));

            MethodInfo method = apiType.GetMethod(methodName, BindingFlags.Public | BindingFlags.Static);
            if (method == null) return Reply(command, Fail(operation, $"Missing API method: {methodName}"));
            method.Invoke(null, null);

            var result = BaseResult(operation, apiType, info);
            result.message = $"Code Coverage {operation} completed.";
            return Reply(command, result);
        }

        private static CodeCoverageResult FindReports(string operation, CodeCoverageParams p)
        {
            var result = Availability(operation);
            int max = p.maxResults > 0 ? p.maxResults : DefaultMaxResults;
            foreach (string root in CandidateRoots(p.reportPath))
            {
                foreach (string file in EnumerateArtifacts(root))
                {
                    result.reports.Add(BuildReportInfo(file));
                    if (result.reports.Count >= max) break;
                }
                if (result.reports.Count >= max) break;
            }
            result.reportCount = result.reports.Count;
            result.message = $"Found {result.reportCount} coverage artifact(s).";
            return result;
        }

        private static CodeCoverageResult Summarize(string operation, CodeCoverageParams p)
        {
            var result = Availability(operation);
            string path = ResolveSummaryPath(p.reportPath);
            if (string.IsNullOrEmpty(path) || !File.Exists(path))
                return Fail(operation, "Coverage summary artifact was not found.");

            result.summary = ReadSummary(path);
            result.reportPath = path;
            result.message = result.summary != null
                ? $"Summarized coverage report: {path}"
                : $"Coverage summary format is unsupported: {path}";
            result.success = result.summary != null;
            return result;
        }

        private static CodeCoverageResult BaseResult(string operation, Type apiType, PackageInfo info)
        {
            return new CodeCoverageResult
            {
                success = true,
                operation = operation,
                packageName = PackageName,
                packageAvailable = IsPackageAvailable(info) || apiType != null,
                apiAvailable = apiType != null,
                packageVersion = info?.version,
                resolvedPath = info?.resolvedPath,
            };
        }

        private static CodeCoverageResult Unavailable(string operation)
        {
            var result = Availability(operation);
            result.success = false;
            result.message = "Unity Code Coverage package/API is not available. "
                + "Run coverage install or install com.unity.testtools.codecoverage.";
            return result;
        }

        private static CodeCoverageResult Fail(string operation, string message)
        {
            var result = Availability(operation);
            result.success = false;
            result.message = message;
            return result;
        }

        private static Type FindType(string fullName)
        {
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type type = assembly.GetType(fullName);
                if (type != null) return type;
            }
            return null;
        }

        private static PackageInfo FindPackageInfo()
        {
            try { return PackageInfo.FindForPackageName(PackageName); }
            catch { return null; }
        }

        private static bool IsPackageAvailable(PackageInfo info)
        {
            if (info != null) return true;
            string root = ProjectRoot();
            if (string.IsNullOrEmpty(root)) return false;
            if (Directory.Exists(Path.Combine(root, "Packages", PackageName))) return true;
            string manifest = Path.Combine(root, "Packages", "manifest.json");
            return File.Exists(manifest) && File.ReadAllText(manifest).Contains(PackageName);
        }

        private static IEnumerable<string> CandidateRoots(string requested)
        {
            if (!string.IsNullOrEmpty(requested))
            {
                yield return AbsolutePath(requested);
                yield break;
            }

            string root = ProjectRoot();
            if (string.IsNullOrEmpty(root)) yield break;
            yield return Path.Combine(root, "CoverageResults");
            yield return Path.Combine(root, "CodeCoverage");
        }

        private static IEnumerable<string> EnumerateArtifacts(string root)
        {
            if (File.Exists(root))
            {
                if (IsCoverageArtifact(root)) yield return root;
                yield break;
            }
            if (!Directory.Exists(root)) yield break;
            foreach (string file in Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories))
            {
                if (IsCoverageArtifact(file)) yield return file;
            }
        }

        private static bool IsCoverageArtifact(string path)
        {
            string name = Path.GetFileName(path);
            string ext = Path.GetExtension(path).ToLowerInvariant();
            return name == "Summary.json" || name == "Summary.xml"
                || name == "index.htm" || name == "index.html"
                || (name.StartsWith("TestCoverageResults_") && ext == ".xml")
                || name.EndsWith("CoverageHistory.xml");
        }

        private static CodeCoverageReportInfo BuildReportInfo(string path)
        {
            var file = new FileInfo(path);
            return new CodeCoverageReportInfo
            {
                path = path,
                kind = ReportKind(path),
                sizeBytes = file.Exists ? file.Length : 0,
                lastWriteTimeUtc = file.Exists ? file.LastWriteTimeUtc.ToString("o") : null,
            };
        }

        private static string ReportKind(string path)
        {
            string name = Path.GetFileName(path);
            if (name == "Summary.json" || name == "Summary.xml") return "summary";
            if (name == "index.htm" || name == "index.html") return "html";
            if (name.EndsWith("CoverageHistory.xml")) return "history";
            return "opencover";
        }

        private static string ResolveSummaryPath(string requested)
        {
            if (!string.IsNullOrEmpty(requested))
            {
                string path = AbsolutePath(requested);
                if (File.Exists(path)) return path;
                if (Directory.Exists(path)) return PreferredSummaryIn(path);
            }
            foreach (string root in CandidateRoots(null))
            {
                string summary = PreferredSummaryIn(root);
                if (!string.IsNullOrEmpty(summary)) return summary;
            }
            return null;
        }

        private static string PreferredSummaryIn(string root)
        {
            string[] names = { "Summary.json", "Summary.xml" };
            foreach (string name in names)
            {
                string direct = Path.Combine(root, "Report", name);
                if (File.Exists(direct)) return direct;
                string nested = Directory.Exists(root)
                    ? Directory.EnumerateFiles(root, name, SearchOption.AllDirectories).FirstOrDefault()
                    : null;
                if (!string.IsNullOrEmpty(nested)) return nested;
            }
            return Directory.Exists(root)
                ? Directory.EnumerateFiles(root, "TestCoverageResults_*.xml",
                    SearchOption.AllDirectories).FirstOrDefault()
                : null;
        }

        private static CodeCoverageSummary ReadSummary(string path)
        {
            if (Path.GetFileName(path) == "Summary.json") return ReadReportGeneratorJson(path);
            XDocument doc = XDocument.Load(path);
            XElement root = doc.Root;
            if (root == null) return null;
            if (root.Name.LocalName == "CoverageReport") return ReadReportGeneratorXml(path, doc);
            return ReadOpenCoverSummary(path, doc);
        }

        private static CodeCoverageSummary ReadReportGeneratorJson(string path)
        {
            var parsed = JsonUtility.FromJson<CoverageSummaryJsonRoot>(File.ReadAllText(path));
            var s = parsed?.summary;
            if (s == null) return null;
            return new CodeCoverageSummary
            {
                path = path,
                format = "reportgenerator-json",
                generatedOn = s.generatedon,
                assemblies = s.assemblies,
                classes = s.classes,
                files = s.files,
                coveredLines = s.coveredlines,
                coverableLines = s.coverablelines,
                totalLines = s.totallines,
                lineCoverage = s.linecoverage,
                coveredBranches = s.coveredbranches,
                totalBranches = s.totalbranches,
                coveredMethods = s.coveredmethods,
                totalMethods = s.totalmethods,
                methodCoverage = s.methodcoverage,
            };
        }

        private static CodeCoverageSummary ReadReportGeneratorXml(string path, XDocument doc)
        {
            XElement s = doc.Descendants().FirstOrDefault(e => e.Name.LocalName == "Summary");
            if (s == null) return null;
            return new CodeCoverageSummary
            {
                path = path,
                format = "reportgenerator-xml",
                generatedOn = ElementText(s, "Generatedon"),
                assemblies = ElementInt(s, "Assemblies"),
                classes = ElementInt(s, "Classes"),
                files = ElementInt(s, "Files"),
                coveredLines = ElementInt(s, "Coveredlines"),
                coverableLines = ElementInt(s, "Coverablelines"),
                totalLines = ElementInt(s, "Totallines"),
                lineCoverage = ElementFloat(s, "Linecoverage"),
                coveredBranches = ElementInt(s, "Coveredbranches"),
                totalBranches = ElementInt(s, "Totalbranches"),
                coveredMethods = ElementInt(s, "Coveredmethods"),
                totalMethods = ElementInt(s, "Totalmethods"),
                methodCoverage = ElementFloat(s, "Methodcoverage"),
            };
        }

        private static CodeCoverageSummary ReadOpenCoverSummary(string path, XDocument doc)
        {
            XElement s = doc.Descendants().FirstOrDefault(e => e.Name.LocalName == "Summary");
            if (s == null) return null;
            return new CodeCoverageSummary
            {
                path = path,
                format = "opencover",
                coveredLines = AttrInt(s, "visitedSequencePoints"),
                coverableLines = AttrInt(s, "numSequencePoints"),
                lineCoverage = AttrFloat(s, "sequenceCoverage"),
                coveredBranches = AttrInt(s, "visitedBranchPoints"),
                totalBranches = AttrInt(s, "numBranchPoints"),
                branchCoverage = AttrFloat(s, "branchCoverage"),
                coveredMethods = AttrInt(s, "visitedMethods"),
                totalMethods = AttrInt(s, "numMethods"),
                classes = AttrInt(s, "numClasses"),
            };
        }

        private static string ProjectRoot()
        {
            return Directory.GetParent(Application.dataPath)?.FullName;
        }

        private static string AbsolutePath(string path)
        {
            return Path.IsPathRooted(path) ? path : Path.Combine(ProjectRoot(), path);
        }

        private static string ElementText(XElement e, string name)
        {
            return e.Elements().FirstOrDefault(x => x.Name.LocalName == name)?.Value;
        }

        private static int ElementInt(XElement e, string name)
        {
            int.TryParse(ElementText(e, name), out int value);
            return value;
        }

        private static float ElementFloat(XElement e, string name)
        {
            float.TryParse(ElementText(e, name), out float value);
            return value;
        }

        private static int AttrInt(XElement e, string name)
        {
            int.TryParse((string)e.Attribute(name), out int value);
            return value;
        }

        private static float AttrFloat(XElement e, string name)
        {
            float.TryParse((string)e.Attribute(name), out float value);
            return value;
        }
    }

}
