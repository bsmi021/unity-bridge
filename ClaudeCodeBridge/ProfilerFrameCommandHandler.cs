using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Profiling;
using UnityEditorInternal;
using UnityEngine;
using UnityEngine.Profiling;

namespace BWS.Editor.ClaudeCodeBridge
{
    public class ProfilerFrameCommandHandler : ICommandHandler
    {
        private static int _captureStopFrameIndex = -1;
        private static int _captureRequestedFrameCount;
        private static int _captureStartFrameIndex = -1;
        private static int _captureStopObservedFrameIndex = -1;
        private static string _captureOwner = "";
        private static bool _captureStopRegistered;

        public string CommandType => "profiler-frame";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<ProfilerFrameParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new ProfilerFrameParams();

                var result = Dispatch(parameters);
                return result.success
                    ? BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result))
                    : BridgeResponse.Error(command.commandId, command.commandType, result.message);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Profiler frame error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private ProfilerFrameResult Dispatch(ProfilerFrameParams p)
        {
            switch (p.operation?.ToLower())
            {
                case "capture-start": return CaptureStart(p);
                case "capture-stop": return CaptureStop();
                case "frame-range": return FrameRange("frame-range");
                case "top-time-samples": return TopTimeSamples(p);
                case "self-time-samples": return HierarchySamples(p, true);
                case "sample-time-summary": return SampleTimeSummary(p);
                case "bottom-up-tree": return BottomUpTree(p);
                case "gc-alloc": return GcAlloc(p);
                case "sample-gc-alloc": return SampleGcAlloc(p);
                case "clear": return ClearFrames();
                default:
                    return Fail(p.operation, $"Unknown profiler-frame operation: {p.operation}");
            }
        }

        private ProfilerFrameResult CaptureStart(ProfilerFrameParams p)
        {
            ClearFrameBudget();
            ResetCaptureState(p.frameCount, "profiler-frame");
            if (!string.IsNullOrEmpty(p.logFile))
            {
                Profiler.logFile = p.logFile;
                Profiler.enableBinaryLog = true;
            }
            ProfilerDriver.profileEditor = true;
            ProfilerDriver.enabled = true;
            Profiler.enabled = true;
            ConfigureFrameBudget(p.frameCount);
            string message = p.frameCount > 0
                ? $"Profiler capture started with a {p.frameCount}-frame budget"
                : "Profiler capture started";
            return FrameRange("capture-start", message);
        }

        private ProfilerFrameResult CaptureStop()
        {
            Profiler.enabled = false;
            ProfilerDriver.enabled = false;
            Profiler.enableBinaryLog = false;
            RecordCaptureStop();
            ClearFrameBudget();
            return FrameRange("capture-stop", "Profiler capture stopped");
        }

        private static void ConfigureFrameBudget(int frameCount)
        {
            if (frameCount <= 0)
                return;
            EditorApplication.update += StopCaptureAtFrameBudget;
            _captureStopRegistered = true;
        }

        private static void StopCaptureAtFrameBudget()
        {
            if (ProfilerDriver.lastFrameIndex < _captureStopFrameIndex)
                return;
            Profiler.enabled = false;
            ProfilerDriver.enabled = false;
            Profiler.enableBinaryLog = false;
            RecordCaptureStop();
            ClearFrameBudget();
        }

        private static void ClearFrameBudget()
        {
            if (_captureStopRegistered)
                EditorApplication.update -= StopCaptureAtFrameBudget;
            _captureStopRegistered = false;
        }

        private static void ResetCaptureState(int frameCount, string owner)
        {
            _captureRequestedFrameCount = Math.Max(frameCount, 0);
            _captureStartFrameIndex = ProfilerDriver.lastFrameIndex;
            _captureStopObservedFrameIndex = -1;
            long target = (long)_captureStartFrameIndex + _captureRequestedFrameCount;
            _captureStopFrameIndex = _captureRequestedFrameCount > 0
                ? (int)Math.Min(target, int.MaxValue)
                : -1;
            _captureOwner = owner;
        }

        private static void RecordCaptureStop()
        {
            _captureStopObservedFrameIndex = ProfilerDriver.lastFrameIndex;
        }

        internal static void StartExternalCapture()
        {
            ClearFrameBudget();
            ResetCaptureState(0, "profiler-control");
        }

        internal static void StopExternalCapture()
        {
            if (!string.IsNullOrEmpty(_captureOwner))
                RecordCaptureStop();
            ClearFrameBudget();
        }

        private ProfilerFrameResult FrameRange(string operation, string message = "Profiler frame range")
        {
            return new ProfilerFrameResult
            {
                operation = operation,
                success = true,
                message = message,
                firstFrameIndex = ProfilerDriver.firstFrameIndex,
                lastFrameIndex = ProfilerDriver.lastFrameIndex,
                requestedFrameCount = _captureRequestedFrameCount,
                startFrameIndex = _captureStartFrameIndex,
                targetFrameIndex = _captureStopFrameIndex,
                stopObservedFrameIndex = _captureStopObservedFrameIndex,
                actualFrameCount = ActualFrameCount(),
                overshootFrames = OvershootFrames(),
                runtimeProfilerEnabled = Profiler.enabled,
                editorDriverEnabled = ProfilerDriver.enabled,
                profileEditor = ProfilerDriver.profileEditor,
                captureOwner = _captureOwner,
                frameBudgetArmed = _captureStopRegistered
            };
        }

        private static int ActualFrameCount()
        {
            if (string.IsNullOrEmpty(_captureOwner))
                return 0;
            return Math.Max(0, ProfilerDriver.lastFrameIndex - _captureStartFrameIndex);
        }

        private static int OvershootFrames()
        {
            return _captureRequestedFrameCount > 0
                ? Math.Max(0, ActualFrameCount() - _captureRequestedFrameCount)
                : 0;
        }

        private ProfilerFrameResult TopTimeSamples(ProfilerFrameParams p)
        {
            if (!FrameIsValid(p.frameIndex, out var error))
                return Fail(p.operation, error);

            using (var view = ProfilerDriver.GetRawFrameDataView(p.frameIndex, p.threadIndex))
            {
                if (!view.valid)
                    return Fail(p.operation, "Profiler raw frame data is not valid.");
                var samples = new List<ProfilerFrameSampleInfo>();
                for (var i = 0; i < view.sampleCount; i++)
                {
                    samples.Add(new ProfilerFrameSampleInfo
                    {
                        markerName = view.GetSampleName(i),
                        markerId = view.GetSampleMarkerId(i),
                        totalTimeMs = view.GetSampleTimeMs(i),
                        callCount = 1
                    });
                }
                samples.Sort((a, b) => b.totalTimeMs.CompareTo(a.totalTimeMs));
                return SamplesResult(p, Take(samples, p.count));
            }
        }

        private ProfilerFrameResult HierarchySamples(ProfilerFrameParams p, bool sortBySelf)
        {
            if (!FrameIsValid(p.frameIndex, out var error))
                return Fail(p.operation, error);

            using (var view = OpenHierarchyView(p))
            {
                if (!view.valid)
                    return Fail(p.operation, "Profiler hierarchy frame data is not valid.");
                var samples = ReadHierarchySamples(view);
                samples.Sort((a, b) => sortBySelf
                    ? b.selfTimeMs.CompareTo(a.selfTimeMs)
                    : b.totalTimeMs.CompareTo(a.totalTimeMs));
                return SamplesResult(p, Take(samples, p.count));
            }
        }

        private ProfilerFrameResult SampleTimeSummary(ProfilerFrameParams p)
        {
            if (!RangeIsValid(p.frameIndexStart, p.frameIndexEnd, out var error))
                return Fail(p.operation, error);

            var summary = new ProfilerFrameSummaryInfo { markerName = p.markerName };
            for (var frame = p.frameIndexStart; frame <= p.frameIndexEnd; frame++)
                AccumulateMarker(frame, p.threadIndex, p.markerName, summary);
            return SummaryResult(p, summary);
        }

        private ProfilerFrameResult GcAlloc(ProfilerFrameParams p)
        {
            var start = p.frameIndex >= 0 ? p.frameIndex : p.frameIndexStart;
            var end = p.frameIndex >= 0 ? p.frameIndex : p.frameIndexEnd;
            if (!RangeIsValid(start, end, out var error))
                return Fail(p.operation, error);

            long total = 0;
            for (var frame = start; frame <= end; frame++)
                total += SumGc(frame, p.threadIndex, null);
            return GcResult(p, start, total);
        }

        private ProfilerFrameResult SampleGcAlloc(ProfilerFrameParams p)
        {
            if (!FrameIsValid(p.frameIndex, out var error))
                return Fail(p.operation, error);
            return GcResult(p, p.frameIndex, SumGc(p.frameIndex, p.threadIndex, p.markerName));
        }

        private ProfilerFrameResult BottomUpTree(ProfilerFrameParams p)
        {
            if (!FrameIsValid(p.frameIndex, out var error))
                return Fail(p.operation, error);

            using (var view = OpenHierarchyView(p))
            {
                var result = BaseResult(p, true, "Bottom-up tree");
                var items = ReadHierarchyItems(view);
                foreach (var id in items)
                {
                    if (view.GetItemName(id) != p.markerName)
                        continue;
                    AddAncestors(view, id, Math.Max(p.depth, 1), result.tree);
                }
                return result;
            }
        }

        private ProfilerFrameResult ClearFrames()
        {
            ClearFrameBudget();
            ProfilerDriver.ClearAllFrames();
            ResetCaptureState(0, "");
            return FrameRange("clear", "Profiler frames cleared");
        }

        private static HierarchyFrameDataView OpenHierarchyView(ProfilerFrameParams p)
        {
            return ProfilerDriver.GetHierarchyFrameDataView(
                p.frameIndex,
                p.threadIndex,
                HierarchyFrameDataView.ViewModes.Default,
                HierarchyFrameDataView.columnDontSort,
                false);
        }

        private static List<ProfilerFrameSampleInfo> ReadHierarchySamples(
            HierarchyFrameDataView view)
        {
            var samples = new List<ProfilerFrameSampleInfo>();
            foreach (var id in ReadHierarchyItems(view))
                samples.Add(ReadSample(view, id));
            return samples;
        }

        private static List<int> ReadHierarchyItems(HierarchyFrameDataView view)
        {
            var result = new List<int>();
            AddChildren(view, view.GetRootItemID(), result);
            return result;
        }

        private static void AddChildren(HierarchyFrameDataView view, int parentId, List<int> result)
        {
            var children = new List<int>();
            view.GetItemChildren(parentId, children);
            foreach (var child in children)
            {
                result.Add(child);
                AddChildren(view, child, result);
            }
        }

        private static ProfilerFrameSampleInfo ReadSample(HierarchyFrameDataView view, int id)
        {
            return new ProfilerFrameSampleInfo
            {
                markerName = view.GetItemName(id),
                markerId = view.GetItemMarkerID(id),
                totalTimeMs = view.GetItemColumnDataAsDouble(id, HierarchyFrameDataView.columnTotalTime),
                selfTimeMs = view.GetItemColumnDataAsDouble(id, HierarchyFrameDataView.columnSelfTime),
                gcBytes = (long)view.GetItemColumnDataAsDouble(id, HierarchyFrameDataView.columnGcMemory),
                callCount = (int)view.GetItemColumnDataAsDouble(id, HierarchyFrameDataView.columnCalls)
            };
        }

        private static void AccumulateMarker(
            int frame, int threadIndex, string markerName, ProfilerFrameSummaryInfo summary)
        {
            var p = new ProfilerFrameParams { frameIndex = frame, threadIndex = threadIndex };
            using (var view = OpenHierarchyView(p))
            {
                foreach (var sample in ReadHierarchySamples(view))
                {
                    if (sample.markerName != markerName)
                        continue;
                    summary.totalTimeMs += sample.totalTimeMs;
                    summary.selfTimeMs += sample.selfTimeMs;
                    summary.gcBytes += sample.gcBytes;
                    summary.callCount += Math.Max(sample.callCount, 1);
                }
            }
        }

        private static long SumGc(int frame, int threadIndex, string markerName)
        {
            long total = 0;
            var p = new ProfilerFrameParams { frameIndex = frame, threadIndex = threadIndex };
            using (var view = OpenHierarchyView(p))
            {
                foreach (var sample in ReadHierarchySamples(view))
                {
                    if (markerName == null || sample.markerName == markerName)
                        total += sample.gcBytes;
                }
            }
            return total;
        }

        private static void AddAncestors(
            HierarchyFrameDataView view, int itemId, int maxDepth, List<ProfilerFrameTreeInfo> tree)
        {
            var ancestors = new List<int>();
            view.GetItemAncestors(itemId, ancestors);
            ancestors.Add(itemId);
            var start = Math.Max(0, ancestors.Count - maxDepth);
            for (var i = start; i < ancestors.Count; i++)
            {
                var sample = ReadSample(view, ancestors[i]);
                tree.Add(new ProfilerFrameTreeInfo
                {
                    depth = i - start,
                    markerName = sample.markerName,
                    totalTimeMs = sample.totalTimeMs,
                    selfTimeMs = sample.selfTimeMs,
                    gcBytes = sample.gcBytes,
                    callCount = sample.callCount
                });
            }
        }

        private static bool FrameIsValid(int frameIndex, out string error)
        {
            error = "";
            if (frameIndex < ProfilerDriver.firstFrameIndex
                || frameIndex > ProfilerDriver.lastFrameIndex)
            {
                error = $"frameIndex {frameIndex} is outside retained range "
                    + $"[{ProfilerDriver.firstFrameIndex}, {ProfilerDriver.lastFrameIndex}].";
                return false;
            }
            return true;
        }

        private static bool RangeIsValid(int start, int end, out string error)
        {
            error = "";
            if (start < 0 || end < start)
            {
                error = "A frame index or valid frame range is required.";
                return false;
            }
            return FrameIsValid(start, out error) && FrameIsValid(end, out error);
        }

        private static List<ProfilerFrameSampleInfo> Take(
            List<ProfilerFrameSampleInfo> samples, int count)
        {
            var max = count > 0 ? count : 10;
            return samples.Count <= max ? samples : samples.GetRange(0, max);
        }

        private static ProfilerFrameResult SamplesResult(
            ProfilerFrameParams p, List<ProfilerFrameSampleInfo> samples)
        {
            var result = BaseResult(p, true, "Profiler samples");
            result.samples = samples;
            return result;
        }

        private static ProfilerFrameResult SummaryResult(
            ProfilerFrameParams p, ProfilerFrameSummaryInfo summary)
        {
            var result = BaseResult(p, true, "Profiler sample summary");
            result.summaries.Add(summary);
            return result;
        }

        private static ProfilerFrameResult GcResult(
            ProfilerFrameParams p, int frameIndex, long totalGcBytes)
        {
            var result = BaseResult(p, true, "Profiler GC allocation");
            result.frameIndex = frameIndex;
            result.totalGcBytes = totalGcBytes;
            return result;
        }

        private static ProfilerFrameResult BaseResult(
            ProfilerFrameParams p, bool success, string message)
        {
            return new ProfilerFrameResult
            {
                operation = p.operation,
                success = success,
                message = message,
                firstFrameIndex = ProfilerDriver.firstFrameIndex,
                lastFrameIndex = ProfilerDriver.lastFrameIndex,
                frameIndex = p.frameIndex
            };
        }

        private static ProfilerFrameResult Fail(string operation, string message)
        {
            return new ProfilerFrameResult
            {
                operation = operation,
                success = false,
                message = message,
                firstFrameIndex = ProfilerDriver.firstFrameIndex,
                lastFrameIndex = ProfilerDriver.lastFrameIndex
            };
        }
    }
}
