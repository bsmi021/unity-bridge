using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal sealed class ExecuteScriptMutationScope : IDisposable
    {
        private readonly Dictionary<string, UnityEngine.Object> _declaredObjects;
        private readonly Dictionary<string, string> _objectStatesBefore;
        private readonly Dictionary<string, UnityEngine.Object> _observedObjects;
        private readonly ExecuteScriptFileTransaction _files;
        private readonly bool _governed;
        private bool _completed;
        private bool _subscribed;

        public ExecuteScriptMutationReport Report { get; }

        private ExecuteScriptMutationScope(
            ExecuteScriptManifest manifest,
            Dictionary<string, UnityEngine.Object> declaredObjects,
            ExecuteScriptFileTransaction files)
        {
            _governed = manifest.intent == "mutating";
            _declaredObjects = declaredObjects;
            _files = files;
            _objectStatesBefore = SnapshotObjects(declaredObjects);
            _observedObjects = new Dictionary<string, UnityEngine.Object>(StringComparer.Ordinal);
            Report = NewReport(manifest, _governed);
        }

        public static bool TryBegin(
            ExecuteScriptManifest manifest,
            out ExecuteScriptMutationScope scope,
            out string message)
        {
            scope = null;
            message = "";
            if (manifest.intent != "mutating")
            {
                scope = new ExecuteScriptMutationScope(
                    manifest,
                    new Dictionary<string, UnityEngine.Object>(StringComparer.Ordinal),
                    null);
                return true;
            }

            if (!TryResolveObjects(manifest.declaredObjectIds, out var objects, out message))
                return false;
            if (!ExecuteScriptFileTransaction.TryBegin(
                Application.dataPath, manifest.declaredFilePaths, out var files, out message))
            {
                return false;
            }

            return TryStartGovernance(manifest, objects, files, out scope, out message);
        }

        public bool Complete(bool executionSucceeded, out string message)
        {
            message = "";
            if (_completed || !_governed)
            {
                _completed = true;
                return executionSucceeded;
            }

            Unsubscribe();
            var filesObserved = _files.TryCaptureChanges(
                out var fileChanges, out var fileCaptureError);
            Report.changedProjectFiles = fileChanges;
            Report.changedObjects = BuildChangedObjects();
            var violations = FindViolations(fileChanges, fileCaptureError);
            if (executionSucceeded && filesObserved && violations.Count == 0)
            {
                Commit();
                return true;
            }

            RollbackAndVerify(violations, out var rollbackErrors);
            message = BuildFailureMessage(violations, rollbackErrors);
            return false;
        }

        public void Dispose()
        {
            try
            {
                if (!_completed)
                    Complete(false, out _);
            }
            finally
            {
                Unsubscribe();
                _files?.Dispose();
            }
        }

        private static bool TryStartGovernance(
            ExecuteScriptManifest manifest,
            Dictionary<string, UnityEngine.Object> objects,
            ExecuteScriptFileTransaction files,
            out ExecuteScriptMutationScope scope,
            out string message)
        {
            try
            {
                Undo.IncrementCurrentGroup();
                scope = new ExecuteScriptMutationScope(manifest, objects, files);
                scope.Report.undoGroup = Undo.GetCurrentGroup();
                Undo.SetCurrentGroupName(manifest.undoLabel);
                foreach (var value in objects.Values)
                    Undo.RegisterCompleteObjectUndo(value, manifest.undoLabel);
                Undo.postprocessModifications += scope.CaptureModifications;
                scope._subscribed = true;
                message = "";
                return true;
            }
            catch (Exception ex)
            {
                files.Dispose();
                scope = null;
                message = $"Could not begin declared mutation transaction: {ex.Message}";
                return false;
            }
        }

        private static bool TryResolveObjects(
            IEnumerable<string> identifiers,
            out Dictionary<string, UnityEngine.Object> objects,
            out string message)
        {
            objects = new Dictionary<string, UnityEngine.Object>(StringComparer.Ordinal);
            foreach (var identifier in identifiers ?? Array.Empty<string>())
            {
                if (!GlobalObjectId.TryParse(identifier, out var globalId))
                    return Fail($"Invalid declared GlobalObjectId: {identifier}", out message);
                var value = GlobalObjectId.GlobalObjectIdentifierToObjectSlow(globalId);
                if (!value)
                    return Fail($"Declared object could not be resolved: {identifier}", out message);
                objects[identifier] = value;
            }
            message = "";
            return true;
        }

        private UndoPropertyModification[] CaptureModifications(
            UndoPropertyModification[] modifications)
        {
            foreach (var modification in modifications ?? Array.Empty<UndoPropertyModification>())
            {
                var target = modification.currentValue?.target
                    ?? modification.previousValue?.target;
                if (target)
                    _observedObjects[StableObjectId(target)] = target;
            }
            return modifications;
        }

        private List<string> FindViolations(
            List<ExecuteScriptFileChange> fileChanges, string fileCaptureError)
        {
            var violations = new List<string>();
            if (!string.IsNullOrEmpty(fileCaptureError))
                violations.Add(fileCaptureError);
            var undeclaredFiles = _files.FindUndeclared(fileChanges);
            if (undeclaredFiles.Count > 0)
                violations.Add($"Observed undeclared project file changes: {Join(undeclaredFiles)}");
            var undeclaredObjects = _observedObjects.Keys
                .Where(identifier => !_declaredObjects.ContainsKey(identifier))
                .OrderBy(identifier => identifier, StringComparer.Ordinal)
                .ToList();
            if (undeclaredObjects.Count > 0)
                violations.Add($"Observed undeclared Unity object changes: {Join(undeclaredObjects)}");
            return violations;
        }

        private void Commit()
        {
            Undo.CollapseUndoOperations(Report.undoGroup);
            _files.Commit();
            _completed = true;
        }

        private void RollbackAndVerify(
            List<string> violations, out List<string> rollbackErrors)
        {
            rollbackErrors = new List<string>();
            try
            {
                Undo.RevertAllDownToGroup(Report.undoGroup);
            }
            catch (Exception ex)
            {
                rollbackErrors.Add($"Undo rollback failed: {ex.Message}");
            }
            if (!_files.RollbackAndVerify(out var fileError))
                rollbackErrors.Add(fileError);
            VerifyObjects(rollbackErrors);
            Report.reverted = violations.Count == 0 && rollbackErrors.Count == 0;
            _completed = true;
        }

        private void VerifyObjects(List<string> rollbackErrors)
        {
            foreach (var pair in _declaredObjects)
            {
                if (!pair.Value)
                {
                    rollbackErrors.Add($"Declared object disappeared during rollback: {pair.Key}");
                    continue;
                }
                var after = EditorJsonUtility.ToJson(pair.Value);
                if (!_objectStatesBefore.TryGetValue(pair.Key, out var before) || before != after)
                    rollbackErrors.Add($"Declared object was not restored: {pair.Key}");
            }
        }

        private List<ExecuteScriptChangedObject> BuildChangedObjects()
        {
            foreach (var pair in _declaredObjects)
            {
                var after = pair.Value ? EditorJsonUtility.ToJson(pair.Value) : "<missing>";
                if (!_objectStatesBefore.TryGetValue(pair.Key, out var before) || before != after)
                    _observedObjects[pair.Key] = pair.Value;
            }
            return _observedObjects.OrderBy(pair => pair.Key, StringComparer.Ordinal)
                .Where(pair => pair.Value)
                .Select(pair => ToChangedObject(pair.Value))
                .ToList();
        }

        private static ExecuteScriptChangedObject ToChangedObject(UnityEngine.Object value)
        {
            return new ExecuteScriptChangedObject
            {
                objectId = ObjectId(value),
                name = value.name,
                type = value.GetType().FullName,
                assetPath = AssetDatabase.GetAssetPath(value) ?? "",
                globalObjectId = StableObjectId(value),
            };
        }

        private static Dictionary<string, string> SnapshotObjects(
            Dictionary<string, UnityEngine.Object> objects)
        {
            return objects.ToDictionary(
                pair => pair.Key,
                pair => EditorJsonUtility.ToJson(pair.Value),
                StringComparer.Ordinal);
        }

        private static ExecuteScriptMutationReport NewReport(
            ExecuteScriptManifest manifest, bool governed)
        {
            return new ExecuteScriptMutationReport
            {
                governed = governed,
                undoLabel = manifest.undoLabel,
                declaredObjectIds = new List<string>(manifest.declaredObjectIds),
                declaredFilePaths = new List<string>(manifest.declaredFilePaths),
            };
        }

        private static string StableObjectId(UnityEngine.Object value)
        {
            try
            {
                return GlobalObjectId.GetGlobalObjectIdSlow(value).ToString();
            }
            catch
            {
                return "";
            }
        }

        private static string ObjectId(UnityEngine.Object value)
        {
#if UNITY_6000_5_OR_NEWER
            return value.GetEntityId().ToString();
#else
            return value.GetInstanceID().ToString();
#endif
        }

        private static string BuildFailureMessage(
            List<string> violations, List<string> rollbackErrors)
        {
            var parts = new List<string>(violations);
            parts.AddRange(rollbackErrors);
            return string.Join(" ", parts);
        }

        private static string Join(IEnumerable<string> values)
        {
            return string.Join(", ", values);
        }

        private static bool Fail(string error, out string message)
        {
            message = error;
            return false;
        }

        private void Unsubscribe()
        {
            if (!_subscribed)
                return;
            Undo.postprocessModifications -= CaptureModifications;
            _subscribed = false;
        }
    }
}
