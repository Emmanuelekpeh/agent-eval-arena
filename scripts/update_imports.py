#!/usr/bin/env python3
"""
Import path updater for AI Battle Arena codebase reorganization.
This script scans all Python files in the project and updates import statements
to reflect the new file structure after consolidation.
"""

import os
import re
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('import_update.log')
    ]
)
logger = logging.getLogger('import_updater')

# ANSI color codes for pretty output
GREEN = '\033[0;32m'
YELLOW = '\033[0;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color

# Get project root (directory of this script's parent)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

print(f"{CYAN}[update_imports]{NC} Starting import updates in {YELLOW}{PROJECT_ROOT}{NC}")

# Mapping of old import paths to new import paths
IMPORT_MAPPINGS = {
    # Core systems
    "systems.system_manager": "systems.core.system_manager",
    "systems.event_system": "systems.core.event_system",
    "systems.base_system": "systems.core.base_system",
    
    # Agent systems
    "systems.agent_system": "systems.agents.agent_system",
    "systems.team_system": "systems.agents.team_system",
    "systems.formation_system": "systems.agents.formation_system",
    "systems.relationship_system": "systems.agents.relationship_system",
    "systems.communication_system": "systems.agents.communication_system",
    
    # Environment systems
    "systems.terrain_system": "systems.environment.terrain_system",
    "systems.resource_system": "systems.environment.resource_system",
    "systems.resource_sharing": "systems.environment.resource_sharing",
    
    # Combat systems
    "systems.combat_system": "systems.combat.combat_system",
    "systems.battle_mechanics": "systems.combat.battle_mechanics",
    "systems.combat_mechanics": "systems.combat.combat_mechanics",
    
    # Learning systems
    "systems.learning_system": "systems.learning.learning_system",
    "systems.behavior_learning": "systems.learning.behavior_learning",
    
    # Deprecated modules
    "systems.performance": "DEPRECATED",
    "systems.team_mechanics": "DEPRECATED",
    "systems.team_formation": "DEPRECATED",
    "systems.team_coordinator": "DEPRECATED",
    "config.settings": "DEPRECATED",
}

# List of deprecated modules (for special handling)
DEPRECATED_MODULES = [
    "systems.performance",
    "systems.team_mechanics",
    "systems.team_formation",
    "systems.team_coordinator",
    "config.settings",
]

class ImportUpdater:
    def __init__(self, directory="."):
        self.directory = directory
        self.updated_files = []
        self.skipped_files = []
        self.error_files = []
        self.changes = defaultdict(list)
        self.stats = {
            "total_files_scanned": 0,
            "files_updated": 0,
            "files_skipped": 0,
            "files_with_errors": 0,
            "imports_updated": 0,
            "imports_deprecated": 0,
            "start_time": time.time()
        }
    
    def update_imports_in_file(self, filepath):
        """Update import statements in a single file and track changes."""
        logger.info(f"Processing {filepath}...")
        self.stats["total_files_scanned"] += 1
        updated = False
        file_changes = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                original_content = content
            
            # Update 'from X import Y' style imports
            for old_path, new_path in IMPORT_MAPPINGS.items():
                # Skip updating imports in the file that is being imported
                if old_path.replace(".", "/") + ".py" in str(filepath):
                    continue
                    
                # Pattern for 'from old_path import X'
                pattern = rf'from\s+{old_path.replace(".", "\.")}\s+import\s+'
                
                matches = re.findall(pattern + r'(.*?)($|\n)', content)
                if matches:
                    for match in matches:
                        imported_items = match[0]
                        if new_path == "DEPRECATED":
                            # Comment out deprecated imports
                            old_import = f"from {old_path} import {imported_items}"
                            new_import = f"# DEPRECATED IMPORT: {old_import}"
                            content = content.replace(
                                f"from {old_path} import {imported_items}", 
                                new_import
                            )
                            file_changes.append({
                                "type": "deprecated",
                                "old": old_import,
                                "new": new_import
                            })
                            self.stats["imports_deprecated"] += 1
                        else:
                            # Update valid imports
                            old_import = f"from {old_path} import {imported_items}"
                            new_import = f"from {new_path} import {imported_items}"
                            content = content.replace(old_import, new_import)
                            file_changes.append({
                                "type": "updated",
                                "old": old_import,
                                "new": new_import
                            })
                            self.stats["imports_updated"] += 1
                        updated = True
            
            # Update 'import X' style imports
            for old_path, new_path in IMPORT_MAPPINGS.items():
                # Skip updating imports in the file that is being imported
                if old_path.replace(".", "/") + ".py" in str(filepath):
                    continue
                    
                # Pattern for 'import old_path'
                pattern = rf'import\s+{old_path.replace(".", "\.")}\s*($|\n)'
                
                if re.search(pattern, content):
                    if new_path == "DEPRECATED":
                        # Comment out deprecated imports
                        old_import = f"import {old_path}"
                        new_import = f"# DEPRECATED IMPORT: {old_import}"
                        content = re.sub(
                            pattern,
                            new_import + r'\1',
                            content
                        )
                        file_changes.append({
                            "type": "deprecated",
                            "old": old_import,
                            "new": new_import
                        })
                        self.stats["imports_deprecated"] += 1
                    else:
                        # Update valid imports
                        old_import = f"import {old_path}"
                        new_import = f"import {new_path}"
                        content = re.sub(
                            pattern,
                            f'{new_import}\n',
                            content
                        )
                        file_changes.append({
                            "type": "updated",
                            "old": old_import,
                            "new": new_import
                        })
                        self.stats["imports_updated"] += 1
                    updated = True
            
            # Update 'import X as Y' style imports
            for old_path, new_path in IMPORT_MAPPINGS.items():
                # Skip updating imports in the file that is being imported
                if old_path.replace(".", "/") + ".py" in str(filepath):
                    continue
                    
                # Pattern for 'import old_path as alias'
                pattern = rf'import\s+{old_path.replace(".", "\.")}\s+as\s+(\w+)\s*($|\n)'
                
                matches = re.findall(pattern, content)
                if matches:
                    for match in matches:
                        alias = match[0]
                        if new_path == "DEPRECATED":
                            # Comment out deprecated imports
                            old_import = f"import {old_path} as {alias}"
                            new_import = f"# DEPRECATED IMPORT: {old_import}"
                            content = content.replace(
                                f"import {old_path} as {alias}", 
                                new_import
                            )
                            file_changes.append({
                                "type": "deprecated",
                                "old": old_import,
                                "new": new_import
                            })
                            self.stats["imports_deprecated"] += 1
                        else:
                            # Update valid imports
                            old_import = f"import {old_path} as {alias}"
                            new_import = f"import {new_path} as {alias}"
                            content = content.replace(old_import, new_import)
                            file_changes.append({
                                "type": "updated",
                                "old": old_import,
                                "new": new_import
                            })
                            self.stats["imports_updated"] += 1
                        updated = True
            
            if updated:
                # Ensure we don't accidentally add extra newlines
                content = re.sub(r'\n{3,}', '\n\n', content)
                
                if content != original_content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.updated_files.append(str(filepath))
                    self.changes[str(filepath)] = file_changes
                    self.stats["files_updated"] += 1
                    logger.info(f"✓ Updated imports in {filepath}")
                    return True
                else:
                    logger.warning(f"⚠ Content unchanged in {filepath} despite matches")
            else:
                self.skipped_files.append(str(filepath))
                self.stats["files_skipped"] += 1
                logger.info(f"- No imports to update in {filepath}")
            
            return False
            
        except Exception as e:
            self.error_files.append(str(filepath))
            self.stats["files_with_errors"] += 1
            logger.error(f"✗ Error processing {filepath}: {str(e)}")
            return False

    def scan_directory(self):
        """Recursively scan directory and update imports in all Python files."""
        logger.info(f"Scanning directory: {self.directory}")
        
        for root, _, files in os.walk(self.directory):
            for file in files:
                if file.endswith('.py'):
                    filepath = Path(root) / file
                    self.update_imports_in_file(filepath)
        
        return self.updated_files

    def generate_report(self):
        """Generate a detailed report of all changes made."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "stats_summary": {
                "elapsed_time": f"{time.time() - self.stats['start_time']:.2f} seconds",
                "files_updated": len(self.updated_files),
                "files_skipped": len(self.skipped_files),
                "files_with_errors": len(self.error_files)
            },
            "updated_files": self.updated_files,
            "skipped_files": self.skipped_files,
            "error_files": self.error_files,
            "changes": self.changes
        }
        
        # Save detailed report as JSON
        with open("import_update_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Count the frequency of each module update
        update_counts = Counter()
        deprecation_counts = Counter()
        
        for file_changes in self.changes.values():
            for change in file_changes:
                if change["type"] == "updated":
                    old_module = change["old"].split()[1].split(".")[0]
                    update_counts[old_module] += 1
                elif change["type"] == "deprecated":
                    old_module = change["old"].split()[1].split(".")[0]
                    deprecation_counts[old_module] += 1
        
        return report

    def print_summary(self):
        """Print a summary of the update process."""
        elapsed_time = time.time() - self.stats["start_time"]
        
        logger.info("\n" + "="*50)
        logger.info("IMPORT UPDATE SUMMARY")
        logger.info("="*50)
        logger.info(f"Completed in {elapsed_time:.2f} seconds")
        logger.info(f"Total files scanned: {self.stats['total_files_scanned']}")
        logger.info(f"Files updated: {self.stats['files_updated']}")
        logger.info(f"Files with no changes needed: {self.stats['files_skipped']}")
        logger.info(f"Files with errors: {self.stats['files_with_errors']}")
        logger.info(f"Total imports updated: {self.stats['imports_updated']}")
        logger.info(f"Total imports deprecated: {self.stats['imports_deprecated']}")
        
        if self.updated_files:
            logger.info("\nUpdated files:")
            for file in sorted(self.updated_files):
                logger.info(f"  ✓ {file}")
        
        if self.error_files:
            logger.info("\nFiles with errors:")
            for file in sorted(self.error_files):
                logger.info(f"  ✗ {file}")
        
        logger.info("\nNOTE: Files with imports marked as 'DEPRECATED' need manual review.")
        logger.info("The following modules are deprecated and should be updated or removed:")
        for module in DEPRECATED_MODULES:
            logger.info(f"  - {module}")
        
        logger.info("\nDetailed report saved to: import_update_report.json")
        logger.info("="*50)


def main():
    """Main function to run the import updater."""
    try:
        if len(sys.argv) > 1:
            directory = sys.argv[1]
        else:
            directory = "."  # Current directory
        
        updater = ImportUpdater(directory)
        updater.scan_directory()
        updater.generate_report()
        updater.print_summary()
        
        return 0
    except Exception as e:
        logger.error(f"Unhandled exception in main: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 