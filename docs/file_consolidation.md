# AI Battle Arena - File Consolidation Guide

This document explains the reorganization of the AI Battle Arena codebase to improve maintainability and architecture.

## New Directory Structure

The systems directory has been reorganized into subdirectories by functional area:

```
systems/
├── core/         # Core systems (event handling, system management)
├── agents/       # Agent-related systems (team, formation, relationship)
├── environment/  # Environment systems (terrain, resources)
├── combat/       # Combat-related systems
├── ui/           # User interface systems
├── utils/        # Utility functions and helpers
└── learning/     # Learning and adaptation systems
```

## File Moves

The following files have been moved to new locations:

| Original Path | New Path |
|---------------|----------|
| systems/system_manager.py | systems/core/system_manager.py |
| systems/event_system.py | systems/core/event_system.py |
| systems/agent_system.py | systems/agents/agent_system.py |
| systems/team_system.py | systems/agents/team_system.py |
| systems/formation_system.py | systems/agents/formation_system.py |
| systems/relationship_system.py | systems/agents/relationship_system.py |
| systems/communication_system.py | systems/agents/communication_system.py |
| systems/terrain_system.py | systems/environment/terrain_system.py |
| systems/resource_system.py | systems/environment/resource_system.py |
| systems/resource_sharing.py | systems/environment/resource_sharing.py |
| systems/combat_system.py | systems/combat/combat_system.py |
| systems/battle_mechanics.py | systems/combat/battle_mechanics.py |
| systems/combat_mechanics.py | systems/combat/combat_mechanics.py |
| systems/learning_system.py | systems/learning/learning_system.py |
| systems/behavior_learning.py | systems/learning/behavior_learning.py |

## Deprecated Files

The following files have been deprecated and removed:

- systems/performance.py
- systems/base_system.py
- config/settings.py
- systems/team_mechanics.py
- systems/team_formation.py
- systems/team_coordinator.py

## Import Updates

All import statements in Python files need to be updated to reflect the new file locations. You can run the provided script to automatically update import statements:

```bash
python scripts/update_imports.py
```

The script will:
1. Update import paths to match the new file locations
2. Comment out deprecated imports with a "DEPRECATED" prefix
3. Report all files that were updated

## Manual Updates Required

After running the automated script, you should:

1. Review any imports marked as "DEPRECATED" and update them accordingly
2. Test all functionality to ensure the imports are working properly
3. Update any documentation references to file paths

## Troubleshooting

If you encounter any issues after the consolidation:

1. Check for lingering references to old file paths in your code
2. Verify that all `__init__.py` files properly expose the needed classes and functions
3. Make sure all import statements use the new directory structure

For any questions or problems with the migration, please reference the project documentation or open an issue in the repository.

## Overview

During the architecture consolidation phase, we've identified several duplicate files and inconsistencies in the codebase. This document provides a clear guide on which files to use and which ones are deprecated.

## Canonical File Locations

The following table shows the canonical (official) location for key system files:

| System Component | Canonical Path |
|------------------|---------------|
| Base System | `systems/core/base_system.py` |
| Performance Monitoring | `systems/core/performance_monitor.py` |
| Formation System | `systems/agents/formation_system.py` |
| Team System | `systems/agents/team_system.py` |
| Combat System | `systems/combat/combat_system.py` |
| Resource System | `systems/environment/resource_system.py` |
| Configuration | `config/unified_config.py` |
| Resource Sharing | `systems/resource_sharing.py` |
| Communication System | `systems/communication_system.py` |
| System Integration | `systems/system_integration.py` |

## Import Migration Guide

When updating code, use the following import migration guide:

```python
# Old imports                           # New imports
from systems.performance import ...     # from systems.core.performance_monitor import ...
from systems.base_system import ...     # from systems.core.base_system import ...
from config.settings import ...         # from config.unified_config import ...
from systems.team_mechanics import ...  # from systems.agents.team_system import ...
from systems.team_formation import ...  # from systems.agents.formation_system import ...
from systems.team_coordinator import ... # from systems.agents.team_system import ...
```

## Consolidation Process

We've created a consolidation script that identifies and resolves duplicate files:

```
python scripts/consolidate_duplicates.py
```

This script will:
1. Identify duplicate files across the project
2. Suggest actions to move or remove files
3. Generate an import migration guide
4. Create a detailed report

By default, the script runs in dry-run mode, showing what actions it would take without actually modifying files. To execute the actions, use:

```
python scripts/consolidate_duplicates.py --execute
```

## System Organization

The overall system organization follows the structure defined in `docs/system_organization.md`. Key systems are organized into logical groups:

- `systems/core/` - Core framework systems
- `systems/agents/` - Agent-related systems
- `systems/environment/` - Environment-related systems
- `systems/combat/` - Combat-related systems
- `systems/ui/` - User interface systems
- `systems/utils/` - Utility systems and helpers
- `systems/learning/` - Learning and adaptation systems

## Unified Configuration System

The configuration system has been consolidated into a unified, hierarchical system at `config/unified_config.py`. This replaces the previous separate configuration systems. See `config/README.md` for details on using the new configuration system.

# File Consolidation Migration Guide

## Overview

The AI Battle Arena codebase has been reorganized into a more modular structure to improve maintainability and organization. This document outlines the changes made and provides guidance on updating imports in your code.

## Directory Structure

The new structure organizes files by their functional area:

```
systems/
├── core/         # Core system components (system_manager, event_system)
├── agents/       # Agent-related systems (agent_system, team_system)
├── environment/  # Environment systems (terrain_system, resource_system)
├── combat/       # Combat-related systems (combat_system, battle_mechanics)
├── ui/           # User interface components
├── utils/        # Utility functions and helpers
└── learning/     # Learning and AI systems
```

## File Migrations

The following files have been moved:

| Original Location | New Location |
|-------------------|--------------|
| systems/system_manager.py | systems/core/system_manager.py |
| systems/event_system.py | systems/core/event_system.py |
| systems/agent_system.py | systems/agents/agent_system.py |
| systems/team_system.py | systems/agents/team_system.py |
| systems/formation_system.py | systems/agents/formation_system.py |
| systems/terrain_system.py | systems/environment/terrain_system.py |
| systems/resource_system.py | systems/environment/resource_system.py |
| systems/combat_system.py | systems/combat/combat_system.py |
| systems/battle_mechanics.py | systems/combat/battle_mechanics.py |
| systems/combat_mechanics.py | systems/combat/combat_mechanics.py |
| systems/learning_system.py | systems/learning/learning_system.py |

## Removed Files

The following deprecated files have been removed:
- systems/performance.py
- systems/base_system.py
- config/settings.py
- systems/team_mechanics.py
- systems/team_formation.py
- systems/team_coordinator.py

## Updating Imports

To update your imports, follow these guidelines:

### For Python Files

Replace imports like:
```python
from systems.system_manager import SystemManager
```

With:
```python
from systems.core.system_manager import SystemManager
```

### Example Import Updates

| Old Import | New Import |
|------------|------------|
| `from systems.system_manager import SystemManager` | `from systems.core.system_manager import SystemManager` |
| `from systems.agent_system import AgentSystem` | `from systems.agents.agent_system import AgentSystem` |
| `from systems.team_system import TeamSystem` | `from systems.agents.team_system import TeamSystem` |
| `from systems.combat_system import CombatSystem` | `from systems.combat.combat_system import CombatSystem` |
| `from systems.learning_system import LearningSystem` | `from systems.learning.learning_system import LearningSystem` |

## Next Steps

After updating imports, run the tests to ensure that everything is working as expected. If you encounter any issues, please check that all imports have been correctly updated.

## Future Considerations

This reorganization provides a foundation for future improvements:

1. We can now add specialized systems to each domain without cluttering the main systems directory
2. The modular structure makes it easier to understand the codebase organization
3. Future contributors can easily identify where new systems should be placed 