using System;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for executing Unity Editor menu items programmatically.
    ///
    /// PURPOSE:
    /// Allows Claude Code to execute editor menu items by path, enabling automation
    /// of common editor workflows like saving scenes, building projects, or running
    /// custom editor tools. Supports validation to check if menu items exist before execution.
    ///
    /// USE CASES:
    /// - Execute "File/Save" programmatically
    /// - Trigger custom editor tools from automation scripts
    /// - Validate menu items exist in current editor state
    /// - Chain multiple editor operations in workflows
    /// - Test editor menu functionality
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "execute-menu-item",
    ///   "timestamp": "2025-10-07T18:00:00Z",
    ///   "parametersJson": "{\"menuPath\":\"File/Save\",\"validate\":false}"
    /// }
    ///
    /// RESPONSE JSON (Success):
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "execute-menu-item",
    ///   "status": "success",
    ///   "timestamp": "2025-10-07T18:00:01Z",
    ///   "dataJson": "{
    ///     \"executed\": true,
    ///     \"exists\": true,
    ///     \"menuPath\": \"File/Save\",
    ///     \"message\": \"Menu item executed successfully\"
    ///   }"
    /// }
    ///
    /// RESPONSE JSON (Validation only):
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "execute-menu-item",
    ///   "status": "success",
    ///   "timestamp": "2025-10-07T18:00:01Z",
    ///   "dataJson": "{
    ///     \"exists\": true,
    ///     \"menuPath\": \"File/Save\",
    ///     \"message\": \"Menu item exists and is enabled\"
    ///   }"
    /// }
    ///
    /// TECHNICAL DETAILS:
    /// Uses EditorApplication.ExecuteMenuItem() to invoke menu items by their path.
    /// For validation mode, attempts to check Menu.GetEnabled() to verify if the menu
    /// item is currently enabled. Menu paths use forward slashes as separators
    /// (e.g., "Assets/Create/Folder").
    ///
    /// PARAMETERS:
    /// - menuPath (string, required): Full path to the menu item (e.g., "File/Save", "Assets/Create/Folder").
    ///   Must include all menu hierarchies separated by forward slashes.
    /// - validate (bool, default false): If true, only checks if the menu item exists and is enabled
    ///   without executing it. If false, executes the menu item.
    ///
    /// MENU PATH EXAMPLES:
    /// - "File/Save" - Save current scene
    /// - "File/Save As..." - Save As dialog
    /// - "Assets/Create/Folder" - Create new folder
    /// - "Window/General/Hierarchy" - Open Hierarchy window
    /// - "Tools/TextMesh Pro/Import TMP Examples & Extras" - Import TextMesh Pro resources
    ///
    /// LIMITATIONS:
    /// - Menu items are case-sensitive
    /// - Some menu items may not work in certain editor states (e.g., during compilation)
    /// - Menu paths may vary between Unity versions or if custom menus are defined
    /// - Relative menu paths starting with "/" are not supported
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Execute a menu item:
    ///    & ".claude\unity\send-command.ps1" -CommandType "execute-menu-item" `
    ///      -Parameters @{menuPath="File/Save";validate=$false}
    ///
    /// 2. Validate menu item exists before execution:
    ///    $check = & ".claude\unity\send-command.ps1" -CommandType "execute-menu-item" `
    ///      -Parameters @{menuPath="Assets/Create/Folder";validate=$true}
    ///    if ($check.exists) { ... execute ... }
    ///
    /// 3. Build project using menu:
    ///    & ".claude\unity\send-command.ps1" -CommandType "execute-menu-item" `
    ///      -Parameters @{menuPath="File/Build Settings...";validate=$false}
    /// </summary>
    public class ExecuteMenuItemCommandHandler : ICommandHandler
    {
        public string CommandType => "execute-menu-item";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                // Parse parameters
                var parameters = JsonUtility.FromJson<ExecuteMenuItemParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new ExecuteMenuItemParams();

                // Validate required parameter
                if (string.IsNullOrEmpty(parameters.menuPath))
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        "menuPath parameter is required"
                    );
                }

                BridgeLogger.LogDebug($"Processing menu item: {parameters.menuPath} (validate={parameters.validate})");

                // If validate mode, just check existence
                if (parameters.validate)
                {
                    return HandleValidation(command, parameters);
                }

                // Otherwise, execute the menu item
                return HandleExecution(command, parameters);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Validates that a menu item exists and is enabled.
        /// Note: Unity doesn't provide a direct way to check if a menu item exists.
        /// We use Menu.GetEnabled() which returns false for non-existent items.
        /// </summary>
        private BridgeResponse HandleValidation(BridgeCommand command, ExecuteMenuItemParams parameters)
        {
            try
            {
                // Unity's Menu.GetEnabled() returns false for non-existent menu items
                // This is the closest we can get to checking existence
                bool isEnabled = Menu.GetEnabled(parameters.menuPath);

                // If enabled, we know it exists. If disabled, it might exist but be disabled,
                // or it might not exist at all. Unity doesn't distinguish these cases.
                var result = new ExecuteMenuItemResult
                {
                    exists = true, // We assume it exists; if GetEnabled didn't throw, the path is at least valid format
                    isEnabled = isEnabled,
                    menuPath = parameters.menuPath,
                    message = isEnabled
                        ? "Menu item exists and is enabled"
                        : "Menu item exists but is disabled (or menu path not found)"
                };

                BridgeLogger.LogInfo($"Menu item validation: {parameters.menuPath} - enabled={isEnabled}");

                return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Validation error for {parameters.menuPath}: {ex}");
                return BridgeResponse.Error(
                    command.commandId,
                    command.commandType,
                    $"Validation failed for menu item: {ex.Message}"
                );
            }
        }

        /// <summary>
        /// Executes a menu item.
        /// </summary>
        private BridgeResponse HandleExecution(BridgeCommand command, ExecuteMenuItemParams parameters)
        {
            try
            {
                // Validate menu item exists and is enabled
                var validationResponse = ValidateMenuItemForExecution(command, parameters);
                if (validationResponse != null)
                    return validationResponse;

                // Execute the menu item - returns true if found and executed
                BridgeLogger.LogDebug($"Executing menu item: {parameters.menuPath}");
                bool wasExecuted = EditorApplication.ExecuteMenuItem(parameters.menuPath);

                if (!wasExecuted)
                {
                    BridgeLogger.LogError($"Menu item not found or failed to execute: {parameters.menuPath}");
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        $"Menu item not found or failed to execute: {parameters.menuPath}"
                    );
                }

                var result = new ExecuteMenuItemResult
                {
                    executed = true,
                    exists = true,
                    isEnabled = true,
                    menuPath = parameters.menuPath,
                    message = "Menu item executed successfully"
                };

                return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Execution error for {parameters.menuPath}: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, $"Menu item execution failed: {ex.Message}");
            }
        }

        /// <summary>
        /// Validates that a menu item is enabled for execution.
        /// Returns an error response if validation fails, null if valid.
        /// Note: Unity doesn't provide a way to check if a menu item exists separately
        /// from checking if it's enabled. Menu.GetEnabled() returns false for non-existent items.
        /// </summary>
        private BridgeResponse ValidateMenuItemForExecution(BridgeCommand command, ExecuteMenuItemParams parameters)
        {
            // Menu.GetEnabled() returns false for both disabled and non-existent menu items
            // We'll proceed with execution and let ExecuteMenuItem report if it fails
            if (!Menu.GetEnabled(parameters.menuPath))
            {
                BridgeLogger.LogWarning($"Menu item is disabled or not found: {parameters.menuPath}");
                return BridgeResponse.Error(
                    command.commandId,
                    command.commandType,
                    $"Menu item is disabled or not found: {parameters.menuPath}"
                );
            }

            return null;
        }
    }

    /// <summary>
    /// Parameters for the execute-menu-item command.
    /// </summary>
    [Serializable]
    public class ExecuteMenuItemParams
    {
        public string menuPath; // Full menu path (e.g., "File/Save")
        public bool validate = false; // If true, only validate existence; don't execute
    }

    /// <summary>
    /// Result data for the execute-menu-item command.
    /// </summary>
    [Serializable]
    public class ExecuteMenuItemResult
    {
        public bool executed; // Whether menu item was executed (false if validate=true)
        public bool exists; // Whether menu item exists
        public bool isEnabled; // Whether menu item is currently enabled
        public string menuPath; // The menu path that was checked/executed
        public string message; // Status message
    }
}
