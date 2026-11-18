#!/usr/bin/env python3
"""
Consolidation script for AI Battle Arena.

This script identifies and resolves duplicate files according to the
organizational structure defined in docs/system_organization.md.
"""

import os
import shutil
from pathlib import Path
import argparse
import json
import sys

# Define the canonical file locations based on the organization plan
CANONICAL_PATHS = {
    # Base system files
    "base_system.py": "systems/core/base_system.py",
    
    # Performance monitoring
    "performance_monitor.py": "systems/core/performance_monitor.py",
    
    # Formation systems
    "formation_system.py": "systems/agents/formation_system.py",
    
    # Team systems
    "team_system.py": "systems/agents/team_system.py",
    
    # Combat systems
    "combat_system.py": "systems/combat/combat_system.py",
    "combat_mechanics.py": "systems/combat/combat_mechanics.py",
    "battle_mechanics.py": "systems/combat/battle_mechanics.py",
    
    # Resource systems
    "resource_system.py": "systems/environment/resource_system.py",
    
    # Configuration
    "config.py": "systems/utils/config.py",
    "unified_config.py": "config/unified_config.py",
}

# Files that should be removed (deprecated)
DEPRECATED_FILES = [
    "systems/performance.py",
    "systems/base_system.py",  # Replaced by systems/core/base_system.py
    "config/settings.py",      # Replaced by unified_config.py
    "systems/team_mechanics.py",
    "systems/team_formation.py",
    "systems/team_coordinator.py",
]

def find_duplicates():
    """Find duplicates based on filename (not considering path)."""
    file_map = {}
    duplicates = {}
    
    # Walk through the systems directory
    for root, _, files in os.walk("systems"):
        for filename in files:
            if filename.endswith(".py"):
                filepath = os.path.join(root, filename)
                if filename in file_map:
                    if filename not in duplicates:
                        duplicates[filename] = [file_map[filename]]
                    duplicates[filename].append(filepath)
                else:
                    file_map[filename] = filepath
    
    return duplicates

def suggest_consolidation(duplicates):
    """Suggest consolidation actions for duplicates."""
    actions = {
        "move": [],
        "remove": [],
        "rename": []
    }
    
    # Process known deprecated files
    for filepath in DEPRECATED_FILES:
        if os.path.exists(filepath):
            actions["remove"].append({
                "path": filepath,
                "reason": "Deprecated or superseded by newer implementation"
            })
    
    # Process duplicates
    for filename, filepaths in duplicates.items():
        # If we know the canonical path
        if filename in CANONICAL_PATHS:
            canonical = CANONICAL_PATHS[filename]
            for filepath in filepaths:
                if filepath != canonical:
                    if canonical in filepaths:
                        # Canonical path exists, remove the duplicate
                        actions["remove"].append({
                            "path": filepath,
                            "reason": f"Duplicate of canonical path {canonical}"
                        })
                    else:
                        # Canonical path doesn't exist, move the file
                        actions["move"].append({
                            "from": filepath,
                            "to": canonical,
                            "reason": "Moving to canonical path"
                        })
        else:
            # We don't know the canonical path, suggest manual review
            actions["rename"].append({
                "files": filepaths,
                "reason": "Multiple files with same name but unknown canonical path"
            })
    
    return actions

def execute_actions(actions, dry_run=True):
    """Execute or print the suggested actions."""
    # Execute remove actions
    for action in actions["remove"]:
        if dry_run:
            print(f"Would remove: {action['path']} - {action['reason']}")
        else:
            try:
                os.remove(action["path"])
                print(f"Removed: {action['path']}")
            except Exception as e:
                print(f"Error removing {action['path']}: {str(e)}")
    
    # Execute move actions
    for action in actions["move"]:
        if dry_run:
            print(f"Would move: {action['from']} -> {action['to']} - {action['reason']}")
        else:
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(action["to"]), exist_ok=True)
                shutil.move(action["from"], action["to"])
                print(f"Moved: {action['from']} -> {action['to']}")
            except Exception as e:
                print(f"Error moving {action['from']}: {str(e)}")
    
    # Print rename suggestions
    for action in actions["rename"]:
        files_str = "\n    ".join(action["files"])
        print(f"Manual review needed - {action['reason']}:\n    {files_str}")

def create_import_migration_guide(actions):
    """Create a guide for updating imports based on moved files."""
    migration_guide = {}
    
    for action in actions["move"]:
        source_module = action["from"].replace(".py", "").replace("/", ".")
        target_module = action["to"].replace(".py", "").replace("/", ".")
        migration_guide[source_module] = target_module
    
    # Add manual entries for renamed files
    additional_mappings = {
        "systems.performance": "systems.core.performance_monitor",
        "config.settings": "config.unified_config",
    }
    migration_guide.update(additional_mappings)
    
    return migration_guide

def main():
    parser = argparse.ArgumentParser(description="Consolidate duplicate files in the project")
    parser.add_argument("--execute", action="store_true", help="Execute actions (default is dry run)")
    parser.add_argument("--report", action="store_true", help="Generate a JSON report of actions")
    args = parser.parse_args()
    
    if not os.path.exists("systems"):
        print("Error: Run this script from the project root directory")
        sys.exit(1)
    
    print("Scanning for duplicates...")
    duplicates = find_duplicates()
    
    print(f"Found {sum(len(files) for files in duplicates.values())} files with {len(duplicates)} unique filenames that have duplicates")
    
    actions = suggest_consolidation(duplicates)
    
    print("\nSuggested actions:")
    execute_actions(actions, dry_run=not args.execute)
    
    # Create import migration guide
    migration_guide = create_import_migration_guide(actions)
    
    print("\nImport migration guide:")
    for old_import, new_import in migration_guide.items():
        print(f"from {old_import} -> from {new_import}")
    
    # Generate report if requested
    if args.report:
        report = {
            "duplicates": {name: paths for name, paths in duplicates.items()},
            "actions": actions,
            "import_migration": migration_guide
        }
        
        with open("duplicate_consolidation_report.json", "w") as f:
            json.dump(report, f, indent=2)
        print("\nReport saved to duplicate_consolidation_report.json")
    
    # Print summary
    print("\nSummary:")
    print(f"  Files to remove: {len(actions['remove'])}")
    print(f"  Files to move: {len(actions['move'])}")
    print(f"  Files needing manual review: {len(actions['rename'])}")
    
    if not args.execute:
        print("\nThis was a dry run. Use --execute to perform these actions.")

if __name__ == "__main__":
    main() 