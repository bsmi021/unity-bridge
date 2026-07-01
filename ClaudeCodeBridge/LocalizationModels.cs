using System;
using System.Collections.Generic;

namespace BWS.Editor.ClaudeCodeBridge
{
    [Serializable]
    public class LocalizationParams
    {
        public string operation;
        public string localeCode;
        public string tableCollectionName;
        public string key;
        public string value;
        public string filePath;
    }

    [Serializable]
    public class LocalizationResult
    {
        public bool success;
        public string operation;
        public bool packageAvailable;
        public bool apiAvailable;
        public string message;
        public string selectedLocale;
        public List<LocalizationLocaleInfo> locales = new List<LocalizationLocaleInfo>();
        public LocalizationTableInfo table;
        public List<LocalizationEntryInfo> entries = new List<LocalizationEntryInfo>();
    }

    [Serializable]
    public class LocalizationLocaleInfo
    {
        public string code;
        public string name;
    }

    [Serializable]
    public class LocalizationTableInfo
    {
        public string tableCollectionName;
        public int tableCount;
        public int entryCount;
    }

    [Serializable]
    public class LocalizationEntryInfo
    {
        public string key;
        public string value;
        public string localeCode;
    }
}
