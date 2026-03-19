# Animator Operation Command Handler - Activation Instructions

## Quick Start

After Unity imports this file, activate the handler:

### Step 1: Uncomment Registration

Open: `Assets/Scripts/Editor/ClaudeCodeBridge/ClaudeUnityBridge.cs`

Find line ~86 and uncomment:
```csharp
// RegisterHandler(new AnimatorOperationCommandHandler()); // TODO: Enable after Unity import
```

Change to:
```csharp
RegisterHandler(new AnimatorOperationCommandHandler());
```

### Step 2: Verify

1. Unity will automatically recompile
2. Go to **Tools → Claude Code Bridge → Show Status**
3. Check console - you should see `animator-operation` in the registered handlers list

### Step 3: Test

Run the test script:
```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\projects\rpg.game\.claude\unity\test-animator-operation.ps1"
```

## What This Handler Does

Provides 22 operations for complete programmatic control over Animator Controllers:

- **Controller**: Create, get info
- **Layers**: Add, configure weight/blending, delete, list
- **States**: Add, set motion/speed, set default, delete, list
- **Transitions**: Add, configure duration/conditions, delete, list
- **Parameters**: Add, set defaults, delete, list

## Documentation

See complete guide: `.claude/unity/ANIMATOR_OPERATION_GUIDE.md`

## Example Usage

```powershell
# Create controller
$params = @{
    operation = "create-controller"
    controllerPath = "Assets/Animations/PlayerController.controller"
} | ConvertTo-Json

# Add parameter
$params = @{
    operation = "add-parameter"
    controllerPath = "Assets/Animations/PlayerController.controller"
    parameterName = "Speed"
    parameterType = "Float"
    defaultValue = "0.0"
} | ConvertTo-Json

# Add state
$params = @{
    operation = "add-state"
    controllerPath = "Assets/Animations/PlayerController.controller"
    layerName = "Base Layer"
    stateName = "Idle"
} | ConvertTo-Json
```

## Supported Operations

1. create-controller
2. get-controller-info
3. add-layer
4. set-layer-weight
5. set-layer-blending
6. delete-layer
7. get-layers
8. add-state
9. set-state-motion
10. set-state-speed
11. set-default-state
12. delete-state
13. get-states
14. add-transition
15. set-transition-duration
16. set-transition-conditions
17. delete-transition
18. get-transitions
19. add-parameter
20. set-parameter-default
21. delete-parameter
22. get-parameters
