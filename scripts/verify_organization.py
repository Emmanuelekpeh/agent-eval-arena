#!/usr/bin/env python
"""
Verification script to check if the codebase is properly organized according to the new structure.
This script scans the codebase and reports:
1. Files that aren't in their expected location
2. Missing expected files
3. Potentially misplaced files
4. Import statements that need to be updated
"""

import os
import re
import sys
import json
from collections import defaultdict
from pathlib import Path
import logging

# ANSI color codes for pretty output
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
NC = "\033[0m"  # No Color

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Get the project root (directory containing this script's parent)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Expected file organization
EXPECTED_ORGANIZATION = {
    "systems/core": [
        "base_system.py",
        "event_system.py",
        "system_manager.py",
        "__init__.py",
    ],
    "systems/agents": [
        "agent_system.py",
        "team_system.py",
        "formation_system.py",
        "relationship_system.py",
        "communication_system.py",
        "__init__.py",
    ],
    "systems/environment": [
        "terrain_system.py",
        "resource_system.py",
        "resource_sharing.py",
        "__init__.py",
    ],
    "systems/combat": [
        "combat_system.py",
        "battle_mechanics.py",
        "combat_mechanics.py",
        "__init__.py",
    ],
    "systems/learning": [
        "learning_system.py",
        "behavior_learning.py",
        "__init__.py",
    ],
    "systems/visualization": [
        "visualization_system.py",
        "rendering.py",
        "__init__.py",
    ],
    "agents/basic": ["__init__.py"],
    "agents/advanced": ["__init__.py"],
    "utils": ["__init__.py"],
    "tests": ["__init__.py"],
    "scripts": ["update_imports.py", "consolidate_codebase.ps1", "__init__.py"],
}

# Files that should no longer exist in the root systems directory
DEPRECATED_SYSTEMS_FILES = [
    "base_system.py",
    "event_system.py",
    "system_manager.py",
    "agent_system.py",
    "team_system.py",
    "formation_system.py",
    "relationship_system.py",
    "communication_system.py",
    "terrain_system.py",
    "resource_system.py",
    "resource_sharing.py",
    "combat_system.py",
    "battle_mechanics.py",
    "combat_mechanics.py",
    "learning_system.py",
    "behavior_learning.py",
    "visualization_system.py",
    "rendering.py",
]

# Import patterns that should be updated
IMPORT_PATTERNS = {
    r"from\s+systems\.base_system\s+import": "from systems.core.base_system import",
    r"from\s+systems\.event_system\s+import": "from systems.core.event_system import",
    r"from\s+systems\.system_manager\s+import": "from systems.core.system_manager import",
    r"from\s+systems\.agent_system\s+import": "from systems.agents.agent_system import",
    r"from\s+systems\.team_system\s+import": "from systems.agents.team_system import",
    r"from\s+systems\.formation_system\s+import": "from systems.agents.formation_system import",
    r"from\s+systems\.relationship_system\s+import": "from systems.agents.relationship_system import",
    r"from\s+systems\.communication_system\s+import": "from systems.agents.communication_system import",
    r"from\s+systems\.terrain_system\s+import": "from systems.environment.terrain_system import",
    r"from\s+systems\.resource_system\s+import": "from systems.environment.resource_system import",
    r"from\s+systems\.resource_sharing\s+import": "from systems.environment.resource_sharing import",
    r"from\s+systems\.combat_system\s+import": "from systems.combat.combat_system import",
    r"from\s+systems\.battle_mechanics\s+import": "from systems.combat.battle_mechanics import",
    r"from\s+systems\.combat_mechanics\s+import": "from systems.combat.combat_mechanics import",
    r"from\s+systems\.learning_system\s+import": "from systems.learning.learning_system import",
    r"from\s+systems\.behavior_learning\s+import": "from systems.learning.behavior_learning import",
    r"from\s+systems\.visualization_system\s+import": "from systems.visualization.visualization_system import",
    r"from\s+systems\.rendering\s+import": "from systems.visualization.rendering import",
    r"import\s+systems\.base_system": "import systems.core.base_system",
    r"import\s+systems\.event_system": "import systems.core.event_system",
    r"import\s+systems\.system_manager": "import systems.core.system_manager",
}

class OrganizationVerifier:
    """Verifies the organization of the codebase."""

    def __init__(self, project_root):
        """Initialize the verifier with the project root directory."""
        self.project_root = Path(project_root)
        self.missing_files = []
        self.misplaced_files = []
        self.unexpected_files = []
        self.deprecated_files = []
        self.import_issues = []
        
    def verify(self):
        """Verify the organization of the codebase."""
        logger.info(f"{CYAN}Verifying codebase organization in {self.project_root}{NC}")
        
        # Check for expected files
        self._check_expected_files()
        
        # Check for deprecated files
        self._check_deprecated_files()
        
        # Check for import issues
        self._check_import_issues()
        
        # Print summary
        self._print_summary()
        
        # Return whether there are any issues
        return (
            len(self.missing_files) == 0 and
            len(self.deprecated_files) == 0 and
            len(self.import_issues) == 0
        )
    
    def _check_expected_files(self):
        """Check if all expected files exist."""
        for directory, files in EXPECTED_ORGANIZATION.items():
            dir_path = self.project_root / directory
            if not dir_path.exists():
                logger.warning(f"{YELLOW}Expected directory {directory} does not exist{NC}")
                self.missing_files.extend([f"{directory}/{file}" for file in files])
                continue
                
            for file in files:
                file_path = dir_path / file
                if not file_path.exists():
                    logger.warning(f"{YELLOW}Expected file {directory}/{file} does not exist{NC}")
                    self.missing_files.append(f"{directory}/{file}")
    
    def _check_deprecated_files(self):
        """Check if any deprecated files still exist in the systems directory."""
        systems_dir = self.project_root / "systems"
        if not systems_dir.exists():
            return
            
        for file in DEPRECATED_SYSTEMS_FILES:
            file_path = systems_dir / file
            if file_path.exists():
                logger.warning(f"{RED}Deprecated file {file_path} still exists{NC}")
                self.deprecated_files.append(str(file_path))
    
    def _check_import_issues(self):
        """Check for old import patterns that need to be updated."""
        for root, _, files in os.walk(self.project_root):
            root_path = Path(root)
            
            # Skip certain directories
            if any(part.startswith(".") for part in root_path.parts):
                continue
            if "venv" in root_path.parts or "backup_" in root_path.parts[-1]:
                continue
            if "__pycache__" in root_path.parts:
                continue
                
            for file in files:
                if not file.endswith(".py"):
                    continue
                    
                file_path = root_path / file
                self._check_file_imports(file_path)
    
    def _check_file_imports(self, file_path):
        """Check a specific file for import issues."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        issues = []
        for pattern, replacement in IMPORT_PATTERNS.items():
            if re.search(pattern, content):
                issues.append(f"Found {pattern.replace('\\s+', ' ')} - should be {replacement}")
                
        if issues:
            self.import_issues.append({
                "file": str(file_path.relative_to(self.project_root)),
                "issues": issues
            })
    
    def _print_summary(self):
        """Print a summary of the verification."""
        logger.info(f"\n{CYAN}{'=' * 50}{NC}")
        logger.info(f"{CYAN}ORGANIZATION VERIFICATION SUMMARY{NC}")
        logger.info(f"{CYAN}{'=' * 50}{NC}")
        
        if not self.missing_files and not self.deprecated_files and not self.import_issues:
            logger.info(f"{GREEN}✓ Codebase organization is correct!{NC}")
            return
            
        # Missing files
        if self.missing_files:
            logger.info(f"\n{YELLOW}Missing expected files ({len(self.missing_files)}):{NC}")
            for file in sorted(self.missing_files):
                logger.info(f"  - {file}")
                
        # Deprecated files
        if self.deprecated_files:
            logger.info(f"\n{RED}Deprecated files that should be moved ({len(self.deprecated_files)}):{NC}")
            for file in sorted(self.deprecated_files):
                logger.info(f"  - {file}")
                
        # Import issues
        if self.import_issues:
            logger.info(f"\n{YELLOW}Files with import issues ({len(self.import_issues)}):{NC}")
            for issue in self.import_issues:
                logger.info(f"  - {issue['file']}:")
                for i in issue['issues']:
                    logger.info(f"    * {i}")
                    
        logger.info(f"\n{CYAN}Recommendations:{NC}")
        if self.deprecated_files:
            logger.info(f"  - Run {BLUE}scripts/consolidate_codebase.ps1{NC} to move files to their canonical locations")
        if self.import_issues:
            logger.info(f"  - Run {BLUE}python scripts/update_imports.py{NC} to fix import statements")
            
        logger.info(f"{CYAN}{'=' * 50}{NC}")

def main():
    """Main function to run the verification."""
    verifier = OrganizationVerifier(PROJECT_ROOT)
    is_valid = verifier.verify()
    
    if is_valid:
        logger.info(f"{GREEN}Codebase organization is valid!{NC}")
        return 0
    else:
        logger.warning(f"{YELLOW}Codebase organization has issues that need to be addressed.{NC}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 