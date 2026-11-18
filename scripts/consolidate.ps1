# AI Battle Arena File Consolidation Script
# This script reorganizes the project files into a more modular structure

# Create directory structure
$directories = @(
    "systems/core",
    "systems/agents",
    "systems/environment",
    "systems/combat",
    "systems/ui",
    "systems/utils",
    "systems/learning"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        Write-Host "Creating directory: $dir"
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Remove deprecated files
$filesToRemove = @(
    "systems/performance.py",
    "systems/base_system.py",
    "config/settings.py",
    "systems/team_mechanics.py",
    "systems/team_formation.py",
    "systems/team_coordinator.py"
)

foreach ($file in $filesToRemove) {
    if (Test-Path $file) {
        Write-Host "Removing deprecated file: $file"
        Remove-Item -Path $file -Force
    }
}

# Move files to their canonical locations
$filesToMove = @(
    @{Source = "systems/system_manager.py"; Destination = "systems/core/"},
    @{Source = "systems/event_system.py"; Destination = "systems/core/"},
    @{Source = "systems/agent_system.py"; Destination = "systems/agents/"},
    @{Source = "systems/team_system.py"; Destination = "systems/agents/"},
    @{Source = "systems/formation_system.py"; Destination = "systems/agents/"},
    @{Source = "systems/terrain_system.py"; Destination = "systems/environment/"},
    @{Source = "systems/resource_system.py"; Destination = "systems/environment/"},
    @{Source = "systems/resource_sharing.py"; Destination = "systems/environment/"},
    @{Source = "systems/combat_system.py"; Destination = "systems/combat/"},
    @{Source = "systems/battle_mechanics.py"; Destination = "systems/combat/"},
    @{Source = "systems/combat_mechanics.py"; Destination = "systems/combat/"},
    @{Source = "systems/learning_system.py"; Destination = "systems/learning/"},
    @{Source = "systems/behavior_learning.py"; Destination = "systems/learning/"},
    @{Source = "systems/relationship_system.py"; Destination = "systems/agents/"},
    @{Source = "systems/communication_system.py"; Destination = "systems/agents/"}
)

foreach ($file in $filesToMove) {
    if (Test-Path $file.Source) {
        Write-Host "Moving $($file.Source) to $($file.Destination)"
        Move-Item -Path $file.Source -Destination $file.Destination -Force
    }
}

# Create __init__.py files in all directories
Get-ChildItem -Path "systems" -Directory -Recurse | ForEach-Object {
    $initFile = Join-Path $_.FullName "__init__.py"
    if (-not (Test-Path $initFile)) {
        Write-Host "Creating $initFile"
        New-Item -ItemType File -Path $initFile -Force | Out-Null
    }
}

# Create __init__.py in systems directory itself if it doesn't exist
$systemsInit = "systems/__init__.py"
if (-not (Test-Path $systemsInit)) {
    Write-Host "Creating $systemsInit"
    New-Item -ItemType File -Path $systemsInit -Force | Out-Null
}

Write-Host "File consolidation complete!"
Write-Host "Remember to update imports in your code. See docs/file_consolidation.md for a migration guide." 