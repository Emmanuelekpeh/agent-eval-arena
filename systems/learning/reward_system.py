import numpy as np
import logging # Added logging import
from typing import Dict, Any # Added typing import

logger = logging.getLogger(__name__) # Added logger

class RewardSystem:
    def __init__(self):
        # Core gameplay rewards - balanced for both survival and combat
        self.rewards = {
            'survival': 0.5,           # Reduced base survival reward
            'hit_enemy': 20,           # Increased hit reward
            'kill_enemy': 75,          # Increased kill reward
            'kill_player': 100,        # New: reward for eliminating other players
            'collect_energy': 15,      # Slightly reduced energy reward
            'critical_energy': 25,     # Energy when needed
            
            # Combat rewards
            'aggressive_play': 10,     # New: reward for staying close to enemies
            'successful_dodge': 15,    # Renamed from dodge_bullet
            'multi_kill': 50,          # New: bonus for multiple kills quickly
            'kill_streak': 25,         # New: bonus for consecutive kills
            
            # Penalties adjusted
            'take_damage': -10,        # Reduced damage penalty
            'death': -50,              # Reduced death penalty
            'camping': -15,            # Increased camping penalty
            'inactivity': -5,          # New: penalty for staying inactive
        }
        
        # Dynamic reward scaling
        self.combo_multiplier = 1.0
        self.wave_multiplier = 1.0
        self.team_multiplier = 1.0

        # Add exploration and tactical rewards
        self.rewards.update({
            'exploration': 5,           # Reward for exploring new areas
            'tactical_position': 15,    # Reward for good positioning
            'team_coordination': 20,    # Reward for team plays
            'resource_efficiency': 10,  # Reward for efficient resource use
            'area_control': 15         # Reward for controlling strategic areas
        })
        
        # Add tactical penalties
        self.rewards.update({
            'position_exposed': -5,     # Penalty for exposed positioning
            'team_separation': -10,     # Penalty for breaking formation
            'resource_waste': -5,       # Penalty for wasting resources
            'tactical_mistake': -8      # Penalty for tactical errors
        })

        # Add tactical rewards
        self.rewards.update({
            'formation_bonus': 15,        # Reward for maintaining formation
            'cover_usage': 10,            # Reward for using cover
            'tactical_retreat': 8,        # Reward for retreating when low health
            'target_priority': 12,        # Reward for targeting dangerous enemies
            'resource_control': 20,       # Reward for controlling resource areas
        })

    def calculate_reward(self, player_name, action_type, context: Dict[str, Any]) -> float:
        """
        Calculates the reward for a given action and context.

        Args:
            player_name (str): The name of the player/agent.
            action_type (str): The type of action performed.
            context (Dict[str, Any]): Dictionary containing contextual information 
                                      (e.g., health, energy, enemy count, 
                                      behavior metrics, tactical score).

        Returns:
            float: The calculated reward value.
        """
        base_reward = self.rewards.get(action_type, 0)
        
        if context:
            # Combat-focused scaling
            if 'health' in context:
                health = context['health']
                if health > 60:  # Encourage aggressive play at high health
                    if action_type in ['hit_enemy', 'kill_enemy', 'aggressive_play']:
                        base_reward *= 1.5
            
            # Survival scaling when needed
            if 'energy' in context and context['energy'] < 30:
                if action_type in ['collect_energy', 'successful_dodge']:
                    base_reward *= 2.0
            
            # Scale based on number of enemies
            if 'enemies_alive' in context:
                enemy_count = context['enemies_alive']
                if enemy_count > 5:  # More rewards in dangerous situations
                    base_reward *= 1.3
        
        # Apply multipliers (Assuming these are updated elsewhere based on game state)
        final_reward = base_reward * self.combo_multiplier * self.wave_multiplier * self.team_multiplier

        # Add exploration bonus
        if context and 'explored_area' in context:
            explored_ratio = context['explored_area']
            # Use .get() for safer access to potentially missing keys
            behavior_metrics = context.get('BEHAVIOR_METRICS', {})
            exploration_weight = behavior_metrics.get('exploration_weight', 0.3)
            final_reward += explored_ratio * exploration_weight * 10
            
        # Add tactical positioning bonus
        if context and 'tactical_score' in context:
            behavior_metrics = context.get('BEHAVIOR_METRICS', {})
            tactical_bonus_weight = behavior_metrics.get('tactical_bonus', 0.25)
            tactical_bonus = context['tactical_score'] * tactical_bonus_weight
            final_reward += tactical_bonus

        # Add formation bonus
        if context and context.get('in_formation', False): # Safer check
            final_reward += self.rewards.get('formation_bonus', 0) # Add fixed bonus
            
        # Add target priority bonus
        if action_type == 'kill_enemy' and context.get('target_threat_level', 0) > 0.7:
            final_reward += self.rewards.get('target_priority', 0) # Add fixed bonus
            
        return final_reward

    # Note: Methods like _get_state, _get_tactical_position_score were part of BattleRoyaleEnv
    # in the provided snippet and are not part of the RewardSystem itself.
    # They would need to be implemented within the environment or passed via context. 