using System;
using System.IO;
using System.Reflection;
using UnityEditor;

namespace BWS.Editor.ClaudeCodeBridge
{
    public partial class LocalizationCommandHandler
    {
        private const string CsvTypeName = "UnityEditor.Localization.Plugins.CSV.Csv";
        private const string XliffTypeName = "UnityEditor.Localization.Plugins.XLIFF.Xliff";

        private static LocalizationResult ExportCsv(string operation, LocalizationParams p)
        {
            Type editorSettingsType = FindType(EditorSettingsTypeName);
            Type csvType = FindType(CsvTypeName);
            if (editorSettingsType == null || csvType == null) return Unavailable(operation);
            if (!ValidateExportParams(p, out LocalizationResult error, operation)) return error;

            object collection = FindCollection(editorSettingsType, p.tableCollectionName);
            if (collection == null)
                return Fail(operation, $"Table collection not found: {p.tableCollectionName}");

            try
            {
                using var writer = new StreamWriter(p.filePath, false);
                object[] args = { writer, collection, null };
                MethodInfo method = FindMethodByParamCount(csvType, "Export", args.Length);
                if (method == null)
                    return Fail(operation, "Could not resolve Csv.Export(TextWriter, "
                        + "StringTableCollection, ITaskReporter) overload.");
                method.Invoke(null, args);
            }
            catch (Exception ex)
            {
                return Fail(operation, $"CSV export failed: {ex.Message}");
            }

            var result = BaseResult(operation, editorSettingsType);
            result.table = BuildTableInfo(collection, p.tableCollectionName);
            result.message = $"Exported {p.tableCollectionName} to {p.filePath}";
            return result;
        }

        private static LocalizationResult ImportCsv(string operation, LocalizationParams p)
        {
            Type editorSettingsType = FindType(EditorSettingsTypeName);
            Type csvType = FindType(CsvTypeName);
            if (editorSettingsType == null || csvType == null) return Unavailable(operation);
            if (!ValidateImportParams(p, out LocalizationResult error, operation)) return error;

            object collection = FindCollection(editorSettingsType, p.tableCollectionName);
            if (collection == null)
                return Fail(operation, $"Table collection not found: {p.tableCollectionName}");

            try
            {
                using var reader = new StreamReader(p.filePath);
                object[] args = { reader, collection, true, null, true };
                MethodInfo method = FindMethodByParamCount(csvType, "ImportInto", args.Length);
                if (method == null)
                    return Fail(operation, "Could not resolve Csv.ImportInto(TextReader, "
                        + "StringTableCollection, bool, ITaskReporter, bool) overload.");
                method.Invoke(null, args);
            }
            catch (Exception ex)
            {
                return Fail(operation, $"CSV import failed: {ex.Message}");
            }

            AssetDatabase.SaveAssets();
            var result = BaseResult(operation, editorSettingsType);
            result.table = BuildTableInfo(collection, p.tableCollectionName);
            result.message = $"Imported {p.filePath} into {p.tableCollectionName}";
            return result;
        }

        private static LocalizationResult ExportXliff(string operation, LocalizationParams p)
        {
            Type editorSettingsType = FindType(EditorSettingsTypeName);
            Type xliffType = FindType(XliffTypeName);
            if (editorSettingsType == null || xliffType == null) return Unavailable(operation);
            if (!ValidateExportParams(p, out LocalizationResult error, operation)) return error;

            object collection = FindCollection(editorSettingsType, p.tableCollectionName);
            if (collection == null)
                return Fail(operation, $"Table collection not found: {p.tableCollectionName}");

            // NOTE: Xliff.CreateDocument / Export overload parameter shapes could not be
            // confirmed against package source in this environment (no live Unity Editor,
            // no cached com.unity.localization source on disk). Only method *names* were
            // verified, not signatures. This resolves the best-effort 2-arg CreateDocument
            // overload (collection, locale) and writes the resulting document with
            // File.WriteAllText via the document's ToString()/Xliff XML — if the real
            // overload differs, MethodInfo lookup returns null and this fails gracefully
            // via the Fail() path rather than throwing past the handler.
            try
            {
                object selectedLocale = GetStaticValue(FindType(SettingsTypeName), "SelectedLocale");
                object document = InvokeStatic(
                    xliffType, "CreateDocument", new object[] { collection, selectedLocale });
                if (document == null)
                    return Fail(operation,
                        "XLIFF export is unavailable: could not resolve Xliff.CreateDocument "
                        + "overload via reflection (unverified signature).");

                File.WriteAllText(p.filePath, document.ToString());
            }
            catch (Exception ex)
            {
                return Fail(operation, $"XLIFF export failed: {ex.Message}");
            }

            var result = BaseResult(operation, editorSettingsType);
            result.table = BuildTableInfo(collection, p.tableCollectionName);
            result.message = $"Exported {p.tableCollectionName} to {p.filePath}";
            return result;
        }

        private static LocalizationResult ImportXliff(string operation, LocalizationParams p)
        {
            Type editorSettingsType = FindType(EditorSettingsTypeName);
            Type xliffType = FindType(XliffTypeName);
            if (editorSettingsType == null || xliffType == null) return Unavailable(operation);
            if (!ValidateImportParams(p, out LocalizationResult error, operation)) return error;

            object collection = FindCollection(editorSettingsType, p.tableCollectionName);
            if (collection == null)
                return Fail(operation, $"Table collection not found: {p.tableCollectionName}");

            // NOTE: Xliff.ImportFileIntoCollection's exact parameter shape could not be
            // confirmed against package source in this environment. Only the method name
            // was verified. This resolves the best-effort 2-arg overload (filePath,
            // collection); if the real signature differs, MethodInfo lookup returns null
            // and the operation fails gracefully via Fail() rather than throwing.
            try
            {
                object[] args = { p.filePath, collection };
                MethodInfo method = FindMethodByParamCount(xliffType, "ImportFileIntoCollection", args.Length);
                if (method == null)
                    return Fail(operation,
                        "XLIFF import is unavailable: could not resolve "
                        + "Xliff.ImportFileIntoCollection overload via reflection "
                        + "(unverified signature).");
                method.Invoke(null, args);
            }
            catch (Exception ex)
            {
                return Fail(operation, $"XLIFF import failed: {ex.Message}");
            }

            AssetDatabase.SaveAssets();
            var result = BaseResult(operation, editorSettingsType);
            result.table = BuildTableInfo(collection, p.tableCollectionName);
            result.message = $"Imported {p.filePath} into {p.tableCollectionName}";
            return result;
        }

        private static bool ValidateExportParams(
            LocalizationParams p, out LocalizationResult error, string operation)
        {
            error = null;
            if (!string.IsNullOrEmpty(p.tableCollectionName) && !string.IsNullOrEmpty(p.filePath))
                return true;
            error = Fail(operation, "tableCollectionName and filePath are required.");
            return false;
        }

        private static bool ValidateImportParams(
            LocalizationParams p, out LocalizationResult error, string operation)
        {
            error = null;
            if (string.IsNullOrEmpty(p.tableCollectionName) || string.IsNullOrEmpty(p.filePath))
            {
                error = Fail(operation, "tableCollectionName and filePath are required.");
                return false;
            }
            if (!File.Exists(p.filePath))
            {
                error = Fail(operation, $"File not found: {p.filePath}");
                return false;
            }
            return true;
        }

        private static MethodInfo FindMethodByParamCount(Type type, string name, int argCount)
        {
            const BindingFlags flags = BindingFlags.Public | BindingFlags.Static;
            return FindMethod(type, name, flags, argCount);
        }
    }
}
