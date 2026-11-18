import pygame
import random
import math
import numpy as np
from systems.core.base_system import BaseSystem
from systems.environment.resource_system import ResourceManager
from systems.environment.terrain_system import TerrainSystem
from systems.environment.hazard_cover_system import HazardCoverSystem
from systems.environment.weather_system import WeatherSystem
from systems.environment.time_system import TimeSystem
from config.unified_config import config
from systems.utils.logging import logger
from typing import Tuple, List, Any, Dict, Optional, cast
from systems.spatial_system import AABB, QuadTree
from opensimplex import OpenSimplex
from systems.core.system_manager import SystemEventType, system_manager
from systems.utils.object_pool import ObjectPool
from systems.constants import STATE_VECTOR_SIZE
from systems.agents.base_agent import BaseAgent
from collections import defaultdict
from systems.visualization.visualization_system import Color
from systems.agents.team_system import TeamSystem
from systems.combat.combat_system import CombatSystem
from systems.agents.personality_system import PersonalitySystem
from enum import Enum, auto
from dataclasses import dataclass, field
import time
import logging # ADDED IMPORT
from systems.agents.agent_system import AgentSystem # For last_action_time
from systems.visualization.visualization_system import VisualizationSystem, Color # For get_agent_color
from systems.visualization.visualization_integration import VisualizationIntegration # To get renderer
from systems.core.system_manager import system_manager # To get systems
from systems.agents.team_system import TeamSystem # To get team ID
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from systems.agents.agent_system import AgentSystem
    from systems.visualization.visualization_integration import VisualizationIntegration
    from systems.visualization.visualization_system import VisualizationSystem, Color

# Import from game_objects instead of game_with_ai
from game_objects.bullet import Bullet
from game_objects.player import Player
# --- ADDED: Import Enemy --- #
from game_objects.enemy import Enemy 
# --- END ADDED --- #
# from game_objects.enemies import FastEnemy, TankEnemy, SniperEnemy # Commented out - Module doesn't exist

# --- Constants (Defined using config.get) --- #
MAX_PICKUPS = config.get("environment", "MAX_PICKUPS", 20)
MAX_HAZARDS = config.get("environment", "MAX_HAZARDS", 5)
MAX_ENEMIES = config.get("environment", "MAX_ENEMIES", 10)

# Forward declare Bullet if needed (Already imported, so remove forward declaration)
# class Bullet:
#     pass

# ADDED: Import for MoraleSuppressionSystem type hint
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from systems.morale.morale_suppression_system import MoraleSuppressionSystem

logger = logging.getLogger(__name__)

class BattleRoyaleEnv(BaseSystem):
    """
    Battle Royale Environment for the AI Battle Arena.
    Manages the game world, resources, terrain, and environmental effects.
    Provides an interface for agents to interact with the environment.
    Handles entity registration in the spatial partitioning system (QuadTree).
    """
    
    def __init__(self, width, height, target_fps):
        """
        Initialize the Battle Royale environment.
        
        Args:
            width (int): Screen width in pixels
            height (int): Screen height in pixels
            target_fps (int): Target frames per second
        """
        super().__init__(name="BattleRoyaleEnv", priority=10)
        self.width = width
        self.height = height
        self.target_fps = target_fps
        
        # Initialize systems OWNED by environment
        self.resource_manager = ResourceManager(width, height) # Reverted to width, height
        self.terrain_system = TerrainSystem(width, height)
        # HazardCoverSystem might be needed early for generation
        self.hazard_cover_system = HazardCoverSystem(width, height)
        system_manager.register_system("HazardCoverSystem", self.hazard_cover_system) # Register owned system
        
        # --- System Dependency Placeholders ---
        self._team_system_instance: Optional[TeamSystem] = None
        self._combat_system_instance: Optional[CombatSystem] = None
        self._team_combat_integration_instance: Optional[TeamCombatIntegration] = None
        self._personality_system_instance: Optional[PersonalitySystem] = None
        self._agent_system_instance: Optional[AgentSystem] = None
        # HazardCoverSystem already initialized and registered above
        # self._hazard_cover_system_instance: Optional[HazardCoverSystem] = None
        
        # Game state
        self.round_number = 1
        self.round_time = 0
        self.max_round_time = config.get("game", "ROUND_TIME_SECONDS", 60) * target_fps
        self.between_rounds = False
        self.round_end_delay = config.get("game", "ROUND_END_DELAY_SECONDS", 3) * target_fps
        
        # Player tracking
        self.agents: Dict[str, Dict[str, Any]] = {} # { agent_id: {'agent': BaseAgent, 'player': Player} }
        self.agent_positions: Dict[str, Tuple[float, float]] = {}
        self.agent_angles: Dict[str, float] = {}
        self.agent_health = {}
        self.agent_energy = {}
        self.agent_scores: Dict[str, int] = {}
        self.eliminated_agents: Dict[str, Any] = {}
        
        # --- ADDED: Enemy Tracking & Spawning --- #
        self.enemies: Dict[str, Any] = {} # Store enemy objects/data {enemy_id: enemy_object}
        self.enemy_spawn_timer = 0.0
        self.enemy_spawn_interval = config.get("environment", "ENEMY_SPAWN_INTERVAL_SEC", 10.0)
        self.max_enemies = MAX_ENEMIES
        # Store enemy type NAMES (strings), let factory handle class mapping
        self.enemy_types: List[str] = config.get("environment", "ENEMY_TYPES", ["MLPAgent1", "PerceptronAgent1"])
        # self.enemy_types: Dict[str, Type[Any]] = { # OLD - Removed direct class references
        #     'FastEnemy': FastEnemy,
        #     'TankEnemy': TankEnemy,
        #     'SniperEnemy': SniperEnemy
        # }
        self.enemy_spawn_weights = config.get("environment", "ENEMY_SPAWN_WEIGHTS", [0.5, 0.5])
        # Ensure weights match types
        if len(self.enemy_spawn_weights) != len(self.enemy_types):
            logger.warning(f"ENEMY_SPAWN_WEIGHTS ({len(self.enemy_spawn_weights)}) != ENEMY_TYPES ({len(self.enemy_types)}). Using equal weights.")
            self.enemy_spawn_weights = [1.0 / len(self.enemy_types)] * len(self.enemy_types) if self.enemy_types else []
        else:
             # Normalize weights
             total_weight = sum(self.enemy_spawn_weights)
             if total_weight > 0:
                  self.enemy_spawn_weights = [w / total_weight for w in self.enemy_spawn_weights]
             else: # Handle zero weights
                  self.enemy_spawn_weights = [1.0 / len(self.enemy_types)] * len(self.enemy_types) if self.enemy_types else []
        # --- END ADDED --- #
        
        # Active Bullets
        self.active_bullets: List[Bullet] = [] # List of active Bullet objects
        self.pickups: List[Dict[str, Any]] = [] # Active pickups
        
        # Environmental effects
        self.weather_conditions = ['clear', 'rain', 'fog', 'storm']
        self.current_weather = 'clear'
        self.weather_intensity = 0.0
        self.day_time = 0.0  # 0.0 to 1.0 representing day cycle
        
        # Combat zone management
        self.safe_zone_radius = config.get("environment", "INITIAL_SAFE_ZONE_RADIUS", 400)
        self.safe_zone_center = (config.get("environment", "CENTER_X", self.width // 2),
                                 config.get("environment", "CENTER_Y", self.height // 2))
        self.target_safe_zone_radius = config.get("environment", "TARGET_SAFE_ZONE_RADIUS", width * 0.4)
        self.shrink_rate = config.get("game", "ZONE_SHRINK_RATE_PER_FRAME", width * 0.00002)
        self.zone_damage = config.get("game", "ZONE_DAMAGE", 1.0)
        
        # --- ADDED: Zone Shrink Timing ---
        self.shrink_interval = config.get("game", "ZONE_SHRINK_INTERVAL_SECONDS", 60) * target_fps
        self.shrink_warning_time = config.get("game", "ZONE_SHRINK_WARNING_SECONDS", 10) * target_fps
        self.shrink_timer = self.shrink_interval # Time until next shrink starts
        self.next_safe_zone_radius = self.safe_zone_radius # Initially no shrink planned
        self.safe_zone_warning_timer = 0.0 # Timer for the visual warning
        self.min_safe_zone_radius = config.get("environment", "MIN_SAFE_ZONE_RADIUS", 50)
        # --- END ADDED ---
        
        # Resource and pickup spawning
        self.resource_spawn_timer = 0
        self.resource_spawn_interval = config.get("game", "RESOURCE_SPAWN_INTERVAL_SECONDS", 5) * target_fps
        self.pickup_types = ['health', 'energy', 'shield', 'weapon']
        self.pickup_spawn_timer = 0
        self.pickup_spawn_interval = config.get("game", "PICKUP_SPAWN_INTERVAL_SECONDS", 10) * target_fps
        
        # Initialize terrain and weather
        self.weather_system = WeatherSystem()
        self.time_system = TimeSystem()
        
        # After terrain is generated, create cover objects
        self.hazard_cover_system.generate_cover(density=config.get("environment", "COVER_DENSITY", 0.03))
        
        self.hazards = {}
        
        # Initialize the QuadTree with the correct AABB
        # Boundary should cover the whole screen
        # Center is (width/2, height/2)
        # Half-width is width/2, Half-height is height/2
        screen_boundary = AABB(
            center_x=self.width / 2.0,
            center_y=self.height / 2.0,
            half_width=self.width / 2.0,
            half_height=self.height / 2.0
        )
        self.collision_tree = QuadTree(screen_boundary, capacity=4)
        
        # Object Pooling - Use the imported Bullet class
        # --- MODIFIED: Explicitly import and use Bullet from game_objects ---
        try:
             from game_objects.bullet import Bullet as GameObjectBullet # Import with alias
             BulletClass = GameObjectBullet # Use the explicitly imported class
             self.bullet_pool = ObjectPool(BulletClass, initial_size=50, max_size=200)
             logger.info(f"Bullet pool initialized with {BulletClass.__module__}.{BulletClass.__name__}")
        except ImportError as e:
             logger.error(f"Failed to import Bullet from game_objects.bullet: {e}. Bullet pool NOT created.")
             self.bullet_pool = None # Ensure pool is None if import fails
        # -------------------------------------------------------------------
        
        # Ensure team_combat attribute exists initially
        self.team_combat = None
        
        # Store cover and hazard data for interactions
        self.cover_data: Dict[str, Dict[str, Any]] = {}
        self.hazard_data: Dict[str, Dict[str, Any]] = {}
        
        # --- ADDED: Store Config Reference --- #
        self.config = config # Store global config instance
        # --- END ADDED --- #
        
        logger.info(f"Battle Royale Environment initialized: {width}x{height} at {target_fps} FPS")
        self.last_spawn_time = time.time() # Initialize spawn timer

        # --- ADDED: Initialize entities dictionary ---
        self.entities = {}
        # -------------------------------------------

        # Pickup management
        self.pickups = []

        self.morale_suppression_system = None
        self.interaction_system = None
        self.hazard_cover_system = None
        # --- REMOVED: Internal QuadTree ---
        # self.collision_tree = QuadTree(pygame.Rect(0, 0, width, height))
        # --- END REMOVED ---

        # Agent and entity tracking
        # ... existing code ...
        # REMOVED: QuadTree update logic
        # Clear and repopulate the collision tree
        # if hasattr(self, 'collision_tree') and self.collision_tree:
        #     self.collision_tree.clear()
        #     # Insert agents
        #     for agent_id, agent in self.agents.items():
        #         if hasattr(agent, 'position') and hasattr(agent, 'radius'):
        #             try:
        #                 self.collision_tree.insert(agent.position, agent_id, agent.radius, 'agent')
        #             except Exception as e:
        #                 logger.error(f"Error inserting agent {agent_id} into QuadTree: {e}")
        #
        #     # Insert bullets
        #     for bullet in self.active_bullets:
        #          if hasattr(bullet, 'position') and hasattr(bullet, 'radius'):
        #             try:
        #                 # Use id(bullet) as bullets might not have unique names/IDs across owners
        #                 self.collision_tree.insert(bullet.position, id(bullet), bullet.radius, 'bullet')
        #             except Exception as e:
        #                 logger.error(f"Error inserting bullet {id(bullet)} into QuadTree: {e}")
        #
        #     # Insert hazards (assuming they have position and radius)
        #     for hazard_id, hazard in self.hazards.items():
        #          if hasattr(hazard, 'position') and hasattr(hazard, 'radius'):
        #             try:
        #                 self.collision_tree.insert(hazard.position, hazard_id, hazard.radius, 'hazard')
        #             except Exception as e:
        #                 logger.error(f"Error inserting hazard {hazard_id} into QuadTree: {e}")
        #
        #     # Insert cover (assuming they have position and radius)
        #     for cover_id, cover_obj in self.cover_data.items():
        #         if isinstance(cover_obj, dict) and 'position' in cover_obj and 'radius' in cover_obj:
        #             try:
        #                 self.collision_tree.insert(cover_obj['position'], cover_id, cover_obj['radius'], 'cover')
        #             except Exception as e:
        #                 logger.error(f"Error inserting cover {cover_id} into QuadTree: {e}")
        # else:
        #     logger.warning("Collision tree not initialized or available for update.")

        # --- REMOVED: Collision Check Calls and Pickup Removal ---
        # # Check for collisions
        # collected_pickup_ids = self._check_pickup_collisions() if hasattr(self, 'collision_tree') else set()
        # bullet_hits = self._check_bullet_collisions() if hasattr(self, 'collision_tree') else set()

        # # Remove collected pickups (if tracking by ID)
        # # Assuming pickups are stored in a list and might need identification
        # if collected_pickup_ids:
        #     self.pickups = [p for p in self.pickups if id(p) not in collected_pickup_ids]
        # --- END REMOVED ---

        # Update safe zone, resources, weather, day cycle
        self._update_safe_zone(delta_time)

    # --- Lazy Loading Properties for System Dependencies ---

    @property
    def team_system(self) -> Optional[TeamSystem]:
        if self._team_system_instance is None:
            # --- MODIFIED: Use lowercase key --- 
            self._team_system_instance = system_manager.get_system("team_system") 
            # --- END MODIFIED ---
            if not self._team_system_instance:
                logger.warning("BattleRoyaleEnv: TeamSystem not found via SystemManager.")
        return self._team_system_instance

    @property
    def combat_system(self) -> Optional[CombatSystem]:
        if self._combat_system_instance is None:
            self._combat_system_instance = system_manager.get_system("CombatSystem")
            if not self._combat_system_instance:
                 logger.warning("BattleRoyaleEnv: CombatSystem not found via SystemManager.")
        return self._combat_system_instance

    @property
    def team_combat_integration(self) -> Optional["TeamCombatIntegration"]:
        if self._team_combat_integration_instance is None:
            # Import locally to avoid circular dependency
            try:
                self._team_combat_integration_instance = system_manager.get_system("TeamCombatIntegration")
                if not self._team_combat_integration_instance:
                    logger.info("BattleRoyaleEnv: TeamCombatIntegration not found via SystemManager.") # Use info, maybe expected
            except Exception as e:
                logger.error(f"Error getting TeamCombatIntegration: {e}")
        return self._team_combat_integration_instance

    @property
    def personality_system(self) -> Optional[PersonalitySystem]:
        if self._personality_system_instance is None:
            self._personality_system_instance = system_manager.get_system("PersonalitySystem")
            # No warning needed if not found, might be optional
        return self._personality_system_instance

    @property
    def agent_system(self) -> Optional["AgentSystem"]:
        if self._agent_system_instance is None:
            self._agent_system_instance = system_manager.get_system("AgentSystem")
            if not self._agent_system_instance:
                logger.warning("BattleRoyaleEnv: AgentSystem not found via SystemManager.")
        return self._agent_system_instance

    # --- ADDED: Lazy loader for MoraleSuppressionSystem ---
    @property
    def morale_suppression_system(self) -> Optional["MoraleSuppressionSystem"]:
        if self._morale_suppression_system is None:
            # Import locally to avoid potential circular import with AgentSystem
            try:
                from systems.morale.morale_suppression_system import MoraleSuppressionSystem
                self._morale_suppression_system = system_manager.get_system("morale_suppression_system")
                if not self._morale_suppression_system:
                    logger.warning("BattleRoyaleEnv: MoraleSuppressionSystem not found via SystemManager.")
            except ImportError:
                 logger.error("BattleRoyaleEnv: Failed to import MoraleSuppressionSystem.")
            except Exception as e:
                 logger.error(f"BattleRoyaleEnv: Error getting MoraleSuppressionSystem: {e}")
        return self._morale_suppression_system
    # --- End Lazy Loading Properties ---

    def initialize(self):
        """
        Final initialization after all systems are expected to be registered.
        Subscribes to events and performs initial setup requiring other systems.
        """
        try:
            # Subscribe to entity events
            system_manager.subscribe(SystemEventType.ENTITY_CREATED, self._handle_entity_created)
            system_manager.subscribe(SystemEventType.ENTITY_DESTROYED, self._handle_entity_destroyed)

            # --- ADDED: Subscribe to combat/action events needed for environment logic --- 
            system_manager.subscribe(SystemEventType.BULLET_FIRED, self._handle_bullet_fired)
            system_manager.subscribe(SystemEventType.HAZARD_ACTIVATED, self._handle_hazard_activated)
            system_manager.subscribe(SystemEventType.PICKUP_ACQUIRED, self._handle_pickup_acquired)
            # -------------------------------------------------------------------------------

            # Spawn initial resources/pickups if needed
            # self.spawn_initial_resources()
            # self.spawn_initial_pickups()
            
            # --- ADDED: Update player colors based on team --- 
            if self.team_system:
                for agent_id, agent_data in self.agents.items():
                    player_instance = agent_data.get('player')
                    if player_instance:
                        team_id = self.team_system.get_team_id_for_agent(agent_id)
                        if team_id and hasattr(self.team_system, 'get_team_color'):
                            player_instance.color = self.team_system.get_team_color(team_id)
                        # else: Player keeps default color set during registration
            else:
                logger.warning("Cannot update player team colors during env init: TeamSystem not found.")
            # -------------------------------------------------
            
            logger.info("BattleRoyaleEnv initialized event subscriptions and player colors.")
        except Exception as e:
            logger.error(f"Error during BattleRoyaleEnv initialization: {e}", exc_info=True)

    def create_agents(self, max_agents):
        """
        Create agents for the battle royale environment.
        
        Args:
            max_agents (int): Maximum number of agents to create
            
        Returns:
            list: Created agent objects
        """
        from systems.agents.agent_factory import create_agent
        
        agents = []
        for i in range(max_agents):
            # DEBUG: Print the contents of config.agent before access
            print(f"DEBUG: config.agent contents in create_agents: {config.agent}") 
            agent_types = config.agent.get('AGENT_TYPES', []) # Use .get() for safe access
            if not agent_types:
                logger.error("AGENT_TYPES configuration is missing or empty in config.agent. Cannot create agent.")
                continue # Skip creating this agent if no types are defined
            agent_type = random.choice(agent_types) # Choose from the list if not empty
            
            agent_name = f"{agent_type}-{i+1}"
            agent = create_agent(agent_type, agent_name)
            # Initialize the agent immediately after creation
            # --- ENSURED CORRECT STATE SIZE --- 
            state_size = STATE_VECTOR_SIZE # Use the size defined in AgentSystem
            # ----------------------------------
            action_size = 5 # Standard action size
            if hasattr(agent, 'initialize_agent'):
                agent.initialize_agent(state_size, action_size)
                logger.debug(f"Initialized agent {agent_name} ({agent_type}) with state_size={state_size}, action_size={action_size}")
            else:
                logger.warning(f"Agent {agent_name} ({agent_type}) does not have an initialize_agent method.")
            agents.append(agent)
            
            # Register agent in environment - FIND VALID SPAWN POINT FIRST
            valid_spawn = self._find_valid_spawn_point()
            if valid_spawn:
                 spawn_x, spawn_y = valid_spawn
                 self.register_agent(agent, spawn_x, spawn_y)
            else:
                 # Handle case where no valid spawn found (e.g., log error, skip agent?)
                 logger.error(f"Failed to find valid spawn for agent {agent_name}. Skipping registration.")
                 # Remove agent logic if registration failed?
                 agents.pop() # Remove the agent we couldn't place
                 # Need to handle potential issues if agent object is already referenced elsewhere

        logger.info(f"Created {len(agents)} agents for battle royale")
        return agents
    
    def _find_valid_spawn_point(self, agent_radius: float = 10, max_attempts: int = 50) -> Optional[Tuple[float, float]]:
        """Attempts to find a valid spawn point for an agent."""
        for _ in range(max_attempts):
            # Sample within a slightly smaller region than the whole map
            buffer = 50
            spawn_x = random.uniform(buffer, self.width - buffer)
            spawn_y = random.uniform(buffer, self.height - buffer)

            # 1. Check Terrain Passability
            if self.terrain_system.get_movement_modifier(spawn_x, spawn_y) < 0.1:
                continue # Spawning in impassable terrain

            # 2. Check Hazards
            if self.hazard_cover_system.check_hazard_effects(spawn_x, spawn_y):
                continue # Spawning inside cover

            # 3. Check Distance from other Agents
            min_dist_sq = (agent_radius * 2.1) ** 2 # Reduced multiplier from 2.5 to 2.1
            too_close = False
            for other_pos in self.agent_positions.values():
                dx = other_pos[0] - spawn_x
                dy = other_pos[1] - spawn_y
                if dx*dx + dy*dy < min_dist_sq:
                    too_close = True
                    break
            if too_close:
                continue # Spawning too close to another agent

            # --- ADDED: Check Distance from Safe Zone Center --- #
            dx_zone = spawn_x - self.safe_zone_center[0]
            dy_zone = spawn_y - self.safe_zone_center[1]
            if dx_zone*dx_zone + dy_zone*dy_zone > self.safe_zone_radius * self.safe_zone_radius:
                continue # Spawning outside the initial safe zone
            # --- END ADDED --- #

            return spawn_x, spawn_y

        return None # Failed to find a valid spawn point

    def register_agent(self, agent, x, y):
        """
        Register an agent in the environment.
        
        Args:
            agent: Agent object
            x (float): Initial x position
            y (float): Initial y position
        """
        agent_id = agent.name # Store ID for convenience
        self.agents[agent_id] = agent # Initially just store agent logic
        self.agent_positions[agent_id] = (x, y)
        self.agent_health[agent_id] = 100.0
        self.agent_energy[agent_id] = 100.0
        self.agent_scores[agent_id] = 0

        # --- MODIFIED: Create Player object with DEFAULT color --- #
        screen_w = self.config.display['SCREEN_WIDTH']
        screen_h = self.config.display['SCREEN_HEIGHT']
        # Use a default color now, team color will be set in initialize()
        # REMOVED: team_id = self.team_system.get_team_id_for_agent(agent.name) if self.team_system else None 
        # REMOVED: if team_id is not None and self.team_system and hasattr(self.team_system, 'get_team_color'):
        # REMOVED:     player_base_color = self.team_system.get_team_color(team_id) # Returns tuple
        # REMOVED: else:
        # REMOVED:     player_base_color = tuple(self.config.colors.get('BLUE', [0, 0, 255]))
        player_base_color = tuple(self.config.colors.get('WHITE', [255, 255, 255])) # Use WHITE as default

        player_instance = Player(
            x=x,
            y=y,
            color=player_base_color,
            screen_width=screen_w,
            screen_height=screen_h,
            bullet_color=tuple(self.config.colors.get('WHITE', [255, 255, 255])),
            health_color=tuple(self.config.colors.get('GREEN', [0, 255, 0])),
            energy_color=tuple(self.config.colors.get('CYAN', [0, 255, 255])),
            indicator_color=tuple(self.config.colors.get('WHITE', [255, 255, 255])),
            hit_color=tuple(self.config.colors.get('RED', [255, 0, 0])),
            name=agent.name
        )
        # Store both the agent logic and the player representation
        # Ensure the agent_id exists before trying to create the inner dict
        self.agents[agent_id] = {'agent': agent, 'player': player_instance}
        # ---------------------------------------------------------- #
    
    def update(self, delta_time):
        """
        Update the environment by delegating to specialized systems.

        Args:
            delta_time (float): Time since last update in seconds
        """
        super().update(delta_time)

        # --- Update Game State ---
        if not self.between_rounds:
            self.round_time += 1
            if self.round_time >= self.max_round_time:
                self.between_rounds = True
                self.round_time = 0
                self.emit_event("round_ended", {"round": self.round_number})
                self.round_number += 1
        else:
            self.round_time += 1
            if self.round_time >= self.round_end_delay:
                self.between_rounds = False
                self.round_time = 0
                self.emit_event("round_started", {"round": self.round_number})

        # --- Update Core Environment Systems ---
        if self.terrain_system:
             self.terrain_system.update(delta_time)
        else:
             logger.warning("TerrainSystem not found during update.")

        if self.resource_manager:
             self.resource_manager.update() # Assumes ResourceManager handles its own delta_time logic if needed
        else:
             logger.warning("ResourceManager not found during update.")

        # --- Remove SafeZoneSystem check --- 
        # if self.safe_zone_system: # Assuming a SafeZoneSystem exists or will be created
        #     self.safe_zone_system.update(delta_time)
        # else:
        # Fallback to internal method if no dedicated system
        self._update_safe_zone(delta_time) # Use internal method directly
        # logger.debug("SafeZoneSystem not found, using internal _update_safe_zone.")
        # --- End Remove --- 

        if self.hazard_cover_system:
             self.hazard_cover_system.update(delta_time)

        if self.weather_system:
             self.weather_system.update()
        else:
             # Fallback to internal method if no dedicated system
             self._update_weather(delta_time) # Keep for now if no dedicated system
             logger.debug("WeatherSystem not found, using internal _update_weather.")


        if self.time_system:
             self.time_system.update()
        else:
             # Fallback to internal method if no dedicated system
             self._update_day_cycle(delta_time) # Keep for now if no dedicated system
             logger.debug("TimeSystem not found, using internal _update_day_cycle.")

        # --- Update Combat-Related Systems ---
        if self.combat_system:
            self.combat_system.update_status_effects(delta_time)
        # else: No warning needed if optional

        # if self.team_combat_integration: # Keep commented out if placeholder
        #     pass

        # --- Update Bullets ---
        inactive_bullets = []
        for bullet in self.active_bullets:
            if not bullet.update(): # Call the Bullet object's update method
                 inactive_bullets.append(bullet)

        if inactive_bullets:
             for bullet in inactive_bullets:
                 self._release_bullet(bullet) # Use helper method for releasing

        # --- Update Enemies ---
        # (Existing enemy update logic remains here for now)
        enemies_to_remove = []
        for enemy_id, enemy in list(self.enemies.items()): # Use list() for safe iteration
            if not enemy.is_alive:
                enemies_to_remove.append(enemy_id)
                continue

            wants_to_shoot = enemy.update()

            if wants_to_shoot and enemy.target_player and enemy.target_player.is_alive:
                # (Existing enemy shooting logic)
                # Attempt to get a bullet from the pool
                bullet = self.bullet_pool.get()
                if bullet:
                    # Calculate angle to target
                    target = enemy.target_player
                    dx = target.x - enemy.x
                    dy = target.y - enemy.y
                    shoot_angle = math.degrees(math.atan2(-dy, dx)) # Note: atan2 convention

                    # Calculate spawn position slightly ahead of the enemy
                    bullet_radius = getattr(bullet, 'radius', 5)
                    spawn_offset = (enemy.width / 2) + bullet_radius + 2 # Offset from center
                    spawn_x = enemy.x + (enemy.width / 2) + math.cos(math.radians(shoot_angle)) * spawn_offset
                    spawn_y = enemy.y + (enemy.height / 2) - math.sin(math.radians(shoot_angle)) * spawn_offset

                    # Reset and activate the bullet
                    enemy_bullet_color = tuple(self.config.colors.get('RED', [255, 0, 0]))
                    bullet.reset(
                        x=spawn_x,
                        y=spawn_y,
                        angle=shoot_angle,
                        color=enemy_bullet_color,
                        owner=enemy_id # Identify the enemy as the owner
                    )
                    self.active_bullets.append(bullet)
                    # logger.debug(f"Enemy {enemy_id} fired a bullet at {target.name}.") # Reduce log noise
                # else: logger.warning(f"Enemy {enemy_id} wants to shoot, but bullet pool is empty.") # Reduce log noise

        # --- Update Collision Tree ---
        # (Collision tree update logic can remain here, as Env owns the entities)
        self.collision_tree.clear()
        # Agents
        for agent_id, agent in self.agents.items():
            pos = self.agent_positions.get(agent_id)
            if pos:
                radius = getattr(agent, 'radius', 10)
                self.collision_tree.insert(pos, agent_id, radius, 'agent')
            # else: logger.warning(f"Position not found for agent {agent_id} during collision tree update.") # Reduce log noise

        # Active Bullets
        for bullet in self.active_bullets:
            if bullet.active:
                bullet_id = id(bullet)
                pos = (bullet.x, bullet.y)
                radius = bullet.radius
                self.collision_tree.insert(pos, bullet_id, radius, 'bullet')

        # Pickups
        for pickup in self.pickups:
            pickup_id = pickup.get('id')
            pos = pickup.get('position')
            radius = pickup.get('radius', 8)
            if pickup_id and pos:
                self.collision_tree.insert(pos, pickup_id, radius, 'pickup')

        # Hazards
        for hazard_id, hazard in self.hazards.items():
            pos = hazard.get('position')
            radius = hazard.get('radius', 15)
            if pos:
                self.collision_tree.insert(pos, hazard_id, radius, 'hazard')

        # --- Collision Checks ---
        # These methods perform checks and emit events or directly resolve effects
        collided_bullets = self._check_bullet_collisions() # Returns set of collided bullet objects
        collided_pickups = self._check_pickup_collisions() # Returns set of collected pickup IDs

        # Remove collided bullets (if not already handled by _check_bullet_collisions)
        # Decision: Assume _check_bullet_collisions handles deactivation/release
        # for bullet in collided_bullets:
        #     self._release_bullet(bullet)

        # Remove collected pickups
        self.pickups = [p for p in self.pickups if p.get('id') not in collided_pickup_ids]

        # Handle dead enemies (queued earlier)
        for enemy_id in enemies_to_remove:
            # Trigger destruction via event (actual removal in handler)
             self.emit_event(SystemEventType.ENTITY_DESTROYED, {
                 'entity_id': enemy_id,
                 'entity_type': 'enemy',
                 'reason': 'health_depleted'
             })
             logger.debug(f"Queued removal for dead enemy {enemy_id}.")

    def _update_safe_zone(self, delta_time):
        """Update the safe zone size and apply damage to agents outside it"""
        # --- REVISED: Use delta_time as frames/ticks, implement warning/shrink cycle ---
        delta_time_frames = delta_time * self.target_fps # Convert seconds to frames/ticks

        self.shrink_timer -= delta_time_frames

        # Update warning timer if active
        if self.safe_zone_warning_timer > 0:
            self.safe_zone_warning_timer -= delta_time_frames
            if self.safe_zone_warning_timer <= 0:
                self.safe_zone_warning_timer = 0 # Clamp to zero

        # Time to shrink?
        if self.shrink_timer <= 0:
            if self.safe_zone_radius > self.min_safe_zone_radius:
                # Perform the shrink
                self.safe_zone_radius = self.next_safe_zone_radius
                logger.info(f"Safe zone shrunk to {self.safe_zone_radius:.2f}")

                # Calculate the NEXT shrink target and reset timers
                # Example: Shrink by a fixed percentage or amount
                shrink_factor = config.get("game", "ZONE_SHRINK_FACTOR", 0.8) # e.g., shrink to 80%
                self.next_safe_zone_radius = max(self.min_safe_zone_radius, self.safe_zone_radius * shrink_factor)
                self.shrink_timer = self.shrink_interval # Reset interval timer
                self.safe_zone_warning_timer = self.shrink_warning_time # Start warning timer for next shrink
                logger.info(f"Next shrink target: {self.next_safe_zone_radius:.2f}. Warning timer started ({self.safe_zone_warning_timer / self.target_fps:.1f}s).")

                # Emit event about the upcoming shrink
                self.emit_event(SystemEventType.ZONE_CHANGED, {
                    "current_radius": self.safe_zone_radius,
                    "next_radius": self.next_safe_zone_radius,
                    "warning_time_frames": self.safe_zone_warning_timer,
                    "center": self.safe_zone_center
                })
            else:
                # Zone is at minimum size, stop shrinking
                self.shrink_timer = float('inf') # Prevent further shrinking
                self.safe_zone_warning_timer = 0
                self.next_safe_zone_radius = self.safe_zone_radius

        # Apply damage to agents outside the CURRENT safe zone
        for agent_name, position in list(self.agent_positions.items()):
            if agent_name not in self.agent_health or agent_name not in self.agent_positions:
                 continue # Agent might have been eliminated by another system or previous loop iteration
            dx = position[0] - self.safe_zone_center[0]
            dy = position[1] - self.safe_zone_center[1]
            distance = math.sqrt(dx*dx + dy*dy)

            if distance > self.safe_zone_radius:
                # Use delta_time (seconds) directly for damage calculation
                damage = self.zone_damage * delta_time
                self.agent_health[agent_name] -= damage
                self.emit_event(SystemEventType.AGENT_DAMAGED, {
                    "target_id": agent_name,
                    "damage": damage,
                    "source": "zone"
                })

                # Check if agent is eliminated
                if self.agent_health[agent_name] <= 0:
                    pass # Agent takes damage but is not eliminated by the zone

    def _update_resource_spawning(self, delta_time):
        """Update resource and pickup spawning"""
        # Spawn resources
        self.resource_spawn_timer += 1
        if self.resource_spawn_timer >= self.resource_spawn_interval:
            self.resource_spawn_timer = 0
            self._spawn_resource()
        
        # Spawn pickups
        self.pickup_spawn_timer += 1
        if self.pickup_spawn_timer >= self.pickup_spawn_interval:
            self.pickup_spawn_timer = 0
            self._spawn_pickup()
    
    def _update_weather(self, delta_time):
        """Update weather conditions"""
        # Random weather changes
        if random.random() < 0.001:  # 0.1% chance per frame
            new_weather = random.choice(self.weather_conditions)
            self.current_weather = new_weather
            self.weather_intensity = random.uniform(0.3, 1.0)
            self.emit_event("weather_changed", {
                "condition": new_weather,
                "intensity": self.weather_intensity
            })
    
    def _update_day_cycle(self, delta_time):
        """Update day/night cycle"""
        day_length = 300  # 5 minutes for full day/night cycle
        cycle_increment = delta_time / day_length
        self.day_time = (self.day_time + cycle_increment) % 1.0
    
    def _spawn_resource(self):
        """Spawn a resource in the environment"""
        resource_type = random.choice(['energy', 'health', 'shield'])
        
        # Place within safe zone with some margin
        radius = random.uniform(0, self.safe_zone_radius * 0.8)
        angle = random.uniform(0, math.pi * 2)
        x = self.safe_zone_center[0] + radius * math.cos(angle)
        y = self.safe_zone_center[1] + radius * math.sin(angle)
        
        # Add to resource manager
        self.resource_manager.spawn_node(x, y, resource_type)
        
        # Emit event
        self.emit_event("resource_spawned", {
            "type": resource_type,
            "position": (x, y)
        })
    
    def _spawn_pickup(self):
        """Spawn a pickup in the environment"""
        pickup_type = random.choice(self.pickup_types)
        
        # Place randomly within the environment
        x = random.randint(50, self.width - 50)
        y = random.randint(50, self.height - 50)
        
        # Add to pickups list
        self.pickups.append({
            "type": pickup_type,
            "position": (x, y),
            "value": random.randint(20, 50)  # Random value based on pickup type
        })
        
        # Emit event
        self.emit_event("pickup_spawned", {
            "type": pickup_type,
            "position": (x, y)
        })
    
    def _eliminate_agent(self, agent_name, cause, killer_id=None):
        """
        Eliminate an agent from the battle.
        
        Args:
            agent_name (str): Name of the agent to eliminate
            cause (str): Cause of elimination (zone, combat, etc.)
            killer_id (str): ID of the killer agent (if applicable)
        """
        if agent_name in self.agents:
            # --- REMOVED TEMPORARY LOGGING ---
            # logger.warning(f"TEMPLOG: Eliminating agent '{agent_name}' due to cause: '{cause}' (Killer: {killer_id})")
            # --- END REMOVED TEMPORARY LOGGING ---
            # Record elimination
            self.eliminated_agents[agent_name] = {
                "score": self.agent_scores[agent_name],
                "cause": cause,
                "round": self.round_number,
                "time": self.round_time
            }
            
            # Remove from active tracking
            self.agents.pop(agent_name, None)
            self.agent_positions.pop(agent_name, None)
            self.agent_health.pop(agent_name, None)
            self.agent_energy.pop(agent_name, None)
            
            # Emit event
            self.emit_event("agent_eliminated", {
                "agent": agent_name,
                "cause": cause,
                "score": self.agent_scores[agent_name],
                "killer_id": killer_id
            })
    
    def spawn_initial_resources(self):
        """Spawn initial resources in the environment"""
        num_resources = random.randint(5, 10)
        for _ in range(num_resources):
            self._spawn_resource()
    
    def get_terrain_modifier(self, x, y):
        """
        Get movement modifier for the terrain at the given position.
        
        Args:
            x (float): X position
            y (float): Y position
            
        Returns:
            float: Movement speed modifier (0.0-1.0)
        """
        return self.terrain_system.get_movement_modifier(x, y)
    
    def get_visibility(self):
        """
        Get current visibility based on weather and time of day.
        
        Returns:
            float: Visibility factor (0.0-1.0)
        """
        # Weather affects visibility
        weather_visibility = {
            'clear': 1.0,
            'rain': 0.7,
            'fog': 0.4,
            'storm': 0.3
        }.get(self.current_weather, 1.0) * (1 - self.weather_intensity * 0.5)
        
        # Time of day affects visibility
        time_visibility = 0.3 + 0.7 * math.sin(math.pi * self.day_time)
        
        return weather_visibility * time_visibility
    
    def render(self, delta_time: float) -> None:
        """Renders the environment state, including terrain, resources, hazards, and effects.

        Args:
            delta_time (float): Time elapsed since the last frame.
        """
        # logger.debug(f"BattleRoyaleEnv.render called with delta_time: {delta_time}")

        # Attempt to get the visualization system (preferred renderer)
        # --- FIXED: Use inherited get_system method ---
        vis_integration = self.get_system("visualization_integration")
        # --- END FIX ---
        if not vis_integration or not hasattr(vis_integration, 'renderer'):
            logger.warning("VisualizationIntegration or its renderer not available for BattleRoyaleEnv rendering.")
            # Decide if basic rendering should happen here or if it's an error
            return # Exit if no visualization integration is found

        renderer = vis_integration.renderer
        if not renderer.is_initialized():
            logger.warning("Renderer is not initialized. Skipping BattleRoyaleEnv rendering.")
            return

        # Render terrain
        # logger.debug("Rendering terrain...")
        self.terrain_system.draw(renderer)

        # Render resources
        # logger.debug("Rendering resources...")
        self.resource_manager.draw(renderer)

        # Render hazards and cover
        # logger.debug("Rendering hazards and cover...")
        self.hazard_cover_system.draw(renderer)

        # Render environmental effects (e.g., weather, safe zone)
        # logger.debug("Rendering environmental effects...")
        self.weather_system.draw(renderer)
        self._render_safe_zone(renderer)

        # Render bullets
        for bullet in self.active_bullets:
            bullet.draw(renderer)

        # NOTE: Agent rendering is now handled by VisualizationIntegration.render
        # logger.debug("Agent rendering responsibility moved to VisualizationIntegration.")

    def _render_safe_zone(self, renderer):
        # Render safe zone
        safe_zone_color = Color(*self.config.colors.get('GREEN', [0, 255, 0]))
        renderer.draw_circle(self.safe_zone_center[0], self.safe_zone_center[1],
                             self.safe_zone_radius, safe_zone_color.with_alpha(60),
                             filled=False, is_world_space=True)
        if self.safe_zone_warning_timer > 0 and self.next_safe_zone_radius < self.safe_zone_radius:
            warning_radius = self.next_safe_zone_radius
            warning_color = Color(*self.config.colors.get('YELLOW', [255, 255, 0]))
            blink_alpha = 150 if int(time.time() * 4) % 2 == 0 else 50 # Use current_time for blink
            renderer.draw_circle(self.safe_zone_center[0], self.safe_zone_center[1],
                                 warning_radius, warning_color.with_alpha(blink_alpha),
                                 filled=False, is_world_space=True)

    def _spawn_random_hazard(self):
        """Spawn a random hazard, preferably outside the safe zone"""
        hazard_types = list(self.hazard_cover_system.hazard_types.keys())
        if not hazard_types:
            logger.warning("No hazard types defined in HazardCoverSystem.")
            return
        hazard_type = random.choice(hazard_types)
        
        # Try to place outside the safe zone
        for _ in range(10):  # Try 10 times
            angle = random.uniform(0, 2 * math.pi)
            # Place somewhere between the safe zone edge and the map edge
            if hasattr(self, 'safe_zone_radius') and self.safe_zone_radius > 0:
                distance = random.uniform(self.safe_zone_radius * 1.1, 
                                         min(self.width, self.height) * 0.5)
                x = self.safe_zone_center[0] + math.cos(angle) * distance
                y = self.safe_zone_center[1] + math.sin(angle) * distance
                
                # Check if in bounds
                if (0 <= x < self.width and 0 <= y < self.height):
                    self.hazard_cover_system.add_hazard(hazard_type, x, y)
                    return
        
        # If all attempts failed, just spawn randomly on the map
        x = random.uniform(0, self.width)
        y = random.uniform(0, self.height)
        self.hazard_cover_system.add_hazard(hazard_type, x, y)

    def check_hazard_effects(self, agent):
        """Check if an agent is in a hazard and apply effects"""
        hazard_effects = self.hazard_cover_system.check_hazard_effects(agent.position[0], agent.position[1])
        
        if hazard_effects: # Check if the list is not empty
            applied_damage_this_step = 0
            for hazard_effect in hazard_effects:
                damage = hazard_effect.get('damage', 0)
                # Apply damage per second, scaled by delta_time (or frame rate)
                # Assuming check_hazard_effects is called every frame
                damage_per_frame = damage * (1.0 / self.target_fps)
                
                effect_type = hazard_effect.get('effect')
                # Assuming duration is in frames, convert to seconds if needed
                effect_duration = hazard_effect.get('duration', 0) / self.target_fps
                
                if damage_per_frame > 0:
                    agent.apply_damage(damage_per_frame)
                    applied_damage_this_step += damage_per_frame
                    
                    self.emit_event(SystemEventType.AGENT_DAMAGED, {
                        'agent_id': agent.id, # Use agent.id
                        'damage': damage_per_frame,
                        'source': f"hazard_{hazard_effect.get('type', 'unknown')}",
                        # 'hazard_id': hazard_id # hazard_id not available here
                    })
                
                if effect_type and hasattr(agent, 'apply_status_effect'):
                    try:
                        agent.apply_status_effect(effect_type, effect_duration)
                    except Exception as e:
                        logger.error(f"Error applying status effect {effect_type} to {agent.id}: {e}")
            
            # Log cumulative damage per frame if any
            if applied_damage_this_step > 0:
                logger.debug(f"Agent {agent.id} took {applied_damage_this_step:.2f} total damage from hazards this frame.")
                if not agent.alive:
                    self._eliminate_agent(agent.id, cause="hazard")
            return True # Agent was affected by at least one hazard
            
        return False
        
    def calculate_damage_modifier(self, attacker, target):
        """Calculate a damage modifier based on cover and other factors"""
        if not self.combat_system:
            return 1.0
            
        # Base modifier from cover
        cover_modifier = 1.0
        
        # Get positions
        ax, ay = attacker.position
        tx, ty = target.position
        
        # Check cover using combat system
        if self.combat_system.cover_system.check_cover(ax, ay, tx, ty):
            cover_modifier = 0.5  # 50% damage when in cover
            
        # Check hazard cover system for more advanced cover
        if self.hazard_cover_system.is_position_in_cover(tx, ty):
            cover_modifier = min(cover_modifier, 0.6)  # Use stronger cover effect
            
        # Apply team-based modifiers if available
        if self.team_combat_integration:
            # Get team attack bonus for the attacker
            team_attack_bonus = self.team_combat_integration.calculate_team_attack_bonus(
                attacker.id, target.id, attacker.position, target.position
            )
            
            # Get team defense bonus for the defender
            defense_bonus = self.team_combat_integration.calculate_defense_bonus(
                target.id, attacker.id
            )
            
            # Final modifier combines cover, team attack, and team defense
            return cover_modifier * team_attack_bonus.get("damage", 1.0) * defense_bonus
            
        return cover_modifier
    
    def damage_cover(self, x, y, damage):
        """Apply damage to cover at the specified position"""
        return self.hazard_cover_system.damage_cover(x, y, damage)
    
    def is_position_in_cover(self, x, y):
        """Check if position provides cover"""
        return self.hazard_cover_system.is_position_in_cover(x, y) is not None

    def process_combat_event(self, event_type, data):
        """Process a combat event and update relevant systems"""
        if not self.combat_system:
            return
            
        if event_type == "attack":
            attacker_id = data.get("attacker_id")
            target_id = data.get("target_id")
            damage = data.get("damage", 0)
            
            # Update team combat stats
            if self.team_combat_integration and attacker_id and damage > 0:
                self.team_combat_integration.update_team_stats(attacker_id, damage=damage)
                
        elif event_type == "kill":
            killer_id = data.get("killer_id")
            victim_id = data.get("victim_id")
            
            # Record kill in combat system
            if killer_id and victim_id:
                self.combat_system.record_kill(killer_id, victim_id)
                
                # Update team combat stats
                if self.team_combat_integration:
                    self.team_combat_integration.update_team_stats(killer_id, kill=True)
                    
        elif event_type == "ability_used":
            team_id = data.get("team_id")
            ability = data.get("ability")
            initiator = data.get("initiator")
            target = data.get("target_position")
            
            # Execute team ability
            if self.team_combat_integration and team_id and ability and initiator:
                self.team_combat_integration.execute_team_ability(team_id, ability, initiator, target) 
                
    def get_nearby_agents(self, position: Tuple[float, float], radius: float) -> List[Any]:
        """
        Get agents within a certain radius using the QuadTree.
        
        Args:
            position: The center position (x, y) to query around.
            radius: The radius of the query area.
            
        Returns:
            List of agent objects found within the radius.
        """
        query_box = AABB(position[0] - radius, position[1] - radius, radius * 2, radius * 2)
        # Query returns tuples of (point, entity) - we only need the entity
        nearby_results = self.collision_tree.query_range(query_box)
        
        # Filter results to ensure they are agents and within the circular radius
        nearby_agents = []
        for point, entity_id, entity_radius, entity_type in nearby_results:
            # Check if the entity is actually an agent and within the circular radius
            if entity_type == 'agent':
                dx = position[0] - point[0]
                dy = position[1] - point[1]
                if math.sqrt(dx*dx + dy*dy) <= radius:
                    # --- MODIFIED: Use entity_id to get agent object ---
                    agent = self.agents.get(entity_id)
                    if agent: # Check if agent exists
                       nearby_agents.append(agent)
        return nearby_agents

    def _check_pickup_collisions(self) -> set:
        """Check for collisions between agents and pickups using the QuadTree.
        Returns a set of IDs of pickups that were collected.
        """
        collected_pickup_ids = set() # Track pickup IDs collected this frame
        
        for agent_name, agent_pos in self.agent_positions.items():
            if agent_name not in self.agents:
                continue # Skip eliminated agents
            
            agent = self.agents[agent_name]
            agent_radius = getattr(agent, 'radius', 10) 
            
            # Define query area around agent
            query_radius = agent_radius + 10 # Agent radius + max pickup radius
            query_box = AABB(center_x=agent_pos[0], center_y=agent_pos[1], half_width=query_radius, half_height=query_radius)
                             
            potential_collisions = self.collision_tree.query_range(query_box)
            
            for pickup_pos, pickup_id, pickup_radius, entity_type in potential_collisions:
                if entity_type == "pickup" and pickup_id not in collected_pickup_ids:
                    # Precise distance check
                    dx = agent_pos[0] - pickup_pos[0]
                    dy = agent_pos[1] - pickup_pos[1]
                    distance_sq = dx*dx + dy*dy
                    combined_radius_sq = (agent_radius + pickup_radius)**2
                            
                    if distance_sq <= combined_radius_sq:
                        # Collision detected!
                        pickup_data = next((p for p in self.pickups if p.get('id') == pickup_id), None)
                        
                        if pickup_data:
                            pickup_type = pickup_data.get('type', 'unknown')
                            logger.info(f"Agent {agent_name} collected pickup {pickup_type} (ID: {pickup_id})")
                            
                            # Apply effect
                            if hasattr(agent, 'apply_pickup'):
                                agent.apply_pickup(pickup_data)
                            else:
                                if pickup_type == 'health':
                                    self.agent_health[agent_name] = min(100, self.agent_health.get(agent_name, 0) + pickup_data.get('value', 20))
                                elif pickup_type == 'energy':
                                     self.agent_energy[agent_name] = min(100, self.agent_energy.get(agent_name, 0) + pickup_data.get('value', 20))
                            
                            collected_pickup_ids.add(pickup_id) 
                            self.emit_event(SystemEventType.RESOURCE_COLLECTED, {'agent_id': agent_name, 'pickup_id': pickup_id, 'type': pickup_type})
                        else:
                            logger.warning(f"Collected pickup ID {pickup_id} not found in self.pickups list.")

        # Remove collected pickups from the main list
        if collected_pickup_ids:
            original_pickup_count = len(self.pickups)
            self.pickups = [p for p in self.pickups if p.get('id') not in collected_pickup_ids]
            removed_count = original_pickup_count - len(self.pickups)
            if removed_count != len(collected_pickup_ids):
                 logger.warning(f"Mismatch removing pickups: Expected {len(collected_pickup_ids)}, Removed {removed_count}")
            logger.debug(f"Removed {removed_count} pickups.")
            # Also emit destroy events for pickups
            for pickup_id in collected_pickup_ids:
                 self.emit_event(SystemEventType.ENTITY_DESTROYED, {'type': 'pickup', 'id': pickup_id, 'reason': 'collected'})
        
        return collected_pickup_ids

    def _check_bullet_collisions(self) -> set:
        """Check bullet collisions using QuadTree. Returns set of collided bullet IDs."""
        collided_bullet_ids = set()
        bullets_to_check = list(self.active_bullets)

        for bullet in bullets_to_check:
            if not bullet.active or id(bullet) in collided_bullet_ids:
                continue

            bullet_id = id(bullet)
            bullet_pos = (bullet.x, bullet.y)
            bullet_radius = bullet.radius
            bullet_owner_id = bullet.owner
            bullet_damage = getattr(bullet, 'damage', 10)

            if bullet_owner_id is None:
                logger.warning(f"Skipping bullet {bullet_id} due to missing owner_id.")
                continue

            search_radius = bullet_radius + 50
            query_box = AABB(center_x=bullet_pos[0], center_y=bullet_pos[1], half_width=search_radius, half_height=search_radius)
            nearby_entities = self.collision_tree.query_range(query_box)

            for entity_pos, entity_id, entity_radius, entity_type in nearby_entities:
                if entity_id == bullet_id or entity_id == bullet_owner_id:
                    continue
                 # Prevent bullets colliding with each other for now
                if entity_type == 'bullet':
                    continue

                distance_sq = (bullet_pos[0] - entity_pos[0])**2 + (bullet_pos[1] - entity_pos[1])**2
                collision_distance_sq = (bullet_radius + entity_radius)**2

                # --- ADDED: Check for Near Miss (Suppression) --- #
                if entity_type == 'agent':
                    near_miss_margin = self.morale_suppression_system._config.get("SUPPRESSION_NEAR_MISS_MARGIN", 10.0) if self.morale_suppression_system else 10.0
                    near_miss_threshold_sq = (bullet_radius + entity_radius + near_miss_margin)**2

                    if collision_distance_sq < distance_sq <= near_miss_threshold_sq:
                        # This is a near miss
                        target_agent_id = entity_id # The agent that was nearly missed
                        proximity = math.sqrt(distance_sq) - (bullet_radius + entity_radius)

                        if self.morale_suppression_system:
                            base_increase = self.morale_suppression_system._suppression_event_modifiers.get("near_miss_bullet", 0.1)
                            # Scale suppression based on how close the miss was within the margin
                            scaling_factor = max(0, 1.0 - (proximity / near_miss_margin))
                            suppression_amount = base_increase * scaling_factor
                            self.morale_suppression_system.apply_suppression_increase(target_agent_id, suppression_amount, f"near_miss_{proximity:.1f}u")
                            # Emit an event as well? Optional.
                            # self.emit_event(SystemEventType.NEAR_MISS_DETECTED, { 'attacker_id': bullet_owner_id, 'target_id': target_agent_id, 'proximity': proximity, 'bullet_id': bullet_id })
                        # Do not break here, the bullet continues until it hits something or expires
                # --- End Near Miss Check --- #

                if distance_sq <= collision_distance_sq:
                    # Collision detected!
                    if entity_type == 'agent':
                        target_agent_obj = self.agents.get(entity_id)
                        if not target_agent_obj: # Check if agent exists
                            logger.warning(f"Bullet {bullet_id} collided with non-existent agent {entity_id}.")
                            continue # Skip this collision

                        # --- Resolve Hit/Miss --- #
                        resolution = self._resolve_hit(bullet, target_agent_obj)
                        attacker_id = bullet_owner_id # Use owner from bullet
                        target_id = entity_id
                        weapon_type = bullet.weapon_type

                        if resolution['result'] == 'hit':
                            logger.debug(f"Bullet {bullet_id} HIT agent {target_id}.")
                            self.emit_event(SystemEventType.ATTACK_HIT, {
                                'attacker_id': attacker_id,
                                'target_id': target_id,
                                'weapon_type': weapon_type,
                                'bullet_id': bullet_id,
                                'position': entity_pos
                            })

                            # --- Calculate Damage --- #
                            if self.combat_system:
                                attacker_pos = bullet.attacker_start_pos # Use start pos from bullet
                                target_pos = entity_pos
                                base_damage = getattr(bullet, 'damage', 10)

                                if attacker_pos:
                                    environment_context = {
                                        "weather": self.current_weather,
                                        "weather_intensity": self.weather_intensity,
                                        "time_of_day": self.day_time,
                                        "is_outside_safe_zone": math.sqrt((target_pos[0] - self.safe_zone_center[0])**2 + (target_pos[1] - self.safe_zone_center[1])**2) > self.safe_zone_radius
                                    }
                                    final_damage = self.combat_system.calculate_final_damage(
                                        attacker_id=attacker_id,
                                        target_id=target_id,
                                        attacker_pos=attacker_pos,
                                        target_pos=target_pos,
                                        base_damage=base_damage,
                                        weapon_type=weapon_type,
                                        environment_context=environment_context
                                    )
                                    if final_damage > 0:
                                        damage_data = {
                                            'target_id': target_id,
                                            'attacker_id': attacker_id,
                                            'damage': final_damage,
                                            'weapon_type': weapon_type,
                                            'position': target_pos,
                                            'critical': False # TODO: Need crit info from CombatSystem?
                                        }
                                        # Emit damage event, AgentSystem should handle health update
                                        self.emit_event(SystemEventType.AGENT_DAMAGED, damage_data)
                                        logger.debug(f"Damage calculated: {final_damage:.2f} to {target_id}.")
                                else:
                                     logger.debug(f"Damage calculation resulted in zero or negative damage for hit on {target_id}.")
                            else:
                                logger.warning("CombatSystem not available (lazy load failed?), cannot calculate damage.")
                        else:
                            logger.warning("CombatSystem not available (lazy load failed?), cannot calculate damage.")

                        # --- End Damage Calculation --- #

                    elif resolution['result'] == 'miss':
                        miss_reason = resolution.get('reason', 'unknown')
                        logger.debug(f"Bullet {bullet_id} MISSED agent {target_id} (Reason: {miss_reason}).")
                        self.emit_event(SystemEventType.ATTACK_MISS, {
                            'attacker_id': attacker_id,
                            'target_id': target_id,
                            'weapon_type': weapon_type,
                            'bullet_id': bullet_id,
                            'reason': miss_reason,
                            'position': entity_pos # Position of the target at time of miss check
                        })

                    # --- Release Bullet after processing agent collision --- #
                    self._release_bullet(bullet)
                    collided_bullet_ids.add(bullet_id)
                    break # Bullet processed, move to next bullet

                elif entity_type == 'hazard':
                    # Bullet hits a hazard. Hazards are timed effects managed by
                    # HazardCoverSystem and are not currently triggerable or
                    # destructible by bullets. Destroy the bullet.
                    logger.debug(f"Bullet {bullet_id} hit hazard {entity_id}. Destroying bullet.")
                    self._release_bullet(bullet)
                    collided_bullet_ids.add(bullet_id)
                    break # Bullet is destroyed

                elif entity_type == 'cover':
                    # Bullet hits cover
                    if not self.hazard_cover_system:
                        logger.warning(f"Bullet {bullet_id} hit cover {entity_id}, but hazard_cover_system is missing.")
                        self._release_bullet(bullet) # Still destroy bullet
                        collided_bullet_ids.add(bullet_id)
                        break

                    cover_piece = self.hazard_cover_system.get_cover_by_id(entity_id)
                    if cover_piece and cover_piece.get('destructible', False):
                        cover_damage = getattr(bullet, 'cover_damage', bullet_damage) # Use specific cover damage if available
                        hit_position = (bullet.x, bullet.y) # Approx hit position
                        self.hazard_cover_system.damage_cover(entity_id, cover_damage, hit_position)
                        logger.debug(f"Bullet {bullet_id} hit destructible cover {entity_id} for {cover_damage} damage.")
                        self._release_bullet(bullet)
                        collided_bullet_ids.add(bullet_id)
                        break # Bullet is destroyed
                    elif cover_piece:
                        logger.debug(f"Bullet {bullet_id} hit non-destructible cover {entity_id}. Destroying bullet.")
                        self._release_bullet(bullet)
                        collided_bullet_ids.add(bullet_id)
                        break # Bullet destroyed by non-destructible cover
                    else:
                        logger.warning(f"Bullet {bullet_id} hit cover entity ID {entity_id}, but cover piece not found.")
                        self._release_bullet(bullet) # Destroy bullet anyway
                        collided_bullet_ids.add(bullet_id)
                        break
                else:
                    # Collision with unknown entity type
                    logger.warning(f"Bullet {bullet_id} collided with unknown entity type '{entity_type}' (ID: {entity_id}).")
                    # Optionally destroy bullet or ignore
                    self._release_bullet(bullet)
                    collided_bullet_ids.add(bullet_id)
                    break # Ensure bullet is destroyed on any collision

        return collided_bullet_ids

    def _handle_entity_destroyed(self, event_data: Dict[str, Any]) -> None:
        """Handle entity destruction, primarily for local tracking if needed."""
        # REMOVED QuadTree interaction
        entity_id = event_data.get('entity_id')
        entity_type = event_data.get('entity_type')

        if not entity_id:
            logger.warning(f"Missing entity_id in ENTITY_DESTROYED event: {event_data}")
            return

        # Clean up specific data stores IF BattleRoyaleEnv still manages them
        # Example: If Env still directly manages enemies outside EntityManager
        if entity_type == 'enemy':
            if entity_id in self.enemies:
                del self.enemies[entity_id]
                logger.debug(f"Enemy {entity_id} removed from environment tracking.")
        
        # Note: Agent removal is likely handled by listening to this event in AgentSystem/other managers
        # Or handled via direct calls to _eliminate_agent which then calls EntityManager.unregister

    def _release_bullet(self, bullet: Bullet):
        """Releases a bullet back to the object pool."""
        # REMOVED QuadTree interaction
        if bullet in self.active_bullets:
             self.active_bullets.remove(bullet)
        bullet.active = False # Ensure bullet is marked inactive
        
        if self.bullet_pool:
             self.bullet_pool.release(bullet)
        else:
             logger.warning("Attempted to release bullet, but object pool is not available.")

    # --- ADDED: _spawn_enemy method --- #
    def _spawn_enemy(self):
        """Spawn an enemy of a type chosen based on config weights."""
        spawn_side = random.choice(['left', 'right'])
        spawn_x, spawn_y = 0, 0
        direction = 1
        screen_w = self.config.display['SCREEN_WIDTH']
        screen_h = self.config.display['SCREEN_HEIGHT']
        buffer = 50

        if spawn_side == 'left':
            spawn_x = -buffer
            spawn_y = random.randint(buffer, screen_h - buffer) # Keep within screen vertically
            direction = 1
        else: # 'right'
            spawn_x = screen_w + buffer
            spawn_y = random.randint(buffer, screen_h - buffer) # Keep within screen vertically
            direction = -1

        # Select enemy type based on weights from config
        enemy_types = self.config.enemy['ENEMY_TYPES']
        enemy_weights = self.config.enemy['ENEMY_SPAWN_WEIGHTS']

        if not enemy_types or not enemy_weights or len(enemy_types) != len(enemy_weights):
            logger.error("Invalid or mismatched enemy types/weights in config. Falling back to base Enemy.")
            selected_type_str = 'Enemy'
        else:
            try:
                selected_type_str = random.choices(enemy_types, weights=enemy_weights, k=1)[0]
            except ValueError as e:
                 logger.error(f"Error choosing enemy type (check weights sum?): {e}. Falling back to base Enemy.")
                 selected_type_str = 'Enemy'

        try:
            # Generate a unique ID first
            entity_id = f"enemy_{selected_type_str}_{random.randint(10000, 99999)}"

            # Instantiate the enemy using the AgentFactory
            # Ensure create_agent is imported: from systems.agents.agent_factory import create_agent
            from systems.agents.agent_factory import create_agent # Import locally if not global
            new_enemy = create_agent(agent_type=selected_type_str, name=entity_id, config=None)

            if not new_enemy:
                 logger.error(f"AgentFactory failed to create enemy of type '{selected_type_str}'. Skipping spawn.")
                 return # Exit if agent creation failed
                 
            # Set initial position if possible
            if hasattr(new_enemy, 'position'):
                 new_enemy.position = [spawn_x, spawn_y]
            elif hasattr(new_enemy, 'set_position'):
                 new_enemy.set_position((spawn_x, spawn_y))

            # Emit creation event with specific enemy type
            self.emit_event(SystemEventType.ENTITY_CREATED, {
                'entity_id': entity_id,
                'entity_type': 'agent', # Use generic 'agent' type
                'position': (spawn_x, spawn_y),
                'radius': getattr(new_enemy, 'radius', 10), # Get radius from instance
                'data': {
                    'agent_type': selected_type_str, # Store specific type
                    'team_id': None, # Enemies likely have no team initially
                    'instance': new_enemy
                 }
            })
            logger.info(f"Spawned {selected_type_str} ({entity_id}) at ({spawn_x:.1f}, {spawn_y:.1f})")

        except Exception as e:
            logger.error(f"Error creating or spawning enemy type {selected_type_str} using AgentFactory: {e}", exc_info=True)
    # --- END ADDED --- #

    def _resolve_hit(self, bullet: Bullet, target_entity: Any) -> Dict[str, Any]:
        """Determines if a bullet hit is successful based on LoS, range, and accuracy."""
        # 1. Get Data
        if not bullet or not target_entity:
            logger.warning("_resolve_hit called with invalid bullet or target.")
            return {'result': 'miss', 'reason': 'invalid_input'}

        attacker_id = bullet.owner
        target_id = getattr(target_entity, 'id', None) or getattr(target_entity, 'name', None)
        weapon_type = bullet.weapon_type
        attacker_start_pos = bullet.attacker_start_pos
        target_pos = getattr(target_entity, 'position', None) # Get target current position

        if not all([attacker_id, target_id, weapon_type, attacker_start_pos, target_pos]):
            logger.warning(f"_resolve_hit missing required data: Att={attacker_id}, Tgt={target_id}, Wpn={weapon_type}, AttPos={attacker_start_pos}, TgtPos={target_pos}")
            return {'result': 'miss', 'reason': 'missing_data'}

        # 1. Check Range (Use squared distance)
        distance_sq = (target_pos[0] - attacker_start_pos[0])**2 + (target_pos[1] - attacker_start_pos[1])**2
        # Ensure bullet has max_range_sq attribute
        effective_range_sq = getattr(bullet, 'max_range_sq', 0.0) 
        if effective_range_sq <= 0: # Handle case where bullet range wasn't set
            logger.warning(f"Bullet {id(bullet)} has invalid max_range_sq: {effective_range_sq}")
            effective_range_sq = 500**2 # Fallback range squared
            
        if distance_sq > effective_range_sq:
            logger.debug(f"_resolve_hit: Miss (Range). DistSq: {distance_sq:.1f}, RangeSq: {effective_range_sq:.1f}")
            return {"result": "miss", "reason": "range"}
        
        # Calculate distance only if needed for subsequent checks
        distance = math.sqrt(distance_sq) 

        # 2. Check Line of Sight (LoS)
        if self.hazard_cover_system:
            has_los, _ = self.hazard_cover_system.check_line_of_sight(attacker_start_pos[0], attacker_start_pos[1], target_pos[0], target_pos[1])
            if not has_los:
                return {'result': 'miss', 'reason': 'los'}
        else:
            logger.warning("HazardCoverSystem not available for LoS check in _resolve_hit.")
            # Proceed without LoS check? Or assume miss? Let's assume it proceeds for now.

        # 3. Range Check
        weapon_stats = self.config.get("combat", f"WEAPON_STATS.{weapon_type}", default={})
        effective_range = weapon_stats.get('range', 1000.0) # Default long range if not specified
        distance = math.dist(attacker_start_pos, target_pos)

        if distance > effective_range:
            return {'result': 'miss', 'reason': 'range'}

        # 4. Accuracy Calculation
        base_accuracy = self.config.get("combat", "BASE_ACCURACY", 0.8)
        weapon_accuracy_mod = weapon_stats.get('accuracy_mod', 1.0)

        # Initialize final accuracy
        final_accuracy = base_accuracy * weapon_accuracy_mod

        # Apply Team Bonus (Accuracy part)
        if self.team_combat_integration:
            try:
                team_bonuses = self.team_combat_integration.calculate_team_attack_bonus(attacker_id, target_id, attacker_start_pos, target_pos)
                final_accuracy *= team_bonuses.get('accuracy', 1.0)
            except Exception as e:
                logger.error(f"Error getting team accuracy bonus for {attacker_id}: {e}")

        # Apply Attacker Personality Bonus
        personality_system = self.personality_system
        if personality_system:
            try:
                # Example: Trait like 'focus' or 'precision' might affect accuracy
                acc_bonus = personality_system.get_effect_value(attacker_id, 'accuracy_bonus')
                final_accuracy *= (1.0 + acc_bonus)
            except Exception as e:
                logger.error(f"Error getting personality accuracy bonus for {attacker_id}: {e}")

        # Apply Attacker Status Effect Modifiers
        # (Requires access to CombatSystem or status effect data)
        # Example: Effect 'accuracy_debuff' with strength 0.8 (multiplier)
        # --- ADDED: Apply Attacker Suppression Penalty --- #
        suppression_penalty = 1.0
        if self.morale_suppression_system:
            attacker_suppression = self.morale_suppression_system.get_suppression(attacker_id)
            # Fetch max penalty from config via the system instance
            config_ms = self.morale_suppression_system._config
            max_accuracy_penalty = config_ms.get("SUPPRESSION_EFFECT_ACCURACY_MAX_PENALTY", 0.6)
            suppression_penalty = 1.0 - (attacker_suppression * max_accuracy_penalty)
            final_accuracy *= suppression_penalty
        # ----------------------------------------------- #

        # Apply Target Evasion Modifiers
        # Example: Status effect 'evasive' strength 0.2 (reduces hit chance by 20%)
        # if self.combat_system and target_id in self.combat_system.active_status_effects:
        #     for effect in self.combat_system.active_status_effects[target_id]:
        #         if effect.type == 'evasive':
        #             final_accuracy *= (1.0 - effect.strength)

        # Clamp final accuracy
        final_accuracy = max(0.0, min(1.0, final_accuracy))

        # 5. Hit Roll
        roll = random.random()
        if roll < final_accuracy:
            logger.debug(f"Attack resolved: HIT (Roll: {roll:.2f} < Accuracy: {final_accuracy:.2f})")
            return {'result': 'hit'}
        else:
            logger.debug(f"Attack resolved: MISS (Roll: {roll:.2f} >= Accuracy: {final_accuracy:.2f})")
            return {'result': 'miss', 'reason': 'accuracy'}

    def _handle_entity_created(self, event_data):
        """Handles the creation of a new entity by adding it to the appropriate list."""
        entity_id = event_data.get('entity_id')
        entity_type = event_data.get('entity_type')
        entity_instance = event_data.get('entity_instance') # Assuming the instance is passed

        if not entity_id or not entity_type or not entity_instance:
            logger.warning(f"ENTITY_CREATED event missing data: {event_data}")
            return

        logger.debug(f"Handling ENTITY_CREATED for {entity_id} ({entity_type})")

        # --- Standardize Position Access for QuadTree ---
        entity_pos = None
        entity_radius = 1 # Default radius if not found
        if isinstance(entity_instance, dict):
            entity_pos = entity_instance.get('position')
            entity_radius = entity_instance.get('radius', entity_radius)
        elif hasattr(entity_instance, 'position'):
            entity_pos = entity_instance.position
            if hasattr(entity_instance, 'radius'):
                 entity_radius = entity_instance.radius
        else:
            logger.warning(f"Could not determine position or radius for {entity_type} {entity_id}")

        # Insert into QuadTree if it exists and position is valid
        if hasattr(self, 'collision_tree') and entity_pos is not None:
            tree_entity_id = id(entity_instance) if entity_type == 'bullet' else entity_id
            try:
                 self.collision_tree.insert(entity_pos, tree_entity_id, entity_radius, entity_type)
                 logger.debug(f"Inserted {entity_type} {entity_id} into QuadTree at {entity_pos} with radius {entity_radius}")
            except Exception as e:
                 logger.error(f"Error inserting {entity_type} {entity_id} into QuadTree: {e}")
        # --- End Standardization ---

        # --- Original logic for storing entities (keep this) ---
        if entity_type == 'agent':
            self.agents[entity_id] = entity_instance
            # REMOVED Quadtree insert - Handled above
        elif entity_type == 'bullet':
            self.active_bullets.append(entity_instance)
            # REMOVED Quadtree insert - Handled above
        elif entity_type == 'cover':
             self.cover_data[entity_id] = entity_instance
             # REMOVED Quadtree insert - Handled above
        elif entity_type == 'hazard':
            self.hazards[entity_id] = entity_instance
            # REMOVED Quadtree insert - Handled above
        elif entity_type == 'pickup':
            self.pickups.append(entity_instance) # Assuming pickups are stored in a list? Check this.
            # REMOVED Quadtree insert - Handled above
        else:
            logger.warning(f"Unhandled entity type '{entity_type}' in _handle_entity_created")

        self.entities[entity_id] = entity_instance # Keep track of all entities by ID

    def _handle_bullet_fired(self, event_data):
        """Handles bullet firing events."""
        # ... existing code ...

    def _handle_hazard_activated(self, event_data):
        """Handles hazard activation events."""
        # ... existing code ...

    def _handle_pickup_acquired(self, event_data):
        """Handles pickup acquisition events."""
        # ... existing code ...