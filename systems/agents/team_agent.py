"""
Team-focused agent implementation for AI Battle Arena.

This module provides a specialized agent implementation that works 
with the TeamSystem to coordinate movement, formation maintenance,
and team-based decision making.
"""

import numpy as np
import math
from typing import Dict, List, Any, Tuple, Optional, Union
import time

from systems.agents.base_agent import BaseAgent
from systems.agents.mlp_agent import MLPAgent
from systems.agents.personality_system import PersonalityTrait

class TeamAgent(BaseAgent):
    """
    Agent implementation specialized for team coordination.
    
    This agent extends the base agent functionality with awareness
    of team formations, roles, and coordination strategies. It integrates
    with the TeamSystem to maintain formations and execute team abilities.
    """
    
    def __init__(self, name: str = "Team-Agent", 
                 team_id: str = None, 
                 role: str = None,
                 hidden_layer_sizes: List[int] = [64, 32, 16]):
        """
        Initialize the team agent.
        
        Args:
            name: Agent name
            team_id: Identifier for the team this agent belongs to
            role: The agent's role within the team (leader, support, etc.)
            hidden_layer_sizes: List of hidden layer sizes for the neural network
        """
        super().__init__(name)
        
        # Team parameters
        self.team_id = team_id
        self.role = role
        self.teammate_positions = []
        self.formation_target = None
        self.formation_bonus = 1.0
        
        # Network architecture (using MLP as the base)
        self.model = MLPAgent(name=f"{name}_model", hidden_layer_sizes=hidden_layer_sizes)
        
        # Role-specific behavior parameters
        self.role_params = {
            'leader': {
                'exploration_factor': 0.8,
                'aggression_factor': 1.2,
                'defense_factor': 1.0,
                'formation_weight': 0.6
            },
            'support': {
                'exploration_factor': 0.5,
                'aggression_factor': 0.8,
                'defense_factor': 1.3,
                'formation_weight': 1.5
            },
            'flanker': {
                'exploration_factor': 1.2,
                'aggression_factor': 1.4,
                'defense_factor': 0.7,
                'formation_weight': 0.8
            },
            'defender': {
                'exploration_factor': 0.4,
                'aggression_factor': 0.7,
                'defense_factor': 1.8,
                'formation_weight': 1.2
            },
            'attacker': {
                'exploration_factor': 0.9,
                'aggression_factor': 1.6,
                'defense_factor': 0.6,
                'formation_weight': 0.7
            },
            'scout': {
                'exploration_factor': 1.6,
                'aggression_factor': 0.6,
                'defense_factor': 0.5,
                'formation_weight': 0.3
            }
        }
        
        # Default role parameters if not assigned a specific role
        self.default_role_params = {
            'exploration_factor': 1.0,
            'aggression_factor': 1.0,
            'defense_factor': 1.0,
            'formation_weight': 1.0
        }
        
        # Coordination parameters
        self.team_history = []  # Record of team actions and outcomes
        self.coordination_weight = 0.8  # How much to prioritize coordination vs individual goals
        self.last_team_ability_time = 0
        self.team_ability_cooldown = 180  # 3 seconds at 60 fps
        
        # Personality reference
        self.personality = None
        self.last_personality_check = 0
        
    def initialize_agent(self, state_size: int, action_size: int) -> None:
        """
        Initialize agent with state and action dimensions.
        
        Args:
            state_size: Dimension of the state vector
            action_size: Number of possible actions
        """
        self.state_size = state_size
        self.action_size = action_size
        
        # Initialize the underlying model
        self.model.initialize(state_size, action_size)
        
    def get_action(self, state: np.ndarray) -> int:
        """
        Select action based on state and team considerations.
        
        This method extends the standard action selection with 
        team-oriented decision making.
        
        Args:
            state: Current state vector
            
        Returns:
            Selected action index
        """
        # Preprocess state and extract team-related information
        state = self.preprocess_state(state)
        team_factors = self._extract_team_factors(state[0])
        
        # Get base action from the model
        try:
            base_action = self.model.get_action(state)
        except Exception as e:
            # If model fails, return a random action
            print(f"Model error for {self.name}: {str(e)}. Using random action.")
            base_action = np.random.randint(0, self.action_size)
        
        # Modify action based on team role and position if we have team information
        if self.team_id and self.formation_target:
            # Calculate if we need to move toward formation position
            action = self._adjust_for_formation(base_action, state[0], team_factors)
        else:
            action = base_action
            
        return action
    
    def learn(self, state: np.ndarray, action: int, reward: float, 
             next_state: np.ndarray, done: bool = False) -> None:
        """
        Update agent knowledge from experience, incorporating team feedback.
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Episode complete flag
        """
        # Adjust reward based on team factors
        adjusted_reward = self._adjust_reward_for_team(reward, state, action)
        
        # Pass the adjusted reward to the underlying model
        self.model.learn(state, action, adjusted_reward, next_state, done)
        
        # Remember team actions for pattern analysis
        if self.team_id:
            self._update_team_history(state, action, adjusted_reward, done)
    
    def set_team_info(self, team_id: str, role: str) -> None:
        """
        Set or update team information for this agent.
        
        Args:
            team_id: Team identifier
            role: Agent's role in the team
        """
        self.team_id = team_id
        self.role = role
    
    def update_formation_target(self, target_position: Tuple[float, float]) -> None:
        """
        Update this agent's target position in the formation.
        
        Args:
            target_position: (x, y) target position in the formation
        """
        self.formation_target = target_position
    
    def update_teammate_positions(self, positions: List[Tuple[float, float]]) -> None:
        """
        Update the known positions of teammates.
        
        Args:
            positions: List of (x, y) positions for teammates
        """
        self.teammate_positions = positions
    
    def set_formation_bonus(self, bonus: float) -> None:
        """
        Set the current formation bonus value.
        
        Args:
            bonus: Formation bonus multiplier
        """
        self.formation_bonus = bonus
    
    def _extract_team_factors(self, state: np.ndarray) -> Dict[str, float]:
        """
        Extract team-related factors from the state.
        
        Args:
            state: Current state vector
            
        Returns:
            Dictionary of team-related factors
        """
        # Get parameters for the agent's role
        role_params = (self.role_params.get(self.role, self.default_role_params) 
                       if self.role else self.default_role_params)
        
        # Calculate distance to formation target if available
        formation_distance = 0.0
        if self.formation_target and len(state) >= 2:
            agent_x, agent_y = state[0], state[1]
            target_x, target_y = self.formation_target
            dx = agent_x - target_x
            dy = agent_y - target_y
            formation_distance = math.sqrt(dx*dx + dy*dy)
        
        # Calculate team spread (distance between furthest teammates)
        team_spread = 0.0
        if len(self.teammate_positions) >= 2:
            max_dist = 0.0
            for i, pos1 in enumerate(self.teammate_positions):
                for j, pos2 in enumerate(self.teammate_positions[i+1:]):
                    dx = pos1[0] - pos2[0]
                    dy = pos1[1] - pos2[1]
                    dist = math.sqrt(dx*dx + dy*dy)
                    max_dist = max(max_dist, dist)
            team_spread = max_dist
        
        # Compile team factors
        team_factors = {
            'formation_distance': formation_distance,
            'team_spread': team_spread,
            'formation_bonus': self.formation_bonus,
            'exploration_factor': role_params['exploration_factor'],
            'aggression_factor': role_params['aggression_factor'],
            'defense_factor': role_params['defense_factor'],
            'formation_weight': role_params['formation_weight'],
            'is_leader': 1.0 if self.role == 'leader' else 0.0,
            'is_attacker': 1.0 if self.role == 'attacker' else 0.0,
            'is_defender': 1.0 if self.role == 'defender' else 0.0
        }
        
        return team_factors
    
    def _adjust_for_formation(self, base_action: int, state: np.ndarray, 
                             team_factors: Dict[str, float]) -> int:
        """
        Adjust action to maintain formation position, considering personality traits.
        
        Args:
            base_action: Original action selected by the model
            state: Current state vector
            team_factors: Team-related factors from state
            
        Returns:
            Adjusted action index
        """
        if not self.formation_target:
            return base_action
            
        # Extract relevant factors
        formation_distance = team_factors['formation_distance']
        role_params = team_factors['role_params']
        
        # Get personality-based factors
        formation_compliance = team_factors.get('formation_compliance', 0.5)
        risk_tolerance = team_factors.get('risk_tolerance', 0.5)
        
        # Determine if we should prioritize formation or continue with base action
        formation_threshold = 50.0 * (1.0 + (1.0 - formation_compliance))
        
        # Higher risk_tolerance means more likely to ignore formation
        if risk_tolerance > 0.7:
            formation_threshold *= 1.5
        
        # Scouts and aggressors can stray further from formation
        if self.role in ['scout', 'flanker']:
            formation_threshold *= 1.5
            
        # If close enough to formation position, continue with base action
        if formation_distance <= formation_threshold:
            return base_action
            
        # Calculate direction to formation target
        if len(state) >= 2:
            agent_x, agent_y = state[0], state[1]
            target_x, target_y = self.formation_target
            dx = target_x - agent_x
            dy = target_y - agent_y
            
            # Determine best direction to move
            if abs(dx) > abs(dy):
                # Move horizontally
                if dx > 0:
                    return 3  # Right
                else:
                    return 2  # Left
            else:
                # Move vertically
                if dy > 0:
                    return 1  # Down
                else:
                    return 0  # Up
        
        return base_action
    
    def _adjust_reward_for_team(self, reward: float, state: np.ndarray, action: int) -> float:
        """
        Adjust reward based on team considerations and personality traits.
        
        Args:
            reward: Original reward
            state: State that led to the action
            action: Action taken
            
        Returns:
            Adjusted reward
        """
        # Default to original reward
        adjusted_reward = reward
        
        # If we have team information, adjust reward
        if self.team_id and self.formation_target:
            # Extract team factors
            team_factors = self._extract_team_factors(self.preprocess_state(state)[0])
            
            # Bonus for maintaining formation
            formation_distance = team_factors['formation_distance']
            role_params = team_factors['role_params']
            
            # Personality factors
            loyalty = team_factors.get('loyalty', 0.5)
            formation_compliance = team_factors.get('formation_compliance', 0.5)
            
            # Calculate formation factor based on distance and role
            # Modify based on the agent's personality traits
            formation_weight = role_params['formation_weight']
            
            # Adjust formation weight based on personality
            formation_weight *= (0.5 + formation_compliance)
            
            # Calculate formation factor
            formation_factor = max(0, 1.0 - formation_distance / (100.0 * formation_weight))
            
            # Apply formation bonus, scaled by loyalty
            formation_reward = (
                0.1 * self.formation_bonus * formation_factor * 
                formation_weight * (0.5 + loyalty * 0.5)
            )
            
            # Combine rewards
            adjusted_reward = reward + formation_reward
            
        return adjusted_reward
    
    def _update_team_history(self, state: np.ndarray, action: int, reward: float, done: bool) -> None:
        """
        Update team action history for pattern analysis.
        
        Args:
            state: Current state
            action: Action taken
            reward: Adjusted reward received
            done: Episode complete flag
        """
        # Add to history
        self.team_history.append((state, action, reward, done))
        
        # Keep history bounded
        if len(self.team_history) > 1000:
            self.team_history = self.team_history[-1000:]
    
    def get_serializable_state(self) -> Dict[str, Any]:
        """
        Get agent state for serialization.
        
        Returns:
            Dictionary with serializable agent state
        """
        state = super().get_serializable_state()
        
        # Add team agent parameters
        state.update({
            'team_id': self.team_id,
            'role': self.role,
            'coordination_weight': self.coordination_weight,
            'model': self.model.get_serializable_state() if self.model else None,
        })
        
        return state
    
    def load_from_state(self, state: Dict[str, Any]) -> None:
        """
        Load agent state from serialized data.
        
        Args:
            state: Dictionary with agent state
        """
        # Load team parameters
        self.team_id = state.get('team_id')
        self.role = state.get('role')
        self.coordination_weight = state.get('coordination_weight', 0.8)
        
        # Load model state if available
        if 'model' in state and self.model:
            self.model.load_from_state(state['model'])


class DefenderTeamAgent(TeamAgent):
    """Specialized team agent that focuses on defensive tactics."""
    
    def __init__(self, name: str = "Defender-Agent", team_id: str = None, role: str = None):
        super().__init__(name=name, team_id=team_id, role=role or "defender", 
                         hidden_layer_sizes=[64, 32, 32])
        
        # Override default coordination settings
        self.coordination_weight = 0.9
        
        # Specialized defensive parameters
        self.shield_ability_threshold = 0.6  # Health threshold to suggest shield


class AttackerTeamAgent(TeamAgent):
    """Specialized team agent that focuses on offensive tactics."""
    
    def __init__(self, name: str = "Attacker-Agent", team_id: str = None, role: str = None):
        super().__init__(name=name, team_id=team_id, role=role or "attacker", 
                         hidden_layer_sizes=[64, 48, 16])
        
        # Override default coordination settings
        self.coordination_weight = 0.7
        
        # Specialized offensive parameters
        self.strike_ability_threshold = 0.7  # Opportunity threshold to suggest strike


class SupportTeamAgent(TeamAgent):
    """Specialized team agent that focuses on supporting teammates."""
    
    def __init__(self, name: str = "Support-Agent", team_id: str = None, role: str = None):
        super().__init__(name=name, team_id=team_id, role=role or "support", 
                         hidden_layer_sizes=[64, 48, 32])
        
        # Override default coordination settings
        self.coordination_weight = 1.0
        
        # Specialized support parameters
        self.energy_transfer_threshold = 0.4  # Energy threshold to transfer to teammates


class ScoutTeamAgent(TeamAgent):
    """Specialized team agent that focuses on exploration and information gathering."""
    
    def __init__(self, name: str = "Scout-Agent", team_id: str = None, role: str = None):
        super().__init__(name=name, team_id=team_id, role=role or "scout", 
                         hidden_layer_sizes=[32, 64, 32])
        
        # Override default coordination settings
        self.coordination_weight = 0.5
        
        # Specialized scout parameters
        self.exploration_radius = 1.5  # Multiplier for exploration distance


# Export all team agent classes
__all__ = [
    'TeamAgent',
    'DefenderTeamAgent',
    'AttackerTeamAgent',
    'SupportTeamAgent',
    'ScoutTeamAgent'
] 