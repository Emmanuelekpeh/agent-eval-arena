# AI Battle Arena Naming Conventions

## Purpose
This document establishes consistent naming conventions for the AI Battle Arena project to improve code readability, maintainability, and collaboration among team members.

## Files and Modules

- Use `snake_case` for all filenames: `team_system.py`, `resource_manager.py`
- Group related files in appropriate subdirectories
- Use descriptive, plural names for directories: `systems/`, `agents/`, `utils/`
- File names should clearly indicate their primary contents: `team_system.py` contains `TeamSystem`

## Classes

- Use `PascalCase` for all class names: `TeamSystem`, `ResourceManager`
- Use standard suffixes to indicate class purpose:
  - `System` for primary system classes that manage game mechanics
  - `Manager` for classes that primarily manage resources or entities
  - `Service` for utility classes that provide specific services
  - `Component` for UI or game object components

## Methods and Functions

- Use `snake_case` for all method and function names: `update_positions()`, `calculate_score()`
- Use verb-noun format for action methods: `get_formation_positions()`, `update_team_positions()`
- Prefix private methods with underscore: `_assign_roles()`, `_update_abilities()`
- Use consistent verbs across similar operations:
  - `get_` for retrieving values
  - `set_` for setting values
  - `update_` for changing state
  - `calculate_` for computing values
  - `check_` for validation
  - `is_` for boolean queries

## Variables and Properties

- Use `snake_case` for all variables and properties
- Use descriptive names that clearly indicate purpose
- Avoid abbreviations unless widely understood (e.g., `pos` for position)
- Prefix class-level variables with `self.`
- Use plural forms for collections: `teams`, `formations`, `positions`

## Constants

- Use `UPPER_SNAKE_CASE` for constants: `MAX_AGENTS`, `TARGET_FPS`
- Define constants at module or class level
- Group related constants in dedicated files or classes

## Type Hints and Documentation

- Include type hints for all function parameters and return types
- Use docstrings for all classes, methods, and functions
- Format docstrings using the Google docstring format

## Event System

- Use `PascalCase` for event type enums: `SystemEventType.FORMATION_CHANGED`
- Use descriptive past tense for event names: `ENTITY_CREATED`, `COMBAT_STARTED`

## Examples

```python
# File: systems/agents/team_system.py
from typing import Dict, List, Tuple

class TeamSystem:
    """
    Manages team formations, coordination, and abilities.
    """
    
    MAX_TEAM_SIZE = 10
    
    def __init__(self):
        self.teams = {}
        self.formation_scores = {}
    
    def get_formation_positions(self, team_id: str, leader_pos: Tuple[float, float]) -> List[Tuple[float, float]]:
        """
        Get the ideal positions for team members in formation.
        
        Args:
            team_id: Team identifier
            leader_pos: Position of the team leader
            
        Returns:
            List of positions for each team member
        """
        # Method implementation
``` 