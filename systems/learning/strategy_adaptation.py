"""
Strategy Adaptation System for AI Battle Arena.

This module provides mechanisms for agents to adapt their strategies
based on performance metrics, opponent analysis, and environmental factors.
"""

import numpy as np
from collections import deque, defaultdict
from typing import Dict, List, Any, Tuple, Optional, Union, Set
import math
import random
import json
import logging
import os
import time

class Strategy:
    """
    Represents a strategy that can be used by an agent or team.
    
    A strategy consists of:
    - A set of heuristics/parameters that guide decision-making
    - Performance metrics for evaluation
    - Conditions under which the strategy is effective
    """
    
    def __init__(self, 
               strategy_id: str, 
               parameters: Dict[str, Any],
               metadata: Dict[str, Any] = None):
        """
        Initialize a strategy.
        
        Args:
            strategy_id: Unique identifier for this strategy
            parameters: Parameters that define the strategy
            metadata: Additional information about the strategy
        """
        self.strategy_id = strategy_id
        self.parameters = parameters
        self.metadata = metadata or {}
        self.performance = {
            'wins': 0,
            'losses': 0,
            'draws': 0,
            'total_reward': 0.0,
            'uses': 0,
            'success_rate': 0.0,
            'avg_reward': 0.0,
            'effectiveness': 0.0
        }
        self.conditions = {
            'enemy_types': set(),
            'team_sizes': set(),
            'formations': set(),
            'environments': set()
        }
        self.history = deque(maxlen=100)  # Recent performance records
        
    def update_performance(self, 
                         outcome: str, 
                         reward: float, 
                         context: Dict[str, Any] = None) -> None:
        """
        Update the performance metrics for this strategy.
        
        Args:
            outcome: 'win', 'loss', or 'draw'
            reward: Total reward received
            context: Additional context about the scenario
        """
        self.performance['uses'] += 1
        self.performance['total_reward'] += reward
        
        if outcome == 'win':
            self.performance['wins'] += 1
        elif outcome == 'loss':
            self.performance['losses'] += 1
        elif outcome == 'draw':
            self.performance['draws'] += 1
            
        # Calculate derived metrics
        total_outcomes = self.performance['wins'] + self.performance['losses'] + self.performance['draws']
        self.performance['success_rate'] = self.performance['wins'] / max(1, total_outcomes)
        self.performance['avg_reward'] = self.performance['total_reward'] / max(1, self.performance['uses'])
        
        # Calculate overall effectiveness (weighted sum of success rate and average reward)
        self.performance['effectiveness'] = (
            0.7 * self.performance['success_rate'] +
            0.3 * min(1.0, self.performance['avg_reward'] / 100.0)  # Normalize reward to 0-1 range
        )
        
        # Record in history
        history_entry = {
            'outcome': outcome,
            'reward': reward,
            'timestamp': 0,  # Would use actual timestamp in real system
            'context': context.copy() if context else {}
        }
        self.history.append(history_entry)
        
        # Update conditions if context provided
        if context:
            if 'enemy_type' in context:
                self.conditions['enemy_types'].add(context['enemy_type'])
            if 'team_size' in context:
                self.conditions['team_sizes'].add(context['team_size'])
            if 'formation' in context:
                self.conditions['formations'].add(context['formation'])
            if 'environment' in context:
                self.conditions['environments'].add(context['environment'])
    
    def get_parameter(self, param_name: str, default: Any = None) -> Any:
        """
        Get a strategy parameter.
        
        Args:
            param_name: Name of the parameter
            default: Default value if parameter not found
            
        Returns:
            Parameter value
        """
        return self.parameters.get(param_name, default)
    
    def set_parameter(self, param_name: str, value: Any) -> None:
        """
        Set a strategy parameter.
        
        Args:
            param_name: Name of the parameter
            value: New value for the parameter
        """
        self.parameters[param_name] = value
        
    def adjust_parameters(self, adjustments: Dict[str, Any]) -> None:
        """
        Adjust multiple parameters at once.
        
        Args:
            adjustments: Dictionary of parameter adjustments
        """
        for param, value in adjustments.items():
            self.parameters[param] = value
    
    def get_effectiveness_for_context(self, context: Dict[str, Any]) -> float:
        """
        Calculate effectiveness for a specific context.
        
        Args:
            context: Context to evaluate effectiveness for
            
        Returns:
            Effectiveness score between 0.0 and 1.0
        """
        # Start with general effectiveness
        effectiveness = self.performance['effectiveness']
        
        # Adjust based on context-specific history
        relevant_history = [
            entry for entry in self.history 
            if self._context_matches(entry['context'], context)
        ]
        
        if relevant_history:
            wins = sum(1 for entry in relevant_history if entry['outcome'] == 'win')
            total = len(relevant_history)
            context_success_rate = wins / total
            
            # Blend general effectiveness with context-specific success rate
            effectiveness = 0.3 * effectiveness + 0.7 * context_success_rate
            
        return effectiveness
    
    def _context_matches(self, history_context: Dict[str, Any], 
                      current_context: Dict[str, Any]) -> bool:
        """
        Check if a historical context matches the current context.
        
        Args:
            history_context: Context from history
            current_context: Current context
            
        Returns:
            True if contexts match on key dimensions
        """
        if not history_context or not current_context:
            return False
            
        # Check key dimensions
        key_dimensions = ['enemy_type', 'team_size', 'formation', 'environment']
        
        for key in key_dimensions:
            if key in history_context and key in current_context:
                if history_context[key] != current_context[key]:
                    return False
                    
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert strategy to dictionary for serialization.
        
        Returns:
            Dictionary representation of the strategy
        """
        return {
            'strategy_id': self.strategy_id,
            'parameters': self.parameters,
            'metadata': self.metadata,
            'performance': self.performance,
            'conditions': {
                'enemy_types': list(self.conditions['enemy_types']),
                'team_sizes': list(self.conditions['team_sizes']),
                'formations': list(self.conditions['formations']),
                'environments': list(self.conditions['environments'])
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Strategy':
        """
        Create strategy from dictionary.
        
        Args:
            data: Dictionary representation of a strategy
            
        Returns:
            Strategy instance
        """
        strategy = cls(
            data['strategy_id'],
            data['parameters'],
            data.get('metadata', {})
        )
        
        strategy.performance = data.get('performance', strategy.performance)
        
        # Convert lists back to sets
        conditions = data.get('conditions', {})
        for key, value in conditions.items():
            if isinstance(value, list):
                strategy.conditions[key] = set(value)
            
        return strategy

class StrategyPool:
    """
    Manages a collection of strategies for different scenarios.
    
    Features:
    - Store and retrieve strategies
    - Track strategy performance
    - Recommend strategies based on context
    - Generate new strategies through variation
    """
    
    def __init__(self, max_strategies: int = 50):
        """
        Initialize a strategy pool.
        
        Args:
            max_strategies: Maximum number of strategies to maintain
        """
        self.max_strategies = max_strategies
        self.strategies = {}  # strategy_id -> Strategy
        self.agent_strategies = defaultdict(set)  # agent_id -> set of strategy_ids
        self.team_strategies = defaultdict(set)  # team_id -> set of strategy_ids
        
    def add_strategy(self, strategy: Strategy) -> None:
        """
        Add a strategy to the pool.
        
        Args:
            strategy: Strategy to add
        """
        self.strategies[strategy.strategy_id] = strategy
        
        # Prune if we exceed maximum
        if len(self.strategies) > self.max_strategies:
            self._prune_strategies()
    
    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """
        Get a strategy by ID.
        
        Args:
            strategy_id: ID of the strategy
            
        Returns:
            Strategy or None if not found
        """
        return self.strategies.get(strategy_id)
    
    def assign_strategy_to_agent(self, agent_id: str, strategy_id: str) -> None:
        """
        Assign a strategy to an agent.
        
        Args:
            agent_id: Agent ID
            strategy_id: Strategy ID
        """
        if strategy_id in self.strategies:
            self.agent_strategies[agent_id].add(strategy_id)
    
    def assign_strategy_to_team(self, team_id: str, strategy_id: str) -> None:
        """
        Assign a strategy to a team.
        
        Args:
            team_id: Team ID
            strategy_id: Strategy ID
        """
        if strategy_id in self.strategies:
            self.team_strategies[team_id].add(strategy_id)
    
    def get_agent_strategies(self, agent_id: str) -> List[Strategy]:
        """
        Get all strategies assigned to an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of strategies
        """
        strategy_ids = self.agent_strategies.get(agent_id, set())
        return [self.strategies[sid] for sid in strategy_ids if sid in self.strategies]
    
    def get_team_strategies(self, team_id: str) -> List[Strategy]:
        """
        Get all strategies assigned to a team.
        
        Args:
            team_id: Team ID
            
        Returns:
            List of strategies
        """
        strategy_ids = self.team_strategies.get(team_id, set())
        return [self.strategies[sid] for sid in strategy_ids if sid in self.strategies]
    
    def recommend_strategy(self, 
                        context: Dict[str, Any], 
                        entity_id: str = None, 
                        is_team: bool = False) -> Optional[Strategy]:
        """
        Recommend the best strategy for a given context.
        
        Args:
            context: Current context
            entity_id: Agent or team ID
            is_team: Whether entity_id refers to a team
            
        Returns:
            Recommended strategy or None
        """
        # Get strategies for this entity if specified
        if entity_id:
            if is_team:
                strategies = self.get_team_strategies(entity_id)
            else:
                strategies = self.get_agent_strategies(entity_id)
        else:
            strategies = list(self.strategies.values())
            
        if not strategies:
            return None
            
        # Calculate effectiveness for each strategy in this context
        effectiveness_scores = [
            (strategy, strategy.get_effectiveness_for_context(context))
            for strategy in strategies
        ]
        
        # Sort by effectiveness
        effectiveness_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return the most effective strategy
        return effectiveness_scores[0][0]
    
    def create_variant(self, 
                     base_strategy_id: str, 
                     variation_amount: float = 0.2) -> Optional[Strategy]:
        """
        Create a variant of an existing strategy.
        
        Args:
            base_strategy_id: ID of the base strategy
            variation_amount: Amount of variation (0.0-1.0)
            
        Returns:
            New strategy or None if base not found
        """
        base_strategy = self.get_strategy(base_strategy_id)
        if not base_strategy:
            return None
            
        # Create a new ID
        new_id = f"{base_strategy_id}_var_{len(self.strategies)}"
        
        # Copy parameters
        new_params = base_strategy.parameters.copy()
        
        # Vary parameters
        for param, value in new_params.items():
            if isinstance(value, (int, float)):
                # Vary numeric parameters
                variation = value * variation_amount * (random.random() * 2 - 1)
                new_params[param] = value + variation
                
        # Create new strategy
        new_strategy = Strategy(
            new_id,
            new_params,
            {**base_strategy.metadata, 'parent': base_strategy_id}
        )
        
        # Add to pool
        self.add_strategy(new_strategy)
        
        return new_strategy
    
    def merge_strategies(self, 
                       strategy_id1: str, 
                       strategy_id2: str) -> Optional[Strategy]:
        """
        Merge two strategies to create a new one.
        
        Args:
            strategy_id1: First strategy ID
            strategy_id2: Second strategy ID
            
        Returns:
            New merged strategy or None if either strategy not found
        """
        strategy1 = self.get_strategy(strategy_id1)
        strategy2 = self.get_strategy(strategy_id2)
        
        if not strategy1 or not strategy2:
            return None
            
        # Create a new ID
        new_id = f"merged_{strategy_id1}_{strategy_id2}"
        
        # Merge parameters
        new_params = {}
        all_keys = set(strategy1.parameters.keys()) | set(strategy2.parameters.keys())
        
        for key in all_keys:
            if key in strategy1.parameters and key in strategy2.parameters:
                # Both have this parameter, use weighted average based on effectiveness
                weight1 = strategy1.performance['effectiveness']
                weight2 = strategy2.performance['effectiveness']
                total_weight = weight1 + weight2
                
                if isinstance(strategy1.parameters[key], (int, float)) and \
                   isinstance(strategy2.parameters[key], (int, float)):
                    # Numeric parameters: weighted average
                    new_params[key] = (
                        (strategy1.parameters[key] * weight1 + 
                         strategy2.parameters[key] * weight2) / 
                        max(0.001, total_weight)
                    )
                else:
                    # Non-numeric: use from more effective strategy
                    new_params[key] = (
                        strategy1.parameters[key] if weight1 >= weight2 
                        else strategy2.parameters[key]
                    )
            elif key in strategy1.parameters:
                new_params[key] = strategy1.parameters[key]
            else:
                new_params[key] = strategy2.parameters[key]
                
        # Create new strategy
        new_strategy = Strategy(
            new_id,
            new_params,
            {'parents': [strategy_id1, strategy_id2]}
        )
        
        # Add to pool
        self.add_strategy(new_strategy)
        
        return new_strategy
    
    def _prune_strategies(self) -> None:
        """
        Remove the least effective strategies to stay under max_strategies.
        """
        # Sort strategies by effectiveness
        sorted_strategies = sorted(
            self.strategies.items(),
            key=lambda x: x[1].performance['effectiveness']
        )
        
        # Remove least effective strategies
        excess = len(self.strategies) - self.max_strategies
        if excess <= 0:
            return
            
        for i in range(excess):
            strategy_id, _ = sorted_strategies[i]
            
            # Remove from strategies
            if strategy_id in self.strategies:
                del self.strategies[strategy_id]
                
            # Remove from agent assignments
            for agent_id in self.agent_strategies:
                self.agent_strategies[agent_id].discard(strategy_id)
                
            # Remove from team assignments
            for team_id in self.team_strategies:
                self.team_strategies[team_id].discard(strategy_id)
    
    def save_to_file(self, filepath: str) -> bool:
        """
        Save strategies to a JSON file.
        
        Args:
            filepath: Path to save to
            
        Returns:
            True if successful
        """
        try:
            data = {
                'strategies': {
                    sid: strategy.to_dict() 
                    for sid, strategy in self.strategies.items()
                },
                'agent_strategies': {
                    agent_id: list(strategy_ids)
                    for agent_id, strategy_ids in self.agent_strategies.items()
                },
                'team_strategies': {
                    team_id: list(strategy_ids)
                    for team_id, strategy_ids in self.team_strategies.items()
                }
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving strategies: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, filepath: str) -> Optional['StrategyPool']:
        """
        Load strategies from a JSON file.
        
        Args:
            filepath: Path to load from
            
        Returns:
            StrategyPool or None if loading failed
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            pool = cls()
            
            # Load strategies
            for sid, strategy_data in data.get('strategies', {}).items():
                strategy = Strategy.from_dict(strategy_data)
                pool.strategies[sid] = strategy
                
            # Load agent assignments
            for agent_id, strategy_ids in data.get('agent_strategies', {}).items():
                pool.agent_strategies[agent_id] = set(strategy_ids)
                
            # Load team assignments
            for team_id, strategy_ids in data.get('team_strategies', {}).items():
                pool.team_strategies[team_id] = set(strategy_ids)
                
            return pool
        except Exception as e:
            print(f"Error loading strategies: {e}")
            return None

class StrategyAdaptationSystem:
    """
    System for adapting agent strategies based on performance metrics and pattern recognition insights.
    Integrates with PatternRecognitionSystem to make informed strategy adjustments.
    """
    
    def __init__(self, 
                 pattern_recognition_system,
                 adaptation_rate=0.05, 
                 strategy_memory_size=10, 
                 min_experience_threshold=5,
                 performance_window_size=20):
        """
        Initialize the strategy adaptation system.
        
        Args:
            pattern_recognition_system: Reference to the PatternRecognitionSystem instance
            adaptation_rate: Rate at which strategies adapt (0.0 to 1.0)
            strategy_memory_size: Number of past strategies to remember per agent
            min_experience_threshold: Minimum experiences needed before adaptation
            performance_window_size: Number of recent outcomes to consider for performance evaluation
        """
        self.pattern_system = pattern_recognition_system
        self.adaptation_rate = max(0.0, min(1.0, adaptation_rate))  # Ensure between 0 and 1
        self.strategy_memory_size = max(1, strategy_memory_size)
        self.min_experience_threshold = max(1, min_experience_threshold)
        self.performance_window_size = performance_window_size
        
        # Agent strategies - map of agent_id to current strategy parameters
        self.agent_strategies = {}
        
        # Strategy history - map of agent_id to deque of past strategies
        self.strategy_history = defaultdict(lambda: deque(maxlen=self.strategy_memory_size))
        
        # Recent performance - map of agent_id to deque of recent outcomes (success/failure)
        self.recent_outcomes = defaultdict(lambda: deque(maxlen=self.performance_window_size))
        
        # Performance metrics - map of agent_id to dict of performance statistics
        self.performance_metrics = defaultdict(lambda: {
            'total_success': 0,
            'total_failure': 0,
            'total_reward': 0.0,
            'adaptations': 0,
            'last_adaptation_time': 0
        })
        
        logging.info(f"StrategyAdaptationSystem initialized with adaptation_rate={adaptation_rate}")
    
    def _initialize_agent_strategy(self, agent_id, personality_traits=None):
        """
        Initialize default strategy parameters for an agent.
        
        Args:
            agent_id: ID of the agent
            personality_traits: Optional dictionary of personality traits
            
        Returns:
            Dictionary of strategy parameters
        """
        # Default strategy parameters
        strategy = {
            'risk_tolerance': 0.5,           # How much risk the agent is willing to take
            'exploration_rate': 0.3,         # How often the agent tries new actions
            'pattern_reliance': 0.6,         # How much the agent relies on recognized patterns
            'reward_focus': 0.5,             # Focus on immediate vs. long-term rewards
            'adaptation_threshold': 0.3,     # Performance threshold that triggers adaptation
            'context_sensitivity': 0.5,      # How much context influences decisions
            'cooperation_tendency': 0.5,     # Tendency to cooperate with others
            'specialist_generalist': 0.5,    # 0 = specialist, 1 = generalist
            'action_preferences': {},        # Action-specific weights
            'context_weights': {},           # Context factor weights
        }
        
        # Adjust based on personality if available
        if personality_traits:
            # Openness affects exploration rate and adaptation
            if 'openness' in personality_traits:
                openness = personality_traits['openness']
                strategy['exploration_rate'] = 0.2 + (openness * 0.4)  # 0.2 to 0.6
                strategy['specialist_generalist'] = 0.3 + (openness * 0.5)  # 0.3 to 0.8
            
            # Conscientiousness affects pattern reliance and context sensitivity
            if 'conscientiousness' in personality_traits:
                conscientiousness = personality_traits['conscientiousness']
                strategy['pattern_reliance'] = 0.4 + (conscientiousness * 0.4)  # 0.4 to 0.8
                strategy['context_sensitivity'] = 0.3 + (conscientiousness * 0.5)  # 0.3 to 0.8
            
            # Extraversion affects cooperation tendency
            if 'extraversion' in personality_traits:
                extraversion = personality_traits['extraversion']
                strategy['cooperation_tendency'] = 0.3 + (extraversion * 0.5)  # 0.3 to 0.8
            
            # Agreeableness affects cooperation and reward focus
            if 'agreeableness' in personality_traits:
                agreeableness = personality_traits['agreeableness']
                strategy['cooperation_tendency'] = (strategy['cooperation_tendency'] + 0.3 + (agreeableness * 0.5)) / 2  # Blend with extraversion effect
                strategy['reward_focus'] = 0.7 - (agreeableness * 0.4)  # 0.3 to 0.7 (inverted, lower means more long-term focus)
            
            # Neuroticism affects risk tolerance
            if 'neuroticism' in personality_traits:
                neuroticism = personality_traits['neuroticism']
                strategy['risk_tolerance'] = 0.7 - (neuroticism * 0.4)  # 0.3 to 0.7 (inverted)
        
        logging.info(f"Initialized strategy for agent {agent_id}")
        return strategy
    
    def integrate_personality_traits(self, agent_id, personality_traits):
        """
        Adjust agent strategy based on personality traits.
        
        Args:
            agent_id: ID of the agent
            personality_traits: Dictionary of personality traits
            
        Returns:
            Boolean indicating success
        """
        try:
            # Initialize strategy if not exists
            if agent_id not in self.agent_strategies:
                self.agent_strategies[agent_id] = self._initialize_agent_strategy(agent_id, personality_traits)
                # Add to history
                self.strategy_history[agent_id].append(self.agent_strategies[agent_id].copy())
            else:
                # Adjust existing strategy
                strategy = self.agent_strategies[agent_id]
                
                # Apply personality influences (with smaller effect than initialization)
                adjustment_rate = 0.15  # Smaller adjustment for existing strategies
                
                if 'openness' in personality_traits:
                    openness = personality_traits['openness']
                    strategy['exploration_rate'] = strategy['exploration_rate'] * (1 - adjustment_rate) + (0.2 + openness * 0.4) * adjustment_rate
                
                if 'conscientiousness' in personality_traits:
                    conscientiousness = personality_traits['conscientiousness']
                    strategy['pattern_reliance'] = strategy['pattern_reliance'] * (1 - adjustment_rate) + (0.4 + conscientiousness * 0.4) * adjustment_rate
                
                if 'neuroticism' in personality_traits:
                    neuroticism = personality_traits['neuroticism']
                    strategy['risk_tolerance'] = strategy['risk_tolerance'] * (1 - adjustment_rate) + (0.7 - neuroticism * 0.4) * adjustment_rate
                
                # Add updated strategy to history
                self.strategy_history[agent_id].append(strategy.copy())
            
            logging.info(f"Integrated personality traits for agent {agent_id}")
            return True
        
        except Exception as e:
            logging.error(f"Error integrating personality traits for agent {agent_id}: {e}")
            return False
    
    def get_agent_strategy(self, agent_id):
        """
        Get the current strategy for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Dictionary of strategy parameters
        """
        # Initialize if not exists
        if agent_id not in self.agent_strategies:
            self.agent_strategies[agent_id] = self._initialize_agent_strategy(agent_id)
            self.strategy_history[agent_id].append(self.agent_strategies[agent_id].copy())
        
        return self.agent_strategies[agent_id]
    
    def record_strategy_outcome(self, agent_id, action, success, reward, context=None):
        """
        Record the outcome of an agent's action for strategy evaluation.
        
        Args:
            agent_id: ID of the agent
            action: Action taken
            success: Boolean indicating if the action was successful
            reward: Reward received
            context: Optional context of the action
            
        Returns:
            Boolean indicating if recording was successful
        """
        try:
            # Initialize strategy if needed
            if agent_id not in self.agent_strategies:
                self.agent_strategies[agent_id] = self._initialize_agent_strategy(agent_id)
                self.strategy_history[agent_id].append(self.agent_strategies[agent_id].copy())
            
            # Update recent outcomes
            self.recent_outcomes[agent_id].append((action, success, reward, context))
            
            # Update performance metrics
            metrics = self.performance_metrics[agent_id]
            if success:
                metrics['total_success'] += 1
            else:
                metrics['total_failure'] += 1
            
            metrics['total_reward'] += reward
            
            # Update action preferences in strategy
            strategy = self.agent_strategies[agent_id]
            if action not in strategy['action_preferences']:
                strategy['action_preferences'][action] = 0.5  # Initialize neutral preference
            
            # Adjust preference based on success/reward
            action_pref = strategy['action_preferences'][action]
            reward_factor = max(-1.0, min(1.0, reward / 10.0))  # Normalize reward to [-1, 1]
            
            if success:
                # Successful actions get preference boost based on reward
                adjustment = 0.05 * (1 + reward_factor)
            else:
                # Failed actions get preference reduction
                adjustment = -0.05 * (1 - reward_factor/2)  # Less penalty for high reward failures
            
            # Apply adjustment with bounds
            strategy['action_preferences'][action] = max(0.1, min(0.9, action_pref + adjustment))
            
            # Update context weights if context provided
            if context and isinstance(context, dict):
                for key, value in context.items():
                    if isinstance(value, (int, float)):  # Only use numerical context values
                        if key not in strategy['context_weights']:
                            strategy['context_weights'][key] = 0.5  # Initialize neutral weight
                        
                        # Update weight based on success/reward
                        if success:
                            # If successful, increase weight slightly (context was valuable)
                            adjustment = 0.02 * (1 + reward_factor)
                        else:
                            # If failed, decrease weight slightly (context may have been misleading)
                            adjustment = -0.02 * (1 - reward_factor/2)
                        
                        current_weight = strategy['context_weights'][key]
                        strategy['context_weights'][key] = max(0.1, min(0.9, current_weight + adjustment))
            
            return True
            
        except Exception as e:
            logging.error(f"Error recording strategy outcome for agent {agent_id}: {e}")
            return False
    
    def evaluate_adaptation(self, agent_id):
        """
        Determine if an agent's strategy needs adaptation.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Boolean indicating if adaptation is needed
        """
        if agent_id not in self.agent_strategies:
            return False
        
        # Get performance metrics
        metrics = self.performance_metrics[agent_id]
        total_experiences = metrics['total_success'] + metrics['total_failure']
        
        # Check if we have enough experiences
        if total_experiences < self.min_experience_threshold:
            return False
        
        # Calculate recent performance
        recent_outcomes = self.recent_outcomes[agent_id]
        if len(recent_outcomes) < 3:  # Need at least 3 outcomes to evaluate
            return False
        
        recent_success_count = sum(1 for _, success, _, _ in recent_outcomes if success)
        recent_success_rate = recent_success_count / len(recent_outcomes)
        
        # Get current adaptation threshold from strategy
        strategy = self.agent_strategies[agent_id]
        adaptation_threshold = strategy.get('adaptation_threshold', 0.3)
        
        # Calculate overall success rate
        overall_success_rate = metrics['total_success'] / total_experiences if total_experiences > 0 else 0
        
        # Conditions for adaptation:
        # 1. Recent performance is below threshold
        # 2. Recent performance is significantly worse than overall
        # 3. Random chance based on exploration rate (occasional adaptation even when doing well)
        
        if recent_success_rate < adaptation_threshold:
            return True
        
        if overall_success_rate > 0 and recent_success_rate < overall_success_rate * 0.8:
            return True
        
        # Random adaptation chance based on exploration rate
        exploration_rate = strategy.get('exploration_rate', 0.3)
        if np.random.random() < exploration_rate * 0.1:  # 10% of exploration rate
            return True
        
        return False
    
    def adapt_strategy(self, agent_id):
        """
        Adapt an agent's strategy based on performance metrics and pattern recognition insights.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Boolean indicating if adaptation was successful
        """
        if agent_id not in self.agent_strategies:
            return False
        
        try:
            # Get current strategy
            strategy = self.agent_strategies[agent_id]
            
            # Get pattern statistics
            pattern_stats = self.pattern_system.get_pattern_statistics(agent_id)
            
            # Get recent outcomes
            recent_outcomes = list(self.recent_outcomes[agent_id])
            recent_success_count = sum(1 for _, success, _, _ in recent_outcomes if success)
            recent_success_rate = recent_success_count / len(recent_outcomes) if recent_outcomes else 0
            
            # Get performance metrics
            metrics = self.performance_metrics[agent_id]
            total_experiences = metrics['total_success'] + metrics['total_failure']
            overall_success_rate = metrics['total_success'] / total_experiences if total_experiences > 0 else 0
            
            # Create a new strategy based on current with adaptations
            new_strategy = strategy.copy()
            
            # 1. Adjust exploration rate based on success rate
            if recent_success_rate < 0.3:
                # Low success rate: increase exploration
                new_strategy['exploration_rate'] = min(0.9, strategy['exploration_rate'] + self.adaptation_rate)
            elif recent_success_rate > 0.7:
                # High success rate: decrease exploration (exploit more)
                new_strategy['exploration_rate'] = max(0.1, strategy['exploration_rate'] - self.adaptation_rate/2)
            
            # 2. Adjust pattern reliance based on pattern system success
            pattern_success_rate = pattern_stats.get('success_rate', 0)
            if pattern_success_rate > 0.6:
                # High pattern success: increase reliance
                new_strategy['pattern_reliance'] = min(0.9, strategy['pattern_reliance'] + self.adaptation_rate)
            elif pattern_success_rate < 0.4:
                # Low pattern success: decrease reliance
                new_strategy['pattern_reliance'] = max(0.2, strategy['pattern_reliance'] - self.adaptation_rate)
            
            # 3. Adjust risk tolerance based on reward history
            recent_rewards = [reward for _, _, reward, _ in recent_outcomes]
            if recent_rewards:
                avg_reward = sum(recent_rewards) / len(recent_rewards)
                if avg_reward > 0:
                    # Positive rewards: can take more risks
                    new_strategy['risk_tolerance'] = min(0.9, strategy['risk_tolerance'] + self.adaptation_rate * 0.5)
                elif avg_reward < 0:
                    # Negative rewards: be more cautious
                    new_strategy['risk_tolerance'] = max(0.1, strategy['risk_tolerance'] - self.adaptation_rate * 0.5)
            
            # 4. Update context sensitivity based on pattern context importance
            context_importance = pattern_stats.get('context_importance', 0.5)
            new_strategy['context_sensitivity'] = (
                strategy['context_sensitivity'] * (1 - self.adaptation_rate) +
                context_importance * self.adaptation_rate
            )
            
            # 5. Adjust adaptation threshold based on overall strategy stability
            if metrics['adaptations'] > 10:
                # Many adaptations might indicate unstable strategy, increase threshold
                new_strategy['adaptation_threshold'] = min(0.6, strategy['adaptation_threshold'] + self.adaptation_rate * 0.3)
            
            # 6. Prune unpromising action preferences
            for action, preference in list(new_strategy['action_preferences'].items()):
                if preference < 0.2:
                    # Check if there are enough samples to confirm this is truly unpromising
                    action_count = sum(1 for a, _, _, _ in recent_outcomes if a == action)
                    if action_count >= 3:
                        # Keep but with minimum value
                        new_strategy['action_preferences'][action] = 0.2
                    # Otherwise keep as is
            
            # Store updated strategy
            self.agent_strategies[agent_id] = new_strategy
            
            # Add to history
            self.strategy_history[agent_id].append(new_strategy.copy())
            
            # Update metrics
            metrics['adaptations'] += 1
            metrics['last_adaptation_time'] = total_experiences
            
            logging.info(f"Adapted strategy for agent {agent_id}, adaptation #{metrics['adaptations']}")
            return True
            
        except Exception as e:
            logging.error(f"Error adapting strategy for agent {agent_id}: {e}")
            return False
    
    def get_recommended_action(self, agent_id, state, available_actions, context=None):
        """
        Get a recommended action for an agent based on strategy and pattern recognition.
        
        Args:
            agent_id: ID of the agent
            state: Current state
            available_actions: List of available actions
            context: Optional context information
            
        Returns:
            Dictionary with recommended action and confidence, or None on error
        """
        if agent_id not in self.agent_strategies or not available_actions:
            return None
        
        try:
            # Get current strategy
            strategy = self.agent_strategies[agent_id]
            
            # Get pattern recommendation
            pattern_recommendation = self.pattern_system.suggest_action(
                agent_id, state, available_actions, context
            )
            
            # Determine if we should explore or exploit
            exploration_rate = strategy.get('exploration_rate', 0.3)
            if np.random.random() < exploration_rate:
                # Exploration: choose random action with preference weighting
                action_weights = {}
                for action in available_actions:
                    # Get preference from strategy, default to 0.5 if not present
                    action_weights[action] = strategy['action_preferences'].get(action, 0.5)
                
                # Normalize weights
                total_weight = sum(action_weights.values())
                if total_weight == 0:
                    # If all weights are 0, use uniform distribution
                    action_weights = {a: 1.0 for a in available_actions}
                    total_weight = len(available_actions)
                
                # Convert to probabilities
                action_probs = {a: w/total_weight for a, w in action_weights.items()}
                
                # Choose based on probabilities
                actions = list(action_probs.keys())
                probs = list(action_probs.values())
                chosen_action = np.random.choice(actions, p=probs)
                
                return {
                    'action': chosen_action,
                    'confidence': 0.5,  # Moderate confidence for exploration
                    'rationale': 'exploration'
                }
            else:
                # Exploitation: use pattern recognition with strategy influence
                if pattern_recommendation:
                    # Use pattern recommendation
                    pattern_reliance = strategy.get('pattern_reliance', 0.6)
                    
                    # Apply risk adjustment based on confidence and risk tolerance
                    pattern_confidence = pattern_recommendation.get('confidence', 0.5)
                    risk_tolerance = strategy.get('risk_tolerance', 0.5)
                    
                    # Low risk tolerance reduces confidence in uncertain patterns
                    adjusted_confidence = pattern_confidence * (0.7 + 0.6 * risk_tolerance)
                    
                    return {
                        'action': pattern_recommendation['action'],
                        'confidence': adjusted_confidence,
                        'rationale': 'pattern_recognition',
                        'pattern_id': pattern_recommendation.get('pattern_id')
                    }
                else:
                    # No pattern match, use action preferences
                    best_action = None
                    best_score = -1
                    
                    for action in available_actions:
                        # Base score is the action preference
                        base_score = strategy['action_preferences'].get(action, 0.5)
                        
                        # Apply context weighting if context provided and context sensitivity is high
                        context_score = 0
                        if context and isinstance(context, dict) and strategy['context_weights']:
                            context_sensitivity = strategy.get('context_sensitivity', 0.5)
                            context_count = 0
                            
                            for key, value in context.items():
                                if key in strategy['context_weights'] and isinstance(value, (int, float)):
                                    weight = strategy['context_weights'][key]
                                    # Normalize context value to [0, 1]
                                    norm_value = max(0, min(1, (value + 1) / 2))
                                    context_score += weight * norm_value
                                    context_count += 1
                            
                            if context_count > 0:
                                context_score /= context_count
                                # Blend base score with context score based on context sensitivity
                                base_score = base_score * (1 - context_sensitivity) + context_score * context_sensitivity
                        
                        if base_score > best_score:
                            best_score = base_score
                            best_action = action
                    
                    if best_action:
                        return {
                            'action': best_action,
                            'confidence': best_score,
                            'rationale': 'strategy_preference'
                        }
                    else:
                        # Fallback to random selection
                        return {
                            'action': np.random.choice(available_actions),
                            'confidence': 0.3,
                            'rationale': 'random_fallback'
                        }
            
        except Exception as e:
            logging.error(f"Error getting recommended action for agent {agent_id}: {e}")
            return None
    
    def get_strategy_evolution(self, agent_id):
        """
        Get the evolution history of an agent's strategy.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of strategy snapshots or empty list if not found
        """
        if agent_id not in self.strategy_history:
            return []
        
        return list(self.strategy_history[agent_id])
    
    def save_system_state(self, save_dir):
        """
        Save the current state of the strategy adaptation system.
        
        Args:
            save_dir: Directory to save the state in
            
        Returns:
            Boolean indicating success
        """
        try:
            os.makedirs(save_dir, exist_ok=True)
            
            # Convert deque objects to lists for serialization
            serializable_history = {}
            for agent_id, history in self.strategy_history.items():
                serializable_history[agent_id] = list(history)
            
            serializable_outcomes = {}
            for agent_id, outcomes in self.recent_outcomes.items():
                serializable_outcomes[agent_id] = list(outcomes)
            
            # Create the state dictionary
            state = {
                'agent_strategies': self.agent_strategies,
                'strategy_history': serializable_history,
                'recent_outcomes': serializable_outcomes,
                'performance_metrics': dict(self.performance_metrics),
                'adaptation_rate': self.adaptation_rate,
                'strategy_memory_size': self.strategy_memory_size,
                'min_experience_threshold': self.min_experience_threshold,
                'performance_window_size': self.performance_window_size
            }
            
            # Save to file
            with open(os.path.join(save_dir, 'strategy_adaptation_state.json'), 'w') as f:
                json.dump(state, f, indent=2)
            
            logging.info(f"Strategy adaptation system state saved to {save_dir}")
            return True
            
        except Exception as e:
            logging.error(f"Error saving strategy adaptation system state: {e}")
            return False
    
    def load_system_state(self, save_dir):
        """
        Load a previously saved state of the strategy adaptation system.
        
        Args:
            save_dir: Directory to load the state from
            
        Returns:
            Boolean indicating success
        """
        try:
            state_path = os.path.join(save_dir, 'strategy_adaptation_state.json')
            if not os.path.exists(state_path):
                logging.warning(f"Strategy adaptation state file not found in {save_dir}")
                return False
            
            # Load from file
            with open(state_path, 'r') as f:
                state = json.load(f)
            
            # Restore system parameters
            self.adaptation_rate = state.get('adaptation_rate', self.adaptation_rate)
            self.strategy_memory_size = state.get('strategy_memory_size', self.strategy_memory_size)
            self.min_experience_threshold = state.get('min_experience_threshold', self.min_experience_threshold)
            self.performance_window_size = state.get('performance_window_size', self.performance_window_size)
            
            # Restore agent strategies
            self.agent_strategies = state.get('agent_strategies', {})
            
            # Restore strategy history (convert lists back to deques)
            self.strategy_history = defaultdict(lambda: deque(maxlen=self.strategy_memory_size))
            for agent_id, history in state.get('strategy_history', {}).items():
                self.strategy_history[agent_id] = deque(history, maxlen=self.strategy_memory_size)
            
            # Restore recent outcomes (convert lists back to deques)
            self.recent_outcomes = defaultdict(lambda: deque(maxlen=self.performance_window_size))
            for agent_id, outcomes in state.get('recent_outcomes', {}).items():
                self.recent_outcomes[agent_id] = deque(outcomes, maxlen=self.performance_window_size)
            
            # Restore performance metrics
            self.performance_metrics = defaultdict(lambda: {
                'total_success': 0,
                'total_failure': 0,
                'total_reward': 0.0,
                'adaptations': 0,
                'last_adaptation_time': 0
            })
            for agent_id, metrics in state.get('performance_metrics', {}).items():
                self.performance_metrics[agent_id] = metrics
            
            logging.info(f"Strategy adaptation system state loaded from {save_dir}")
            return True
            
        except Exception as e:
            logging.error(f"Error loading strategy adaptation system state: {e}")
            return False 