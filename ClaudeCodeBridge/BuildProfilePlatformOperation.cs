#if UNITY_6000_0_OR_NEWER
using UnityEditor.Build.Profile;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal static class BuildProfilePlatformOperation
    {
        internal static BuildProfileOperationResult Execute()
        {
            var result = new BuildProfileOperationResult { operation = "list-platforms" };
#if UNITY_6000_5_OR_NEWER
            foreach (var platform in BuildProfile.GetInstalledPlatformModules())
            {
                result.platforms.Add(new BuildProfilePlatformInfo
                {
                    displayName = platform.displayName,
                    platformId = platform.platformGuid.ToString()
                });
            }

            result.totalCount = result.platforms.Count;
            result.success = true;
            result.message = $"Found {result.totalCount} installed build profile platforms";
#else
            result.success = false;
            result.message = "Build profile platform discovery requires Unity 6.5 or newer.";
#endif
            return result;
        }
    }
}
#endif
