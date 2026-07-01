using System;
using UnityEditor;
using UnityEngine;
using UnityEngine.Playables;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for com.unity.timeline operations.
    /// Requires the Timeline package. Returns an error if it is not installed.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "create-track" - Create a top-level track on a TimelineAsset
    /// 2. "create-clip"  - Create a clip on a track (default clip if no asset given)
    /// 3. "get-clips"    - List clips on a track
    /// 4. "delete-clip"  - Delete a clip from a track by index
    /// 5. "get-info"     - List tracks on a TimelineAsset
    /// 6. "evaluate"     - Bind/scrub/evaluate a PlayableDirector
    ///
    /// Track creation only supports top-level (null-parent) tracks in v1 —
    /// parent-track grouping is out of scope.
    ///
    /// Clips are addressed by (trackIndex, clipIndex), the position within
    /// TimelineAsset's track list and that track's GetClips() order at query
    /// time. Indices can shift after any mutation; re-query via get-clips
    /// before reuse.
    ///
    /// PlayableDirector is a built-in engine type (DirectorModule), always
    /// present regardless of the Timeline package, so it is used directly
    /// with no reflection. TimelineAsset/TrackAsset/TimelineClip live in the
    /// optional Unity.Timeline.dll package assembly and are only ever touched
    /// through TimelineHelpers' reflection layer.
    /// </summary>
    public class TimelineCommandHandler : ICommandHandler
    {
        public string CommandType => "timeline-operation";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (!TimelineHelpers.IsTimelineAvailable())
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Timeline package (com.unity.timeline) is not installed. "
                        + "Install it via Package Manager.");
                }

                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot perform Timeline operations while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<TimelineParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new TimelineParams();

                BridgeLogger.LogDebug($"Executing timeline operation: {parameters.operation}");

                switch (parameters.operation?.ToLower())
                {
                    case "create-track":
                        return ExecuteCreateTrack(command, parameters);
                    case "create-clip":
                        return ExecuteCreateClip(command, parameters);
                    case "get-clips":
                        return ExecuteGetClips(command, parameters);
                    case "delete-clip":
                        return ExecuteDeleteClip(command, parameters);
                    case "get-info":
                        return ExecuteGetInfo(command, parameters);
                    case "evaluate":
                        return ExecuteEvaluate(command, parameters);
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown timeline operation: {parameters.operation}. "
                            + "Supported: create-track, create-clip, get-clips, "
                            + "delete-clip, get-info, evaluate");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Timeline operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse ExecuteCreateTrack(BridgeCommand command, TimelineParams p)
        {
            if (string.IsNullOrEmpty(p.timelineAssetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "timelineAssetPath is required for create-track operation.");
            }
            if (string.IsNullOrEmpty(p.trackType))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "trackType is required for create-track operation.");
            }

            var timelineAsset = TimelineHelpers.LoadTimelineAsset(p.timelineAssetPath);
            if (timelineAsset == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"TimelineAsset not found: {p.timelineAssetPath}");
            }

            var trackType = TimelineHelpers.ResolveTrackType(p.trackType);
            if (trackType == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Unknown track type: {p.trackType}. "
                    + $"Supported short names: {TimelineHelpers.SupportedTrackTypeNames()} "
                    + "(or a fully-qualified UnityEngine.Timeline.* type name).");
            }

            var track = TimelineHelpers.CreateTrack(timelineAsset, trackType, p.trackName, out var error);
            if (track == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    error ?? "Failed to create track.");
            }

            TimelineHelpers.MarkDirtyAndSave(timelineAsset);

            var tracks = TimelineHelpers.GetTracks(timelineAsset);
            int trackIndex = tracks.Count - 1;
            for (int i = 0; i < tracks.Count; i++)
            {
                if (ReferenceEquals(tracks[i], track)) { trackIndex = i; break; }
            }

            var result = new TimelineTrackResult
            {
                operation = "create-track",
                success = true,
                trackIndex = trackIndex,
                name = TimelineHelpers.GetName(track),
                typeName = trackType.FullName,
                message = $"Created track '{TimelineHelpers.GetName(track)}' at index {trackIndex}"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteCreateClip(BridgeCommand command, TimelineParams p)
        {
            if (string.IsNullOrEmpty(p.timelineAssetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "timelineAssetPath is required for create-clip operation.");
            }
            if (p.trackIndex < 0)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "trackIndex is required for create-clip operation.");
            }

            var timelineAsset = TimelineHelpers.LoadTimelineAsset(p.timelineAssetPath);
            if (timelineAsset == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"TimelineAsset not found: {p.timelineAssetPath}");
            }

            var tracks = TimelineHelpers.GetTracks(timelineAsset);
            if (p.trackIndex >= tracks.Count)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"trackIndex {p.trackIndex} is out of range (0-{tracks.Count - 1}).");
            }
            var track = tracks[p.trackIndex];

            var clip = TimelineHelpers.CreateDefaultClip(track, out var error);
            if (clip == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    error ?? "Failed to create clip.");
            }

            if (!string.IsNullOrEmpty(p.clipAssetPath))
            {
                var playableAsset = AssetDatabase.LoadAssetAtPath<UnityEngine.Playables.PlayableAsset>(
                    p.clipAssetPath);
                if (playableAsset == null)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        $"PlayableAsset not found at clipAssetPath: {p.clipAssetPath}");
                }
                if (!TimelineHelpers.SetClipAsset(clip, playableAsset))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "TimelineClip.asset property was not found or is not writable.");
                }
            }

            TimelineHelpers.MarkDirtyAndSave(timelineAsset);

            var clips = TimelineHelpers.GetClips(track);
            int clipIndex = clips.Count - 1;
            for (int i = 0; i < clips.Count; i++)
            {
                if (ReferenceEquals(clips[i], clip)) { clipIndex = i; break; }
            }

            var result = new TimelineClipResult
            {
                operation = "create-clip",
                success = true,
                trackIndex = p.trackIndex,
                clipIndex = clipIndex,
                displayName = TimelineHelpers.GetDisplayName(clip),
                start = TimelineHelpers.GetDouble(clip, "start"),
                duration = TimelineHelpers.GetDouble(clip, "duration"),
                message = $"Created clip at track {p.trackIndex}, clip index {clipIndex}"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteGetClips(BridgeCommand command, TimelineParams p)
        {
            if (string.IsNullOrEmpty(p.timelineAssetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "timelineAssetPath is required for get-clips operation.");
            }
            if (p.trackIndex < 0)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "trackIndex is required for get-clips operation.");
            }

            var timelineAsset = TimelineHelpers.LoadTimelineAsset(p.timelineAssetPath);
            if (timelineAsset == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"TimelineAsset not found: {p.timelineAssetPath}");
            }

            var tracks = TimelineHelpers.GetTracks(timelineAsset);
            if (p.trackIndex >= tracks.Count)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"trackIndex {p.trackIndex} is out of range (0-{tracks.Count - 1}).");
            }
            var track = tracks[p.trackIndex];
            var clips = TimelineHelpers.GetClips(track);

            var result = new TimelineClipsResult
            {
                operation = "get-clips",
                success = true,
                trackIndex = p.trackIndex,
                message = $"Found {clips.Count} clips on track {p.trackIndex}"
            };
            for (int i = 0; i < clips.Count; i++)
            {
                var clip = clips[i];
                result.clips.Add(new TimelineClipInfo
                {
                    trackIndex = p.trackIndex,
                    clipIndex = i,
                    displayName = TimelineHelpers.GetDisplayName(clip),
                    start = TimelineHelpers.GetDouble(clip, "start"),
                    duration = TimelineHelpers.GetDouble(clip, "duration"),
                });
            }
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteDeleteClip(BridgeCommand command, TimelineParams p)
        {
            if (string.IsNullOrEmpty(p.timelineAssetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "timelineAssetPath is required for delete-clip operation.");
            }
            if (p.trackIndex < 0 || p.clipIndex < 0)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "trackIndex and clipIndex are required for delete-clip operation.");
            }

            var timelineAsset = TimelineHelpers.LoadTimelineAsset(p.timelineAssetPath);
            if (timelineAsset == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"TimelineAsset not found: {p.timelineAssetPath}");
            }

            var tracks = TimelineHelpers.GetTracks(timelineAsset);
            if (p.trackIndex >= tracks.Count)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"trackIndex {p.trackIndex} is out of range (0-{tracks.Count - 1}).");
            }
            var track = tracks[p.trackIndex];
            var clips = TimelineHelpers.GetClips(track);
            if (p.clipIndex >= clips.Count)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"clipIndex {p.clipIndex} is out of range (0-{clips.Count - 1}) "
                    + $"for track {p.trackIndex}.");
            }

            bool deleted = TimelineHelpers.DeleteClip(track, clips[p.clipIndex]);
            if (!deleted)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Failed to delete clip at track {p.trackIndex}, clip {p.clipIndex}.");
            }

            TimelineHelpers.MarkDirtyAndSave(timelineAsset);

            var result = new TimelineResult
            {
                operation = "delete-clip",
                success = true,
                message = $"Deleted clip at track {p.trackIndex}, clip index {p.clipIndex}. "
                    + "Remaining clip indices may have shifted — re-query via get-clips."
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteGetInfo(BridgeCommand command, TimelineParams p)
        {
            if (string.IsNullOrEmpty(p.timelineAssetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "timelineAssetPath is required for get-info operation.");
            }

            var timelineAsset = TimelineHelpers.LoadTimelineAsset(p.timelineAssetPath);
            if (timelineAsset == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"TimelineAsset not found: {p.timelineAssetPath}");
            }

            var tracks = TimelineHelpers.GetTracks(timelineAsset);
            var result = new TimelineInfoResult
            {
                operation = "get-info",
                success = true,
                timelineAssetPath = p.timelineAssetPath,
                message = $"Found {tracks.Count} tracks on {p.timelineAssetPath}"
            };
            for (int i = 0; i < tracks.Count; i++)
            {
                var track = tracks[i];
                result.tracks.Add(new TimelineTrackInfo
                {
                    trackIndex = i,
                    name = TimelineHelpers.GetName(track),
                    typeName = track.GetType().FullName,
                    clipCount = TimelineHelpers.GetClips(track).Count
                });
            }
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteEvaluate(BridgeCommand command, TimelineParams p)
        {
            if (string.IsNullOrEmpty(p.directorPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "directorPath is required for evaluate operation.");
            }

            var directorObject = GameObject.Find(p.directorPath);
            if (directorObject == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"GameObject not found at path: {p.directorPath}");
            }

            var director = directorObject.GetComponent<PlayableDirector>();
            if (director == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"No PlayableDirector component found on: {p.directorPath}");
            }

            if (!string.IsNullOrEmpty(p.timelineAssetPath))
            {
                var timelineAsset = TimelineHelpers.LoadTimelineAsset(p.timelineAssetPath);
                if (timelineAsset == null)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        $"TimelineAsset not found: {p.timelineAssetPath}");
                }
                director.playableAsset = timelineAsset as PlayableAsset;
            }

            bool hasTime = !float.IsNaN(p.time);
            if (hasTime)
                director.time = p.time;

            director.Evaluate();

            var result = new TimelineResult
            {
                operation = "evaluate",
                success = true,
                message = hasTime
                    ? $"Evaluated '{p.directorPath}' at time {p.time}"
                    : $"Evaluated '{p.directorPath}' at current time {director.time}"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }
    }
}
