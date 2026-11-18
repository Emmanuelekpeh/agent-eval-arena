# consolidate_codebase.ps1
# Script to consolidate the AI Battle Arena codebase by moving files to their
# canonical locations and removing deprecated modules.

# ANSI color codes for pretty output (also works in modern PowerShell)
$GREEN = "`e[0;32m"
$YELLOW = "`e[0;33m"
$RED = "`e[0;31m"
$BLUE = "`e[0;34m"
$CYAN = "`e[0;36m"
$NC = "`e[0m"  # No Color

# Get the project root (directory containing this script's parent)
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

# Create timestamp for backup
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_DIR = Join-Path $PROJECT_ROOT "backup_$TIMESTAMP"

Write-Host "${CYAN}[consolidate]${NC} Starting codebase consolidation"
Write-Host "${CYAN}[consolidate]${NC} Project root: ${YELLOW}$PROJECT_ROOT${NC}"
Write-Host "${CYAN}[consolidate]${NC} Backup directory: ${YELLOW}$BACKUP_DIR${NC}"

# Create backup directory
New-Item -ItemType Directory -Force -Path $BACKUP_DIR | Out-Null

# Function to create directory if it does not exist
function Create-DirectoryIfNotExists {
    param(
        [string]$Path
    )
    if (-not (Test-Path -Path $Path -PathType Container)) {
        Write-Host "${CYAN}[consolidate]${NC} Creating directory: ${YELLOW}$Path${NC}"
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

# Function to move a file with backup
function Move-FileWithBackup {
    param(
        [string]$SourceFile,
        [string]$TargetFile
    )
    
    # Check if source file exists
    if (-not (Test-Path -Path $SourceFile -PathType Leaf)) {
        Write-Host "${RED}[consolidate] Source file does not exist: ${SourceFile}${NC}"
        return $false
    }
    
    # Create target directory if it doesn't exist
    $TargetDir = Split-Path -Parent $TargetFile
    Create-DirectoryIfNotExists -Path $TargetDir
    
    # Backup the target file if it exists
    if (Test-Path -Path $TargetFile -PathType Leaf) {
        $RelativePath = $TargetFile.Replace("$PROJECT_ROOT\", "").Replace("/", "\")
        $BackupPath = Join-Path $BACKUP_DIR $RelativePath
        $BackupDir = Split-Path -Parent $BackupPath
        Create-DirectoryIfNotExists -Path $BackupDir
        Copy-Item -Path $TargetFile -Destination $BackupPath -Force
        Write-Host "${BLUE}[consolidate]${NC} Backed up: ${YELLOW}$TargetFile${NC} to ${YELLOW}$BackupPath${NC}"
    }
    
    # Move the file
    Write-Host "${CYAN}[consolidate]${NC} Moving: ${YELLOW}$SourceFile${NC} to ${YELLOW}$TargetFile${NC}"
    Copy-Item -Path $SourceFile -Destination $TargetFile -Force
    Remove-Item -Path $SourceFile -Force
    
    return $true
}

# Function to handle deprecated files
function Remove-DeprecatedFile {
    param(
        [string]$FilePath
    )
    
    # Check if file exists
    if (-not (Test-Path -Path $FilePath -PathType Leaf)) {
        Write-Host "${YELLOW}[consolidate] Deprecated file already removed: ${FilePath}${NC}"
        return $true
    }
    
    # Create backup
    $RelativePath = $FilePath.Replace("$PROJECT_ROOT\", "").Replace("/", "\")
    $BackupPath = Join-Path $BACKUP_DIR $RelativePath
    $BackupDir = Split-Path -Parent $BackupPath
    Create-DirectoryIfNotExists -Path $BackupDir
    Copy-Item -Path $FilePath -Destination $BackupPath -Force
    
    # Remove the file
    Write-Host "${RED}[consolidate]${NC} Removing deprecated file: ${YELLOW}$FilePath${NC} (backed up to ${YELLOW}$BackupPath${NC})"
    Remove-Item -Path $FilePath -Force
    
    return $true
}

# Create necessary directories
Write-Host "${CYAN}[consolidate]${NC} Creating canonical directory structure"
Create-DirectoryIfNotExists -Path (Join-Path $PROJECT_ROOT "systems\core")
Create-DirectoryIfNotExists -Path (Join-Path $PROJECT_ROOT "systems\agents")
Create-DirectoryIfNotExists -Path (Join-Path $PROJECT_ROOT "systems\environment")
Create-DirectoryIfNotExists -Path (Join-Path $PROJECT_ROOT "systems\combat")
Create-DirectoryIfNotExists -Path (Join-Path $PROJECT_ROOT "systems\learning")
Create-DirectoryIfNotExists -Path (Join-Path $PROJECT_ROOT "systems\visualization")
Create-DirectoryIfNotExists -Path (Join-Path $PROJECT_ROOT "agents\basic")
Create-DirectoryIfNotExists -Path (Join-Path $PROJECT_ROOT "agents\advanced")
Create-DirectoryIfNotExists -Path (Join-Path $PROJECT_ROOT "utils")
Create-DirectoryIfNotExists -Path (Join-Path $PROJECT_ROOT "tests")

# Create __init__.py files if they don't exist
Write-Host "${CYAN}[consolidate]${NC} Ensuring all packages have __init__.py files"
$directories = Get-ChildItem -Path $PROJECT_ROOT -Directory -Recurse | 
               Where-Object { $_.FullName -notlike "*\.*" -and $_.FullName -notlike "*\venv*" -and $_.FullName -notlike "*\backup*" }

foreach ($dir in $directories) {
    $initFile = Join-Path $dir.FullName "__init__.py"
    if (-not (Test-Path -Path $initFile -PathType Leaf)) {
        Write-Host "${BLUE}[consolidate]${NC} Creating __init__.py in ${YELLOW}$($dir.FullName)${NC}"
        New-Item -ItemType File -Path $initFile -Force | Out-Null
    }
}

# Move core system files
Write-Host "${CYAN}[consolidate]${NC} Moving core system files"
$sourcePath = Join-Path $PROJECT_ROOT "systems\base_system.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\core\base_system.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

$sourcePath = Join-Path $PROJECT_ROOT "systems\event_system.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\core\event_system.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

$sourcePath = Join-Path $PROJECT_ROOT "systems\system_manager.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\core\system_manager.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

# Move agent-related system files
Write-Host "${CYAN}[consolidate]${NC} Moving agent system files"
$sourcePath = Join-Path $PROJECT_ROOT "systems\agent_system.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\agents\agent_system.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

$sourcePath = Join-Path $PROJECT_ROOT "systems\team_system.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\agents\team_system.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

$sourcePath = Join-Path $PROJECT_ROOT "systems\formation_system.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\agents\formation_system.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

$sourcePath = Join-Path $PROJECT_ROOT "systems\relationship_system.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\agents\relationship_system.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

$sourcePath = Join-Path $PROJECT_ROOT "systems\communication_system.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\agents\communication_system.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

# Move environment-related system files
Write-Host "${CYAN}[consolidate]${NC} Moving environment system files"
$sourcePath = Join-Path $PROJECT_ROOT "systems\terrain_system.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\environment\terrain_system.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

$sourcePath = Join-Path $PROJECT_ROOT "systems\resource_system.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\environment\resource_system.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

$sourcePath = Join-Path $PROJECT_ROOT "systems\resource_sharing.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\environment\resource_sharing.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

# Move combat-related system files
Write-Host "${CYAN}[consolidate]${NC} Moving combat system files"
$sourcePath = Join-Path $PROJECT_ROOT "systems\combat_system.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\combat\combat_system.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

$sourcePath = Join-Path $PROJECT_ROOT "systems\battle_mechanics.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\combat\battle_mechanics.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

$sourcePath = Join-Path $PROJECT_ROOT "systems\combat_mechanics.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\combat\combat_mechanics.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

# Move learning-related system files
Write-Host "${CYAN}[consolidate]${NC} Moving learning system files"
$sourcePath = Join-Path $PROJECT_ROOT "systems\learning_system.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\learning\learning_system.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

$sourcePath = Join-Path $PROJECT_ROOT "systems\behavior_learning.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\learning\behavior_learning.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

# Move visualization-related system files
Write-Host "${CYAN}[consolidate]${NC} Moving visualization system files"
$sourcePath = Join-Path $PROJECT_ROOT "systems\visualization_system.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\visualization\visualization_system.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

$sourcePath = Join-Path $PROJECT_ROOT "systems\rendering.py"
$targetPath = Join-Path $PROJECT_ROOT "systems\visualization\rendering.py"
if (Test-Path -Path $sourcePath -PathType Leaf) {
    Move-FileWithBackup -SourceFile $sourcePath -TargetFile $targetPath
}

# Handle deprecated modules
Write-Host "${CYAN}[consolidate]${NC} Removing deprecated modules"
$filePath = Join-Path $PROJECT_ROOT "systems\deprecated_system.py"
if (Test-Path -Path $filePath -PathType Leaf) {
    Remove-DeprecatedFile -FilePath $filePath
}

$filePath = Join-Path $PROJECT_ROOT "systems\old_formation.py"
if (Test-Path -Path $filePath -PathType Leaf) {
    Remove-DeprecatedFile -FilePath $filePath
}

$filePath = Join-Path $PROJECT_ROOT "agents\deprecated_agent.py"
if (Test-Path -Path $filePath -PathType Leaf) {
    Remove-DeprecatedFile -FilePath $filePath
}

# Clean up empty directories
Write-Host "${CYAN}[consolidate]${NC} Cleaning up empty directories"
$emptyDirs = Get-ChildItem -Path $PROJECT_ROOT -Directory -Recurse | 
             Where-Object { $_.FullName -notlike "*\.*" -and $_.FullName -notlike "*\venv*" -and $_.FullName -notlike "*\backup*" } |
             Where-Object { (Get-ChildItem -Path $_.FullName -Recurse -Force).Count -eq 0 }

foreach ($dir in $emptyDirs) {
    Write-Host "${YELLOW}[consolidate]${NC} Removing empty directory: ${YELLOW}$($dir.FullName)${NC}"
    Remove-Item -Path $dir.FullName -Force
}

# Final message
Write-Host "`n${GREEN}===============================================${NC}"
Write-Host "${GREEN}Codebase consolidation completed successfully!${NC}"
Write-Host "${GREEN}===============================================${NC}"
Write-Host "Backup saved to: ${YELLOW}$BACKUP_DIR${NC}"
Write-Host "`n${YELLOW}Next steps:${NC}"
Write-Host "1. Check the results and ensure everything is in place"
Write-Host "2. Run ${CYAN}python scripts/update_imports.py${NC} to fix import statements"
Write-Host "3. Update any references in documentation`n" 