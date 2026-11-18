import numpy as np
import logging
import json
import os
from collections import defaultdict, deque
from datetime import datetime
import time
from typing import Optional, Dict, List, Tuple, Any, TYPE_CHECKING

from systems.core.system_manager import system_manager, SystemEventType
from agents.agent import Agent # <<< IMPORT Agent class

# Forward references for type hints
if TYPE_CHECKING:
    from systems.agents.personality_system import PersonalitySystem, PersonalityTrait
    from systems.agents.relationship_system import RelationshipSystem, RelationshipType, RelationshipMetric
    # REMOVED: Entity hint might not be needed if Agent is the base/only relevant type
    # from systems.core.entity import Entity 

class StrategyAdaptationSystem:
    """
    A system that adapts agent strategies based on experiences and personality traits.
    
    This system:
    1. Maintains strategy profiles for each agent
    2. Adapts strategies based on success/failure experiences
    3. Handles situation-specific strategy adjustments
    4. Integrates personality traits into strategy adaptation
    """
    
    def __init__(self, 
                 adaptation_rate=0.05, 
                 exploration_factor=0.2,
                 strategy_memory_size=100,
                 initial_strategy=None):
        """
        Initialize the strategy adaptation system.
        
        Args:
            adaptation_rate (float): How quickly strategies adapt to new experiences (0-1)
            exploration_factor (float): How much random exploration to incorporate (0-1)
            strategy_memory_size (int): How many recent strategy changes to remember
            initial_strategy (dict, optional): Default starting strategy values
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Strategy Adaptation System")
        
        self.adaptation_rate = adaptation_rate
        self.exploration_factor = exploration_factor
        self.strategy_memory_size = strategy_memory_size
        
        # Default strategy parameters if none provided
        self.default_strategy = initial_strategy or {
            "aggression": 0.5,
            "defense": 0.5,
            "resource_focus": 0.3,
            "team_coordination": 0.4,
            "caution": 0.5, # Added caution based on usage elsewhere
            "adaptability": 0.5 # Added adaptability based on usage elsewhere
        }
        
        # Agent-specific strategies
        self.agent_strategies: Dict[str, Dict[str, Any]] = {}
        
        # History of strategy changes for each agent
        self.strategy_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Situation triggers for strategy adjustment
        self.situation_triggers: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Strategy effectiveness tracking
        self.strategy_effectiveness: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "success_count": 0,
            "failure_count": 0,
            "total_reward": 0.0,
            "actions_taken": 0
        })

        # System Dependencies (Lazy Loaded)
        self._personality_system_instance: Optional["PersonalitySystem"] = None
        self._relationship_system_instance: Optional["RelationshipSystem"] = None
        # REMOVED: _event_system_instance

        # Subscribe to events
        self._subscribe_to_events()

    # --- Lazy Loading Properties ---
    # REMOVED: event_system property

    @property
    def personality_system(self) -> Optional["PersonalitySystem"]:
        if self._personality_system_instance is None:
            self._personality_system_instance = system_manager.get_system("PersonalitySystem")
            if not self._personality_system_instance:
                self.logger.info("PersonalitySystem not found via SystemManager in StrategyAdaptationSystem.")
        return self._personality_system_instance

    @property
    def relationship_system(self) -> Optional["RelationshipSystem"]:
        if self._relationship_system_instance is None:
            self._relationship_system_instance = system_manager.get_system("RelationshipSystem")
            if not self._relationship_system_instance:
                self.logger.info("RelationshipSystem not found via SystemManager in StrategyAdaptationSystem.")
        return self._relationship_system_instance
    # --- End Lazy Loading Properties ---

    def _subscribe_to_events(self):
        """Subscribe to relevant system events using SystemManager.""" 
        # --- MODIFIED: Use system_manager.subscribe directly --- 
        try:
            system_manager.subscribe(SystemEventType.ENTITY_CREATED, self._handle_entity_created)
            system_manager.subscribe(SystemEventType.ENTITY_DESTROYED, self._handle_entity_destroyed)
            self.logger.info("Subscribed to ENTITY_CREATED and ENTITY_DESTROYED events via SystemManager.")
        except Exception as e:
            # Log error if subscription fails (e.g., SystemManager not fully ready?)
            self.logger.error(f"Could not subscribe to events via SystemManager: {e}", exc_info=True)
        # ----------------------------------------------------------

    # --- MODIFIED: Change type hint from Entity to Any, rely on isinstance check --- 
    def _handle_entity_created(self, entity: Any):
        """Handle entity creation events to register agents."""
        # Check using isinstance instead of entity_type attribute 
        if isinstance(entity, Agent):
            agent_id = entity.id # Assuming agent instance has an 'id' attribute
            if agent_id not in self.agent_strategies:
                self._initialize_agent_strategy(agent_id)
                self.logger.info(f"Registered agent {agent_id} in StrategyAdaptationSystem.")
            else:
                self.logger.warning(f"Agent {agent_id} already registered upon creation event.")
        #     self.logger.debug(f"Ignoring non-agent entity creation: {entity.id} (type: {type(entity).__name__})") 

    # --- MODIFIED: Change type hint from Entity to Any, rely on isinstance check --- 
    def _handle_entity_destroyed(self, entity: Any):
        """Handle entity destruction events to unregister agents."""
        # Check using isinstance instead of entity_type attribute 
        if isinstance(entity, Agent):
            agent_id = entity.id # Assuming agent instance has an 'id' attribute
            if agent_id in self.agent_strategies:
                del self.agent_strategies[agent_id]
                # Also clean up other dictionaries
                if agent_id in self.strategy_effectiveness:
                    del self.strategy_effectiveness[agent_id]
                if agent_id in self.situation_triggers:
                    del self.situation_triggers[agent_id]
                if agent_id in self.strategy_history:
                    del self.strategy_history[agent_id]
                self.logger.info(f"Unregistered agent {agent_id} from StrategyAdaptationSystem.")
            else:
                # This might happen if the agent was never properly registered or destroyed twice
                self.logger.warning(f"Attempted to unregister agent {agent_id} which was not registered.")
        #     self.logger.debug(f"Ignoring non-agent entity destruction: {entity.id} (type: {type(entity).__name__})") 

    def _initialize_agent_strategy(self, agent_id: str):
        """
        Initialize the strategy for a newly registered agent.
        Copies the default strategy and potentially applies personality modifications later.
        """
        if agent_id in self.agent_strategies:
            self.logger.warning(f"Agent {agent_id} is already initialized.")
            return

        new_strategy = self.default_strategy.copy()
        
        # --- Personality Integration (Example) ---
        # If personality system is available, adjust initial strategy based on traits
        if self.personality_system:
            personality = self.personality_system.get_agent_personality(agent_id)
            if personality:
                self.logger.debug(f"Applying personality traits to initial strategy for agent {agent_id}")
                # Example: Higher Conscientiousness -> Higher Defense/Caution
                conscientiousness = personality.get_trait(PersonalityTrait.CONSCIENTIOUSNESS)
                new_strategy["defense"] = min(1.0, new_strategy["defense"] + (conscientiousness - 0.5) * 0.2)
                new_strategy["caution"] = min(1.0, new_strategy["caution"] + (conscientiousness - 0.5) * 0.2)
                
                # Example: Higher Agreeableness -> Higher Team Coordination
                agreeableness = personality.get_trait(PersonalityTrait.AGREEABLENESS)
                new_strategy["team_coordination"] = min(1.0, new_strategy["team_coordination"] + (agreeableness - 0.5) * 0.3)
                
                # Example: Higher Neuroticism -> Higher Caution, Lower Aggression
                neuroticism = personality.get_trait(PersonalityTrait.NEUROTICISM)
                new_strategy["caution"] = min(1.0, new_strategy["caution"] + (neuroticism - 0.5) * 0.3)
                new_strategy["aggression"] = max(0.0, new_strategy["aggression"] - (neuroticism - 0.5) * 0.2)

                # Ensure all values are clipped [0, 1] after personality adjustments
                for key in new_strategy:
                     if isinstance(new_strategy[key], (int, float)): # Check if numeric
                         new_strategy[key] = max(0.0, min(1.0, new_strategy[key]))
            else:
                self.logger.warning(f"Could not retrieve personality for agent {agent_id} during strategy initialization.")

        # Store the initialized strategy in the expected structure
        self.agent_strategies[agent_id] = {
            'current_strategy': new_strategy, 
            'history': [] # Initialize history list
        }

        # Initialize effectiveness tracking for the agent
        self.strategy_effectiveness[agent_id] = { # Ensure effectiveness is initialized
            "success_count": 0, "failure_count": 0, "total_reward": 0.0, "actions_taken": 0
        }

        # Add an initial history entry
        history_entry = {
            "timestamp": time.time(),
            "old_strategy": None, # No old strategy
            "new_strategy": new_strategy.copy(),
            "reason": "initialization",
        }
        self._add_to_strategy_history(agent_id, history_entry)
        
        self.logger.debug(f"Initialized strategy for agent {agent_id}: {new_strategy}")

    def record_outcome(self, agent_id, context, success, reward):
        """
        Record an outcome (success/failure) to adjust the agent's strategy.
        
        Args:
            agent_id (str): Unique identifier for the agent
            context (dict): Context information about the situation
            success (bool): Whether the action was successful
            reward (float): Numerical reward received
            
        Returns:
            bool: Whether the strategy was updated
        """
        if agent_id not in self.agent_strategies:
            self.logger.warning(f"Agent {agent_id} not initialized when recording outcome. Initializing now.")
            self._initialize_agent_strategy(agent_id)
            if agent_id not in self.agent_strategies:
                self.logger.error(f"Failed to initialize agent {agent_id} during record_outcome. Cannot record.")
                return False

        if agent_id not in self.agent_strategies:
            self.logger.warning(f"Agent {agent_id} not registered in StrategyAdaptationSystem. Cannot record outcome.")
            return False

        current_strategy = self.agent_strategies[agent_id]['current_strategy']
        strategy_key = json.dumps(current_strategy, sort_keys=True)

        if strategy_key not in self.strategy_effectiveness[agent_id]:
            self.strategy_effectiveness[agent_id][strategy_key] = {
                "success_count": 0, "failure_count": 0, "total_reward": 0.0, "actions_taken": 0
            }

        effectiveness = self.strategy_effectiveness[agent_id][strategy_key]

        effectiveness["actions_taken"] += 1
        effectiveness["total_reward"] += reward
        if success:
            effectiveness["success_count"] += 1
        else:
            effectiveness["failure_count"] += 1

        adjustment_factor = reward * self.adaptation_rate
        
        if "aggression" in current_strategy:
            current_strategy["aggression"] = max(0.0, min(1.0, current_strategy["aggression"] + adjustment_factor))
        
        if context and context.get("situation") == "gathering":
            if "resource_focus" in current_strategy:
                current_strategy["resource_focus"] = max(0.0, min(1.0, current_strategy["resource_focus"] + adjustment_factor * 2))
        
        success_rate = effectiveness["success_count"] / effectiveness["actions_taken"] if effectiveness["actions_taken"] > 0 else 0.5
        if success_rate < 0.4 and effectiveness["actions_taken"] > 10:
            if "caution" in current_strategy:
                current_strategy["caution"] = min(1.0, current_strategy["caution"] + self.adaptation_rate * 0.5)

        self.agent_strategies[agent_id]['current_strategy'] = current_strategy

        history_entry = {
            'timestamp': time.time(),
            'strategy': current_strategy.copy(),
            'context': context,
            'success': success,
            'reward': reward
        }
        self._add_to_strategy_history(agent_id, history_entry)

        self.logger.debug(f"Recorded outcome for agent {agent_id}. Success: {success}, Reward: {reward:.2f}, Adapted Strategy: {current_strategy}")
        return True

    def get_action_weights(self, agent_id, state, available_actions):
        """
        Get weights for available actions based on the agent's current strategy.
        
        Args:
            agent_id (str): Unique identifier for the agent
            state (dict): Current state of the agent
            available_actions (list): List of available actions
            
        Returns:
            dict: Mapping of actions to weight values (0-1)
        """
        if agent_id not in self.agent_strategies:
            self.logger.warning(f"Agent {agent_id} not registered. Using default strategy.")
            strategy = self.default_strategy
        else:
            strategy = self.agent_strategies[agent_id]['current_strategy']
            
            # Apply situation triggers if applicable
            strategy = self._apply_situation_triggers(agent_id, state, strategy)
        
        # Initialize weights for all actions equally
        weights = {action: 0.5 for action in available_actions}
        
        # Adjust weights based on strategy and action characteristics
        for action in available_actions:
            # Basic classifications (this would be expanded in a real system)
            is_aggressive = "attack" in action.lower() or "charge" in action.lower()
            is_defensive = "defend" in action.lower() or "cover" in action.lower()
            is_team_oriented = "assist" in action.lower() or "coordinate" in action.lower()
            is_cautious = "retreat" in action.lower() or "heal" in action.lower()
            
            # Apply strategy influences
            if is_aggressive:
                weights[action] += 0.3 * strategy["aggression"]
            if is_defensive:
                weights[action] += 0.3 * (1 - strategy["aggression"])
            if is_team_oriented:
                weights[action] += 0.3 * strategy["coordination"]
            if is_cautious:
                weights[action] += 0.3 * strategy["caution"]
            
            # Add some exploration factor (randomness)
            weights[action] += np.random.uniform(-0.1, 0.1) * self.exploration_factor
            
            # Ensure value is in range [0,1]
            weights[action] = max(0.0, min(1.0, weights[action]))
        
        return weights

    def suggest_action(self, agent_id, state, available_actions, context=None):
        """
        Suggest an action for the agent based on current strategy.
        
        Args:
            agent_id (str): Unique identifier for the agent
            state (dict): Current state of the agent
            available_actions (list): List of available actions
            context (dict, optional): Additional context information
            
        Returns:
            dict: Suggested action with confidence score
        """
        if not available_actions:
            return None
        
        # Get action weights
        weights = self.get_action_weights(agent_id, state, available_actions)
        
        # Select action (weighted random choice)
        weights_list = [weights[action] for action in available_actions]
        total_weight = sum(weights_list)
        
        if total_weight == 0:
            # If all weights are zero, choose randomly
            chosen_action = np.random.choice(available_actions)
            confidence = 1.0 / len(available_actions)
        else:
            # Normalize weights to probabilities
            probs = [w/total_weight for w in weights_list]
            chosen_action = np.random.choice(available_actions, p=probs)
            confidence = weights[chosen_action]
        
        # Get current strategy for reference
        if agent_id in self.agent_strategies:
            strategy = self.agent_strategies[agent_id]['current_strategy']
        else:
            strategy = self.default_strategy
            
        # Store the selected strategy influences for context
        strategy_influence = {
            key: value for key, value in strategy.items() 
            if key in ["aggression", "caution", "coordination"]
        }
        
        return {
            "action": chosen_action,
            "confidence": confidence,
            "strategy_influence": strategy_influence
        }

    def define_situation_trigger(self, agent_id, trigger_name, condition, strategy_adjustment):
        """
        Define a trigger that adjusts strategy based on specific situations.
        
        Args:
            agent_id (str): Unique identifier for the agent
            trigger_name (str): Name for this trigger
            condition (dict): Condition that activates the trigger (e.g., {"health": {"below": 30}})
            strategy_adjustment (dict): Adjustments to make to strategy when triggered
            
        Returns:
            bool: Whether the trigger was successfully defined
        """
        if agent_id not in self.agent_strategies:
            self.logger.warning(f"Agent {agent_id} not registered. Cannot define trigger.")
            return False
        
        # Store the trigger
        self.situation_triggers[agent_id][trigger_name] = {
            "condition": condition,
            "adjustment": strategy_adjustment
        }
        
        self.logger.info(f"Defined situation trigger '{trigger_name}' for agent {agent_id}")
        return True

    def _apply_situation_triggers(self, agent_id, state, strategy):
        """
        Apply situation triggers to modify the strategy if conditions are met.
        
        Args:
            agent_id (str): Unique identifier for the agent
            state (dict): Current state to check against triggers
            strategy (dict): Current strategy values
            
        Returns:
            dict: Potentially modified strategy
        """
        if agent_id not in self.situation_triggers:
            return strategy
        
        # Create a copy of the strategy to modify
        modified_strategy = strategy.copy()
        
        # Check each trigger
        for trigger_name, trigger_data in self.situation_triggers[agent_id].items():
            condition = trigger_data["condition"]
            adjustment = trigger_data["adjustment"]
            
            # Check if condition is met
            is_triggered = self._check_trigger_condition(state, condition)
            
            if is_triggered:
                self.logger.debug(f"Trigger '{trigger_name}' activated for agent {agent_id}")
                
                # Apply adjustments
                for param, value in adjustment.items():
                    if param in modified_strategy:
                        modified_strategy[param] += value
                        # Ensure value stays in range [0,1]
                        modified_strategy[param] = max(0.0, min(1.0, modified_strategy[param]))
        
        return modified_strategy

    def _check_trigger_condition(self, state, condition):
        """
        Check if a state meets a trigger condition.
        
        Args:
            state (dict): Current state
            condition (dict): Condition to check
            
        Returns:
            bool: Whether the condition is met
        """
        for key, criteria in condition.items():
            if key not in state:
                return False
            
            if isinstance(criteria, dict):
                # Complex condition like {"below": 30}
                if "below" in criteria and state[key] >= criteria["below"]:
                    return False
                if "above" in criteria and state[key] <= criteria["above"]:
                    return False
                if "equals" in criteria and state[key] != criteria["equals"]:
                    return False
            else:
                # Simple equality check
                if state[key] != criteria:
                    return False
        
        return True
    
    def get_strategy(self, agent_id):
        """
        Get the current strategy for an agent.
        
        Args:
            agent_id (str): Unique identifier for the agent
            
        Returns:
            dict: Current strategy values
        """
        if agent_id not in self.agent_strategies:
            self.logger.warning(f"Agent {agent_id} not found when getting strategy. Initializing now.")
            self._initialize_agent_strategy(agent_id)
            if agent_id not in self.agent_strategies:
                self.logger.error(f"Failed to initialize agent {agent_id} during get_strategy. Returning default strategy.")
                return self.default_strategy.copy()
        
        strategy_data = self.agent_strategies.get(agent_id)
        if strategy_data and 'current_strategy' in strategy_data:
            return strategy_data['current_strategy'].copy()
        else:
            self.logger.error(f"Agent {agent_id} found but has no 'current_strategy' key after initialization attempt. Returning default.")
            return self.default_strategy.copy()
    
    def get_strategy_effectiveness(self, agent_id):
        """
        Get metrics on how effective an agent's strategy has been.
        
        Args:
            agent_id (str): Unique identifier for the agent
            
        Returns:
            dict: Strategy effectiveness metrics
        """
        if agent_id not in self.strategy_effectiveness:
            return {
                "success_rate": 0.0,
                "avg_reward": 0.0,
                "total_actions": 0
            }
        
        effectiveness = self.strategy_effectiveness[agent_id]
        total_actions = effectiveness["actions_taken"]
        
        if total_actions == 0:
            return {
                "success_rate": 0.0,
                "avg_reward": 0.0,
                "total_actions": 0
            }
        
        success_rate = effectiveness["success_count"] / total_actions
        avg_reward = effectiveness["total_reward"] / total_actions
        
        return {
            "success_rate": success_rate,
            "avg_reward": avg_reward,
            "total_actions": total_actions,
            "success_count": effectiveness["success_count"],
            "failure_count": effectiveness["failure_count"],
            "total_reward": effectiveness["total_reward"]
        }
    
    def get_recent_strategy_changes(self, agent_id, limit=5):
        """
        Get recent strategy changes for an agent.
        
        Args:
            agent_id (str): Unique identifier for the agent
            limit (int): Maximum number of changes to return
            
        Returns:
            list: Recent strategy changes
        """
        if agent_id not in self.strategy_history:
            return []
        
        # Get most recent changes
        recent_changes = sorted(
            self.strategy_history[agent_id],
            key=lambda x: x["timestamp"], 
            reverse=True
        )[:limit]
        
        # Format changes to be more readable
        formatted_changes = []
        for change in recent_changes:
            # Calculate changes for each parameter
            param_changes = {}
            if change["old_strategy"] and change["new_strategy"]:
                for param in change["old_strategy"]:
                    old_val = change["old_strategy"][param]
                    new_val = change["new_strategy"].get(param, old_val)
                    delta = new_val - old_val
                    if abs(delta) > 0.01:  # Only report significant changes
                        param_changes[param] = {
                            "before": round(old_val, 2),
                            "after": round(new_val, 2),
                            "delta": round(delta, 2)
                        }
            
            formatted_change = {
                "timestamp": change["timestamp"],
                "reason": change["reason"],
                "param_changes": param_changes
            }
            
            # Include success/reward info if available
            if "success" in change:
                formatted_change["success"] = change["success"]
            if "reward" in change:
                formatted_change["reward"] = change["reward"]
                
            formatted_changes.append(formatted_change)
        
        return formatted_changes
    
    def _add_to_strategy_history(self, agent_id, history_entry):
        """
        Add an entry to an agent's strategy history.
        
        Args:
            agent_id (str): Unique identifier for the agent
            history_entry (dict): History entry to add
        """
        if agent_id not in self.strategy_history:
            self.strategy_history[agent_id] = []
        
        # Add entry
        self.strategy_history[agent_id].append(history_entry)
        
        # Trim if needed
        if len(self.strategy_history[agent_id]) > self.strategy_memory_size:
            self.strategy_history[agent_id] = self.strategy_history[agent_id][-self.strategy_memory_size:]
    
    def share_strategy(self, source_agent_id, target_agent_id):
        """
        Share strategy insights from one agent to another, influenced by personality and relationship.
        
        Args:
            source_agent_id (str): ID of agent sharing their strategy
            target_agent_id (str): ID of agent receiving the strategy
            
        Returns:
            bool: Whether sharing was successful
        """
        if source_agent_id not in self.agent_strategies:
            self.logger.warning(f"Source agent {source_agent_id} not registered. Cannot share strategy.")
            return False
            
        if target_agent_id not in self.agent_strategies:
            self.logger.warning(f"Target agent {target_agent_id} not registered. Cannot receive strategy.")
            return False
        
        source_strategy = self.agent_strategies[source_agent_id]['current_strategy']
        target_strategy = self.agent_strategies[target_agent_id]['current_strategy']
        
        # Record current state of target before changes
        history_entry = {
            "timestamp": time.time(),
            "old_strategy": target_strategy.copy(),
            "reason": f"shared_from_{source_agent_id}",
            "new_strategy": None  # Will be updated later
        }
        
        # Determine influence strength based on personality and relationship
        influence_strength = 0.2  # Base influence
        relationship_modifier = 1.0 # Base relationship mod

        # Fetch target personality
        target_personality = self.personality_system.get_agent_personality(target_agent_id) if self.personality_system else None
        if target_personality:
            # Openness increases receptiveness to others' strategies
            openness = target_personality.get_trait(PersonalityTrait.OPENNESS)
            influence_strength = 0.1 + (openness * 0.3)  # 0.1-0.4 range
                
            # Agreeableness also affects receptiveness
            agreeableness = target_personality.get_trait(PersonalityTrait.AGREEABLENESS)
            influence_strength += agreeableness * 0.1  # Additional 0-0.1
        
        # Fetch relationship
        if self.relationship_system:
             relationship = self.relationship_system.get_relationship(source_agent_id, target_agent_id)
             if relationship:
                 # Example: Increase influence for teammates/high trust
                 if relationship.relationship_type == RelationshipType.TEAMMATE:
                     relationship_modifier *= 1.2 # Slightly less boost than pattern sharing?
                 trust = relationship.get_metric(RelationshipMetric.TRUST)
                 relationship_modifier *= (1.0 + (trust - 50) / 125) # Milder trust effect (+/- 40%)
        
        final_influence = influence_strength * relationship_modifier
        final_influence = max(0.0, min(0.5, final_influence)) # Clamp influence to avoid drastic shifts

        # Apply influence from source to target
        strategy_changed = False
        for key in source_strategy:
            if key in target_strategy:
                target_value = target_strategy[key]
                source_value = source_strategy[key]
                
                # Move target value slightly toward source value
                new_value = target_value + (final_influence * (source_value - target_value))
                new_value = max(0.0, min(1.0, new_value)) # Ensure value stays in [0, 1] range

                if abs(new_value - target_value) > 1e-3: # Only record if change is significant
                     target_strategy[key] = new_value
                     strategy_changed = True
        
        if not strategy_changed:
             self.logger.debug(f"No significant strategy change from {source_agent_id} to {target_agent_id}")
             return False
             
        # Update history entry
        history_entry["new_strategy"] = target_strategy.copy()
        self._add_to_strategy_history(target_agent_id, history_entry)
        
        self.logger.info(f"Shared strategy from agent {source_agent_id} to {target_agent_id} with influence {final_influence:.3f}")
        return True
    
    def save_system_state(self, directory_path):
        """
        Save the current state of the strategy adaptation system.
        
        Args:
            directory_path (str): Directory to save the state to
            
        Returns:
            bool: Whether saving was successful
        """
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
        
        strategy_file = os.path.join(directory_path, "strategy_system.json")
        
        try:
            # Prepare data for saving
            save_data = {
                "agent_strategies": self.agent_strategies,
                "strategy_effectiveness": {
                    agent_id: data for agent_id, data in self.strategy_effectiveness.items()
                    if isinstance(data, dict)  # Filter out defaultdict factory
                },
                "situation_triggers": {
                    agent_id: triggers for agent_id, triggers in self.situation_triggers.items()
                    if triggers  # Only save non-empty triggers
                },
                "strategy_history": {
                    agent_id: history[:self.strategy_memory_size] 
                    for agent_id, history in self.strategy_history.items()
                },
                "system_params": {
                    "adaptation_rate": self.adaptation_rate,
                    "exploration_factor": self.exploration_factor,
                    "strategy_memory_size": self.strategy_memory_size,
                    "default_strategy": self.default_strategy
                }
            }
            
            # Save to file
            with open(strategy_file, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            self.logger.info(f"Strategy adaptation system state saved to {strategy_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving strategy adaptation system state: {e}")
            return False
    
    def load_system_state(self, directory_path):
        """
        Load a saved state of the strategy adaptation system.
        
        Args:
            directory_path (str): Directory to load the state from
            
        Returns:
            bool: Whether loading was successful
        """
        strategy_file = os.path.join(directory_path, "strategy_system.json")
        
        if not os.path.exists(strategy_file):
            self.logger.warning(f"No saved state found at {strategy_file}")
            return False
        
        try:
            # Load from file
            with open(strategy_file, 'r') as f:
                load_data = json.load(f)
            
            # Restore data
            if "agent_strategies" in load_data:
                self.agent_strategies = load_data["agent_strategies"]
            
            if "strategy_effectiveness" in load_data:
                # Convert to defaultdict
                self.strategy_effectiveness = defaultdict(lambda: {
                    "success_count": 0,
                    "failure_count": 0,
                    "total_reward": 0.0,
                    "actions_taken": 0
                })
                # Load saved effectiveness data
                for agent_id, data in load_data["strategy_effectiveness"].items():
                    self.strategy_effectiveness[agent_id] = data
                # Ensure all loaded agents have at least a default entry
                if "agent_strategies" in load_data:
                    for agent_id in load_data["agent_strategies"]:
                        # Accessing the key triggers the defaultdict factory if it doesn't exist
                        _ = self.strategy_effectiveness[agent_id]
            
            if "situation_triggers" in load_data:
                self.situation_triggers = defaultdict(dict)
                for agent_id, triggers in load_data["situation_triggers"].items():
                    self.situation_triggers[agent_id] = triggers
            
            if "strategy_history" in load_data:
                self.strategy_history = defaultdict(list)
                for agent_id, history in load_data["strategy_history"].items():
                    self.strategy_history[agent_id] = history
            
            if "system_params" in load_data:
                params = load_data["system_params"]
                self.adaptation_rate = params.get("adaptation_rate", self.adaptation_rate)
                self.exploration_factor = params.get("exploration_factor", self.exploration_factor)
                self.strategy_memory_size = params.get("strategy_memory_size", self.strategy_memory_size)
                self.default_strategy = params.get("default_strategy", self.default_strategy)
            
            self.logger.info(f"Strategy adaptation system state loaded from {strategy_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading strategy adaptation system state: {e}")
            return False 