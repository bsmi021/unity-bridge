using System;
using System.Collections.Generic;

namespace BWS.Editor.ClaudeCodeBridge
{
    [Serializable]
    public class CinemachineParams
    {
        public string operation;
        public string cameraPath;
        public int priority;
        public float fieldOfView = -1f;
        public float orthographicSize = -1f;
        public float nearClipPlane = -1f;
        public float farClipPlane = -1f;
        public float dutch = float.NaN;
        public string followPath;
        public string lookAtPath;
    }

    [Serializable]
    public class CinemachineResult
    {
        public string operation;
        public bool success;
        public string message;
    }

    [Serializable]
    public class CinemachineCameraInfo
    {
        public string path;
        public int priority;
        public bool enabled;
        public bool activeInHierarchy;
    }

    [Serializable]
    public class CinemachineListResult
    {
        public string operation;
        public List<CinemachineCameraInfo> cameras = new List<CinemachineCameraInfo>();
        public bool success;
        public string message;
    }

    [Serializable]
    public class CinemachineCameraInfoResult
    {
        public string operation;
        public string path;
        public int priority;
        public bool enabled;
        public float fieldOfView;
        public float orthographicSize;
        public float nearClipPlane;
        public float farClipPlane;
        public float dutch;
        public string followPath;
        public string lookAtPath;
        public bool success;
        public string message;
    }

    [Serializable]
    public class CinemachineActiveCameraResult
    {
        public string operation;
        public bool hasActiveCamera;
        public string activeCameraName;
        public bool isBlending;
        public string outputCameraName;
        public bool success;
        public string message;
    }
}
