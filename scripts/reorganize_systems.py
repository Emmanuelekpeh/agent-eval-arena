#!/usr/bin/env python3
"""
Reorganize system files according to the new project structure.
This script creates the directory structure, copies files to their new locations,
and updates imports where necessary.
"""

import os
import shutil
import re
from pathlib import Path

# Define the new directory structure
DIRECTORY_STRUCTURE = {
    'systems/core': [
        'system_manager.py',
        'event_system.py',
        'performance_monitor.py',
    ],
    'systems/agents': [
        'agent_system.py',
        'team_system.py',
        'formation_system.py',
        'learning_system.py',
    ],
    'systems/environment': [
        'terrain_system.py',
        'spatial_system.py',
        'resource_system.py',
        'combat_zones.py',
    ],
    'systems/combat': [
        'combat_system.py',
        'weapon_system.py',
        'ability_system.py',
        'battle_mechanics.py',
    ],
    'systems/ui': [
        'visual_feedback.py',
        'analytics.py',
    ],
    'systems/utils': [
        'config_manager.py',
        'quality_manager.py',
    ],
}

# File mapping from old location to new location
FILE_MAPPING = {
    'systems/system_manager.py': 'systems/core/system_manager.py',
    'systems/event_system.py': 'systems/core/event_system.py',
    'systems/performance_monitor.py': 'systems/core/performance_monitor.py',
    'systems/performance.py': 'systems/core/performance.py',
    
    'systems/agent_system.py': 'systems/agents/agent_system.py',
    'systems/agents/team_system.py': 'systems/agents/team_system.py',
    'systems/formation_system.py': 'systems/agents/formation_system.py',
    'systems/team_formation.py': 'systems/agents/team_formation.py',
    'systems/team_coordinator.py': 'systems/agents/team_coordinator.py',
    'systems/team_mechanics.py': 'systems/agents/team_mechanics.py',
    'systems/learning_system.py': 'systems/agents/learning_system.py',
    
    'systems/terrain_system.py': 'systems/environment/terrain_system.py',
    'systems/environment.py': 'systems/environment/environment.py',
    'systems/spatial_system.py': 'systems/environment/spatial_system.py',
    'systems/resource_system.py': 'systems/environment/resource_system.py',
    'systems/combat_zones.py': 'systems/environment/combat_zones.py',
    
    'systems/combat_system.py': 'systems/combat/combat_system.py',
    'systems/battle_mechanics.py': 'systems/combat/battle_mechanics.py',
    'systems/combat_mechanics.py': 'systems/combat/combat_mechanics.py',
    
    'systems/visual_feedback.py': 'systems/ui/visual_feedback.py',
    'systems/analytics.py': 'systems/ui/analytics.py',
    'systems/training_mode.py': 'systems/ui/training_mode.py',
    
    'systems/quality_manager.py': 'systems/utils/quality_manager.py',
    'utils/logging.py': 'systems/utils/logging.py',
    'config.py': 'systems/utils/config.py',
    'config/settings.py': 'systems/utils/settings.py',
}

# Regular expression to find import statements
IMPORT_REGEX = re.compile(r'from\s+(systems|utils)(\.\w+)?\s+import\s+')

def create_directories():
    """Create the new directory structure"""
    for directory in DIRECTORY_STRUCTURE:
        Path(directory).mkdir(parents=True, exist_ok=True)
    print("✅ Created directory structure")

def copy_files():
    """Copy files to their new locations"""
    for old_path, new_path in FILE_MAPPING.items():
        if Path(old_path).exists():
            # Create the destination directory if it doesn't exist
            Path(new_path).parent.mkdir(parents=True, exist_ok=True)
            # Copy the file
            shutil.copy2(old_path, new_path)
            print(f"Copied: {old_path} -> {new_path}")
        else:
            print(f"⚠️ File not found: {old_path}")
    print("✅ Copied files to new locations")

def update_imports():
    """Update import statements in the new files"""
    for new_path in FILE_MAPPING.values():
        if Path(new_path).exists():
            with open(new_path, 'r') as file:
                content = file.read()
            
            # Update import statements
            updated_content = content
            for match in IMPORT_REGEX.finditer(content):
                old_import = match.group(0)
                base_module = match.group(1)
                sub_module = match.group(2) if match.group(2) else ''
                
                # Determine the new import path based on the new file organization
                if base_module == 'systems':
                    # Figure out which submodule this file should import from
                    # This is a simplified approach and might need manual adjustments
                    for dir_name, files in DIRECTORY_STRUCTURE.items():
                        dir_part = dir_name.split('/')[-1]
                        if Path(new_path).name in files:
                            # This file is found in this directory
                            new_import = f'from systems.{dir_part}{sub_module} import '
                            updated_content = updated_content.replace(old_import, new_import)
                            break
                        
            # Write updated content back to the file
            if content != updated_content:
                with open(new_path, 'w') as file:
                    file.write(updated_content)
                print(f"Updated imports in: {new_path}")
    
    print("✅ Updated import statements")

def update_main_file():
    """Update the main.py file to use the new system structure"""
    main_file = 'main.py'
    if Path(main_file).exists():
        with open(main_file, 'r') as file:
            content = file.read()
        
        # Update imports in main.py
        content = content.replace('from systems import BattleRoyaleEnv', 
                                 'from systems.environment import BattleRoyaleEnv')
        content = content.replace('from systems.core.system_manager import system_manager', 
                                 'from systems.core.system_manager import system_manager')
        content = content.replace('from utils.logging import logger',
                                 'from systems.utils.logging import logger')
        
        with open(main_file, 'w') as file:
            file.write(content)
        print(f"✅ Updated {main_file}")
    else:
        print(f"⚠️ File not found: {main_file}")

def main():
    """Run the reorganization process"""
    print("🔄 Starting system reorganization...")
    create_directories()
    copy_files()
    update_imports()
    update_main_file()
    print("✅ System reorganization complete!")
    print("\nNOTE: Manual review of import statements is recommended.")
    print("      Run tests to ensure everything still works correctly.")

if __name__ == "__main__":
    main() 