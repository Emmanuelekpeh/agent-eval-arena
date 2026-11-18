"""
Behavior Learning System for AI Battle Arena.

This module provides mechanisms for agents to learn from observing
the behavior of other agents, both allies and enemies.
"""

import numpy as np
from collections import deque
import random
from typing import Dict, List, Any, Tuple, Optional, Union
import math

class BehaviorPattern:
    """
    Represents an observed behavior pattern.
    
    A behavior pattern consists of a sequence of state-action pairs
    with associated context information and outcome evaluation.
    """
    
    def __init__(self, agent_id: str, context: Dict[str, Any] = None):
        """
        Initialize a behavior pattern.
        
        Args:
            agent_id: Agent that performed the behavior
            context: Additional context information
        """
        self.agent_id = agent_id
        self.context = context or {}
        self.sequence = []
        self.reward = 0.0
        self.success = False
        self.completed = False
        
    def add_step(self, 
               state: np.ndarray, 
               action: int, 
               reward: float) -> None:
        """
        Add a step to the pattern.
        
        Args:
            state: State at this step
            action: Action taken
            reward: Reward received
        """
        self.sequence.append({
            'state': state.copy(),
            'action': action,
            'reward': reward
        })
        self.reward += reward
        
    def complete(self, success: bool) -> None:
        """
        Mark the pattern as complete.
        
        Args:
            success: Whether the pattern was successful
        """
        self.completed = True
        self.success = success
        
    def get_similarity(self, 
                     state: np.ndarray, 
                     context: Dict[str, Any] = None) -> float:
        """
        Calculate similarity of a state to this pattern's initial state.
        
        Args:
            state: State to compare
            context: Context information
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not self.sequence:
            return 0.0
            
        initial_state = self.sequence[0]['state']
        
        # Check state dimensions match
        if initial_state.shape != state.shape:
            return 0.0
            
        # Calculate state similarity (normalized dot product)
        state_similarity = self._calculate_state_similarity(state, initial_state)
        
        # Calculate context similarity if context provided
        context_similarity = 1.0
        if context and self.context:
            context_similarity = self._calculate_context_similarity(context, self.context)
            
        # Combine similarities
        return state_similarity * 0.7 + context_similarity * 0.3
        
    def _calculate_state_similarity(self, 
                                 state1: np.ndarray, 
                                 state2: np.ndarray) -> float:
        """
        Calculate similarity between two states.
        
        Args:
            state1: First state
            state2: Second state
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Normalized dot product
        norm1 = np.linalg.norm(state1)
        norm2 = np.linalg.norm(state2)
        
        if norm1 > 0 and norm2 > 0:
            return np.dot(state1, state2) / (norm1 * norm2)
        return 0.0
        
    def _calculate_context_similarity(self, 
                                   context1: Dict[str, Any],
                                   context2: Dict[str, Any]) -> float:
        """
        Calculate similarity between two contexts.
        
        Args:
            context1: First context
            context2: Second context
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Simple matching of keys and values
        if not context1 or not context2:
            return 0.0
            
        # Count matching keys
        common_keys = set(context1.keys()) & set(context2.keys())
        if not common_keys:
            return 0.0
            
        # Calculate matches
        matches = 0
        for key in common_keys:
            if context1[key] == context2[key]:
                matches += 1
                
        return matches / len(common_keys)
    
    def suggest_action(self, 
                     state: np.ndarray, 
                     step: int = 0) -> Tuple[int, float]:
        """
        Suggest an action based on this pattern.
        
        Args:
            state: Current state
            step: Current step in the pattern
            
        Returns:
            Tuple of (suggested action, confidence)
        """
        if not self.sequence or step >= len(self.sequence):
            return -1, 0.0
            
        pattern_state = self.sequence[step]['state']
        similarity = self._calculate_state_similarity(state, pattern_state)
        
        # Only suggest if similarity is high enough
        if similarity > 0.7:
            return self.sequence[step]['action'], similarity
        
        return -1, 0.0

class BehaviorLearningSystem:
    """
    System for learning from observed behaviors.
    
    Features:
    - Record behavior patterns of successful agents
    - Identify patterns that lead to success
    - Suggest actions based on observed patterns
    - Adapt patterns to different contexts
    """
    
    def __init__(self, pattern_capacity: int = 1000):
        """
        Initialize the behavior learning system.
        
        Args:
            pattern_capacity: Maximum number of patterns to store
        """
        self.pattern_capacity = pattern_capacity
        self.patterns = deque(maxlen=pattern_capacity)
        self.active_patterns = {}  # agent_id -> current active pattern
        self.agent_roles = {}  # agent_id -> role
        self.agent_teams = {}  # agent_id -> team_id
        self.pattern_stats = {
            'successful': 0,
            'unsuccessful': 0,
            'total_recorded': 0,
            'by_agent': {},
            'by_team': {}
        }
        
    def start_pattern(self, 
                    agent_id: str, 
                    initial_state: np.ndarray,
                    initial_action: int,
                    reward: float,
                    context: Dict[str, Any] = None) -> None:
        """
        Start recording a new behavior pattern.
        
        Args:
            agent_id: Agent executing the pattern
            initial_state: Initial state
            initial_action: First action
            reward: Initial reward
            context: Additional context information
        """
        # Create new pattern
        pattern = BehaviorPattern(agent_id, context)
        
        # Add initial step
        pattern.add_step(initial_state, initial_action, reward)
        
        # Store as active pattern
        self.active_patterns[agent_id] = pattern
        
        # Update team and role mapping
        if context:
            if 'team_id' in context:
                self.agent_teams[agent_id] = context['team_id']
            if 'role' in context:
                self.agent_roles[agent_id] = context['role']
    
    def record_step(self, 
                  agent_id: str, 
                  state: np.ndarray,
                  action: int,
                  reward: float) -> None:
        """
        Record a step in an active behavior pattern.
        
        Args:
            agent_id: Agent executing the pattern
            state: Current state
            action: Action taken
            reward: Reward received
        """
        if agent_id in self.active_patterns:
            self.active_patterns[agent_id].add_step(state, action, reward)
    
    def complete_pattern(self, agent_id: str, success: bool) -> None:
        """
        Complete an active behavior pattern.
        
        Args:
            agent_id: Agent executing the pattern
            success: Whether the pattern was successful
        """
        if agent_id in self.active_patterns:
            pattern = self.active_patterns[agent_id]
            pattern.complete(success)
            
            # Only store patterns with at least 2 steps
            if len(pattern.sequence) >= 2:
                self.patterns.append(pattern)
                
                # Update statistics
                self.pattern_stats['total_recorded'] += 1
                if success:
                    self.pattern_stats['successful'] += 1
                else:
                    self.pattern_stats['unsuccessful'] += 1
                    
                # Update agent stats
                if agent_id not in self.pattern_stats['by_agent']:
                    self.pattern_stats['by_agent'][agent_id] = {
                        'total': 0, 'successful': 0
                    }
                self.pattern_stats['by_agent'][agent_id]['total'] += 1
                if success:
                    self.pattern_stats['by_agent'][agent_id]['successful'] += 1
                    
                # Update team stats
                team_id = self.agent_teams.get(agent_id)
                if team_id:
                    if team_id not in self.pattern_stats['by_team']:
                        self.pattern_stats['by_team'][team_id] = {
                            'total': 0, 'successful': 0
                        }
                    self.pattern_stats['by_team'][team_id]['total'] += 1
                    if success:
                        self.pattern_stats['by_team'][team_id]['successful'] += 1
            
            # Remove from active patterns
            del self.active_patterns[agent_id]
    
    def cancel_pattern(self, agent_id: str) -> None:
        """
        Cancel an active behavior pattern.
        
        Args:
            agent_id: Agent executing the pattern
        """
        if agent_id in self.active_patterns:
            del self.active_patterns[agent_id]
    
    def suggest_action(self, 
                     agent_id: str, 
                     state: np.ndarray,
                     context: Dict[str, Any] = None) -> Tuple[int, float]:
        """
        Suggest an action based on observed patterns.
        
        Args:
            agent_id: Agent requesting suggestion
            state: Current state
            context: Additional context information
            
        Returns:
            Tuple of (suggested action, confidence)
        """
        # Check for active pattern first
        if agent_id in self.active_patterns:
            pattern = self.active_patterns[agent_id]
            step = len(pattern.sequence)
            
            # Find matching pattern in history
            best_match = None
            best_similarity = 0.0
            
            for stored_pattern in self.patterns:
                # Only consider successful patterns
                if not stored_pattern.success:
                    continue
                    
                # Only consider patterns with enough steps
                if len(stored_pattern.sequence) <= step:
                    continue
                    
                # Calculate similarity to initial steps of pattern
                similarity = self._calculate_sequence_similarity(
                    pattern.sequence, 
                    stored_pattern.sequence[:step+1]
                )
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = stored_pattern
            
            # If we found a good match, suggest next action
            if best_match and best_similarity > 0.8:
                return best_match.sequence[step]['action'], best_similarity
        
        # If no active pattern or no match, look for a new pattern to start
        return self._find_matching_pattern(agent_id, state, context)
    
    def _find_matching_pattern(self, 
                            agent_id: str, 
                            state: np.ndarray,
                            context: Dict[str, Any] = None) -> Tuple[int, float]:
        """
        Find a pattern that matches the current state.
        
        Args:
            agent_id: Agent requesting suggestion
            state: Current state
            context: Additional context information
            
        Returns:
            Tuple of (suggested action, confidence)
        """
        best_action = -1
        best_confidence = 0.0
        
        team_id = self.agent_teams.get(agent_id)
        role = self.agent_roles.get(agent_id)
        
        # Add team and role to context if available
        search_context = context.copy() if context else {}
        if team_id:
            search_context['team_id'] = team_id
        if role:
            search_context['role'] = role
        
        # Search for matching patterns
        for pattern in self.patterns:
            # Only consider successful patterns
            if not pattern.success:
                continue
                
            # Check similarity
            similarity = pattern.get_similarity(state, search_context)
            
            # If similar enough, consider this pattern
            if similarity > best_confidence:
                best_confidence = similarity
                best_action = pattern.sequence[0]['action']
        
        return best_action, best_confidence
    
    def _calculate_sequence_similarity(self, 
                                    seq1: List[Dict[str, Any]], 
                                    seq2: List[Dict[str, Any]]) -> float:
        """
        Calculate similarity between two action sequences.
        
        Args:
            seq1: First sequence
            seq2: Second sequence
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Check if lengths match
        if len(seq1) != len(seq2):
            return 0.0
            
        # Calculate similarity for each step
        similarities = []
        for i in range(len(seq1)):
            state1 = seq1[i]['state']
            state2 = seq2[i]['state']
            
            # Calculate state similarity
            state_similarity = self._calculate_state_similarity(state1, state2)
            
            # Check action match
            action_match = 1.0 if seq1[i]['action'] == seq2[i]['action'] else 0.0
            
            # Combine
            step_similarity = state_similarity * 0.7 + action_match * 0.3
            similarities.append(step_similarity)
            
        # Average similarity across steps
        return sum(similarities) / len(similarities)
    
    def _calculate_state_similarity(self, 
                                 state1: np.ndarray, 
                                 state2: np.ndarray) -> float:
        """
        Calculate similarity between two states.
        
        Args:
            state1: First state
            state2: Second state
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Check state dimensions match
        if state1.shape != state2.shape:
            return 0.0
            
        # Normalized dot product
        norm1 = np.linalg.norm(state1)
        norm2 = np.linalg.norm(state2)
        
        if norm1 > 0 and norm2 > 0:
            return np.dot(state1, state2) / (norm1 * norm2)
        return 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the behavior learning system.
        
        Returns:
            Dictionary of statistics
        """
        return {
            'total_patterns': len(self.patterns),
            'active_patterns': len(self.active_patterns),
            'success_rate': (self.pattern_stats['successful'] / 
                          max(1, self.pattern_stats['total_recorded'])),
            'patterns_by_agent': {
                agent_id: stats['total'] 
                for agent_id, stats in self.pattern_stats['by_agent'].items()
            },
            'patterns_by_team': {
                team_id: stats['total'] 
                for team_id, stats in self.pattern_stats['by_team'].items()
            }
        }

class ImitationLearning:
    """
    System for agents to learn by imitating successful behaviors.
    
    Features:
    - Learn from observing successful agents
    - Adapt observed behaviors to agent's own capabilities
    - Weight learning toward agents with similar roles/teams
    - Track learning progress and effectiveness
    """
    
    def __init__(self, learning_rate: float = 0.1):
        """
        Initialize the imitation learning system.
        
        Args:
            learning_rate: Rate at which to incorporate observed behaviors
        """
        self.learning_rate = learning_rate
        self.observations = {}  # agent_id -> list of observations
        self.imitation_stats = {}  # agent_id -> imitation statistics
        self.similarity_weights = {
            'same_team': 1.5,
            'same_role': 1.3,
            'enemy': 0.7
        }
        
    def observe_agent(self, 
                    observer_id: str, 
                    observed_id: str,
                    state: np.ndarray,
                    action: int,
                    reward: float,
                    success: bool,
                    context: Dict[str, Any] = None) -> None:
        """
        Record an observation of another agent.
        
        Args:
            observer_id: Agent doing the observing
            observed_id: Agent being observed
            state: State at time of observation
            action: Action taken by observed agent
            reward: Reward received by observed agent
            success: Whether the action was successful
            context: Additional context information
        """
        # Initialize observations for observer if needed
        if observer_id not in self.observations:
            self.observations[observer_id] = []
            
        # Create observation record
        observation = {
            'observed_id': observed_id,
            'state': state.copy(),
            'action': action,
            'reward': reward,
            'success': success,
            'context': context.copy() if context else {},
            'timestamp': 0  # Would use actual timestamp in real system
        }
        
        # Add to observations
        self.observations[observer_id].append(observation)
        
        # Limit observations (keep most recent)
        if len(self.observations[observer_id]) > 1000:
            self.observations[observer_id] = self.observations[observer_id][-1000:]
            
        # Update imitation stats
        if observer_id not in self.imitation_stats:
            self.imitation_stats[observer_id] = {
                'total_observations': 0,
                'successful_observations': 0,
                'observations_by_agent': {},
                'imitated_actions': 0,
                'imitation_success': 0
            }
            
        self.imitation_stats[observer_id]['total_observations'] += 1
        if success:
            self.imitation_stats[observer_id]['successful_observations'] += 1
            
        if observed_id not in self.imitation_stats[observer_id]['observations_by_agent']:
            self.imitation_stats[observer_id]['observations_by_agent'][observed_id] = 0
            
        self.imitation_stats[observer_id]['observations_by_agent'][observed_id] += 1
    
    def suggest_imitated_action(self, 
                             agent_id: str, 
                             state: np.ndarray,
                             context: Dict[str, Any] = None) -> Tuple[int, float]:
        """
        Suggest an action based on observed behaviors.
        
        Args:
            agent_id: Agent requesting suggestion
            state: Current state
            context: Additional context information
            
        Returns:
            Tuple of (suggested action, confidence)
        """
        if agent_id not in self.observations:
            return -1, 0.0
            
        # Get relevant observations
        observations = self.observations[agent_id]
        
        # If no observations, can't suggest anything
        if not observations:
            return -1, 0.0
            
        # Find most similar situation from observations
        best_match = None
        best_similarity = 0.0
        
        for obs in observations:
            # Calculate state similarity
            similarity = self._calculate_state_similarity(state, obs['state'])
            
            # Adjust based on context
            if context and 'team_id' in context and 'observed_team_id' in obs['context']:
                if context['team_id'] == obs['context']['observed_team_id']:
                    similarity *= self.similarity_weights['same_team']
                else:
                    similarity *= self.similarity_weights['enemy']
                    
            if context and 'role' in context and 'observed_role' in obs['context']:
                if context['role'] == obs['context']['observed_role']:
                    similarity *= self.similarity_weights['same_role']
            
            # Check if this is the best match so far
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = obs
                
        # If we found a good match, suggest its action
        if best_match and best_similarity > 0.75:
            return best_match['action'], best_similarity
            
        return -1, 0.0
    
    def record_imitation_result(self, 
                             agent_id: str, 
                             action: int, 
                             success: bool) -> None:
        """
        Record the result of an imitated action.
        
        Args:
            agent_id: Agent that imitated
            action: Action that was imitated
            success: Whether the imitation was successful
        """
        if agent_id in self.imitation_stats:
            self.imitation_stats[agent_id]['imitated_actions'] += 1
            if success:
                self.imitation_stats[agent_id]['imitation_success'] += 1
    
    def adjust_learning_rate(self, 
                          agent_id: str, 
                          success_rate: float) -> None:
        """
        Adjust learning rate based on imitation success.
        
        Args:
            agent_id: Agent to adjust
            success_rate: Success rate of imitated actions
        """
        # If imitation is working well, increase learning rate
        if success_rate > 0.7:
            self.learning_rate = min(0.9, self.learning_rate * 1.1)
        # If imitation is doing poorly, decrease learning rate
        elif success_rate < 0.3:
            self.learning_rate = max(0.01, self.learning_rate * 0.9)
    
    def _calculate_state_similarity(self, 
                                 state1: np.ndarray, 
                                 state2: np.ndarray) -> float:
        """
        Calculate similarity between two states.
        
        Args:
            state1: First state
            state2: Second state
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Check state dimensions match
        if state1.shape != state2.shape:
            return 0.0
            
        # Normalized dot product
        norm1 = np.linalg.norm(state1)
        norm2 = np.linalg.norm(state2)
        
        if norm1 > 0 and norm2 > 0:
            return np.dot(state1, state2) / (norm1 * norm2)
        return 0.0
    
    def get_stats(self, agent_id: str = None) -> Dict[str, Any]:
        """
        Get statistics about the imitation learning system.
        
        Args:
            agent_id: Agent to get stats for, or None for all
            
        Returns:
            Dictionary of statistics
        """
        if agent_id:
            if agent_id in self.imitation_stats:
                stats = self.imitation_stats[agent_id]
                return {
                    'observation_count': stats['total_observations'],
                    'successful_observations': stats['successful_observations'],
                    'observation_success_rate': (stats['successful_observations'] / 
                                            max(1, stats['total_observations'])),
                    'imitated_actions': stats['imitated_actions'],
                    'imitation_success': stats['imitation_success'],
                    'imitation_success_rate': (stats['imitation_success'] / 
                                          max(1, stats['imitated_actions'])),
                    'observed_agents': len(stats['observations_by_agent'])
                }
            return {}
            
        return {
            'total_agents': len(self.imitation_stats),
            'total_observations': sum(
                stats['total_observations'] 
                for stats in self.imitation_stats.values()
            ),
            'average_imitation_success': np.mean([
                stats['imitation_success'] / max(1, stats['imitated_actions'])
                for stats in self.imitation_stats.values()
            ]) if self.imitation_stats else 0.0,
            'learning_rate': self.learning_rate
        } 