from abc import ABC, abstractmethod
import numpy as np
from collections import deque, defaultdict
import random
import math
import logging
from typing import Dict, Any, Optional, Tuple, List, TYPE_CHECKING
import heapq # Import heapq for nsmallest
import time
from enum import Enum, auto

from systems.core.base_system import BaseSystem
from systems.core.system_manager import SystemEventType, system_manager
from systems.spatial_system import AABB, QuadTree # Corrected import
from systems.agents.base_agent import BaseAgent # Make sure BaseAgent is imported if it's defined elsewhere
from systems.utils.config import config # Import the global config object
from .agent_factory import create_agent # Use factory
# --- ADDED IMPORTS for agent types ---
from .mlp_agent import MLPAgent
from .perceptron_agent import PerceptronAgent
# --- END ADDED IMPORTS ---
from systems.constants import (
    STATE_VECTOR_SIZE, MAX_NEARBY_AGENTS, MAX_NEARBY_BULLETS,
    MAX_NEARBY_PICKUPS, MAX_NEARBY_HAZARDS, AGENT_FEATURES,
    BULLET_FEATURES, HAZARD_FEATURES, PICKUP_FEATURES, SELF_FEATURES,
    ENV_FEATURES, MORALE_SUPPRESSION_FEATURES,
    ACTION_IDLE, ACTION_MOVE_FORWARD, ACTION_ROTATE_LEFT,
    ACTION_ROTATE_RIGHT, ACTION_SHOOT, ACTION_SET_TARGET,
    PICKUP_TYPE_MAP, HAZARD_TYPE_MAP
)
from systems.core.system_manager import SystemManager
from systems.core.entity_manager import EntityManager
from systems.agents.state_builder import StateBuilder
from systems.agents.action_executor import ActionExecutor

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from systems.environment.environment import BattleRoyaleEnv
    from systems.morale.morale_suppression_system import MoraleSuppressionSystem
    # Add other systems accessed via self.get_system if needed for type hints

class AgentSystem(BaseSystem):
    """
    Manages the update cycle for all agents, including state gathering,
    action selection, and action execution within the environment.
    Also handles collision responses between agents.
    """
    def __init__(self):
        super().__init__(name="agent_system", priority=50) # Initialize BaseSystem
        self.logger = logging.getLogger(__name__) # Explicitly initialize logger

        self.env = None # Will be set by Environment or retrieved from shared state
        self.agent_objects = {} # Stores agent instances {agent_id: AgentInstance}
        self.agent_targets = {} # Stores agent target IDs {agent_id: target_id or None}
        self.agent_threat_level = defaultdict(int) # Stores perceived threat from each agent {agent_id: threat_level}
        self.agent_action_cooldowns = {} # Stores cooldowns for actions {agent_id: {action_type: cooldown_timer}}
        self.agent_intended_moves = {} # {agent_id: (dx, dy)} - Set by _execute_action
        self.agent_last_positions = {} # {agent_id: (x, y)} - Used for state delta
        self.agent_action_context = {} # ADDED: Initialize agent action context dictionary
        self.collision_adjustments = {} # ADDED: Initialize collision adjustments dictionary
        self.start_positions = {} # ADDED: Initialize start positions dictionary
        self.agent_goals = {} # ADDED: Initialize agent goals dictionary
        self._morale_suppression_system: Optional["MoraleSuppressionSystem"] = None
        self.agent_last_action_time = defaultdict(float) # ADDED: Track last action time

        # Lazy loaded dependencies
        self._env: Optional[BattleRoyaleEnv] = None
        self._entity_manager: Optional[EntityManager] = None
        # --- ADDED StateBuilder and ActionExecutor placeholders ---
        self._state_builder: Optional[StateBuilder] = None
        self._action_executor: Optional[ActionExecutor] = None
        # ---------------------------------------------------------

        # Subscribe to relevant events
        self.subscribe_to_event(SystemEventType.ENTITY_CREATED, self._handle_entity_created)
        self.subscribe_to_event(SystemEventType.ENTITY_DESTROYED, self._handle_entity_destroyed)
        self.subscribe_to_event(SystemEventType.ENTITY_COLLISION, self._handle_agent_collision) # CORRECTED: Use ENTITY_COLLISION
        self.subscribe_to_event(SystemEventType.AGENT_DAMAGED, self._handle_agent_damaged)
        self.subscribe_to_event(SystemEventType.AGENT_ACTION, self._handle_agent_action_event) # Listen for external action triggers

    @property # ADDED: Lazy loader property
    def morale_suppression_system(self) -> Optional["MoraleSuppressionSystem"]:
        if self._morale_suppression_system is None:
            self._morale_suppression_system = system_manager.get_system("morale_suppression_system")
            if not self._morale_suppression_system:
                 logger.warning("AgentSystem: MoraleSuppressionSystem not found.")
        return self._morale_suppression_system

    @property
    def env(self) -> Optional[BattleRoyaleEnv]:
        if self._env is None:
            self._env = system_manager.get_system("battle_royale_env")
            if not self._env:
                 logger.error(f"{self.name}: BattleRoyaleEnv not found!")
        return self._env

    @property
    def entity_manager(self) -> Optional[EntityManager]:
        if self._entity_manager is None:
            self._entity_manager = system_manager.get_system("entity_manager")
            if not self._entity_manager:
                 logger.error(f"{self.name}: EntityManager not found!")
        return self._entity_manager

    @property
    def state_builder(self) -> Optional[StateBuilder]:
        if self._state_builder is None:
            self._state_builder = system_manager.get_system("state_builder")
            if not self._state_builder:
                 logger.error(f"{self.name}: StateBuilder not found!")
        return self._state_builder
        
    @property
    def action_executor(self) -> Optional[ActionExecutor]:
        if self._action_executor is None:
            self._action_executor = system_manager.get_system("action_executor")
            if not self._action_executor:
                 logger.error(f"{self.name}: ActionExecutor not found!")
        return self._action_executor

    def initialize(self):
        """Get references to other systems and subscribe to collision events."""
        self.env = self.get_system("battle_royale_env")
        self.learning_integration = self.get_system("learning_integration") # Optional
        if not self.env:
            logger.error("AgentSystem could not find required system 'battle_royale_env'.")
            return # Cannot proceed without env
            
        # Precompute max distance for normalization
        self.max_env_distance = math.sqrt(self.env.width**2 + self.env.height**2) if self.env.width > 0 and self.env.height > 0 else 1.0
        if self.max_env_distance == 0: self.max_env_distance = 1.0 # Avoid division by zero
            
        # Ensure agents are initialized if created by env
        if not self.env.agents:
             max_agents = min(config.performance.get('MAX_AGENTS', 10), config.agent.get('MAX_AGENTS', 50))
             self.env.create_agents(max_agents=max_agents)

        # Initialize target and threat dicts for existing agents
        for agent_id in self.env.agents.keys(): # Use env.agents keys
            self.agent_targets[agent_id] = None
            self.agent_threat_level[agent_id] = 0
            self.agent_goals[agent_id] = {}
            self.agent_intended_moves[agent_id] = (0.0, 0.0) # Initialize intended moves
            # self.collision_adjustments cleared in update

        logger.info("AgentSystem initialized and subscribed to collisions and agent actions.")

    def update(self, delta_time: float):
        """Main update loop for all agents."""
        # print(f"--- AgentSystem.update START (delta_time: {delta_time}) ---")
        # logger.debug(f"--- AgentSystem.update START (delta_time: {delta_time}) ---")
        
        # Ensure dependencies are loaded
        if not self.entity_manager or not self.state_builder or not self.action_executor:
             logger.error("AgentSystem cannot update: Critical dependencies (EntityManager, StateBuilder, ActionExecutor) missing.")
             return
             
        if not self.env: # Env might still be needed for some logic (like agent list)
            logger.error("AgentSystem.update: Environment (self.env) is not set. Cannot update agents.")
            return

        # Use EntityManager to get the list of active agents
        active_agent_data = self.entity_manager.get_all_entities_of_type('agent')
        active_agent_ids = [data['id'] for data in active_agent_data if data.get('alive', True)]
        
        if not active_agent_ids:
             # logger.debug("AgentSystem Update: No active agents found.")
             return

        # logger.debug(f"AgentSystem Update: Processing active agents: {active_agent_ids}")

        # --- Store initial data for learning --- 
        agent_initial_states = {}
        agent_actions_taken = {}
        agent_contexts = {}
        
        # --- Agent Action Selection Loop ---
        for agent_id in active_agent_ids:
            # Get agent instance (still needed for get_action)
            agent_object = self.env.agents.get(agent_id)
            if not agent_object:
                 logger.warning(f"Agent object for {agent_id} not found in self.env.agents. Skipping.")
                 continue

            # 1. Build State Vector
            state_vector = self.state_builder.build_state_vector(agent_id)
            if state_vector is None:
                logger.warning(f"Failed to build state vector for agent {agent_id}. Skipping action.")
                continue
            agent_initial_states[agent_id] = state_vector # Store for learning
            
            # 2. Get Action from Agent
            action_taken = agent_object.get_action(state_vector)
            context_taken = {} # Placeholder for potential context from agent
            agent_actions_taken[agent_id] = action_taken
            agent_contexts[agent_id] = context_taken

            # logger.debug(f"Agent {agent_id} chose action: {action_taken}")

        # --- Action Execution Loop --- 
        # Execute actions AFTER all agents have decided
        for agent_id in active_agent_ids:
             if agent_id in agent_actions_taken:
                  action_id = agent_actions_taken[agent_id]
                  context = agent_contexts[agent_id]
                  # Add delta_time to the context for the executor
                  context['delta_time'] = delta_time
                  
                  # 3. Execute Action via ActionExecutor
                  self.action_executor.execute_action(agent_id, action_id, context)

        # --- Learning Step Loop --- 
        # Perform learning step AFTER actions are executed (or based on stored initial state?)
        for agent_id in active_agent_ids:
             agent_object = self.env.agents.get(agent_id)
             if agent_object and agent_id in agent_initial_states and agent_id in agent_actions_taken:
                  # Only perform learning if the agent class supports it (has 'learn' method)
                  if hasattr(agent_object, 'learn'): 
                       initial_state = agent_initial_states[agent_id]
                       action_id = agent_actions_taken[agent_id]
                       context = agent_contexts[agent_id]
                       # The _perform_learning_step helper likely needs adjustment 
                       # based on how rewards are calculated now.
                       self._perform_learning_step(agent_id, agent_object, initial_state, action_id, context, delta_time)

        # --- Collision Resolution (Remains the same for now) ---
        # This part seems to apply adjustments based on events handled by _handle_agent_collision.
        # ActionExecutor handles the intended move, this part adjusts for collisions.
        self.collision_adjustments.clear() 
        # Events processed during system_manager.update will populate self.collision_adjustments
        # via self._handle_agent_collision

        # --- Apply Final Movement Adjustments (If needed) ---
        # This loop might be redundant if ActionExecutor's move handles final position updates 
        # AND collision resolution directly modifies entity positions/velocities via EntityManager.
        # Keeping it for now, assuming _handle_agent_collision still populates self.collision_adjustments.
        for agent_id in active_agent_ids: 
            agent_entity_data = self.entity_manager.get_entity(agent_id)
            if not agent_entity_data or not agent_entity_data.get('alive', True):
                continue # Agent might have been destroyed

            intended_dx, intended_dy = self.agent_intended_moves.get(agent_id, (0.0, 0.0)) # Where did agent INTEND?
            # Collision adjustments populated by _handle_agent_collision
            collision_push_x, collision_push_y, slide_dx, slide_dy = self.collision_adjustments.get(agent_id, (0.0, 0.0, intended_dx, intended_dy)) 
            
            # If ActionExecutor handles the primary move, this adjustment logic needs review.
            # Let's assume for now ActionExecutor updated the position, and this applies ONLY the push.
            final_dx = collision_push_x
            final_dy = collision_push_y
            
            if abs(final_dx) > 1e-6 or abs(final_dy) > 1e-6: # Only apply if there's a push
                current_pos = agent_entity_data.get('position')
                if current_pos:
                    new_x = current_pos[0] + final_dx
                    new_y = current_pos[1] + final_dy
                    
                    # Clamp position to bounds (consider moving clamping to EntityManager or a Physics system)
                    world_width = config.display.get('SCREEN_WIDTH', 1000)
                    world_height = config.display.get('SCREEN_HEIGHT', 1000)
                    agent_radius = agent_entity_data.get('radius', 5)
                    new_x_clamped = max(agent_radius, min(world_width - agent_radius, new_x))
                    new_y_clamped = max(agent_radius, min(world_height - agent_radius, new_y))
                    
                    # Update agent position via EntityManager
                    self.entity_manager.update_entity_position(agent_id, (new_x_clamped, new_y_clamped))
                    # logger.debug(f"Agent {agent_id} collision push applied: ({final_dx:.2f}, {final_dy:.2f})")

    def shutdown(self):
        logger.info("AgentSystem shutting down.")
        pass

    # ------------------------------------
    # --- ADDED: Learning Step Method ---
    # ------------------------------------
    def _perform_learning_step(self, agent_id: str, agent: BaseAgent, initial_state: np.ndarray, action_taken: Any, context_taken: Dict[str, Any], delta_time: float):
        # Implement learning logic here
        pass

    def preprocess_state(self, state: Any) -> np.ndarray:
        """Default state preprocessing. Assumes state is already a NumPy array.
           Agents can override this for more specific preprocessing.
        """
        if isinstance(state, np.ndarray):
            # Optional: Add check for correct shape/size here if needed
            # if state.shape == (self.state_size,):
            #     return state
            # else:
            #     logger.warning(f"Agent {self.name} received state with unexpected shape: {state.shape}")
            #     # Attempt reshape or return default
            return state
        elif isinstance(state, dict):
            # This path should ideally not be taken if _get_agent_state works correctly
            logger.warning(f"Agent {self.name} received dict state in preprocess_state. System should provide np.array.")
            # Attempt basic flattening as fallback
            flat_list = []
            for key in sorted(state.keys()):
                val = state[key]
                if isinstance(val, (int, float, bool)):
                    flat_list.append(float(val))
                elif isinstance(val, (tuple, list)) and all(isinstance(x, (int, float)) for x in val):
                    flat_list.extend(float(x) for x in val)
            expected_size = getattr(self, 'state_size', STATE_VECTOR_SIZE)
            if len(flat_list) < expected_size:
                 flat_list.extend([0.0] * (expected_size - len(flat_list)))
            elif len(flat_list) > expected_size:
                 flat_list = flat_list[:expected_size]
            return np.array(flat_list, dtype=float) if flat_list else np.zeros(expected_size)

        logger.error(f"Agent {self.name}: Received unsupported state type for preprocessing: {type(state)}")
        return np.zeros(getattr(self, 'state_size', STATE_VECTOR_SIZE)) # Fallback

    def _handle_agent_collision(self, event_data: Dict[str, Any]) -> None:
        """Handles ENTITY_COLLISION events, resolving agent-agent and agent-obstacle collisions."""
        entity1_id = event_data.get('entity1_id')
        entity2_id = event_data.get('entity2_id')
        entity1_type = event_data.get('entity1_type')
        entity2_type = event_data.get('entity2_type')
        entity1_pos = event_data.get('entity1_pos')
        entity2_pos = event_data.get('entity2_pos')

        # --- Agent-Agent Collision Resolution ---
        if entity1_type == 'agent' and entity2_type == 'agent':
            # Existing agent-agent logic...
            agent1_id = entity1_id
            agent2_id = entity2_id
            agent1 = self.env.agents.get(agent1_id)
            agent2 = self.env.agents.get(agent2_id)
            pos1 = entity1_pos
            pos2 = entity2_pos

            if not agent1 or not agent2 or not pos1 or not pos2:
                # logger.warning(f"Agent data missing for collision between {agent1_id} and {agent2_id}")
                return # Cannot resolve if data is missing

            radius1 = getattr(agent1, 'radius', 10)
            radius2 = getattr(agent2, 'radius', 10)
            target_dist = radius1 + radius2

            dx = pos2[0] - pos1[0]
            dy = pos2[1] - pos1[1]
            dist_sq = dx*dx + dy*dy

            if dist_sq < 1e-6:
                dist = 0.1
                penetration = target_dist - dist
                normal_x, normal_y = 1.0, 0.0
            else:
                dist = math.sqrt(dist_sq)
                penetration = target_dist - dist
                normal_x = dx / dist
                normal_y = dy / dist

            if penetration > 0:
                push_amount = penetration / 2.0
                push1_x, push1_y = -normal_x * push_amount, -normal_y * push_amount
                push2_x, push2_y = normal_x * push_amount, normal_y * push_amount

                dx1_intent, dy1_intent = self.agent_intended_moves.get(agent1_id, (0.0, 0.0))
                dx2_intent, dy2_intent = self.agent_intended_moves.get(agent2_id, (0.0, 0.0))

                rel_vx = dx2_intent - dx1_intent
                rel_vy = dy2_intent - dy1_intent
                vel_along_normal = rel_vx * normal_x + rel_vy * normal_y

                slide1_dx, slide1_dy = dx1_intent, dy1_intent
                slide2_dx, slide2_dy = dx2_intent, dy2_intent

                if vel_along_normal < 0:
                    # --- SET RESTITUTION TO 0 FOR PURE SLIDING ---
                    restitution = 0.0 # Was 0.5
                    # ---------------------------------------------
                    impulse_magnitude = -(1 + restitution) * vel_along_normal
                    impulse_x = normal_x * impulse_magnitude
                    impulse_y = normal_y * impulse_magnitude

                    vel1_normal_comp_x = (dx1_intent * normal_x + dy1_intent * normal_y) * normal_x
                    vel1_normal_comp_y = (dx1_intent * normal_x + dy1_intent * normal_y) * normal_y
                    slide1_dx -= vel1_normal_comp_x
                    slide1_dy -= vel1_normal_comp_y
                    slide1_dx += impulse_x * 0.5
                    slide1_dy += impulse_y * 0.5

                    vel2_normal_comp_x = (dx2_intent * normal_x + dy2_intent * normal_y) * normal_x
                    vel2_normal_comp_y = (dx2_intent * normal_x + dy2_intent * normal_y) * normal_y
                    slide2_dx -= vel2_normal_comp_x
                    slide2_dy -= vel2_normal_comp_y
                    slide2_dx -= impulse_x * 0.5
                    slide2_dy -= impulse_y * 0.5

                current_adj1 = self.collision_adjustments.get(agent1_id, (0.0, 0.0, dx1_intent, dy1_intent))
                current_adj2 = self.collision_adjustments.get(agent2_id, (0.0, 0.0, dx2_intent, dy2_intent))

                new_push1_x = current_adj1[0] + push1_x
                new_push1_y = current_adj1[1] + push1_y
                new_push2_x = current_adj2[0] + push2_x
                new_push2_y = current_adj2[1] + push2_y

                self.collision_adjustments[agent1_id] = (new_push1_x, new_push1_y, slide1_dx, slide1_dy)
                self.collision_adjustments[agent2_id] = (new_push2_x, new_push2_y, slide2_dx, slide2_dy)

        # --- Agent-Obstacle Collision Resolution ---
        elif (entity1_type == 'agent' and entity2_type in ['cover', 'hazard']) or \
             (entity2_type == 'agent' and entity1_type in ['cover', 'hazard']):

            if entity1_type == 'agent':
                agent_id = entity1_id
                agent_pos = entity1_pos
                obstacle_id = entity2_id
                obstacle_pos = entity2_pos
                obstacle_type = entity2_type
            else: # entity2 must be agent
                agent_id = entity2_id
                agent_pos = entity2_pos
                obstacle_id = entity1_id
                obstacle_pos = entity1_pos
                obstacle_type = entity1_type

            agent = self.env.agents.get(agent_id)
            if not agent or not agent_pos or not obstacle_pos:
                # logger.warning(f"Data missing for agent-obstacle collision: {agent_id} vs {obstacle_id}")
                return

            agent_radius = getattr(agent, 'radius', 10)
            # --- MODIFIED: Get dynamic obstacle radius --- 
            obstacle_radius = 15 # Default fallback
            hcs = self.get_system("hazard_cover_system")
            if hcs:
                if obstacle_type == 'cover' and obstacle_id in hcs.cover_objects:
                    obstacle_radius = hcs.cover_objects[obstacle_id].get('radius', 15)
                elif obstacle_type == 'hazard' and obstacle_id in hcs.hazard_areas:
                    obstacle_radius = hcs.hazard_areas[obstacle_id].get('radius', 15)
            # else: logger.warning(f"Could not get HazardCoverSystem to find radius for {obstacle_id}")
            # --- END MODIFIED ---

            target_dist = agent_radius + obstacle_radius

            dx = agent_pos[0] - obstacle_pos[0] # Vector from obstacle to agent
            dy = agent_pos[1] - obstacle_pos[1]
            dist_sq = dx*dx + dy*dy

            if dist_sq < 1e-6:
                dist = 0.1
                penetration = target_dist - dist
                normal_x, normal_y = 1.0, 0.0 # Default normal if overlapping
            else:
                dist = math.sqrt(dist_sq)
                penetration = target_dist - dist
                normal_x = dx / dist
                normal_y = dy / dist

            if penetration > 0:
                # 1. Calculate Push Adjustment (only push agent)
                push_amount = penetration # Agent pushed by full penetration amount
                push_x = normal_x * push_amount
                push_y = normal_y * push_amount

                # 2. Calculate Sliding Velocity Adjustment
                dx_intent, dy_intent = self.agent_intended_moves.get(agent_id, (0.0, 0.0))
                intended_velocity_magnitude_sq = dx_intent**2 + dy_intent**2

                # Only adjust velocity if agent intended to move
                if intended_velocity_magnitude_sq > 1e-6:
                    vel_along_normal = dx_intent * normal_x + dy_intent * normal_y

                    slide_dx, slide_dy = dx_intent, dy_intent

                    # If moving towards the obstacle along the normal
                    if vel_along_normal < 0:
                        # Project intended velocity onto the tangent plane (remove normal component)
                        vel_normal_comp_x = vel_along_normal * normal_x
                        vel_normal_comp_y = vel_along_normal * normal_y
                        
                        # The adjusted velocity allows sliding along the surface
                        slide_dx = dx_intent - vel_normal_comp_x
                        slide_dy = dy_intent - vel_normal_comp_y
                        # logger.debug(f"Agent {agent_id} sliding against {obstacle_type} {obstacle_id}. Intent:({dx_intent:.2f},{dy_intent:.2f}), Slide:({slide_dx:.2f},{slide_dy:.2f})")
                else:
                    # If no intended movement, slide velocity is zero
                    slide_dx, slide_dy = 0.0, 0.0

                # 3. Accumulate Adjustments
                current_adj = self.collision_adjustments.get(agent_id, (0.0, 0.0, dx_intent, dy_intent))

                # Accumulate push vector
                new_push_x = current_adj[0] + push_x
                new_push_y = current_adj[1] + push_y

                # Store the calculated slide velocity (replacing original intent)
                self.collision_adjustments[agent_id] = (new_push_x, new_push_y, slide_dx, slide_dy)
                # logger.debug(f"Calculated obstacle collision adjustment for {agent_id}. Push:({push_x:.2f},{push_y:.2f}), Slide:({slide_dx:.2f},{slide_dy:.2f})")

    def _handle_agent_damaged(self, event_data: Dict[str, Any]) -> None:
        """Handles the AGENT_DAMAGED event to apply damage to the agent's health."""
        target_id = event_data.get('target_id')
        damage = event_data.get('damage')

        if target_id is None or damage is None:
            logger.warning(f"AGENT_DAMAGED event missing target_id or damage: {event_data}")
            return

        if not self.env:
            logger.error("Environment not available in AgentSystem to apply damage.")
            return

        agent = self.env.agents.get(target_id)
        if agent:
            try:
                # --- MODIFIED: Directly update health in env --- 
                if target_id in self.env.agent_health:
                    # Apply damage reduction if in cover (need cover status)
                    # TODO: Get cover status for target_id. Requires access to agent state or env method.
                    # For now, apply damage directly without cover reduction.
                    # cover_factor = 1.0 # Default: no reduction
                    # if self.env.is_position_in_cover(agent.position[0], agent.position[1]): # Assumes env has this method & agent has position
                    #     cover_factor = 0.5 # Simple reduction
                    
                    damage_to_apply = damage # * cover_factor
                    current_health = self.env.agent_health[target_id]
                    new_health = max(0, current_health - damage_to_apply) # Ensure health doesn't go below 0
                    self.env.agent_health[target_id] = new_health
                    logger.debug(f"Applied {damage_to_apply:.2f} damage to agent {target_id}. New health: {new_health:.2f}")

                    # Check for elimination
                    if new_health <= 0:
                        logger.info(f"Agent {target_id} eliminated by damage.")
                    # NOTE: The actual removal of the agent from env lists 
                    # should be handled by the listener for ENTITY_DESTROYED 
                    # (e.g., in BattleRoyaleEnv._handle_entity_destroyed)
                else:
                    logger.warning(f"Cannot apply damage: Agent {target_id} not found in self.env.agent_health.")
                # --- END MODIFICATION ---
            except Exception as e:
                logger.error(f"Error applying damage for agent {target_id}: {e}", exc_info=True)
        else:
            # Agent might have been destroyed between damage calculation and event handling
            logger.debug(f"Agent {target_id} not found when trying to apply damage (possibly already destroyed).")

    def _handle_agent_action_event(self, event_data: Dict[str, Any]) -> None:
        """Handles AGENT_ACTION events, specifically for team maneuvers."""
        action_type = event_data.get('action')

        if action_type == 'team_flanking_maneuver_start':
            flankers_data = event_data.get('flankers') # Dict {flanker_id: target_pos}
            target_id = event_data.get('target_id')
            team_id = event_data.get('team_id')
            initiator_id = event_data.get('agent_id')
            
            if flankers_data and isinstance(flankers_data, dict):
                logger.info(f"Handling flanking maneuver for team {team_id}, initiated by {initiator_id}. Assigning goals to {list(flankers_data.keys())}")
                for flanker_id, target_pos in flankers_data.items():
                    if flanker_id in self.env.agents: # Check if agent exists
                        self.agent_goals[flanker_id] = {
                            'type': 'move_to',
                            'position': target_pos,
                            'context': {'maneuver': 'flank', 'target_id': target_id}
                        }
                        logger.debug(f"Assigned flanking goal to {flanker_id}: move to {target_pos}")
                    else:
                         logger.warning(f"Cannot assign flanking goal: Agent {flanker_id} not found.")

        # Can handle other team actions here if needed

    # --- Event Handlers ---
    def _handle_entity_created(self, event_data: Dict[str, Any]) -> None:
        """Handle newly created entities, specifically agents."""
        entity_id = event_data.get('entity_id')
        entity_type = event_data.get('entity_type')
        entity = event_data.get('entity') # The actual object

        if entity_type == 'agent' and entity_id and entity:
            if entity_id not in self.agent_objects:
                self.agent_objects[entity_id] = entity
                self.agent_targets[entity_id] = None # Initialize target
                self.agent_threat_level[entity_id] = 0 # Initialize threat
                self.agent_action_cooldowns[entity_id] = {} # Initialize cooldowns
                self.agent_intended_moves[entity_id] = (0.0, 0.0) # Initialize intended move
                self.agent_last_positions[entity_id] = self.env.agent_positions.get(entity_id)
                self.agent_action_context[entity_id] = {} # Initialize action context

                # Optional: Initialize agent in LearningIntegration if it exists
                if self.learning_integration:
                    try:
                        self.learning_integration.register_agent(entity_id, entity)
                    except AttributeError:
                         logger.warning(f"LearningIntegration missing register_agent method for {entity_id}")
                    except Exception as e:
                         logger.error(f"Error registering agent {entity_id} with LearningIntegration: {e}")

                logger.debug(f"AgentSystem registered new agent: {entity_id}")
            else:
                 logger.warning(f"AgentSystem received ENTITY_CREATED for already known agent: {entity_id}")
        # else: Ignore non-agent entities

    def _handle_entity_destroyed(self, event_data: Dict[str, Any]) -> None:
        """Handle entity destruction, cleaning up agent-specific data."""
        entity_id = event_data.get('entity_id')
        entity_type = event_data.get('entity_type')

        if entity_type == 'agent' and entity_id:
            if entity_id in self.agent_objects:
                # Remove agent from all internal tracking dictionaries
                self.agent_objects.pop(entity_id, None)
                self.agent_targets.pop(entity_id, None)
                self.agent_threat_level.pop(entity_id, None)
                self.agent_action_cooldowns.pop(entity_id, None)
                self.agent_intended_moves.pop(entity_id, None)
                self.agent_last_positions.pop(entity_id, None)
                self.agent_action_context.pop(entity_id, None)

                # Update threat levels related to this agent
                # Decrement threat level FROM the destroyed agent towards others
                # (Not typically tracked this way, but could be added if needed)

                # Decrement threat level TOWARDS the destroyed agent from others
                # Need to iterate through all agents targeting this one (inefficient)
                # Alternative: Let target selection logic handle invalid targets
                # OR: Store who is targeting whom.
                for agent_id, target_id in list(self.agent_targets.items()):
                     if target_id == entity_id:
                          self.agent_targets[agent_id] = None # Clear target
                          # Maybe reduce threat perceived by agent_id?

                # Optional: Unregister from LearningIntegration
                if self.learning_integration:
                    try:
                        # Need a way to unregister or mark as inactive in LearningIntegration
                        # self.learning_integration.unregister_agent(entity_id) # If method exists
                         pass # Placeholder if unregister doesn't exist
                    except AttributeError:
                        pass # Ignore if method doesn't exist
                    except Exception as e:
                         logger.error(f"Error unregistering agent {entity_id} from LearningIntegration: {e}")

                logger.debug(f"AgentSystem unregistered agent: {entity_id}")
            else:
                # Agent might have been destroyed before being fully registered or double event
                logger.warning(f"AgentSystem received ENTITY_DESTROYED for unknown/already removed agent: {entity_id}")
        # else: Ignore non-agent entities

# --- Concrete Agent Implementations (Should ideally be in separate files) ---
# Example: Keep existing agent definitions here for now if they were in this file
# If they are already in mlp_agent.py, perceptron_agent.py etc., remove from here.

# Remove TeamCoordinator if it's not an agent class
# class TeamCoordinator:
#     ...

# UPDATE __all__ list to reflect moved classes
__all__ = [
    # Assuming these are defined elsewhere (e.g., mlp_agent.py, perceptron_agent.py)
    # If these are *also* in this file, they should be removed too.
    'MLPAgent1',
    'MLPAgent2',
    'PerceptronAgent1',
    'PerceptronAgent2',
    'PerceptronAgent3',
    # The following were moved to their own files
    # 'ConvolutionalAgent',
    # 'EvolutionaryAgent',
    # 'FuzzyAgent'

    # Add classes actually defined in this file
    'AgentSystem',
]