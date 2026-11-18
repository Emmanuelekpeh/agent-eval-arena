from typing import Dict, Any, Tuple, Optional
import logging
import uuid # For unique bullet IDs
import math
import time
import random

from systems.core.base_system import BaseSystem, SystemEventType
# Potential system dependencies
from systems.core.entity_manager import EntityManager
from systems.environment.terrain_system import TerrainSystem
from systems.environment.resource_system import ResourceManager # Assuming direct interaction is needed
from systems.environment.hazard_cover_system import HazardCoverSystem
from systems.combat.combat_system import CombatSystem # For energy costs, weapon stats?
from systems.morale.morale_suppression_system import MoraleSuppressionSystem
# Need access to SystemManager to get other systems
from systems.core.system_manager import system_manager
from systems.config import config # Access global config

# Constants
from systems.constants import (
    ACTION_IDLE,
    ACTION_MOVE_FORWARD,
    ACTION_ROTATE_LEFT,
    ACTION_ROTATE_RIGHT,
    ACTION_SHOOT,
    ACTION_INTERACT, # Assuming a generic interact action ID
    AGENT_TYPE, BULLET_TYPE 
)

logger = logging.getLogger(__name__)

class ActionExecutor(BaseSystem):
    """Handles the execution of agent actions and their physical consequences."""

    def __init__(self, name: str = "ActionExecutor", priority: int = 62): # Adjusted priority
        super().__init__(name, priority)
        # Cache system references
        self._entity_manager: Optional[EntityManager] = None
        self._terrain_system: Optional[TerrainSystem] = None
        self._resource_manager: Optional[ResourceManager] = None
        self._hazard_system: Optional[HazardCoverSystem] = None
        self._combat_system: Optional[CombatSystem] = None
        self._morale_system: Optional[MoraleSuppressionSystem] = None
        
        # Internal state for cooldowns etc.
        self._weapon_cooldowns = {}

        logger.info("ActionExecutor initialized")

    # --- System Getters with Caching (Lazy Loading) --- #
    @property
    def entity_manager(self) -> Optional[EntityManager]:
        if self._entity_manager is None:
            self._entity_manager = system_manager.get_system("entity_manager")
        return self._entity_manager

    @property
    def terrain_system(self) -> Optional[TerrainSystem]:
        if self._terrain_system is None:
            self._terrain_system = system_manager.get_system("terrain_system")
        return self._terrain_system

    @property
    def resource_manager(self) -> Optional[ResourceManager]:
        if self._resource_manager is None:
            self._resource_manager = system_manager.get_system("resource_manager")
        return self._resource_manager

    @property
    def hazard_system(self) -> Optional[HazardCoverSystem]:
        if self._hazard_system is None:
            self._hazard_system = system_manager.get_system("hazard_cover_system")
        return self._hazard_system

    @property
    def combat_system(self) -> Optional[CombatSystem]:
        if self._combat_system is None:
            self._combat_system = system_manager.get_system("CombatSystem") # Name used in main.py
        return self._combat_system
        
    @property
    def morale_system(self) -> Optional[MoraleSuppressionSystem]:
         if self._morale_system is None:
             self._morale_system = system_manager.get_system("morale_suppression_system")
         return self._morale_system
    # --- End System Getters --- #

    def initialize(self) -> None:
        # Trigger lazy loading once if needed, or just rely on first use
        _ = self.entity_manager
        _ = self.terrain_system
        _ = self.resource_manager
        _ = self.hazard_system
        _ = self.combat_system
        _ = self.morale_system
        logger.info("ActionExecutor initialized and dependencies checked.")
        if not self._entity_manager: logger.error("ActionExecutor: EntityManager FAILED to load!")
        if not self._combat_system: logger.warning("ActionExecutor: CombatSystem not found.")
        if not self._morale_system: logger.warning("ActionExecutor: MoraleSystem not found.")

    def shutdown(self) -> None:
        logger.info("ActionExecutor shutting down")
        # Clear references
        self._entity_manager = None
        self._terrain_system = None
        self._resource_manager = None
        self._hazard_system = None
        self._combat_system = None
        self._morale_system = None
        self._weapon_cooldowns.clear()

    # --- Central Action Execution --- 
    def execute_action(self, agent_id: str, action_id: int, context: Optional[Dict] = None) -> None:
        """Executes the specified action for the agent."""
        if context is None: context = {}
        
        # Ensure critical systems are available
        if not self.entity_manager:
            logger.error(f"Cannot execute action for {agent_id}: EntityManager is unavailable.")
            return
            
        agent_data = self.entity_manager.get_entity(agent_id)
        if not agent_data or agent_data.get('type') != AGENT_TYPE:
            # logger.warning(f"Cannot execute action: Agent {agent_id} not found or invalid.")
            return
        
        # Check if agent is alive
        if not agent_data.get('alive', True):
            # logger.debug(f"Agent {agent_id} cannot act: not alive.")
            return

        # Basic action dispatch
        if action_id == ACTION_IDLE:
            self._handle_idle(agent_id, agent_data, context)
        elif action_id == ACTION_MOVE_FORWARD:
            self._handle_move(agent_id, agent_data, context)
        elif action_id == ACTION_ROTATE_LEFT:
            context['rotation_direction'] = -1 # Add direction to context
            self._handle_rotate(agent_id, agent_data, context)
        elif action_id == ACTION_ROTATE_RIGHT:
            context['rotation_direction'] = 1 # Add direction to context
            self._handle_rotate(agent_id, agent_data, context)
        elif action_id == ACTION_SHOOT:
            self._handle_shoot(agent_id, agent_data, context)
        # elif action_id == ACTION_INTERACT: # Example
        #     self._handle_interact(agent_id, agent_data, context)
        else:
            logger.warning(f"Agent {agent_id} requested unknown action ID: {action_id}")

    # --- Action Handlers --- 
    def _handle_idle(self, agent_id: str, agent_data: Dict, context: Dict) -> None:
        # logger.debug(f"Agent {agent_id} executing IDLE")
        # Optional: Implement passive effects like slight energy regen
        pass

    def _handle_move(self, agent_id: str, agent_data: Dict, context: Dict) -> None:
        # logger.debug(f"Agent {agent_id} executing MOVE_FORWARD")
        delta_time = context.get('delta_time')
        if delta_time is None:
            logger.error(f"Cannot execute move for {agent_id}: delta_time missing in context.")
            return
            
        current_pos = agent_data.get('position')
        current_angle_rad = agent_data.get('angle', 0.0)
        base_speed = agent_data.get('speed', 50.0)
        
        if not current_pos:
             logger.warning(f"Agent {agent_id} has no position for move.")
             return

        # Get modifiers
        terrain_mod = 1.0
        if self.terrain_system:
            terrain_mod = self.terrain_system.get_movement_modifier(current_pos[0], current_pos[1])
            
        suppression_mod = 1.0
        if self.morale_system:
            suppression = self.morale_system.get_suppression(agent_id)
            suppression_penalty = self.morale_system._config.get("SUPPRESSION_MOVE_PENALTY", 0.5) # Max 50% penalty
            suppression_mod = 1.0 - (suppression * suppression_penalty)

        # Calculate final speed
        final_speed = base_speed * terrain_mod * suppression_mod * delta_time
        
        # Calculate movement vector based on agent's current angle
        dx = math.cos(current_angle_rad) * final_speed
        dy = math.sin(current_angle_rad) * final_speed
        
        new_x = current_pos[0] + dx
        new_y = current_pos[1] + dy
        
        # Basic world boundary check (Get bounds from config or entity_manager?)
        world_width = config.display.get('SCREEN_WIDTH', 1000)
        world_height = config.display.get('SCREEN_HEIGHT', 1000)
        agent_radius = agent_data.get('radius', 5)
        new_x = max(agent_radius, min(world_width - agent_radius, new_x))
        new_y = max(agent_radius, min(world_height - agent_radius, new_y))
        
        # Update position via EntityManager
        self.entity_manager.update_entity_position(agent_id, (new_x, new_y))

    def _handle_rotate(self, agent_id: str, agent_data: Dict, context: Dict) -> None:
        delta_time = context.get('delta_time')
        rotation_direction = context.get('rotation_direction') # -1 for left, 1 for right
        if delta_time is None or rotation_direction is None:
            logger.error(f"Cannot execute rotate for {agent_id}: delta_time or rotation_direction missing.")
            return
        # logger.debug(f"Agent {agent_id} executing ROTATE {'LEFT' if rotation_direction < 0 else 'RIGHT'}")

        current_angle_rad = agent_data.get('angle', 0.0)
        base_rotation_speed = agent_data.get('rotation_speed', math.radians(90)) # Radians per second
        
        # Apply suppression modifier
        suppression_mod = 1.0
        if self.morale_system:
             suppression = self.morale_system.get_suppression(agent_id)
             suppression_penalty = self.morale_system._config.get("SUPPRESSION_ROTATE_PENALTY", 0.3) # Max 30% penalty
             suppression_mod = 1.0 - (suppression * suppression_penalty)

        angle_change = base_rotation_speed * rotation_direction * suppression_mod * delta_time
        new_angle_rad = (current_angle_rad + angle_change) % (2 * math.pi)

        # Update angle via EntityManager
        self.entity_manager.update_entity_attribute(agent_id, 'angle', new_angle_rad)

    def _handle_shoot(self, agent_id: str, agent_data: Dict, context: Dict) -> None:
        # logger.debug(f"Agent {agent_id} executing SHOOT")
        if not self.combat_system:
            logger.warning(f"Agent {agent_id} cannot shoot: CombatSystem unavailable.")
            return

        current_time = time.time() # Use a consistent time source
        
        # Get weapon type (from agent data or context? Assume agent data)
        weapon_type = agent_data.get('equipped_weapon', 'standard') 
        weapon_stats = self.combat_system.get_weapon_stats(weapon_type)
        if not weapon_stats:
             logger.warning(f"Agent {agent_id} tried to shoot unknown weapon: {weapon_type}")
             return

        # Check cooldown
        cooldown_duration = weapon_stats.get('cooldown', 500) / 1000.0 # Cooldown in seconds
        last_shot_time = self._weapon_cooldowns.get(agent_id, 0)
        if current_time < last_shot_time + cooldown_duration:
            # logger.debug(f"Agent {agent_id} weapon on cooldown.")
            return # Still on cooldown

        # Check energy cost
        energy_cost = weapon_stats.get('energy_cost', 10)
        current_energy = agent_data.get('energy', 0)
        if current_energy < energy_cost:
            # logger.debug(f"Agent {agent_id} failed to shoot: Not enough energy ({current_energy}/{energy_cost})")
            return

        # Fire!
        # Deduct energy & Set cooldown
        new_energy = current_energy - energy_cost
        self.entity_manager.update_entity_attribute(agent_id, 'energy', new_energy)
        self._weapon_cooldowns[agent_id] = current_time
        
        # Calculate bullet spawn position
        agent_pos = agent_data.get('position')
        agent_angle_rad = agent_data.get('angle', 0.0)
        agent_radius = agent_data.get('radius', 5)
        spawn_offset = agent_radius + 2 # Spawn just outside agent radius
        spawn_x = agent_pos[0] + math.cos(agent_angle_rad) * spawn_offset
        spawn_y = agent_pos[1] + math.sin(agent_angle_rad) * spawn_offset
        spawn_pos = (spawn_x, spawn_y)

        # Calculate bullet angle (consider spread/inaccuracy)
        # TODO: Factor in accuracy modifiers (suppression, morale?)
        spread_degrees = weapon_stats.get('spread', 0)
        angle_offset_rad = math.radians(random.uniform(-spread_degrees / 2, spread_degrees / 2))
        bullet_angle_rad = agent_angle_rad + angle_offset_rad

        # Create bullet properties
        bullet_id = f"bullet_{uuid.uuid4()}" # Use UUID for uniqueness
        bullet_properties = {
            'type': BULLET_TYPE,
            'owner_id': agent_id,
            'weapon_type': weapon_type,
            'damage': weapon_stats.get('damage', 10),
            'speed': weapon_stats.get('speed', 200),
            'range_left': weapon_stats.get('range', 1000), # Max travel distance
            'angle': bullet_angle_rad,
            'radius': 2, # Example bullet radius
            'position': spawn_pos,
            'alive': True
        }

        # Register bullet with EntityManager
        self.entity_manager.register_entity(
            entity_id=bullet_id, 
            entity_type=BULLET_TYPE, 
            position=spawn_pos, 
            radius=bullet_properties['radius'], 
            initial_state=bullet_properties
        )

        # Emit BULLET_FIRED event
        self.emit_event(SystemEventType.BULLET_FIRED, {
            'agent_id': agent_id, 
            'bullet_id': bullet_id,
            'weapon_type': weapon_type,
            'position': spawn_pos,
            'angle': bullet_angle_rad
        })
        # logger.debug(f"Agent {agent_id} fired bullet {bullet_id}")

    # --- Placeholder Handlers for other actions --- 
    # def _handle_interact(self, agent_id: str, agent_data: Dict, context: Dict) -> None:
    #     target_id = context.get('target_id')
    #     if not target_id:
    #         logger.warning(f"Agent {agent_id} INTERACT action missing target_id in context.")
    #         return
    #     # ... logic for resource, pickup, cover ...
    #     logger.warning("_handle_interact not fully implemented.")

    def update(self, delta_time: float) -> None:
        # ActionExecutor is primarily reactive to execute_action calls.
        # Could potentially manage ongoing actions here if needed (e.g., channeled abilities)
        pass

# Remove old public execute methods
# def execute_move(...)
# def execute_rotate(...)
# def execute_shoot(...)
# def execute_resource_interaction(...)
# def execute_cover_interaction(...)