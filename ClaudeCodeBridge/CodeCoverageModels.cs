using System;
using System.Collections.Generic;

namespace BWS.Editor.ClaudeCodeBridge
{
    [Serializable]
    public class CodeCoverageParams
    {
        public string operation;
        public string identifier;
        public string reportPath;
        public int maxResults;
    }

    [Serializable]
    public class CodeCoverageResult
    {
        public bool success;
        public string operation;
        public string packageName;
        public bool packageAvailable;
        public bool apiAvailable;
        public string packageVersion;
        public string resolvedPath;
        public string identifier;
        public string reportPath;
        public int reportCount;
        public List<CodeCoverageReportInfo> reports = new List<CodeCoverageReportInfo>();
        public CodeCoverageSummary summary;
        public string message;
    }

    [Serializable]
    public class CodeCoverageReportInfo
    {
        public string path;
        public string kind;
        public long sizeBytes;
        public string lastWriteTimeUtc;
    }

    [Serializable]
    public class CodeCoverageSummary
    {
        public string path;
        public string format;
        public string generatedOn;
        public int assemblies;
        public int classes;
        public int files;
        public int coveredLines;
        public int coverableLines;
        public int totalLines;
        public float lineCoverage;
        public int coveredBranches;
        public int totalBranches;
        public float branchCoverage;
        public int coveredMethods;
        public int totalMethods;
        public float methodCoverage;
    }

    [Serializable]
    internal class CoverageSummaryJsonRoot
    {
        public CoverageSummaryJson summary;
    }

    [Serializable]
    internal class CoverageSummaryJson
    {
        public string generatedon;
        public int assemblies;
        public int classes;
        public int files;
        public int coveredlines;
        public int coverablelines;
        public int totallines;
        public float linecoverage;
        public int coveredbranches;
        public int totalbranches;
        public int coveredmethods;
        public int totalmethods;
        public float methodcoverage;
    }
}
