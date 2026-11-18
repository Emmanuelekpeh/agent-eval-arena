"""
Experience Memory System for AI agents.

This module provides a comprehensive experience memory system with
prioritized replay, pattern recognition, and shared learning capabilities.
"""

import numpy as np
from collections import deque
import random
from typing import List, Dict, Any, Tuple, Optional, Union

class ExperienceMemory:
    """
    Experience memory with prioritized replay and pattern recognition.
    
    Features:
    - Store experiences with priorities
    - Sample experiences based on importance
    - Recognize patterns in successful strategies
    - Share knowledge between similar agents
    """
    
    def __init__(self, capacity: int = 10000, alpha: float = 0.6, beta: float = 0.4):
        """
        Initialize the experience memory.
        
        Args:
            capacity: Maximum number of experiences to store
            alpha: Priority exponent (0 = uniform sampling, 1 = greedy prioritization)
            beta: Importance-sampling correction exponent
        """
        self.capacity = capacity
        self.alpha = alpha
        self.beta = beta
        self.beta_increment = 0.001  # How much to increase beta over time
        
        # Main memory storage
        self.memories = deque(maxlen=capacity)
        self.priorities = deque(maxlen=capacity)
        
        # Pattern recognition storage
        self.pattern_memory = {}
        self.successful_sequences = []
        
        # Statistics
        self.insertion_count = 0
        self.min_priority = 1.0
        
    def add_experience(self, 
                     state: np.ndarray, 
                     action: int, 
                     reward: float, 
                     next_state: np.ndarray, 
                     done: bool,
                     context: Dict[str, Any] = None) -> None:
        """
        Add an experience to memory with priority.
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Whether the episode is complete
            context: Additional context information
        """
        # Create experience tuple with optional context
        experience = (state, action, reward, next_state, done, context)
        
        # Calculate priority based on reward magnitude, novelty and TD error
        priority = self._calculate_priority(state, reward, next_state)
        
        # Add to memory
        self.memories.append(experience)
        self.priorities.append(priority)
        
        # Update min priority for normalization
        self.min_priority = min(self.min_priority, priority)
        
        # Update insertion count
        self.insertion_count += 1
        
        # Check for patterns if this was a positive experience
        if reward > 0 and context is not None:
            self._check_for_patterns(experience)
    
    def _calculate_priority(self, 
                         state: np.ndarray, 
                         reward: float, 
                         next_state: Optional[np.ndarray] = None) -> float:
        """
        Calculate priority for an experience.
        
        Args:
            state: Current state
            reward: Reward received
            next_state: Next state (optional)
            
        Returns:
            Priority value
        """
        # Base priority on reward magnitude
        priority = abs(reward) + 1.0  # Add 1.0 to ensure positive priority
        
        # Add novelty factor
        novelty = self.calculate_novelty(state)
        priority += novelty
        
        # If we have a next state, include state change magnitude
        if next_state is not None:
            state_change = np.sum(np.abs(next_state - state))
            priority += min(1.0, state_change / 10.0)  # Normalize and add
        
        return priority ** self.alpha
    
    def sample(self, batch_size: int = 32) -> Tuple[List, np.ndarray, np.ndarray]:
        """
        Sample a batch of experiences based on priorities.
        
        Args:
            batch_size: Number of experiences to sample
            
        Returns:
            Tuple of (experiences, indices, importance weights)
        """
        if len(self.memories) == 0:
            return [], np.array([]), np.array([])
            
        # Calculate sampling probabilities
        priorities = np.array(self.priorities)
        probabilities = priorities / sum(priorities)
        
        # Sample indices based on probabilities
        indices = np.random.choice(
            len(self.memories), 
            min(batch_size, len(self.memories)),
            replace=False,
            p=probabilities
        )
        
        # Retrieve experiences
        experiences = [self.memories[i] for i in indices]
        
        # Calculate importance sampling weights
        weights = (len(self.memories) * probabilities[indices]) ** (-self.beta)
        weights /= weights.max()  # Normalize
        
        # Increase beta
        self.beta = min(1.0, self.beta + self.beta_increment)
        
        return experiences, indices, weights
    
    def update_priorities(self, indices: List[int], priorities: List[float]) -> None:
        """
        Update priorities for specific experiences.
        
        Args:
            indices: Indices of experiences to update
            priorities: New priority values
        """
        for idx, priority in zip(indices, priorities):
            if 0 <= idx < len(self.priorities):
                self.priorities[idx] = priority ** self.alpha
                self.min_priority = min(self.min_priority, priority)
    
    def calculate_novelty(self, state: np.ndarray) -> float:
        """
        Calculate novelty of a state compared to recent experiences.
        
        Args:
            state: State to check
            
        Returns:
            Novelty score between 0.0 and 1.0
        """
        if len(self.memories) < 2:
            return 1.0
            
        # Get recent states
        recent_states = [m[0] for m in list(self.memories)[-20:]]
        
        # Calculate average difference
        diffs = []
        for old_state in recent_states:
            # Ensure shapes match
            if old_state.shape == state.shape:
                diff = np.mean(np.abs(state - old_state))
                diffs.append(diff)
            
        if not diffs:
            return 1.0
            
        avg_diff = np.mean(diffs)
        return min(1.0, avg_diff)
    
    def _check_for_patterns(self, experience: Tuple) -> None:
        """
        Check for patterns in successful experiences.
        
        Args:
            experience: New experience to check
        """
        state, action, reward, next_state, done, context = experience
        
        # Only process experiences with context
        if context is None:
            return
            
        # Extract relevant context
        sequence_id = context.get('sequence_id', None)
        step = context.get('step', 0)
        
        if sequence_id is not None:
            # Check if this is a new sequence
            if sequence_id not in self.pattern_memory:
                self.pattern_memory[sequence_id] = {
                    'steps': {},
                    'total_reward': 0,
                    'completed': False
                }
            
            # Add this step to the sequence
            self.pattern_memory[sequence_id]['steps'][step] = {
                'state': state,
                'action': action,
                'reward': reward
            }
            
            # Update total reward
            self.pattern_memory[sequence_id]['total_reward'] += reward
            
            # Mark sequence as completed if episode is done
            if done:
                self.pattern_memory[sequence_id]['completed'] = True
                
                # If sequence was successful (positive reward), add to successful sequences
                if self.pattern_memory[sequence_id]['total_reward'] > 0:
                    self.successful_sequences.append(self.pattern_memory[sequence_id].copy())
                    
                    # Keep only the top 100 successful sequences
                    if len(self.successful_sequences) > 100:
                        # Sort by total reward
                        self.successful_sequences.sort(
                            key=lambda seq: seq['total_reward'], 
                            reverse=True
                        )
                        # Keep only top 100
                        self.successful_sequences = self.successful_sequences[:100]
    
    def get_similar_experiences(self, 
                             state: np.ndarray,
                             similarity_threshold: float = 0.8) -> List[Tuple]:
        """
        Find experiences with similar states.
        
        Args:
            state: State to compare against
            similarity_threshold: Minimum similarity to include
            
        Returns:
            List of similar experiences
        """
        similar_experiences = []
        
        for experience in self.memories:
            exp_state = experience[0]
            
            # Calculate similarity
            if exp_state.shape == state.shape:
                # Normalized dot product as similarity metric
                norm1 = np.linalg.norm(state)
                norm2 = np.linalg.norm(exp_state)
                
                if norm1 > 0 and norm2 > 0:
                    similarity = np.dot(state, exp_state) / (norm1 * norm2)
                    
                    if similarity >= similarity_threshold:
                        similar_experiences.append(experience)
        
        return similar_experiences
    
    def suggest_action(self, state: np.ndarray) -> Optional[int]:
        """
        Suggest an action based on successful patterns.
        
        Args:
            state: Current state
            
        Returns:
            Suggested action or None if no suggestion
        """
        if not self.successful_sequences:
            return None
            
        # Find similar states in successful sequences
        best_similarity = 0.0
        suggested_action = None
        
        for sequence in self.successful_sequences:
            for step_data in sequence['steps'].values():
                pattern_state = step_data['state']
                
                # Calculate similarity
                if pattern_state.shape == state.shape:
                    # Normalized dot product as similarity metric
                    norm1 = np.linalg.norm(state)
                    norm2 = np.linalg.norm(pattern_state)
                    
                    if norm1 > 0 and norm2 > 0:
                        similarity = np.dot(state, pattern_state) / (norm1 * norm2)
                        
                        if similarity > best_similarity:
                            best_similarity = similarity
                            suggested_action = step_data['action']
        
        # Only suggest if similarity is significant
        if best_similarity > 0.9:
            return suggested_action
            
        return None
    
    def clear(self) -> None:
        """Clear all stored experiences."""
        self.memories.clear()
        self.priorities.clear()
        self.min_priority = 1.0
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the memory.
        
        Returns:
            Dictionary of memory statistics
        """
        return {
            'size': len(self.memories),
            'capacity': self.capacity,
            'usage': len(self.memories) / self.capacity if self.capacity > 0 else 0,
            'beta': self.beta,
            'insertion_count': self.insertion_count,
            'patterns_found': len(self.successful_sequences),
            'min_priority': self.min_priority,
            'max_priority': max(self.priorities) if self.priorities else 0
        }

class TeamExperienceMemory:
    """
    Team-based experience memory for coordinated learning.
    
    Features:
    - Store team experiences with formation information
    - Recognize successful team strategies
    - Share knowledge between team members
    """
    
    def __init__(self, capacity: int = 1000):
        """
        Initialize the team experience memory.
        
        Args:
            capacity: Maximum number of team experiences to store
        """
        self.capacity = capacity
        self.team_memories = {}  # team_id -> deque of experiences
        self.formation_memories = {}  # formation_type -> deque of (positions, score)
        self.coordination_patterns = {}  # team_id -> successful coordination patterns
        
    def add_team_experience(self, 
                          team_id: str, 
                          states: Dict[str, np.ndarray],
                          actions: Dict[str, int],
                          rewards: Dict[str, float],
                          formation: str,
                          positions: List[Tuple[float, float]],
                          formation_score: float) -> None:
        """
        Add a team experience to memory.
        
        Args:
            team_id: Team identifier
            states: Dict of agent_id -> state
            actions: Dict of agent_id -> action
            rewards: Dict of agent_id -> reward
            formation: Formation type
            positions: List of agent positions
            formation_score: Score for formation maintenance
        """
        # Initialize team memory if needed
        if team_id not in self.team_memories:
            self.team_memories[team_id] = deque(maxlen=self.capacity)
            
        # Create team experience
        team_experience = {
            'states': states,
            'actions': actions,
            'rewards': rewards,
            'formation': formation,
            'positions': positions,
            'formation_score': formation_score,
            'team_reward': sum(rewards.values())
        }
        
        # Add to team memory
        self.team_memories[team_id].append(team_experience)
        
        # Add to formation memory
        if formation not in self.formation_memories:
            self.formation_memories[formation] = deque(maxlen=self.capacity)
            
        self.formation_memories[formation].append((positions, formation_score))
        
        # Check for coordination patterns if team reward is positive
        if team_experience['team_reward'] > 0:
            self._check_coordination_pattern(team_id, team_experience)
    
    def _check_coordination_pattern(self, team_id: str, experience: Dict[str, Any]) -> None:
        """
        Check for coordination patterns in team experience.
        
        Args:
            team_id: Team identifier
            experience: Team experience
        """
        # Initialize coordination patterns if needed
        if team_id not in self.coordination_patterns:
            self.coordination_patterns[team_id] = []
            
        # Extract relevant data
        formation = experience['formation']
        positions = experience['positions']
        actions = experience['actions']
        team_reward = experience['team_reward']
        
        # Create coordination pattern
        pattern = {
            'formation': formation,
            'relative_positions': self._calculate_relative_positions(positions),
            'action_pattern': self._extract_action_pattern(actions),
            'reward': team_reward
        }
        
        # Add to coordination patterns
        self.coordination_patterns[team_id].append(pattern)
        
        # Keep only top 50 patterns
        if len(self.coordination_patterns[team_id]) > 50:
            # Sort by reward
            self.coordination_patterns[team_id].sort(
                key=lambda pat: pat['reward'], 
                reverse=True
            )
            # Keep only top 50
            self.coordination_patterns[team_id] = self.coordination_patterns[team_id][:50]
    
    def _calculate_relative_positions(self, 
                                  positions: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Calculate positions relative to first position (leader).
        
        Args:
            positions: List of absolute positions
            
        Returns:
            List of relative positions
        """
        if not positions:
            return []
            
        leader_pos = positions[0]
        return [(pos[0] - leader_pos[0], pos[1] - leader_pos[1]) for pos in positions]
    
    def _extract_action_pattern(self, actions: Dict[str, int]) -> Dict[str, int]:
        """
        Extract pattern of actions by role rather than agent ID.
        
        Args:
            actions: Dict of agent_id -> action
            
        Returns:
            Dict representing action pattern
        """
        # Simple representation: count of each action type
        action_counts = {}
        for action in actions.values():
            if action not in action_counts:
                action_counts[action] = 0
            action_counts[action] += 1
            
        return action_counts
    
    def get_best_formation(self, team_id: str, team_size: int) -> str:
        """
        Get best formation for a team based on past performance.
        
        Args:
            team_id: Team identifier
            team_size: Number of agents in team
            
        Returns:
            Recommended formation type or 'arrow' as default
        """
        if team_id not in self.team_memories or not self.team_memories[team_id]:
            return 'arrow'  # Default
            
        # Calculate average reward per formation
        formation_rewards = {}
        
        for exp in self.team_memories[team_id]:
            formation = exp['formation']
            reward = exp['team_reward']
            
            if formation not in formation_rewards:
                formation_rewards[formation] = {'total': 0, 'count': 0}
                
            formation_rewards[formation]['total'] += reward
            formation_rewards[formation]['count'] += 1
        
        # Find formation with highest average reward
        best_formation = 'arrow'  # Default
        best_avg_reward = -float('inf')
        
        for formation, stats in formation_rewards.items():
            if stats['count'] > 0:
                avg_reward = stats['total'] / stats['count']
                if avg_reward > best_avg_reward:
                    best_avg_reward = avg_reward
                    best_formation = formation
        
        return best_formation
    
    def suggest_team_actions(self, 
                          team_id: str,
                          states: Dict[str, np.ndarray],
                          positions: List[Tuple[float, float]],
                          formation: str) -> Dict[str, int]:
        """
        Suggest actions for team members based on successful patterns.
        
        Args:
            team_id: Team identifier
            states: Dict of agent_id -> state
            positions: List of agent positions
            formation: Current formation
            
        Returns:
            Dict of agent_id -> suggested action (empty if no suggestions)
        """
        suggestions = {}
        
        # Check if we have patterns for this team
        if team_id not in self.coordination_patterns:
            return suggestions
            
        # Calculate relative positions
        relative_positions = self._calculate_relative_positions(positions)
        
        # Find similar patterns
        for pattern in self.coordination_patterns[team_id]:
            # Check if same formation
            if pattern['formation'] == formation:
                # Calculate position similarity
                pos_similarity = self._calculate_position_similarity(
                    relative_positions, 
                    pattern['relative_positions']
                )
                
                # If positions are similar, suggest actions from pattern
                if pos_similarity > 0.8:
                    action_pattern = pattern['action_pattern']
                    
                    # Assign actions based on pattern (simple approach)
                    action_counts = action_pattern.copy()
                    
                    # Assign actions to agents
                    for agent_id in states.keys():
                        if action_counts:
                            # Get most common action in pattern
                            action = max(action_counts.items(), key=lambda x: x[1])[0]
                            suggestions[agent_id] = action
                            
                            # Reduce count
                            action_counts[action] -= 1
                            if action_counts[action] == 0:
                                del action_counts[action]
                    
                    # If we found a match, return suggestions
                    if suggestions:
                        return suggestions
        
        return suggestions
    
    def _calculate_position_similarity(self, 
                                   pos1: List[Tuple[float, float]], 
                                   pos2: List[Tuple[float, float]]) -> float:
        """
        Calculate similarity between two sets of positions.
        
        Args:
            pos1: First set of positions
            pos2: Second set of positions
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # If lengths don't match, return low similarity
        if len(pos1) != len(pos2):
            return 0.0
            
        # Calculate average distance between corresponding positions
        total_dist = 0.0
        for p1, p2 in zip(pos1, pos2):
            dist = ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5
            total_dist += dist
            
        avg_dist = total_dist / len(pos1)
        
        # Convert distance to similarity (closer = more similar)
        similarity = 1.0 / (1.0 + avg_dist / 100.0)  # Normalize with scaling factor
        
        return similarity
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the team memory.
        
        Returns:
            Dictionary of memory statistics
        """
        stats = {
            'teams': len(self.team_memories),
            'formations': len(self.formation_memories),
            'team_memories': {},
            'pattern_counts': {}
        }
        
        for team_id, memories in self.team_memories.items():
            stats['team_memories'][team_id] = len(memories)
            
        for team_id, patterns in self.coordination_patterns.items():
            stats['pattern_counts'][team_id] = len(patterns)
            
        return stats 