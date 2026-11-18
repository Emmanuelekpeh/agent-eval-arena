@echo off
echo Starting file consolidation...

REM Create new directory structure
mkdir systems\core 2>nul
mkdir systems\agents 2>nul
mkdir systems\environment 2>nul
mkdir systems\combat 2>nul
mkdir systems\ui 2>nul
mkdir systems\utils 2>nul
mkdir systems\learning 2>nul

REM Create __init__.py files in each directory
echo. > systems\core\__init__.py
echo. > systems\agents\__init__.py
echo. > systems\environment\__init__.py
echo. > systems\combat\__init__.py
echo. > systems\ui\__init__.py
echo. > systems\utils\__init__.py
echo. > systems\learning\__init__.py

REM Move files to their new locations
echo Moving files to new locations...

REM Core systems
move /Y systems\system_manager.py systems\core\system_manager.py
move /Y systems\event_system.py systems\core\event_system.py

REM Agent systems
move /Y systems\agent_system.py systems\agents\agent_system.py
move /Y systems\team_system.py systems\agents\team_system.py
move /Y systems\formation_system.py systems\agents\formation_system.py
move /Y systems\relationship_system.py systems\agents\relationship_system.py
move /Y systems\communication_system.py systems\agents\communication_system.py

REM Environment systems
move /Y systems\terrain_system.py systems\environment\terrain_system.py
move /Y systems\resource_system.py systems\environment\resource_system.py
move /Y systems\resource_sharing.py systems\environment\resource_sharing.py

REM Combat systems
move /Y systems\combat_system.py systems\combat\combat_system.py
move /Y systems\battle_mechanics.py systems\combat\battle_mechanics.py
move /Y systems\combat_mechanics.py systems\combat\combat_mechanics.py

REM Learning systems
move /Y systems\learning_system.py systems\learning\learning_system.py
move /Y systems\behavior_learning.py systems\learning\behavior_learning.py

REM Remove deprecated files (commented out for safety, uncomment if desired)
REM del systems\performance.py
REM del systems\base_system.py
REM del config\settings.py
REM del systems\team_mechanics.py
REM del systems\team_formation.py
REM del systems\team_coordinator.py

echo File consolidation complete!
echo.
echo Next steps:
echo 1. Run 'python scripts/update_imports.py' to update import statements
echo 2. Review any imports marked as "DEPRECATED" and update them manually
echo 3. Test all functionality to ensure everything works properly

pause 