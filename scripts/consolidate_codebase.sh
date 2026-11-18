#!/bin/bash
# consolidate_codebase.sh
# Script to consolidate the AI Battle Arena codebase by moving files to their
# canonical locations and removing deprecated modules.

set -e  # Exit on error

# ANSI color codes for pretty output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'  # No Color

# Get the project root (directory containing this script's parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Create timestamp for backup
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="$PROJECT_ROOT/backup_$TIMESTAMP"

echo -e "${CYAN}[consolidate]${NC} Starting codebase consolidation"
echo -e "${CYAN}[consolidate]${NC} Project root: ${YELLOW}$PROJECT_ROOT${NC}"
echo -e "${CYAN}[consolidate]${NC} Backup directory: ${YELLOW}$BACKUP_DIR${NC}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Function to create directory if it does not exist
create_dir_if_not_exists() {
    if [ ! -d "$1" ]; then
        echo -e "${CYAN}[consolidate]${NC} Creating directory: ${YELLOW}$1${NC}"
        mkdir -p "$1"
    fi
}

# Function to move a file with backup
move_file() {
    local source_file="$1"
    local target_file="$2"
    
    # Check if source file exists
    if [ ! -f "$source_file" ]; then
        echo -e "${RED}[consolidate] Source file does not exist: ${source_file}${NC}"
        return 1
    fi
    
    # Create target directory if it doesn't exist
    local target_dir=$(dirname "$target_file")
    create_dir_if_not_exists "$target_dir"
    
    # Backup the target file if it exists
    if [ -f "$target_file" ]; then
        local backup_path="$BACKUP_DIR/$(echo "$target_file" | sed "s|$PROJECT_ROOT/||")"
        local backup_dir=$(dirname "$backup_path")
        create_dir_if_not_exists "$backup_dir"
        cp "$target_file" "$backup_path"
        echo -e "${BLUE}[consolidate]${NC} Backed up: ${YELLOW}$target_file${NC} to ${YELLOW}$backup_path${NC}"
    fi
    
    # Move the file
    echo -e "${CYAN}[consolidate]${NC} Moving: ${YELLOW}$source_file${NC} to ${YELLOW}$target_file${NC}"
    cp "$source_file" "$target_file" && rm "$source_file"
    
    return 0
}

# Function to handle deprecated files
remove_deprecated() {
    local file_path="$1"
    
    # Check if file exists
    if [ ! -f "$file_path" ]; then
        echo -e "${YELLOW}[consolidate] Deprecated file already removed: ${file_path}${NC}"
        return 0
    fi
    
    # Create backup
    local backup_path="$BACKUP_DIR/$(echo "$file_path" | sed "s|$PROJECT_ROOT/||")"
    local backup_dir=$(dirname "$backup_path")
    create_dir_if_not_exists "$backup_dir"
    cp "$file_path" "$backup_path"
    
    # Remove the file
    echo -e "${RED}[consolidate]${NC} Removing deprecated file: ${YELLOW}$file_path${NC} (backed up to ${YELLOW}$backup_path${NC})"
    rm "$file_path"
    
    return 0
}

# Create necessary directories
echo -e "${CYAN}[consolidate]${NC} Creating canonical directory structure"
create_dir_if_not_exists "$PROJECT_ROOT/systems/core"
create_dir_if_not_exists "$PROJECT_ROOT/systems/agents"
create_dir_if_not_exists "$PROJECT_ROOT/systems/environment"
create_dir_if_not_exists "$PROJECT_ROOT/systems/combat"
create_dir_if_not_exists "$PROJECT_ROOT/systems/learning"
create_dir_if_not_exists "$PROJECT_ROOT/systems/visualization"
create_dir_if_not_exists "$PROJECT_ROOT/agents/basic"
create_dir_if_not_exists "$PROJECT_ROOT/agents/advanced"
create_dir_if_not_exists "$PROJECT_ROOT/utils"
create_dir_if_not_exists "$PROJECT_ROOT/tests"

# Create __init__.py files if they don't exist
echo -e "${CYAN}[consolidate]${NC} Ensuring all packages have __init__.py files"
for dir in $(find "$PROJECT_ROOT" -type d -not -path "*/\.*" -not -path "*/venv*" -not -path "*/backup*"); do
    if [[ "$dir" == *"$PROJECT_ROOT"* ]]; then
        if [ ! -f "$dir/__init__.py" ]; then
            echo -e "${BLUE}[consolidate]${NC} Creating __init__.py in ${YELLOW}$dir${NC}"
            touch "$dir/__init__.py"
        fi
    fi
done

# Move core system files
echo -e "${CYAN}[consolidate]${NC} Moving core system files"
move_file "$PROJECT_ROOT/systems/base_system.py" "$PROJECT_ROOT/systems/core/base_system.py" || true
move_file "$PROJECT_ROOT/systems/event_system.py" "$PROJECT_ROOT/systems/core/event_system.py" || true
move_file "$PROJECT_ROOT/systems/system_manager.py" "$PROJECT_ROOT/systems/core/system_manager.py" || true

# Move agent-related system files
echo -e "${CYAN}[consolidate]${NC} Moving agent system files"
move_file "$PROJECT_ROOT/systems/agent_system.py" "$PROJECT_ROOT/systems/agents/agent_system.py" || true
move_file "$PROJECT_ROOT/systems/team_system.py" "$PROJECT_ROOT/systems/agents/team_system.py" || true
move_file "$PROJECT_ROOT/systems/formation_system.py" "$PROJECT_ROOT/systems/agents/formation_system.py" || true
move_file "$PROJECT_ROOT/systems/relationship_system.py" "$PROJECT_ROOT/systems/agents/relationship_system.py" || true
move_file "$PROJECT_ROOT/systems/communication_system.py" "$PROJECT_ROOT/systems/agents/communication_system.py" || true

# Move environment-related system files
echo -e "${CYAN}[consolidate]${NC} Moving environment system files"
move_file "$PROJECT_ROOT/systems/terrain_system.py" "$PROJECT_ROOT/systems/environment/terrain_system.py" || true
move_file "$PROJECT_ROOT/systems/resource_system.py" "$PROJECT_ROOT/systems/environment/resource_system.py" || true
move_file "$PROJECT_ROOT/systems/resource_sharing.py" "$PROJECT_ROOT/systems/environment/resource_sharing.py" || true

# Move combat-related system files
echo -e "${CYAN}[consolidate]${NC} Moving combat system files"
move_file "$PROJECT_ROOT/systems/combat_system.py" "$PROJECT_ROOT/systems/combat/combat_system.py" || true
move_file "$PROJECT_ROOT/systems/battle_mechanics.py" "$PROJECT_ROOT/systems/combat/battle_mechanics.py" || true
move_file "$PROJECT_ROOT/systems/combat_mechanics.py" "$PROJECT_ROOT/systems/combat/combat_mechanics.py" || true

# Move learning-related system files
echo -e "${CYAN}[consolidate]${NC} Moving learning system files"
move_file "$PROJECT_ROOT/systems/learning_system.py" "$PROJECT_ROOT/systems/learning/learning_system.py" || true
move_file "$PROJECT_ROOT/systems/behavior_learning.py" "$PROJECT_ROOT/systems/learning/behavior_learning.py" || true

# Move visualization-related system files
echo -e "${CYAN}[consolidate]${NC} Moving visualization system files"
move_file "$PROJECT_ROOT/systems/visualization_system.py" "$PROJECT_ROOT/systems/visualization/visualization_system.py" || true
move_file "$PROJECT_ROOT/systems/rendering.py" "$PROJECT_ROOT/systems/visualization/rendering.py" || true

# Handle deprecated modules
echo -e "${CYAN}[consolidate]${NC} Removing deprecated modules"
remove_deprecated "$PROJECT_ROOT/systems/deprecated_system.py" || true
remove_deprecated "$PROJECT_ROOT/systems/old_formation.py" || true
remove_deprecated "$PROJECT_ROOT/agents/deprecated_agent.py" || true

# Clean up empty directories
echo -e "${CYAN}[consolidate]${NC} Cleaning up empty directories"
find "$PROJECT_ROOT" -type d -empty -not -path "*/\.*" -not -path "*/venv*" -not -path "*/backup*" -delete

# Final message
echo -e "\n${GREEN}===============================================${NC}"
echo -e "${GREEN}Codebase consolidation completed successfully!${NC}"
echo -e "${GREEN}===============================================${NC}"
echo -e "Backup saved to: ${YELLOW}$BACKUP_DIR${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo -e "1. Check the results and ensure everything is in place"
echo -e "2. Run ${CYAN}python scripts/update_imports.py${NC} to fix import statements"
echo -e "3. Update any references in documentation\n" 