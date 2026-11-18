# Unified Configuration System

## Overview

The AI Battle Arena now uses a unified, hierarchical configuration system that provides better organization, validation, and extensibility. This system replaces the previous separate configuration systems (`GameConfig` in `settings.py` and `Config` in `config.py`).

## Key Features

- **Hierarchical Structure**: Configuration is organized into logical sections (display, performance, agent, environment)
- **Validation**: Configuration values are validated to ensure they meet requirements
- **Versioning**: Configuration files include version information for backward compatibility
- **Deep Merging**: Custom configuration can override nested values without replacing entire sections
- **Typed Access**: Configuration access and modification through type-checked methods

## Configuration Sections

### Display

Graphics and display settings:
- `SCREEN_WIDTH`: Width of the game window in pixels
- `SCREEN_HEIGHT`: Height of the game window in pixels
- `TARGET_FPS`: Target frames per second
- `MAX_FPS`: Maximum frames per second
- `MIN_FPS`: Minimum acceptable frames per second

### Performance

Performance-related settings:
- `MIN_FPS`: Minimum FPS before quality reduction triggers
- `MAX_MEMORY_MB`: Maximum memory usage in megabytes
- `MAX_AGENTS`: Maximum number of agents to allow
- `MIN_DECISION_TIME_MS`: Minimum time allotted for agent decisions
- `MEMORY_WARNING_THRESHOLD`: Memory threshold for warnings

### Agent

Agent-specific settings:
- `MIN_MEMORY_PER_AGENT`: Minimum memory allocation per agent
- `MAX_AGENTS`: Maximum number of agents
- `STATE_SIZE`: Size of the agent state vector
- `BEHAVIOR_METRICS`: Weights for different behavior aspects

### Environment

Environment configuration:
- `GRID_SIZE`: Size of the environment grid
- `HAZARD_DAMAGE`: Damage caused by hazards
- `ZONE_SHRINK_RATE`: Rate at which zones shrink
- `RESOURCE_SPAWN_INTERVAL`: Interval between resource spawns

## Migrating from the Old System

We provide a migration script that automatically converts your old configuration to the new format:

```bash
python -m config.migrate_config
```

This script will:
1. Read your existing configuration from `settings.py` and `config.py`
2. Convert it to the new unified format
3. Save it as `game_config.json` in the config directory

## Manual Configuration

You can manually edit the `game_config.json` file to adjust settings. The file has the following structure:

```json
{
  "version": "1.0.0",
  "display": {
    "SCREEN_WIDTH": 1200,
    "SCREEN_HEIGHT": 800,
    "TARGET_FPS": 30,
    "MAX_FPS": 60,
    "MIN_FPS": 20
  },
  "performance": {
    "MIN_FPS": 25,
    "MAX_MEMORY_MB": 1500,
    "MAX_AGENTS": 10,
    "MIN_DECISION_TIME_MS": 16,
    "MEMORY_WARNING_THRESHOLD": 0.8
  },
  "agent": {
    "MIN_MEMORY_PER_AGENT": 51200,
    "MAX_AGENTS": 50,
    "STATE_SIZE": 30,
    "BEHAVIOR_METRICS": {
      "exploration_weight": 0.3,
      "tactical_bonus": 0.25,
      "team_synergy": 0.2,
      "resource_efficiency": 0.15,
      "combat_effectiveness": 0.1
    }
  },
  "environment": {
    "GRID_SIZE": 32,
    "HAZARD_DAMAGE": 1,
    "ZONE_SHRINK_RATE": 0.99,
    "RESOURCE_SPAWN_INTERVAL": 300
  }
}
```

## Programmatic Usage

In your code, access the configuration using the `config` instance from `config.unified_config`:

```python
from config.unified_config import config

# Access configuration values
screen_width = config.display['SCREEN_WIDTH']
max_agents = config.agent['MAX_AGENTS']

# Or use the get method with a default value
grid_size = config.get('environment', 'GRID_SIZE', 32)

# Modify configuration
config.set('performance', 'MAX_MEMORY_MB', 2000)

# Save changes
config.save_config()
```

## Validation

The configuration system includes validation to ensure settings are reasonable:

```python
# Check if configuration is valid
if not config.validate():
    print("Configuration is invalid!")
``` 