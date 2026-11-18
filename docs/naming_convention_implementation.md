# Naming Convention Implementation Guide

## Overview

This document provides a step-by-step guide for implementing the naming conventions defined in `naming_conventions.md`. The process will involve:

1. Updating filenames to follow snake_case
2. Refactoring class names to follow PascalCase
3. Refactoring method and variable names to follow snake_case
4. Standardizing constants to use UPPER_SNAKE_CASE
5. Adding type hints and improving docstrings

## Implementation Process

### 1. File Renaming

- Files should use snake_case: all lowercase with underscores between words
- Example: `TeamCoordinator.py` → `team_coordinator.py`

This step will be handled by the reorganization script which will place files in their new locations with proper naming.

### 2. Class Renaming

For each file:

1. Identify class names not following PascalCase convention
2. Rename the class definition
3. Update all references to the class within the file
4. Search the codebase for other references to the class and update them

Example:
```python
# Before
class teamCoordinator:
    def __init__(self):
        pass

# After
class TeamCoordinator:
    def __init__(self):
        pass
```

### 3. Method and Variable Renaming

For each class:

1. Identify methods not following snake_case convention
2. Rename the method definition
3. Update all calls to the method within the class
4. Search the codebase for other calls to the method and update them
5. Repeat for class variables and instance variables

Example:
```python
# Before
def getFormationPositions(self, teamId, leaderPos):
    self.formationScore = 1.0
    return positions

# After
def get_formation_positions(self, team_id, leader_pos):
    self.formation_score = 1.0
    return positions
```

### 4. Constant Standardization

For each module:

1. Identify constants (variables that should not change)
2. Move them to the top of the file or class
3. Rename them to use UPPER_SNAKE_CASE

Example:
```python
# Before
class FormationSystem:
    def __init__(self):
        self.maxTeamSize = 10
        self.defaultSpacing = 50

# After
class FormationSystem:
    MAX_TEAM_SIZE = 10
    DEFAULT_SPACING = 50
    
    def __init__(self):
        pass
```

### 5. Adding Type Hints and Improving Docstrings

For each function and method:

1. Add type hints for parameters and return values
2. Ensure docstrings follow Google style format
3. Include descriptions for all parameters and return values

Example:
```python
# Before
def calculate_formation_score(self, positions, ideal_positions):
    """Calculate how well the agents maintain formation."""
    # Implementation

# After
def calculate_formation_score(self, positions: List[Tuple[float, float]], 
                             ideal_positions: List[Tuple[float, float]]) -> float:
    """
    Calculate how well the agents maintain formation.
    
    Args:
        positions: Actual positions of each agent
        ideal_positions: Ideal positions for perfect formation
        
    Returns:
        Formation score between 0.0 and 1.0
    """
    # Implementation
```

## Implementation Tools

To assist with this process, we can use:

1. IDE find and replace tools with regular expressions
2. Static code analysis tools to identify naming issues
3. Custom scripts to automate repetitive changes

## Testing and Verification

After implementing the naming changes:

1. Run all tests to ensure functionality hasn't broken
2. Review diffs thoroughly before committing
3. Implement one type of change at a time to isolate potential issues

## Phased Implementation

To minimize disruption, implement changes in phases:

1. Phase 1: File and directory reorganization
2. Phase 2: Class and method renaming in core systems
3. Phase 3: Variable and constant standardization
4. Phase 4: Type hints and docstring improvements

Each phase should be separately tested and verified before proceeding to the next. 