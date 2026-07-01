using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Reflection plumbing for com.unity.timeline. The Timeline package is an
    /// optional Package Manager package (Unity.Timeline.dll) — never reference
    /// its types directly (a hard CS0246 would kill the whole bridge assembly
    /// when the package is absent). All type/member lookups go through here.
    /// </summary>
    internal static class TimelineHelpers
    {
        private static readonly Dictionary<string, string> ShortTrackTypeNames =
            new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
            {
                { "AnimationTrack", "UnityEngine.Timeline.AnimationTrack" },
                { "GroupTrack", "UnityEngine.Timeline.GroupTrack" },
                { "AudioTrack", "UnityEngine.Timeline.AudioTrack" },
                { "ActivationTrack", "UnityEngine.Timeline.ActivationTrack" },
                { "MarkerTrack", "UnityEngine.Timeline.MarkerTrack" },
                { "ControlTrack", "UnityEngine.Timeline.ControlTrack" },
                { "PlayableTrack", "UnityEngine.Timeline.PlayableTrack" },
                { "SignalTrack", "UnityEngine.Timeline.SignalTrack" },
            };

        public static bool IsTimelineAvailable() => FindType("UnityEngine.Timeline.TimelineAsset") is not null;

        public static Type FindType(string fullName)
        {
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type type = assembly.GetType(fullName);
                if (type is not null) return type;
            }
            return null;
        }

        public static Type ResolveTrackType(string trackType)
        {
            if (string.IsNullOrEmpty(trackType)) return null;
            if (ShortTrackTypeNames.TryGetValue(trackType, out var fullName))
            {
                var resolved = FindType(fullName);
                if (resolved is not null) return resolved;
            }
            return FindType(trackType);
        }

        public static UnityEngine.Object LoadTimelineAsset(string path)
        {
            var type = FindType("UnityEngine.Timeline.TimelineAsset");
            if (type is null) return null;
            return AssetDatabase.LoadAssetAtPath(path, type);
        }

        public static IList GetTracks(UnityEngine.Object timelineAsset)
        {
            // GetRootTracks() (not GetOutputTracks()) is required here: root tracks
            // are top-level by hierarchy position and include GroupTrack, matching
            // this handler's "top-level only" v1 contract. GetOutputTracks() excludes
            // GroupTrack entirely (it never generates a PlayableOutput), which would
            // silently break trackIndex addressing for any GroupTrack created via
            // create-track.
            var method = timelineAsset.GetType().GetMethod("GetRootTracks",
                BindingFlags.Public | BindingFlags.Instance);
            var enumerable = method?.Invoke(timelineAsset, null) as IEnumerable;
            var list = new List<object>();
            if (enumerable is not null)
                foreach (var track in enumerable) list.Add(track);
            return list;
        }

        public static object CreateTrack(
            UnityEngine.Object timelineAsset, Type trackType, string trackName, out string error)
        {
            error = null;
            var method = timelineAsset.GetType().GetMethod("CreateTrack",
                BindingFlags.Public | BindingFlags.Instance,
                null,
                new[] { typeof(Type), FindType("UnityEngine.Timeline.TrackAsset"), typeof(string) },
                null);
            if (method is null)
            {
                error = "TimelineAsset.CreateTrack(Type, TrackAsset, string) overload not found.";
                return null;
            }

            try
            {
                return method.Invoke(timelineAsset, new object[] { trackType, null, trackName ?? "" });
            }
            catch (TargetInvocationException tie) when (tie.InnerException is InvalidOperationException ioe)
            {
                error = $"Unable to create track: {ioe.Message}";
                return null;
            }
        }

        public static IList GetClips(object track)
        {
            var method = track.GetType().GetMethod("GetClips",
                BindingFlags.Public | BindingFlags.Instance);
            var enumerable = method?.Invoke(track, null) as IEnumerable;
            var list = new List<object>();
            if (enumerable is not null)
                foreach (var clip in enumerable) list.Add(clip);
            return list;
        }

        public static object CreateDefaultClip(object track, out string error)
        {
            error = null;
            var method = track.GetType().GetMethod("CreateDefaultClip",
                BindingFlags.Public | BindingFlags.Instance);
            if (method is null)
            {
                error = "TrackAsset.CreateDefaultClip() was not found.";
                return null;
            }
            return method.Invoke(track, null);
        }

        public static bool SetClipAsset(object clip, UnityEngine.Object playableAsset)
        {
            var prop = clip.GetType().GetProperty("asset",
                BindingFlags.Public | BindingFlags.Instance);
            if (prop is null || !prop.CanWrite) return false;
            prop.SetValue(clip, playableAsset);
            return true;
        }

        public static bool DeleteClip(object track, object clip)
        {
            var method = track.GetType().GetMethod("DeleteClip",
                BindingFlags.Public | BindingFlags.Instance);
            if (method is null) return false;
            var result = method.Invoke(track, new object[] { clip });
            return result is bool deleted && deleted;
        }

        public static string GetName(object target)
        {
            var prop = target.GetType().GetProperty("name", BindingFlags.Public | BindingFlags.Instance);
            return prop?.GetValue(target)?.ToString() ?? "";
        }

        public static string GetDisplayName(object clip)
        {
            var prop = clip.GetType().GetProperty("displayName", BindingFlags.Public | BindingFlags.Instance);
            return prop?.GetValue(clip)?.ToString() ?? "";
        }

        public static double GetDouble(object target, string propertyName)
        {
            var prop = target.GetType().GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
            if (prop is null) return 0d;
            var value = prop.GetValue(target);
            return value is double d ? d : 0d;
        }

        public static void MarkDirtyAndSave(UnityEngine.Object timelineAsset)
        {
            EditorUtility.SetDirty(timelineAsset);
            AssetDatabase.SaveAssets();
        }

        public static string SupportedTrackTypeNames() => string.Join(", ", ShortTrackTypeNames.Keys);
    }
}
