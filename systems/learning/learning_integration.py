"""
Learning integration module that connects pattern recognition with strategy adaptation.

This module provides the bridge between the pattern recognition system and 
strategy adaptation, enabling agents to adapt their strategies based on 
identified patterns of success and failure.
"""

import numpy as np
import logging
from typing import Dict, List, Any, Tuple, Optional
import time
import os
from collections import defaultdict
import random

# Add BaseAgent import
from systems.agents.base_agent import BaseAgent
# Import the correct state size constant
from systems.agents.agent_system import STATE_VECTOR_SIZE, ACTION_IDLE, ACTION_SET_TARGET # Import constants

from systems.learning.pattern_recognition_system import PatternRecognitionSystem
from systems.learning.strategy_adaptation_system import StrategyAdaptationSystem
from systems.visualization.learning_visualizer import LearningVisualizer
from systems.environment.environment import BattleRoyaleEnv
from systems.agents.evolutionary_agent import EvolutionaryAgent
from multiprocessing import Lock

logger = logging.getLogger(__name__)

class EvolutionManager:
    """Manages the evolutionary process for a population of agents."""
    def __init__(self, population_size: int, state_size: int, action_size: int, 
                 mutation_rate: float = 0.1, crossover_rate: float = 0.7, elite_fraction: float = 0.1):
        self.population_size = population_size
        self.state_size = state_size
        self.action_size = action_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_fraction = elite_fraction
        
        # Initialize population: list of weight matrices (np.ndarray)
        self.population: List[np.ndarray] = self._initialize_population()
        self.fitness: Dict[int, float] = {i: 0.0 for i in range(population_size)} # index -> fitness
        self.generation = 0

    def _initialize_population(self) -> List[np.ndarray]:
        """Creates the initial population of random weight matrices."""
        pop = []
        for _ in range(self.population_size):
            # Example: Simple linear weights
            scale = np.sqrt(2.0 / (self.state_size + self.action_size)) if self.state_size + self.action_size > 0 else 0.1
            weights = np.random.randn(self.state_size, self.action_size) * scale
            pop.append(weights)
        return pop

    def get_weights(self, individual_index: int) -> Optional[np.ndarray]:
        """Returns the weights for a specific individual in the population."""
        if 0 <= individual_index < self.population_size:
            return self.population[individual_index]
        logger.warning(f"Attempted to get weights for invalid index: {individual_index}")
        return None

    def record_fitness(self, individual_index: int, score: float) -> None:
        """Records the fitness score for an individual after evaluation."""
        if 0 <= individual_index < self.population_size:
            # Aggregate fitness (e.g., average or cumulative score over an episode/round)
            # For simplicity, let's just update with the latest score for now.
            # A better approach would be to accumulate score over an evaluation period.
            self.fitness[individual_index] = score 
            # logger.debug(f"Recorded fitness {score} for individual {individual_index}")
        else:
            logger.warning(f"Attempted to record fitness for invalid index: {individual_index}")

    def evolve(self) -> None:
        """Performs one generation of evolution: selection, crossover, mutation."""
        logger.info(f"Starting evolution for generation {self.generation + 1}")
        
        new_population = []
        
        # --- 1. Selection (Elitism + Tournament) ---
        num_elites = max(1, int(self.population_size * self.elite_fraction))
        
        # Sort population by fitness (descending)
        sorted_indices = sorted(self.fitness, key=self.fitness.get, reverse=True)
        
        # Add elites directly to the new population
        for i in range(num_elites):
            elite_index = sorted_indices[i]
            new_population.append(self.population[elite_index].copy())
            # logger.debug(f"Elite {i+1} selected: Index {elite_index}, Fitness {self.fitness[elite_index]:.2f}")

        # --- 2. Crossover & Mutation ---
        while len(new_population) < self.population_size:
            # Select two parents using tournament selection
            parent1_idx = self._tournament_selection(sorted_indices)
            parent2_idx = self._tournament_selection(sorted_indices)
            
            parent1_weights = self.population[parent1_idx]
            parent2_weights = self.population[parent2_idx]

            # Crossover
            if random.random() < self.crossover_rate:
                child1_weights, child2_weights = self._crossover(parent1_weights, parent2_weights)
            else:
                child1_weights = parent1_weights.copy()
                child2_weights = parent2_weights.copy() # Or just one child if needed

            # Mutation
            child1_weights = self._mutate(child1_weights)
            if len(new_population) < self.population_size:
                child2_weights = self._mutate(child2_weights)
                new_population.append(child2_weights)

            new_population.append(child1_weights)
            
        # Ensure population size is correct (handle odd numbers if necessary)
        self.population = new_population[:self.population_size]
        
        # Reset fitness for the new generation
        self.fitness = {i: 0.0 for i in range(self.population_size)}
        self.generation += 1
        logger.info(f"Evolution complete. New generation: {self.generation}")

    def _tournament_selection(self, sorted_indices: List[int], tournament_size: int = 3) -> int:
        """Selects an individual using tournament selection."""
        if not sorted_indices:
            logger.error("Cannot perform tournament selection on empty population.")
            return 0 # Should not happen
            
        # Pick candidates for the tournament
        candidates_indices = random.sample(sorted_indices, min(tournament_size, len(sorted_indices)))
        
        # The best candidate (highest fitness) wins the tournament
        # Since sorted_indices is sorted by fitness descending, the one appearing earliest wins.
        winner_index = min(candidates_indices, key=lambda idx: sorted_indices.index(idx))
        return winner_index

    def _crossover(self, weights1: np.ndarray, weights2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Performs uniform crossover between two weight matrices."""
        if weights1.shape != weights2.shape:
             logger.error(f"Crossover shape mismatch: {weights1.shape} vs {weights2.shape}")
             return weights1.copy(), weights2.copy() # Return copies on error
             
        mask = np.random.rand(*weights1.shape) < 0.5
        child1 = np.where(mask, weights1, weights2)
        child2 = np.where(mask, weights2, weights1)
        return child1, child2

    def _mutate(self, weights: np.ndarray) -> np.ndarray:
        """Applies Gaussian mutation to the weights."""
        mutation_mask = np.random.rand(*weights.shape) < self.mutation_rate
        # Scale mutation strength slightly (e.g., by 0.1)
        mutations = np.random.normal(0, 0.1, weights.shape) 
        mutated_weights = weights + mutations * mutation_mask
        return mutated_weights

class LearningIntegration:
    """
    Integrates various learning systems including pattern recognition and strategy adaptation
    to create a comprehensive learning framework for agents.
    """
    
    def __init__(self, 
                 env: BattleRoyaleEnv,
                 personality_system=None,
                 pattern_recognition_kwargs=None,
                 strategy_adaptation_kwargs=None,
                 visualizer=None,
                 # Evolution Manager parameters
                 evo_population_size: int = 20,
                 evo_mutation_rate: float = 0.1,
                 evo_crossover_rate: float = 0.7,
                 evo_elite_fraction: float = 0.1):
        """
        Initialize the learning integration system.
        
        Args:
            env (BattleRoyaleEnv): The main environment instance
            personality_system: The personality system for trait integration
            pattern_recognition_kwargs (dict): Arguments for PatternRecognitionSystem
            strategy_adaptation_kwargs (dict): Arguments for StrategyAdaptationSystem
            visualizer (LearningVisualizer, optional): Visualizer for learning metrics
            evo_population_size (int): Size of the evolutionary population.
            evo_mutation_rate (float): Mutation rate for the GA.
            evo_crossover_rate (float): Crossover rate for the GA.
            evo_elite_fraction (float): Fraction of elites to keep.
        """
        self.env = env
        self.logger = logging.getLogger(__name__)
        self.personality_system = personality_system
        
        # Initialize pattern recognition system
        pattern_kwargs = pattern_recognition_kwargs or {}
        self.pattern_system = PatternRecognitionSystem(**pattern_kwargs)
        
        # Initialize strategy adaptation system
        strategy_kwargs = strategy_adaptation_kwargs or {}
        self.strategy_system = StrategyAdaptationSystem(**strategy_kwargs)
        
        # Initialize visualizer or use provided one
        self.visualizer = visualizer or LearningVisualizer()
        
        # Track registered agents
        self.registered_agents: Dict[str, Any] = {} # Store agent instance or type info
        
        # Integration settings
        self.sharing_frequency = 50  # Share every N experiences
        self.experience_counter = defaultdict(int)
        
        # Learning metrics tracking
        self.agent_rewards = defaultdict(list)
        self.agent_losses = defaultdict(list)
        self.visualization_update_frequency = 10  # Update visualizations every N experiences

        # --- Evolution Manager Integration ---
        self.evo_manager: Optional[EvolutionManager] = None
        self.agent_to_evo_index: Dict[str, int] = {}
        self.assigned_evo_indices: set[int] = set()
        self.agent_fitness_accumulator: Dict[str, List[float]] = defaultdict(list)
        self.evo_population_size = evo_population_size

        # Initialize Evo Manager if population size > 0
        if self.evo_population_size > 0:
            # Use the imported STATE_VECTOR_SIZE constant
            state_size = STATE_VECTOR_SIZE
            # Assuming action size is fixed (e.g., 5 for idle, move, rotate L/R, shoot)
            # If action size can vary, this needs a more robust way to determine it.
            action_size = 5 
            
            if state_size > 0 and action_size > 0:
                self.logger.info(f"Initializing EvolutionManager with State Size: {state_size}, Action Size: {action_size}")
                self.evo_manager = EvolutionManager(
                    population_size=self.evo_population_size,
                    state_size=state_size, # Use correct state_size
                    action_size=action_size,
                    mutation_rate=evo_mutation_rate,
                    crossover_rate=evo_crossover_rate,
                    elite_fraction=evo_elite_fraction
                )
                self.logger.info(f"Evolution Manager initialized with population size {self.evo_population_size}")
            else:
                self.logger.error("Could not determine valid state/action size for Evolution Manager initialization.")
        # ------------------------------------
        
        self.logger.info("Learning integration system initialized")
    
    def register_agent(self, agent_id: str, agent_instance: BaseAgent, personality_traits=None):
        """
        Register an agent with the learning system.
        
        Args:
            agent_id (str): Unique identifier for the agent
            agent_instance (BaseAgent): The actual agent object.
            personality_traits (dict): The agent's personality traits
            
        Returns:
            bool: True if registration succeeded
        """
        # Get personality traits if not provided and system is available
        if personality_traits is None and self.personality_system:
            personality_traits = self.personality_system.get_agent_personality(agent_id)
        
        # Register with subsystems
        # REMOVED: self.pattern_system.integrate_with_personality(agent_id, personality_traits)
        # REMOVED: self.strategy_system.integrate_personality_traits(agent_id, personality_traits)
        
        # Store agent info (e.g., instance or type)
        self.registered_agents[agent_id] = agent_instance # Store the instance
        self.logger.info(f"Agent {agent_id} registered with learning systems.")

        # --- Assign Evolutionary Agent to Evo Manager Population ---
        if self.evo_manager and isinstance(agent_instance, EvolutionaryAgent):
            if len(self.assigned_evo_indices) < self.evo_population_size:
                # Find the next available index
                evo_index = 0
                while evo_index in self.assigned_evo_indices:
                    evo_index += 1
                
                if evo_index < self.evo_population_size:
                    self.agent_to_evo_index[agent_id] = evo_index
                    self.assigned_evo_indices.add(evo_index)
                    
                    # Get initial weights and set them in the agent
                    initial_weights = self.evo_manager.get_weights(evo_index)
                    if initial_weights is not None:
                        agent_instance.set_weights(initial_weights)
                        self.logger.info(f"Assigned EvolutionaryAgent {agent_id} to population index {evo_index} and set initial weights.")
                    else:
                         self.logger.error(f"Could not get initial weights for EvolutionaryAgent {agent_id} at index {evo_index}.")
                else:
                     self.logger.warning(f"Evolution Manager population full. Cannot assign EvolutionaryAgent {agent_id}.")
            else:
                self.logger.warning(f"Evolution Manager population full. Cannot assign EvolutionaryAgent {agent_id}.")
        # --------------------------------------------------------

        # Initialize agent in subsystems
        if self.strategy_system:
            self.strategy_system._initialize_agent_strategy(agent_id)
            self.logger.debug(f"Initialized strategy for agent {agent_id}.")
        else:
            self.logger.warning("StrategyAdaptationSystem not available for agent initialization.")

        # TODO: Determine if PatternRecognitionSystem needs explicit initialization here
        # if self.pattern_system:
        #     # Assuming a method like initialize_agent exists or is needed
        #     # self.pattern_system.initialize_agent(agent_id, personality_traits) 
        #     self.logger.debug(f"Initialized patterns for agent {agent_id}.") # Placeholder
        # else:
        #     self.logger.warning("PatternRecognitionSystem not available for agent initialization.")

        return True
    
    def _ensure_agent_registered(self, agent_id):
        """Ensure an agent is registered. Logs warning if not.
           Note: Registration now requires the agent instance.
        """
        if agent_id not in self.registered_agents:
            self.logger.warning(f"Agent {agent_id} accessed learning integration without being registered.")
            # Cannot auto-register without the instance
            # Consider how to handle this - maybe require registration before use.
            return False
        return True
    
    def _preprocess_state(self, state, agent_id, personality_traits=None):
        """
        Preprocess the state based on agent's personality traits.
        
        Args:
            state (dict or np.ndarray): The state to preprocess
            agent_id (str): Unique identifier for the agent
            personality_traits (dict): The agent's personality traits
            
        Returns:
            np.ndarray: The preprocessed state as a numpy array
        """
        # Skip preprocessing if no personality system or traits
        if not self.personality_system and not personality_traits:
            # Ensure state is a numpy array
            if isinstance(state, np.ndarray):
                return state
            elif isinstance(state, dict):
                # Convert dictionary to flat array
                try:
                    # Try to convert simple numeric dictionary to array
                    values = []
                    for key in sorted(state.keys()):
                        value = state[key]
                        if isinstance(value, (int, float)):
                            values.append(value)
                        elif isinstance(value, (list, tuple)) and all(isinstance(x, (int, float)) for x in value):
                            values.extend(value)
                    
                    if values:
                        return np.array(values, dtype=float)
                    else:
                        # If conversion failed, create a simple vector with a dummy value
                        self.logger.warning(f"Could not convert dictionary state to array for agent {agent_id}")
                        return np.zeros(5)  # Default size
                except Exception as e:
                    self.logger.error(f"Error converting dictionary state to array: {e}")
                    return np.zeros(5)  # Default size
            else:
                # For any other type, try to create a numpy array
                try:
                    return np.array(state, dtype=float)
                except:
                    self.logger.warning(f"Could not convert state to array for agent {agent_id}")
                    return np.zeros(5)  # Default size
        
        # Get personality traits
        if not personality_traits and self.personality_system:
            personality_traits = self.personality_system.get_agent_personality(agent_id)
        
        if not personality_traits:
            # Default conversion as above
            if isinstance(state, np.ndarray):
                return state
            elif isinstance(state, dict):
                try:
                    values = []
                    for key in sorted(state.keys()):
                        value = state[key]
                        if isinstance(value, (int, float)):
                            values.append(value)
                        elif isinstance(value, (list, tuple)) and all(isinstance(x, (int, float)) for x in value):
                            values.extend(value)
                    
                    if values:
                        return np.array(values, dtype=float)
                    else:
                        return np.zeros(5)
                except:
                    return np.zeros(5)
            else:
                try:
                    return np.array(state, dtype=float)
                except:
                    return np.zeros(5)
        
        # Create a copy to modify
        if isinstance(state, dict):
            processed_state = state.copy()
            
            # Conscientiousness affects detail preservation
            if "conscientiousness" in personality_traits:
                conscientiousness = personality_traits["conscientiousness"]
                
                # Higher conscientiousness preserves more detail
                if conscientiousness < 0.3:
                    # Low conscientiousness - reduce detail
                    # Keep only high-level keys
                    simplified_state = {}
                    for key, value in processed_state.items():
                        # Keep only primitive values or first level of collections
                        if isinstance(value, (str, int, float, bool)):
                            simplified_state[key] = value
                        elif isinstance(value, (list, tuple)) and len(value) > 0:
                            # Just keep count and a sample
                            simplified_state[key] = {
                                "count": len(value),
                                "sample": value[0] if not isinstance(value[0], dict) else "complex_item"
                            }
                        elif isinstance(value, dict):
                            # Just keep the keys
                            simplified_state[key] = {"keys": list(value.keys())}
                    
                    processed_state = simplified_state
            
            # Convert the dictionary to a vector
            try:
                values = []
                for key in sorted(processed_state.keys()):
                    value = processed_state[key]
                    if isinstance(value, (int, float)):
                        values.append(value)
                    elif isinstance(value, (list, tuple)) and all(isinstance(x, (int, float)) for x in value):
                        values.extend(value)
                
                if values:
                    return np.array(values, dtype=float)
                else:
                    return np.zeros(5)
            except:
                return np.zeros(5)
        elif isinstance(state, np.ndarray):
            # Already a numpy array, just return it
            return state
        else:
            # Try to convert to numpy array
            try:
                return np.array(state, dtype=float)
            except:
                return np.zeros(5)
    
    def record_experience(self, agent_id, state, action, reward, next_state, context=None):
        """
        Record an experience and learn from it.
        
        Args:
            agent_id (str): Unique identifier for the agent
            state: The state in which the action was taken
            action: The action that was taken
            reward (float): The reward received
            next_state: The resulting state
            context (dict, optional): Additional contextual information
            
        Returns:
            bool: True if recording was successful
        """
        if not self._ensure_agent_registered(agent_id):
            return False # Cannot record if not registered
        
        # Preprocess states
        processed_state = self._preprocess_state(state, agent_id)
        processed_next_state = self._preprocess_state(next_state, agent_id)
        
        # Record with pattern recognition system
        pattern_result = self.pattern_system.record_experience(
            agent_id, processed_state, action, reward, context
        )
        
        # --- MODIFIED: Call record_outcome instead of update_strategy ---
        success = reward > 0  # Determine success based on reward
        strategy_result = self.strategy_system.record_outcome(
            agent_id, context, success, reward
        )
        # --- END MODIFIED ---
        
        # Increment experience counter for this agent
        self.experience_counter[agent_id] += 1
        
        # Track rewards for visualization
        self.agent_rewards[agent_id].append(reward)

        # --- ADDED: Log reward being recorded ---
        logger.debug(f"LearningIntegration: Recording experience for {agent_id} - Action: {action}, Reward: {reward:.4f}")
        # --- END ADDED ---

        # --- Accumulate fitness for Evolutionary Agents ---
        if self.evo_manager and agent_id in self.agent_to_evo_index:
            self.agent_fitness_accumulator[agent_id].append(reward)
        # -------------------------------------------------
        
        # Periodically share learning with other agents (if beneficial)
        if self.experience_counter[agent_id] % self.sharing_frequency == 0:
            # Add nearby agent info to context before recording experience if not already present
            if context is None: context = {}
            # Preprocess nearby_agents into numeric context features if not done already
            if 'num_nearby_agents' not in context:
                agent_pos = state.get('position') if isinstance(state, dict) else None
                if agent_pos and hasattr(self.env, 'get_nearby_agents'):
                    query_radius = 150.0
                    nearby_agents_list = self.env.get_nearby_agents(agent_pos, query_radius)
                    nearby_agents_filtered = [a for a in nearby_agents_list if a.name != agent_id]
                    
                    context['num_nearby_agents'] = len(nearby_agents_filtered)
                    if nearby_agents_filtered:
                        positions = [getattr(a, 'position', agent_pos) for a in nearby_agents_filtered 
                                     if hasattr(a, 'position') and getattr(a, 'position') is not None]
                        if positions:
                            distances = [np.linalg.norm(np.array(agent_pos) - np.array(p)) for p in positions]
                            context['avg_nearby_dist'] = np.mean(distances) if distances else 0.0
                            context['min_nearby_dist'] = np.min(distances) if distances else query_radius
                        else:
                            context['avg_nearby_dist'] = query_radius
                            context['min_nearby_dist'] = query_radius
                    else:
                        context['avg_nearby_dist'] = query_radius
                        context['min_nearby_dist'] = query_radius

            self._share_learning_with_peers(agent_id)
        
        # Periodically update visualization data
        if self.visualizer and self.experience_counter[agent_id] % self.visualization_update_frequency == 0:
            self._update_visualization_data(agent_id)
        
        return True
    
    def record_experience_with_context(self, agent_id, state, action, reward, next_state, context):
        """
        Record an experience with explicit context information.
        
        This is a convenience method that calls record_experience with the context parameter.
        
        Args:
            agent_id (str): Unique identifier for the agent
            state (dict): The state when the action was taken
            action (str/dict): The action taken
            reward (float): The reward received
            next_state (dict): The resulting state after taking the action
            context (dict): Additional context for the experience
            
        Returns:
            bool: True if experience was recorded successfully
        """
        return self.record_experience(agent_id, state, action, reward, next_state, context)
    
    def suggest_action(self, agent_id, state, context=None):
        """
        Suggest an action for an agent based on patterns and strategy.
        If the suggested action is ACTION_SET_TARGET, include the suggested target_id.
        
        Args:
            agent_id (str): Unique identifier for the agent
            state (dict or np.ndarray): The current state
            context (dict): Additional context (optional)
            
        Returns:
            dict or int: Either an action ID (int) or a dictionary 
                         like {'action': action_id, 'target_id': target_id}
        """
        self._ensure_agent_registered(agent_id)
        
        # Get the current strategy
        strategy = self.strategy_system.get_strategy(agent_id)
        
        # Apply situation triggers if context is provided
        if context:
            strategy = self.strategy_system._apply_situation_triggers(agent_id, context, strategy)
        
        # Preprocess state based on personality
        processed_state = self._preprocess_state(state, agent_id)
        
        # Include strategy in context for pattern recognition
        if context is None:
            context = {}
        context["current_strategy"] = strategy
        
        # Add nearby agents to context
        target_id_suggestion = None # Placeholder for determined target
        num_nearby_agents = 0
        agent_pos = None
        if isinstance(state, dict): 
            agent_pos = state.get('position') 
        elif isinstance(state, np.ndarray):
             # Need a way to reliably get position from state vector if it's an array
             # This depends heavily on the vector's structure defined in AgentSystem
             # Assuming position isn't directly in the standard state vector
             # We might need to get it from the environment again, which is suboptimal here.
             # Fallback: Get from env if AgentSystem passed it in context?
             if context and 'agent_pos' in context:
                  agent_pos = context['agent_pos']
             elif self.env and hasattr(self.env, 'agent_positions'): # Last resort
                  agent_pos = self.env.agent_positions.get(agent_id)

        if agent_pos and hasattr(self.env, 'get_nearby_agents'):
            query_radius = 150.0 
            nearby_agents_list = self.env.get_nearby_agents(agent_pos, query_radius)
            nearby_enemies_filtered = []
            # TODO: Use TeamSystem/RelationshipSystem for hostility check
            agent_team_id = None # Need a way to get agent's team ID here
            if self.env.team_system: 
                 try: # Add try-except for safety
                      agent_team_id = self.env.team_system.get_team_id_for_agent(agent_id)
                 except Exception as e:
                      logger.warning(f"Error getting team ID for agent {agent_id} in LearningIntegration: {e}")
            if agent_team_id:
                for agent_obj in nearby_agents_list:
                     other_id = getattr(agent_obj, 'name', None)
                     if not other_id or other_id == agent_id: continue
                     
                     is_hostile = True # Default assumption
                     if agent_team_id and self.env.team_system:
                          other_team_id = None
                          try:
                               other_team_id = self.env.team_system.get_team_id_for_agent(other_id)
                               if other_team_id == agent_team_id:
                                    is_hostile = False
                               # Check for alliance using should_help_ally if it exists
                               elif hasattr(self.env.team_system, 'should_help_ally') and self.env.team_system.should_help_ally(agent_team_id, other_team_id):
                                    is_hostile = False # Treat allies as non-hostile for targeting context
                          except Exception as e:
                               logger.warning(f"Error getting team ID or checking alliance for {other_id} in LearningIntegration: {e}")
                     if is_hostile:
                          nearby_enemies_filtered.append(agent_obj)

            context['num_nearby_agents'] = len(nearby_agents_list) - 1 # Exclude self
            context['num_nearby_enemies'] = len(nearby_enemies_filtered)
            num_nearby_agents = len(nearby_agents_list) -1

            if nearby_enemies_filtered:
                positions = [getattr(a, 'position', agent_pos) for a in nearby_enemies_filtered 
                             if hasattr(a, 'position') and getattr(a, 'position') is not None]
                if positions:
                    distances = [np.linalg.norm(np.array(agent_pos) - np.array(p)) for p in positions]
                    context['avg_nearby_enemy_dist'] = np.mean(distances) if distances else 0.0
                    min_dist_idx = np.argmin(distances) if distances else -1
                    context['min_nearby_enemy_dist'] = distances[min_dist_idx] if min_dist_idx != -1 else query_radius
                    # --- Potential Target Selection --- 
                    # Simplistic: If close enemy exists, consider targeting the closest one
                    if min_dist_idx != -1:
                         target_id_suggestion = getattr(nearby_enemies_filtered[min_dist_idx], 'name', None)
                    # ---------------------------------
                else:
                    context['avg_nearby_enemy_dist'] = query_radius
                    context['min_nearby_enemy_dist'] = query_radius
            else:
                context['avg_nearby_enemy_dist'] = query_radius
                context['min_nearby_enemy_dist'] = query_radius

        # Get action suggestion from pattern system
        action_id, confidence = self.pattern_system.suggest_action(
            agent_id, processed_state, context
        ) or (None, 0.0)
        
        # --- Combine Action and Target ID --- 
        if action_id is not None:
            # Modify confidence based on exploration
            if "exploration" in strategy:
                confidence *= (1.0 - (strategy.get("exploration", 0.0) * 0.3))

            if action_id == ACTION_SET_TARGET and target_id_suggestion:
                 # Return tuple containing dict and confidence
                 return ({'action': ACTION_SET_TARGET, 'target_id': target_id_suggestion}, confidence)
            else:
                 # Return tuple containing action ID and confidence
                 return (action_id, confidence)
        else:
            # Pattern system had no suggestion, try strategy system
            strategy_action = self.strategy_system.suggest_action(agent_id, processed_state, context)
            if strategy_action is not None:
                # Strategy system provided an action
                # Return it directly (assume confidence is handled internally or not needed here)
                # Or should we return a tuple like (strategy_action, default_confidence)? For now, just action.
                return strategy_action # Return just the action ID suggested by strategy
            else:
                # Strategy system also had no suggestion, fallback to agent's default behavior
                agent_instance = self.registered_agents.get(agent_id)
                if agent_instance:
                    # Use the processed state for the agent's internal logic
                    agent_action = agent_instance.get_action(processed_state)
                    return agent_action
                else:
                    # Agent instance not found (shouldn't happen if _ensure_agent_registered worked)
                    self.logger.error(f"Agent instance {agent_id} not found during fallback action suggestion.")
                    return None # Cannot suggest anything

    def _share_learning_with_peers(self, source_agent_id, target_agent_ids=None):
        """
        Share learning patterns between agents.
        
        Args:
            source_agent_id (str): Agent sharing their patterns
            target_agent_ids (list): Agents to share with (None = all registered)
            
        Returns:
            int: Number of patterns shared
        """
        if target_agent_ids is None:
            # Share with all registered agents except self
            target_agent_ids = [aid for aid in self.registered_agents 
                               if aid != source_agent_id]
        
        if not target_agent_ids:
            return 0
            
        # Get personality traits if available
        source_personality = None
        if self.personality_system:
            source_personality = self.personality_system.get_agent_personality(source_agent_id)
            
        total_shared = 0
        for target_id in target_agent_ids:
            # Share pattern knowledge
            patterns_shared = self.pattern_system.share_patterns(
                source_agent_id, target_id
            )
            
            # Share strategy knowledge
            strategy_shared = self.strategy_system.share_strategy(
                source_agent_id, target_id
            )
            
            if patterns_shared or strategy_shared:
                total_shared += 1
                
        return total_shared
    
    def share_learning(self, source_agent_id, target_agent_id):
        """
        Share learning from one agent to another.
        
        Args:
            source_agent_id (str): Agent sharing knowledge
            target_agent_id (str): Agent receiving knowledge
            
        Returns:
            bool: True if knowledge was shared
        """
        return self._share_learning_with_peers(source_agent_id, [target_agent_id]) > 0
    
    def define_situation_trigger(self, agent_id, trigger_name, condition, strategy_adjustment):
        """
        Define a situation-specific trigger for strategy adaptation.
        
        Args:
            agent_id (str): Agent identifier
            trigger_name (str): Name for the trigger
            condition (dict): Condition that activates the trigger
            strategy_adjustment (dict): How to adjust the strategy when triggered
            
        Returns:
            bool: True if trigger was defined
        """
        self._ensure_agent_registered(agent_id)
        
        return self.strategy_system.define_situation_trigger(
            agent_id, trigger_name, condition, strategy_adjustment
        )
    
    def get_learning_statistics(self, agent_id):
        """
        Get statistics about the agent's learning progress.
        
        Args:
            agent_id (str): Agent identifier
            
        Returns:
            dict: Statistics about patterns and strategies
        """
        self._ensure_agent_registered(agent_id)
        
        # Get pattern statistics
        pattern_stats = self.pattern_system.get_pattern_stats(agent_id)
        
        # Get strategy statistics
        strategy_effectiveness = self.strategy_system.get_strategy_effectiveness(agent_id)
        recent_changes = self.strategy_system.get_recent_strategy_changes(agent_id)
        current_strategy = self.strategy_system.get_strategy(agent_id)
        
        return {
            "agent_id": agent_id,
            "pattern_stats": pattern_stats,
            "strategy_stats": {
                "effectiveness": strategy_effectiveness,
                "recent_changes": recent_changes,
                "current_strategy": current_strategy
            },
            "experience_count": self.experience_counter[agent_id]
        }
    
    def save_system_state(self, directory):
        """
        Save the learning system state to disk.
        
        Args:
            directory (str): Directory to save the state in
            
        Returns:
            bool: True if the state was saved successfully
        """
        try:
            os.makedirs(directory, exist_ok=True)
            
            # Save pattern system state
            pattern_path = os.path.join(directory, "pattern_system.json")
            pattern_state = self.pattern_system.save_to_dict()
            
            # Save strategy system state
            strategy_path = os.path.join(directory, "strategy_system.json")
            self.strategy_system.save_system_state(strategy_path)
            
            # Save integration system state
            with open(os.path.join(directory, "integration_state.json"), "w") as f:
                import json
                json.dump({
                    "registered_agents": list(self.registered_agents),
                    "experience_counter": dict(self.experience_counter),
                    "sharing_frequency": self.sharing_frequency
                }, f)
                
            return True
        except Exception as e:
            self.logger.error(f"Error saving system state: {e}")
            return False
    
    def load_system_state(self, directory):
        """
        Load the learning system state from disk.
        
        Args:
            directory (str): Directory to load the state from
            
        Returns:
            bool: True if the state was loaded successfully
        """
        try:
            # Load pattern system state
            pattern_path = os.path.join(directory, "pattern_system.json")
            with open(pattern_path, "r") as f:
                import json
                pattern_state = json.load(f)
                self.pattern_system.load_from_dict(pattern_state)
            
            # Load strategy system state
            strategy_path = os.path.join(directory, "strategy_system.json")
            self.strategy_system.load_system_state(strategy_path)
            
            # Load integration system state
            with open(os.path.join(directory, "integration_state.json"), "r") as f:
                import json
                integration_state = json.load(f)
                self.registered_agents = set(integration_state["registered_agents"])
                self.experience_counter = defaultdict(int, integration_state["experience_counter"])
                self.sharing_frequency = integration_state["sharing_frequency"]
                
            return True
        except Exception as e:
            self.logger.error(f"Error loading system state: {e}")
            return False
    
    def _update_visualization_data(self, agent_id):
        """
        Update visualization data for an agent.
        
        Args:
            agent_id (str): The agent to update visualization data for
        """
        # Get recent rewards
        if self.agent_rewards[agent_id]:
            # Calculate recent average reward
            recent_rewards = self.agent_rewards[agent_id][-50:]  # Last 50 rewards
            avg_reward = sum(recent_rewards) / len(recent_rewards)
            
            # Learning metrics
            learning_data = {
                'rewards': avg_reward,
                'recent_reward': recent_rewards[-1],
                'reward_trend': avg_reward - sum(recent_rewards[:min(10, len(recent_rewards))]) / min(10, len(recent_rewards)),
                'experiences': self.experience_counter[agent_id]
            }
            
            # Add loss if available (would be tracked elsewhere)
            if self.agent_losses[agent_id]:
                recent_losses = self.agent_losses[agent_id][-10:]
                learning_data['losses'] = sum(recent_losses) / len(recent_losses)
            
            # Update visualization with learning data
            self.visualizer.add_learning_data(agent_id, learning_data)
        
        # Get pattern statistics
        pattern_stats = self.pattern_system.get_pattern_stats(agent_id)
        if pattern_stats:
            # Update visualization with pattern data
            self.visualizer.add_pattern_data(agent_id, pattern_stats)
        
        # Get strategy effectiveness
        strategy_data = self.strategy_system.get_strategy_effectiveness(agent_id)
        if strategy_data:
            # Update visualization with strategy data
            self.visualizer.add_strategy_data(agent_id, strategy_data)
    
    def visualize_learning_curve(self, agent_ids=None, metric='rewards', save_path=None):
        """
        Visualize the learning curve for specified agents.
        
        Args:
            agent_ids (list): List of agent IDs to visualize (None for all)
            metric (str): Which metric to plot ('rewards', 'losses', etc.)
            save_path (str): Path to save the visualization (None to not save)
            
        Returns:
            Figure: Matplotlib figure object
        """
        # Ensure we have the latest data
        if agent_ids:
            for agent_id in agent_ids:
                if agent_id in self.registered_agents:
                    self._update_visualization_data(agent_id)
        else:
            for agent_id in self.registered_agents:
                self._update_visualization_data(agent_id)
        
        # Generate the visualization
        save_plot = save_path is not None
        fig = self.visualizer.plot_learning_curve(agent_ids, metric, save_plot=save_plot)
        
        if save_plot and save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def visualize_pattern_progress(self, agent_ids=None, save_path=None):
        """
        Visualize pattern recognition progress for specified agents.
        
        Args:
            agent_ids (list): List of agent IDs to visualize (None for all)
            save_path (str): Path to save the visualization (None to not save)
            
        Returns:
            Figure: Matplotlib figure object
        """
        # Ensure we have the latest data
        if agent_ids:
            for agent_id in agent_ids:
                if agent_id in self.registered_agents:
                    self._update_visualization_data(agent_id)
        else:
            for agent_id in self.registered_agents:
                self._update_visualization_data(agent_id)
        
        # Generate the visualization
        save_plot = save_path is not None
        fig = self.visualizer.plot_pattern_recognition_progress(agent_ids, save_plot=save_plot)
        
        if save_plot and save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def visualize_strategy_adaptation(self, agent_ids=None, save_path=None):
        """
        Visualize strategy adaptation progress for specified agents.
        
        Args:
            agent_ids (list): List of agent IDs to visualize (None for all)
            save_path (str): Path to save the visualization (None to not save)
            
        Returns:
            Figure: Matplotlib figure object
        """
        # Ensure we have the latest data
        if agent_ids:
            for agent_id in agent_ids:
                if agent_id in self.registered_agents:
                    self._update_visualization_data(agent_id)
        else:
            for agent_id in self.registered_agents:
                self._update_visualization_data(agent_id)
        
        # Generate the visualization
        save_plot = save_path is not None
        fig = self.visualizer.plot_strategy_adaptation(agent_ids, save_plot=save_plot)
        
        if save_plot and save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def visualize_pattern_clusters(self, agent_id, save_path=None):
        """
        Visualize pattern clusters for a specific agent.
        
        Args:
            agent_id (str): Agent ID to visualize patterns for
            save_path (str): Path to save the visualization (None to not save)
            
        Returns:
            Figure: Matplotlib figure object
        """
        if agent_id not in self.registered_agents:
            self.logger.error(f"Agent {agent_id} not registered for pattern visualization")
            return None
        
        # Ensure we have the latest data
        self._update_visualization_data(agent_id)
        
        # Generate the visualization
        save_plot = save_path is not None
        try:
            fig = self.visualizer.visualize_pattern_clusters(agent_id, save_plot=save_plot)
            
            if save_plot and save_path:
                fig.savefig(save_path, dpi=300, bbox_inches='tight')
            
            return fig
        except Exception as e:
            self.logger.error(f"Error visualizing pattern clusters: {e}")
            return None
    
    def visualize_cross_agent_comparison(self, metric='rewards', save_path=None):
        """
        Visualize a comparison of learning across multiple agents.
        
        Args:
            metric (str): Which metric to compare ('rewards', 'losses', etc.)
            save_path (str): Path to save the visualization (None to not save)
            
        Returns:
            Figure: Matplotlib figure object
        """
        # Ensure we have the latest data for all agents
        for agent_id in self.registered_agents:
            self._update_visualization_data(agent_id)
        
        # Generate the visualization
        save_plot = save_path is not None
        fig = self.visualizer.visualize_cross_agent_learning(metric, save_plot=save_plot)
        
        if save_plot and save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def finalize_evolution_round(self) -> None:
        """Finalizes fitness, performs evolution, and updates agent weights."""
        if not self.evo_manager:
            self.logger.debug("Evolution Manager not initialized, skipping evolution step.")
            return

        if not self.agent_fitness_accumulator:
             self.logger.debug("No fitness data accumulated, skipping evolution step.")
             return

        self.logger.info(f"Finalizing fitness for generation {self.evo_manager.generation}")
        # --- Record Final Fitness --- 
        for agent_id, rewards in self.agent_fitness_accumulator.items():
            if agent_id in self.agent_to_evo_index:
                evo_index = self.agent_to_evo_index[agent_id]
                # Calculate final fitness (e.g., average reward)
                final_fitness = np.mean(rewards) if rewards else 0.0
                self.evo_manager.record_fitness(evo_index, final_fitness)
                # logger.debug(f"Final fitness for {agent_id} (Index {evo_index}): {final_fitness:.2f}")

        # --- Perform Evolution --- 
        self.evo_manager.evolve()

        # --- Update Agents with New Weights --- 
        self.logger.info(f"Assigning evolved weights for generation {self.evo_manager.generation}")
        updated_count = 0
        for agent_id, evo_index in self.agent_to_evo_index.items():
            if agent_id in self.registered_agents:
                agent_instance = self.registered_agents[agent_id]
                if isinstance(agent_instance, EvolutionaryAgent):
                    new_weights = self.evo_manager.get_weights(evo_index)
                    if new_weights is not None:
                        agent_instance.set_weights(new_weights)
                        updated_count += 1
                        # logger.debug(f"Updated weights for {agent_id} (Index {evo_index})")
                    else:
                         logger.warning(f"Could not get new weights for {agent_id} (Index {evo_index}) after evolution.")
            else:
                 logger.warning(f"Agent {agent_id} (Index {evo_index}) not found in registered agents during weight update.")
        
        self.logger.info(f"Updated weights for {updated_count} Evolutionary Agents.")

        # --- Reset Fitness Accumulator --- 
        self.agent_fitness_accumulator.clear()
    