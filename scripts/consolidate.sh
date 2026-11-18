#!/bin/bash
# Simple script to consolidate duplicate files in the AI Battle Arena project

echo "AI Battle Arena File Consolidation"
echo "---------------------------------"

# Create directory structure if it doesn't exist
echo "Creating directory structure..."
mkdir -p systems/core
mkdir -p systems/agents
mkdir -p systems/environment
mkdir -p systems/combat
mkdir -p systems/ui
mkdir -p systems/utils
mkdir -p systems/learning

# First remove deprecated files
echo "Removing deprecated files..."
rm -f systems/performance.py
rm -f systems/base_system.py
rm -f config/settings.py
rm -f systems/team_mechanics.py
rm -f systems/team_formation.py
rm -f systems/team_coordinator.py

# Move files to canonical locations (with backup)
echo "Moving files to canonical locations..."

# Core systems
if [ -f systems/system_manager.py ]; then
  cp systems/system_manager.py systems/core/
  echo "Moved: system_manager.py → systems/core/"
fi

if [ -f systems/event_system.py ]; then
  cp systems/event_system.py systems/core/
  echo "Moved: event_system.py → systems/core/"
fi

# Agent systems
if [ -f systems/agent_system.py ]; then
  cp systems/agent_system.py systems/agents/
  echo "Moved: agent_system.py → systems/agents/"
fi

if [ -f systems/team_system.py ]; then
  cp systems/team_system.py systems/agents/
  echo "Moved: team_system.py → systems/agents/"
fi

if [ -f systems/formation_system.py ]; then
  cp systems/formation_system.py systems/agents/
  echo "Moved: formation_system.py → systems/agents/"
fi

# Environment systems
if [ -f systems/terrain_system.py ]; then
  cp systems/terrain_system.py systems/environment/
  echo "Moved: terrain_system.py → systems/environment/"
fi

if [ -f systems/resource_system.py ]; then
  cp systems/resource_system.py systems/environment/
  echo "Moved: resource_system.py → systems/environment/"
fi

# Combat systems
if [ -f systems/combat_system.py ]; then
  cp systems/combat_system.py systems/combat/
  echo "Moved: combat_system.py → systems/combat/"
fi

if [ -f systems/battle_mechanics.py ]; then
  cp systems/battle_mechanics.py systems/combat/
  echo "Moved: battle_mechanics.py → systems/combat/"
fi

if [ -f systems/combat_mechanics.py ]; then
  cp systems/combat_mechanics.py systems/combat/
  echo "Moved: combat_mechanics.py → systems/combat/"
fi

# Learning systems
if [ -f systems/learning_system.py ]; then
  cp systems/learning_system.py systems/learning/
  echo "Moved: learning_system.py → systems/learning/"
fi

# Create __init__.py files in all directories
echo "Creating __init__.py files in all directories..."
touch systems/__init__.py
touch systems/core/__init__.py
touch systems/agents/__init__.py
touch systems/environment/__init__.py
touch systems/combat/__init__.py
touch systems/ui/__init__.py
touch systems/utils/__init__.py
touch systems/learning/__init__.py

echo ""
echo "Consolidation completed!"
echo ""
echo "IMPORTANT: You will need to update imports in your code."
echo "Use the migration guide in docs/file_consolidation.md" 