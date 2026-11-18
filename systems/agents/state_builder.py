from typing import Dict, Any, Tuple, Optional, List
import numpy as np
import logging
import math

# Need access to SystemManager to get other systems
from systems.core.system_manager import SystemManager
# Potential system dependencies (add more as needed)
from systems.core.entity_manager import EntityManager
from systems.morale.morale_suppression_system import MoraleSuppressionSystem
from systems.agents.team_system import TeamSystem
from systems.formation_movement import FormationMovementSystem # For formation score
from systems.environment.hazard_cover_system import HazardCoverSystem
from systems.environment.battle_royale_env import BattleRoyaleEnv # For safe zone info
from systems.environment.weather_system import WeatherSystem # For visibility
# Constants
from systems.constants import (
    AGENT_TYPE, BULLET_TYPE, PICKUP_TYPE, RESOURCE_TYPE, OBSTACLE_TYPE, COVER_TYPE,
    STATE_VECTOR_SIZE # Assuming this is defined
)

logger = logging.getLogger(__name__)

# Define constants for state vector structure (example)
STATE_SELF_HEALTH = 0
STATE_SELF_ENERGY = 1
STATE_SELF_ANGLE = 2 # Normalized 0-1?
STATE_SELF_MORALE = 3
STATE_SELF_SUPPRESSION = 4
STATE_ENEMY_DIST = 5
STATE_ENEMY_ANGLE = 6
STATE_ENEMY_HEALTH = 7 # Added
STATE_TEAMMATE_DIST = 8
STATE_TEAMMATE_ANGLE = 9
STATE_RESOURCE_DIST = 10
STATE_RESOURCE_ANGLE = 11
STATE_PICKUP_DIST = 12
STATE_PICKUP_ANGLE = 13
STATE_BULLET_DIST = 14
STATE_BULLET_ANGLE = 15
STATE_COVER_DIST = 16
STATE_COVER_ANGLE = 17
STATE_FORMATION_COMP = 18
STATE_IN_COVER = 19
STATE_SAFE_ZONE_DIST = 20
STATE_WEATHER_VIS = 21
# ... Add more up to STATE_VECTOR_SIZE - 1 ...

class StateBuilder:
    """Constructs the state vector for an agent by querying relevant systems."""
    
    # We might not need BaseSystem if it doesn't have its own update loop
    # but it needs access to the system_manager
    def __init__(self, system_manager: SystemManager):
        self.system_manager = system_manager
        # Cache system references for performance
        self._entity_manager: Optional[EntityManager] = None
        self._morale_system: Optional[MoraleSuppressionSystem] = None
        self._team_system: Optional[TeamSystem] = None
        self._formation_system: Optional[FormationMovementSystem] = None
        self._hazard_system: Optional[HazardCoverSystem] = None
        self._env_system: Optional[BattleRoyaleEnv] = None
        self._weather_system: Optional[WeatherSystem] = None
        # Add other system references as needed
        logger.info("StateBuilder initialized")

    # --- System Getters with Caching --- #
    @property
    def entity_manager(self) -> Optional[EntityManager]:
        if self._entity_manager is None:
            self._entity_manager = self.system_manager.get_system("entity_manager")
        return self._entity_manager

    @property
    def morale_system(self) -> Optional[MoraleSuppressionSystem]:
        if self._morale_system is None:
            self._morale_system = self.system_manager.get_system("morale_suppression_system")
        return self._morale_system

    @property
    def team_system(self) -> Optional[TeamSystem]:
        if self._team_system is None:
            self._team_system = self.system_manager.get_system("team_system")
        return self._team_system

    @property
    def formation_system(self) -> Optional[FormationMovementSystem]:
        if self._formation_system is None:
             # Assumes it's registered with this name
            self._formation_system = self.system_manager.get_system("formation_movement_system") 
        return self._formation_system

    @property
    def hazard_system(self) -> Optional[HazardCoverSystem]:
        if self._hazard_system is None:
            self._hazard_system = self.system_manager.get_system("hazard_cover_system")
        return self._hazard_system

    @property
    def env_system(self) -> Optional[BattleRoyaleEnv]:
        if self._env_system is None:
            self._env_system = self.system_manager.get_system("battle_royale_env")
        return self._env_system

    @property
    def weather_system(self) -> Optional[WeatherSystem]:
        if self._weather_system is None:
            self._weather_system = self.system_manager.get_system("weather_system")
        return self._weather_system
    # --- End System Getters ---

    def build_state_vector(self, agent_id: str) -> Optional[np.ndarray]:
        """Builds the state vector for the specified agent."""
        
        # --- 1. Get core agent data (from EntityManager) ---
        if not self.entity_manager:
            logger.error("StateBuilder: EntityManager not found!")
            return None
            
        agent_data = self.entity_manager.get_entity(agent_id)
        if not agent_data:
            logger.warning(f"StateBuilder: Agent {agent_id} not found in EntityManager.")
            return None
        
        agent_pos = agent_data.get('position')
        if not agent_pos:
             logger.warning(f"StateBuilder: Agent {agent_id} has no position data.")
             return None
        
        agent_type = agent_data.get('type') # Should be 'agent'
        agent_health = agent_data.get('health', 100.0) 
        agent_energy = agent_data.get('energy', 100.0)
        agent_angle_rad = agent_data.get('angle', 0.0) # Assuming angle in radians

        # --- 2. Query other systems --- 
        # Morale/Suppression
        morale, suppression = 0.5, 0.0 # Defaults
        if self.morale_system:
             morale = self.morale_system.get_morale(agent_id)
             suppression = self.morale_system.get_suppression(agent_id)
             
        # Team Info
        team_id = None
        formation_compliance = 0.0
        if self.team_system:
             team_id = self.team_system.get_team_id_for_agent(agent_id)
        if team_id and self.formation_system:
             # Use formation system to get score
             formation_compliance = self.formation_system.get_formation_score(team_id)

        # Nearby Entities (Agents, Bullets, Resources, Pickups)
        # TODO: Define search radius and entity types based on config/agent needs
        search_radius = 500 # Example value
        nearby_entities = self.entity_manager.get_entities_in_range(agent_pos, search_radius)
        
        # --- 3. Process and Assemble State Vector --- 
        # This part needs careful definition based on what the agents expect.
        # Example structure (needs refinement based on actual agent input requirements):
        state_parts = []
        
        # Self state
        state_parts.extend([agent_health / 100.0, agent_energy / 100.0, 
                            agent_angle_rad % (2 * math.pi), morale / 100.0, suppression / 100.0])
                            
        # Process nearby entities (example: encode closest enemy, closest resource, nearest bullet)
        # This is complex and depends heavily on the desired state representation
        closest_enemy = {'dist': search_radius, 'angle': 0.0, 'health': 0.0}
        closest_teammate = {'dist': search_radius, 'angle': 0.0}
        closest_resource = {'dist': search_radius, 'angle': 0.0}
        closest_pickup = {'dist': search_radius, 'angle': 0.0}
        closest_bullet = {'dist': search_radius, 'angle': 0.0}
        
        agent_angle_deg = math.degrees(agent_angle_rad) # Convert agent angle once

        for entity in nearby_entities:
            entity_id = entity.get('id')
            if entity_id == agent_id: continue # Skip self

            entity_pos = entity.get('position')
            entity_type = entity.get('type')

            if not entity_pos or not entity_type:
                continue

            dist = calculate_distance(agent_pos, entity_pos)
            if dist >= search_radius: continue # Skip entities exactly at or beyond radius

            angle = calculate_relative_angle(agent_pos, agent_angle_deg, entity_pos)

            # Check Agent type (Enemy or Teammate)
            if entity_type == AGENT_TYPE:
                is_enemy_flag = is_enemy(self.team_system, agent_id, entity_id) # Use helper
                if is_enemy_flag:
                    if dist < closest_enemy['dist']:
                        closest_enemy['dist'] = dist
                        closest_enemy['angle'] = angle
                        closest_enemy['health'] = entity.get('health', 0.0) / 100.0 # Normalized health
                elif entity_id != agent_id: # Is a teammate
                     if dist < closest_teammate['dist']:
                          closest_teammate['dist'] = dist
                          closest_teammate['angle'] = angle
            
            # Check other types
            elif entity_type == RESOURCE_TYPE:
                 if dist < closest_resource['dist']:
                      closest_resource['dist'] = dist
                      closest_resource['angle'] = angle
            elif entity_type == PICKUP_TYPE:
                 if dist < closest_pickup['dist']:
                      closest_pickup['dist'] = dist
                      closest_pickup['angle'] = angle
            elif entity_type == BULLET_TYPE:
                 # Maybe filter bullets not heading towards agent?
                 if dist < closest_bullet['dist']:
                      closest_bullet['dist'] = dist
                      closest_bullet['angle'] = angle
            # elif entity_type == COVER_TYPE: # Handled by hazard system query?
            #     pass

        # --- 4. Assemble State Vector --- 
        state_vector = np.zeros(STATE_VECTOR_SIZE, dtype=np.float32)

        # Normalize self state
        state_vector[STATE_SELF_HEALTH] = agent_health / 100.0
        state_vector[STATE_SELF_ENERGY] = agent_energy / 100.0
        state_vector[STATE_SELF_ANGLE] = (agent_angle_rad % (2 * math.pi)) / (2 * math.pi) # Normalize 0-1
        state_vector[STATE_SELF_MORALE] = morale # Assuming morale is already 0-1
        state_vector[STATE_SELF_SUPPRESSION] = suppression # Assuming suppression is already 0-1

        # Normalize entity info (distance 0-1, angle -1 to 1)
        state_vector[STATE_ENEMY_DIST] = closest_enemy['dist'] / search_radius
        state_vector[STATE_ENEMY_ANGLE] = closest_enemy['angle'] / 180.0
        state_vector[STATE_ENEMY_HEALTH] = closest_enemy['health'] # Already normalized 0-1
        state_vector[STATE_TEAMMATE_DIST] = closest_teammate['dist'] / search_radius
        state_vector[STATE_TEAMMATE_ANGLE] = closest_teammate['angle'] / 180.0
        state_vector[STATE_RESOURCE_DIST] = closest_resource['dist'] / search_radius
        state_vector[STATE_RESOURCE_ANGLE] = closest_resource['angle'] / 180.0
        state_vector[STATE_PICKUP_DIST] = closest_pickup['dist'] / search_radius
        state_vector[STATE_PICKUP_ANGLE] = closest_pickup['angle'] / 180.0
        state_vector[STATE_BULLET_DIST] = closest_bullet['dist'] / search_radius
        state_vector[STATE_BULLET_ANGLE] = closest_bullet['angle'] / 180.0

        # Team state (example)
        state_vector[STATE_FORMATION_COMP] = formation_compliance # Already 0-1

        # Hazard/Cover Info
        # TODO: Query HazardCoverSystem and add relevant features
        # e.g., is_in_cover, nearest_cover_dist, nearest_hazard_dist
        in_cover = False
        closest_cover_dist = 1.0 # Normalized default (max distance)
        closest_cover_angle = 0.0 # Default angle
        if self.hazard_system:
            in_cover = self.hazard_system.is_position_in_cover(agent_pos[0], agent_pos[1])
            # Finding closest cover might require querying EntityManager or HazardSystem specific method
            # Placeholder for closest cover logic
            pass 
        
        # Environment Info
        safe_zone_dist_norm = 1.0 # Default (far)
        if self.env_system and hasattr(self.env_system, 'get_safe_zone_distance_normalized'):
             safe_zone_dist_norm = self.env_system.get_safe_zone_distance_normalized(agent_pos)
        
        weather_visibility = 1.0 # Default
        if self.weather_system:
             weather_visibility = self.weather_system.get_visibility()

        # Other states
        state_vector[STATE_IN_COVER] = 1.0 if in_cover else 0.0
        state_vector[STATE_SAFE_ZONE_DIST] = safe_zone_dist_norm # Already normalized?
        state_vector[STATE_WEATHER_VIS] = weather_visibility # Already 0-1

        # Ensure vector has the correct size (important!)
        if len(state_vector) != STATE_VECTOR_SIZE:
            logger.error(f"Constructed state vector size ({len(state_vector)}) does not match expected size ({STATE_VECTOR_SIZE}) for agent {agent_id}. Returning None.")
            # Optionally pad/truncate with warning, but returning None is safer initially.
            # Pad:
            # if len(state_vector) < STATE_VECTOR_SIZE:
            #     padding = np.zeros(STATE_VECTOR_SIZE - len(state_vector), dtype=np.float32)
            #     state_vector = np.concatenate((state_vector, padding))
            # Truncate:
            # elif len(state_vector) > STATE_VECTOR_SIZE:
            #     state_vector = state_vector[:STATE_VECTOR_SIZE]
            return None 

        # logger.debug(f"Built state vector for {agent_id}: size {len(state_vector)}")
        return state_vector

# Helper functions (could be moved to a utils module)
def calculate_distance(pos1, pos2):
    if not pos1 or not pos2:
        return float('inf')
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

def calculate_relative_angle(agent_pos, agent_angle_deg, target_pos):
    if not agent_pos or not target_pos:
         return 0.0
    dx = target_pos[0] - agent_pos[0]
    dy = target_pos[1] - agent_pos[1]
    if dx == 0 and dy == 0:
         return 0.0
    target_angle_rad = math.atan2(dy, dx)
    target_angle_deg = math.degrees(target_angle_rad)
    
    relative_angle = target_angle_deg - agent_angle_deg
    # Normalize to -180 to 180
    while relative_angle > 180:
        relative_angle -= 360
    while relative_angle <= -180:
        relative_angle += 360
    return relative_angle

def is_enemy(team_system: Optional[TeamSystem], agent1_id: str, agent2_id: str) -> bool:
    """Checks if two agents are enemies based on team membership."""
    if not team_system:
        # If no team system, assume all others are enemies (simple FFA logic)
        return agent1_id != agent2_id
        
    agent1_team = team_system.get_team_id_for_agent(agent1_id)
    agent2_team = team_system.get_team_id_for_agent(agent2_id)
    
    # If either agent has no team, they are enemies with everyone (including teamed agents)
    if agent1_team is None or agent2_team is None:
        return True 
        
    # If they are on different teams, they are enemies
    return agent1_team != agent2_team 