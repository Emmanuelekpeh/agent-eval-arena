"""
Pattern recognition system for identifying successful and unsuccessful behavioral patterns.

This module analyzes agent experiences to extract action patterns that lead to success
or failure, enabling agents to learn from past interactions and improve decision-making.
"""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional, Set
import time
import math
from collections import defaultdict

class ActionPattern:
    """
    Represents a sequence of actions that forms a recognizable pattern.
    
    Action patterns capture sequences of state-action pairs that consistently
    lead to positive or negative outcomes, allowing agents to recognize and
    adapt to successful strategies.
    """
    
    def __init__(self, id: str, sequence_length: int = 3):
        """
        Initialize an action pattern.
        
        Args:
            id: Unique identifier for this pattern
            sequence_length: Number of state-action pairs in this pattern
        """
        self.id = id
        self.sequence_length = sequence_length
        self.state_action_sequence = []
        self.context_features = {}
        self.outcome_history = []
        self.success_rate = 0.0
        self.confidence = 0.0
        self.total_reward = 0.0
        self.last_updated = time.time()
        self.usage_count = 0
        self.tags = set()
        
    def add_state_action(self, state_features: Dict[str, float], action: int) -> None:
        """
        Add a state-action pair to this pattern.
        
        Args:
            state_features: Extracted features from the state
            action: Action taken in this state
        """
        self.state_action_sequence.append((state_features, action))
        
        # Trim to sequence length
        if len(self.state_action_sequence) > self.sequence_length:
            self.state_action_sequence = self.state_action_sequence[-self.sequence_length:]
            
    def record_outcome(self, success: bool, reward: float, context: Dict[str, Any] = None) -> None:
        """
        Record the outcome of applying this pattern.
        
        Args:
            success: Whether the pattern led to a successful outcome
            reward: Total reward received for this pattern execution
            context: Contextual information about the environment
        """
        self.outcome_history.append((success, reward, context))
        self.last_updated = time.time()
        
        # Update pattern statistics
        successes = sum(1 for outcome, _, _ in self.outcome_history if outcome)
        total = len(self.outcome_history)
        
        self.success_rate = successes / total if total > 0 else 0.0
        self.total_reward += reward
        
        # Calculate confidence based on number of observations
        self.confidence = min(1.0, math.sqrt(total) / 10.0)
        
        # Extract and update contextual features
        if context:
            self._update_context_features(context)
            
    def _update_context_features(self, context: Dict[str, Any]) -> None:
        """
        Extract and update contextual features that correlate with success.
        
        Args:
            context: Current context dictionary
        """
        # For each context feature, track its correlation with success
        for key, value in context.items():
            if key not in self.context_features:
                self.context_features[key] = {
                    'value_counts': defaultdict(int),
                    'success_counts': defaultdict(int),
                    'correlation': 0.0
                }
                
            # Convert value to hashable type if needed
            if isinstance(value, list) or isinstance(value, np.ndarray):
                hash_value = str(value)
            else:
                hash_value = value
                
            # Update counts
            self.context_features[key]['value_counts'][hash_value] += 1
            
            # If last outcome was success, update success count
            if self.outcome_history[-1][0]:  # Check if latest outcome was success
                self.context_features[key]['success_counts'][hash_value] += 1
                
            # Calculate correlation
            total = sum(self.context_features[key]['value_counts'].values())
            successes = sum(self.context_features[key]['success_counts'].values())
            
            if total > 0:
                overall_success_rate = successes / total
                
                # Calculate how much each value's success rate differs from overall
                correlation_sum = 0.0
                for hash_value, count in self.context_features[key]['value_counts'].items():
                    value_success = self.context_features[key]['success_counts'][hash_value]
                    value_success_rate = value_success / count if count > 0 else 0
                    
                    # Weight by count
                    correlation_sum += abs(value_success_rate - overall_success_rate) * count
                    
                # Normalize
                self.context_features[key]['correlation'] = correlation_sum / total
            
    def matches(self, sequence: List[Tuple[Dict[str, float], int]]) -> float:
        """
        Check how well a sequence matches this pattern.
        
        Args:
            sequence: List of (state features, action) pairs to match
            
        Returns:
            Match score between 0.0 and 1.0
        """
        if not sequence or not self.state_action_sequence:
            return 0.0
            
        # Match as many elements as possible
        max_items = min(len(sequence), len(self.state_action_sequence))
        
        total_similarity = 0.0
        
        for i in range(max_items):
            seq_features, seq_action = sequence[i]
            pattern_features, pattern_action = self.state_action_sequence[i]
            
            # Action must match exactly
            if seq_action != pattern_action:
                return 0.0
                
            # Calculate state similarity
            state_similarity = self._calculate_state_similarity(seq_features, pattern_features)
            total_similarity += state_similarity
            
        # Return average similarity
        return total_similarity / max_items
            
    def _calculate_state_similarity(self, features1: Dict[str, float], 
                                  features2: Dict[str, float]) -> float:
        """
        Calculate similarity between two state feature sets.
        
        Args:
            features1: First feature dictionary
            features2: Second feature dictionary
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Find common keys
        common_keys = set(features1.keys()) & set(features2.keys())
        
        if not common_keys:
            return 0.0
            
        # Calculate similarity for each common feature
        total_similarity = 0.0
        for key in common_keys:
            value1 = features1[key]
            value2 = features2[key]
            
            # Calculate similarity based on feature type
            if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
                # For numerical values, use normalized difference
                max_value = max(abs(value1), abs(value2))
                if max_value == 0:
                    similarity = 1.0  # Both values are 0
                else:
                    similarity = 1.0 - min(1.0, abs(value1 - value2) / max_value)
            else:
                # For other types, check equality
                similarity = 1.0 if value1 == value2 else 0.0
                
            total_similarity += similarity
            
        return total_similarity / len(common_keys)
        
    def is_applicable(self, context: Dict[str, Any]) -> float:
        """
        Determine if this pattern is applicable in the current context.
        
        Args:
            context: Current context dictionary
            
        Returns:
            Applicability score between 0.0 and 1.0
        """
        if not context or not self.context_features:
            return self.confidence  # Base applicability on confidence
            
        # Check how well the context matches favorable conditions
        total_correlation = 0.0
        total_match_score = 0.0
        
        for key, feature_data in self.context_features.items():
            if key not in context:
                continue
                
            # Get correlation weight for this feature
            correlation = feature_data['correlation']
            if correlation <= 0.1:  # Ignore features with low correlation
                continue
                
            current_value = context[key]
            # Make value hashable
            if isinstance(current_value, list) or isinstance(current_value, np.ndarray):
                hash_value = str(current_value)
            else:
                hash_value = current_value
                
            # Calculate match score for this feature
            if hash_value in feature_data['value_counts']:
                count = feature_data['value_counts'][hash_value]
                success_count = feature_data['success_counts'][hash_value]
                
                if count > 0:
                    feature_score = success_count / count
                    total_match_score += feature_score * correlation
                    total_correlation += correlation
                    
        # Compute final applicability
        if total_correlation > 0:
            context_score = total_match_score / total_correlation
            # Combine with base confidence
            return (context_score * 0.7) + (self.confidence * 0.3)
        else:
            return self.confidence
    
    def add_tag(self, tag: str) -> None:
        """
        Add a tag to this pattern to categorize it.
        
        Args:
            tag: Tag to add (e.g., 'combat', 'exploration', 'resource_gathering')
        """
        self.tags.add(tag)
        
    def get_tags(self) -> Set[str]:
        """
        Get all tags associated with this pattern.
        
        Returns:
            Set of tags
        """
        return self.tags
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert pattern to dictionary for serialization.
        
        Returns:
            Dictionary representation of the pattern
        """
        return {
            'id': self.id,
            'sequence_length': self.sequence_length,
            'state_action_sequence': self.state_action_sequence,
            'context_features': self.context_features,
            'success_rate': self.success_rate,
            'confidence': self.confidence,
            'total_reward': self.total_reward,
            'usage_count': self.usage_count,
            'tags': list(self.tags)
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionPattern':
        """
        Create pattern from dictionary representation.
        
        Args:
            data: Dictionary representation of a pattern
            
        Returns:
            ActionPattern instance
        """
        pattern = cls(data['id'], data['sequence_length'])
        pattern.state_action_sequence = data['state_action_sequence']
        pattern.context_features = data['context_features']
        pattern.success_rate = data['success_rate']
        pattern.confidence = data['confidence']
        pattern.total_reward = data['total_reward']
        pattern.usage_count = data['usage_count']
        pattern.tags = set(data['tags'])
        return pattern


class PatternRecognitionSystem:
    """
    System for identifying and utilizing action patterns from agent experiences.
    
    This system analyzes sequences of state-action pairs to identify patterns
    that consistently lead to success or failure, enabling agents to recognize
    and adapt to effective strategies.
    """
    
    def __init__(self, max_patterns: int = 1000, min_confidence: float = 0.2):
        """
        Initialize the pattern recognition system.
        
        Args:
            max_patterns: Maximum number of patterns to store
            min_confidence: Minimum confidence threshold for pattern recognition
        """
        self.patterns = {}
        self.agent_sequences = {}
        self.agent_contexts = {}
        self.max_patterns = max_patterns
        self.min_confidence = min_confidence
        self.team_patterns = {}
        self.personality_patterns = {}
        
        # Performance metrics
        self.pattern_usage_stats = defaultdict(int)
        self.pattern_success_stats = defaultdict(lambda: [0, 0])  # [successes, attempts]
        
    def record_experience(self, agent_id: str, state: np.ndarray, action: int, 
                         reward: float, context: Dict[str, Any] = None) -> None:
        """
        Record an agent's experience for pattern analysis.
        
        Args:
            agent_id: Identifier for the agent
            state: State observation
            action: Action taken
            reward: Reward received
            context: Additional contextual information
        """
        # Initialize agent data if not present
        if agent_id not in self.agent_sequences:
            self.agent_sequences[agent_id] = []
            self.agent_contexts[agent_id] = {}
            
        # Extract relevant features from state
        state_features = self._extract_features(state)
        
        # Add to agent sequence
        self.agent_sequences[agent_id].append((state_features, action))
        
        # Keep sequence bounded
        if len(self.agent_sequences[agent_id]) > 10:  # Limit sequence history
            self.agent_sequences[agent_id] = self.agent_sequences[agent_id][-10:]
            
        # Update context
        if context:
            self.agent_contexts[agent_id].update(context)
            
        # Attempt to detect pattern completion
        if reward != 0:  # Non-zero reward might indicate pattern completion
            self._check_pattern_completion(agent_id, reward > 0, reward)
            
    def _extract_features(self, state: np.ndarray) -> Dict[str, float]:
        """
        Extract relevant features from a state observation.
        
        Args:
            state: Raw state observation
            
        Returns:
            Dictionary of extracted features
        """
        # Basic feature extraction (customize based on state representation)
        features = {}
        
        # Handle 1D array states
        if len(state.shape) == 1:
            # Game-specific feature extraction would go here
            # For now, just use some state indices as features
            features['position_x'] = float(state[0]) if state.size > 0 else 0.0
            features['position_y'] = float(state[1]) if state.size > 1 else 0.0
            features['velocity'] = float(state[2]) if state.size > 2 else 0.0
            features['health'] = float(state[3]) if state.size > 3 else 0.0
            features['energy'] = float(state[4]) if state.size > 4 else 0.0
            
            # Calculate additional derived features
            if state.size > 5:
                features['nearby_entity'] = 1.0 if state[5] > 0.5 else 0.0
                
            if state.size > 6:
                features['resource_nearby'] = 1.0 if state[6] > 0.5 else 0.0
                
            if state.size > 8:
                # Calculate a danger score if we have enemy info
                features['danger_level'] = float(state[7] * state[8])  # e.g., enemy_present * enemy_proximity
        
        # Add more sophisticated feature extraction if needed
        
        return features
            
    def _check_pattern_completion(self, agent_id: str, success: bool, reward: float) -> None:
        """
        Check if a newly completed sequence forms a pattern.
        
        Args:
            agent_id: Identifier for the agent
            success: Whether the outcome was successful
            reward: Reward received
        """
        if agent_id not in self.agent_sequences:
            return
            
        # Get last few actions as potential pattern
        sequence = self.agent_sequences[agent_id][-3:]  # Last 3 actions
        
        # Get current context
        context = self.agent_contexts.get(agent_id, {})
        
        # Check if this matches an existing pattern
        matched_pattern = None
        highest_match = 0.0
        
        for pattern_id, pattern in self.patterns.items():
            match_score = pattern.matches(sequence)
            if match_score > highest_match and match_score > 0.7:  # 70% similarity threshold
                highest_match = match_score
                matched_pattern = pattern
                
        if matched_pattern:
            # Update existing pattern with new outcome
            matched_pattern.record_outcome(success, reward, context)
            matched_pattern.usage_count += 1
            
            # Update stats
            self.pattern_usage_stats[matched_pattern.id] += 1
            self.pattern_success_stats[matched_pattern.id][1] += 1  # Attempts
            if success:
                self.pattern_success_stats[matched_pattern.id][0] += 1  # Successes
        else:
            # Create new pattern if sequence is meaningful
            # Only create patterns for successful sequences or highly negative outcomes
            if success or reward < -0.5:
                self._create_new_pattern(agent_id, sequence, success, reward, context)
                
    def _create_new_pattern(self, agent_id: str, sequence: List[Tuple[Dict[str, float], int]],
                          success: bool, reward: float, context: Dict[str, Any]) -> None:
        """
        Create a new pattern from a sequence.
        
        Args:
            agent_id: Identifier for the agent
            sequence: Sequence of (state features, action) pairs
            success: Whether the outcome was successful
            reward: Reward received
            context: Current context dictionary
        """
        # Generate unique ID for pattern
        pattern_id = f"pattern_{agent_id}_{len(self.patterns)}"
        
        # Create pattern
        pattern = ActionPattern(pattern_id, len(sequence))
        
        # Add state-action pairs
        for state_features, action in sequence:
            pattern.add_state_action(state_features, action)
            
        # Record outcome
        pattern.record_outcome(success, reward, context)
        
        # Add appropriate tags
        self._tag_pattern(pattern, context)
        
        # Store pattern
        self.patterns[pattern_id] = pattern
        
        # Store in team patterns if applicable
        if 'team_id' in context:
            team_id = context['team_id']
            if team_id not in self.team_patterns:
                self.team_patterns[team_id] = []
            self.team_patterns[team_id].append(pattern_id)
            
        # Store in personality patterns if applicable
        if 'personality_type' in context:
            personality_type = context['personality_type']
            if personality_type not in self.personality_patterns:
                self.personality_patterns[personality_type] = []
            self.personality_patterns[personality_type].append(pattern_id)
            
        # Prune patterns if needed
        if len(self.patterns) > self.max_patterns:
            self._prune_patterns()
            
    def _tag_pattern(self, pattern: ActionPattern, context: Dict[str, Any]) -> None:
        """
        Add appropriate tags to a pattern based on context.
        
        Args:
            pattern: Pattern to tag
            context: Context dictionary
        """
        # Tag based on context information
        if 'in_combat' in context and context['in_combat']:
            pattern.add_tag('combat')
            
        if 'exploring' in context and context['exploring']:
            pattern.add_tag('exploration')
            
        if 'gathering_resources' in context and context['gathering_resources']:
            pattern.add_tag('resource_gathering')
            
        if 'in_formation' in context and context['in_formation']:
            pattern.add_tag('formation')
            
        if 'team_ability' in context and context['team_ability']:
            pattern.add_tag('team_ability')
            
        if 'near_enemy' in context and context['near_enemy']:
            pattern.add_tag('enemy_interaction')
            
        if 'near_ally' in context and context['near_ally']:
            pattern.add_tag('ally_interaction')
            
        # Add additional tags based on pattern characteristics
        actions = [action for _, action in pattern.state_action_sequence]
        
        # Add tags based on action patterns
        if all(a < 4 for a in actions):  # Assuming 0-3 are movement actions
            pattern.add_tag('movement')
        
        if any(a == 4 for a in actions):  # Assuming 4 is attack action
            pattern.add_tag('attack')
            
        if pattern.success_rate > 0.8:
            pattern.add_tag('high_success')
        elif pattern.success_rate < 0.2:
            pattern.add_tag('low_success')
            
    def _prune_patterns(self) -> None:
        """Prune least valuable patterns to maintain maximum count."""
        # Calculate value for each pattern
        pattern_values = {}
        for pattern_id, pattern in self.patterns.items():
            # Value based on success rate, confidence, and recency
            recency = 1.0 / (1.0 + (time.time() - pattern.last_updated) / 3600)  # Hours factor
            value = (pattern.success_rate * 0.5 + 
                     pattern.confidence * 0.3 + 
                     recency * 0.2)
            pattern_values[pattern_id] = value
            
        # Sort patterns by value
        sorted_patterns = sorted(pattern_values.items(), key=lambda x: x[1])
        
        # Remove lowest value patterns
        patterns_to_remove = len(self.patterns) - self.max_patterns
        
        for i in range(patterns_to_remove):
            if i < len(sorted_patterns):
                pattern_id = sorted_patterns[i][0]
                
                # Remove from main patterns dict
                if pattern_id in self.patterns:
                    del self.patterns[pattern_id]
                    
                # Remove from team patterns
                for team_id in self.team_patterns:
                    if pattern_id in self.team_patterns[team_id]:
                        self.team_patterns[team_id].remove(pattern_id)
                        
                # Remove from personality patterns
                for p_type in self.personality_patterns:
                    if pattern_id in self.personality_patterns[p_type]:
                        self.personality_patterns[p_type].remove(pattern_id)
    
    def suggest_action(self, agent_id: str, state: np.ndarray, 
                    context: Dict[str, Any] = None) -> Tuple[Optional[int], float]:
        """
        Suggest an action based on recognized patterns.
        
        Args:
            agent_id: Identifier for the agent
            state: Current state observation
            context: Additional contextual information
            
        Returns:
            Tuple of (suggested action, confidence) or (None, 0.0) if no suggestion
        """
        if agent_id not in self.agent_sequences:
            return None, 0.0
            
        # Get recent sequence
        recent_sequence = self.agent_sequences[agent_id][-2:]  # Last 2 actions
        
        # Extract features for current state
        state_features = self._extract_features(state)
        
        # Update context dictionary
        full_context = self.agent_contexts.get(agent_id, {}).copy()
        if context:
            full_context.update(context)
            
        # Find relevant patterns
        relevant_patterns = []
        
        for pattern_id, pattern in self.patterns.items():
            # Only consider patterns with sufficient confidence
            if pattern.confidence < self.min_confidence:
                continue
                
            # Check if the pattern is applicable in this context
            applicability = pattern.is_applicable(full_context)
            if applicability < 0.3:  # Minimum applicability threshold
                continue
                
            # Calculate how well the current state and recent actions match the pattern's start
            if len(pattern.state_action_sequence) > 0:
                # Create test sequence with recent actions + current state
                test_sequence = recent_sequence.copy()
                
                # Score based on matching the start of the pattern
                match_score = 0.0
                
                # Get minimum comparison length
                compare_length = min(len(test_sequence), len(pattern.state_action_sequence) - 1)
                
                if compare_length > 0:
                    pattern_start = pattern.state_action_sequence[:compare_length]
                    
                    # Calculate similarity for each state-action pair
                    similarity_sum = 0.0
                    for i in range(compare_length):
                        test_features, test_action = test_sequence[i]
                        pattern_features, pattern_action = pattern_start[i]
                        
                        # Action must match exactly
                        if test_action != pattern_action:
                            similarity_sum = 0.0
                            break
                            
                        # Calculate state similarity
                        state_similarity = pattern._calculate_state_similarity(
                            test_features, pattern_features)
                        similarity_sum += state_similarity
                        
                    if compare_length > 0:
                        match_score = similarity_sum / compare_length
                        
                # Only consider patterns with sufficient match score
                if match_score >= 0.6:
                    # Calculate final relevance score
                    relevance = (match_score * 0.6 + 
                                pattern.success_rate * 0.3 + 
                                applicability * 0.1)
                    
                    relevant_patterns.append((pattern, relevance))
        
        # If no relevant patterns found
        if not relevant_patterns:
            return None, 0.0
            
        # Sort patterns by relevance
        relevant_patterns.sort(key=lambda x: x[1], reverse=True)
        
        # Get the most relevant pattern
        best_pattern, relevance = relevant_patterns[0]
        
        # Get the next action from the pattern
        current_step = len(recent_sequence) % len(best_pattern.state_action_sequence)
        _, next_action = best_pattern.state_action_sequence[current_step]
        
        # Update pattern usage stats
        best_pattern.usage_count += 1
        self.pattern_usage_stats[best_pattern.id] += 1
        
        return next_action, relevance * best_pattern.confidence
    
    def get_team_patterns(self, team_id: str, tag: Optional[str] = None) -> List[ActionPattern]:
        """
        Get patterns associated with a specific team.
        
        Args:
            team_id: Team identifier
            tag: Optional tag to filter by
            
        Returns:
            List of patterns associated with the team
        """
        if team_id not in self.team_patterns:
            return []
            
        patterns = [self.patterns[p_id] for p_id in self.team_patterns[team_id] 
                   if p_id in self.patterns]
                   
        # Filter by tag if specified
        if tag:
            patterns = [p for p in patterns if tag in p.get_tags()]
            
        return patterns
        
    def get_personality_patterns(self, personality_type: str) -> List[ActionPattern]:
        """
        Get patterns associated with a specific personality type.
        
        Args:
            personality_type: Personality type identifier
            
        Returns:
            List of patterns associated with the personality type
        """
        if personality_type not in self.personality_patterns:
            return []
            
        return [self.patterns[p_id] for p_id in self.personality_patterns[personality_type] 
               if p_id in self.patterns]
    
    def get_successful_patterns(self, min_success_rate: float = 0.7, 
                            min_confidence: float = 0.5) -> List[ActionPattern]:
        """
        Get patterns with high success rates.
        
        Args:
            min_success_rate: Minimum success rate threshold
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of successful patterns
        """
        return [pattern for pattern in self.patterns.values() 
               if pattern.success_rate >= min_success_rate and 
               pattern.confidence >= min_confidence]
               
    def share_patterns(self, source_agent_id: str, target_agent_id: str, 
                    tag: Optional[str] = None, max_patterns: int = 5) -> int:
        """
        Share successful patterns between agents.
        
        Args:
            source_agent_id: Source agent identifier
            target_agent_id: Target agent identifier
            tag: Optional tag to filter by
            max_patterns: Maximum number of patterns to share
            
        Returns:
            Number of patterns shared
        """
        # Get source agent's successful patterns
        source_patterns = []
        for pattern_id, pattern in self.patterns.items():
            if (pattern_id.startswith(f"pattern_{source_agent_id}_") and
                pattern.success_rate >= 0.6 and
                pattern.confidence >= 0.4):
                
                # Filter by tag if specified
                if tag and tag not in pattern.get_tags():
                    continue
                    
                source_patterns.append(pattern)
                
        # Sort by success rate
        source_patterns.sort(key=lambda p: p.success_rate, reverse=True)
        
        # Limit number of patterns
        source_patterns = source_patterns[:max_patterns]
        
        if not source_patterns:
            return 0
            
        # Create clones for target agent
        for pattern in source_patterns:
            # Generate new ID for the pattern
            new_id = f"pattern_{target_agent_id}_shared_{len(self.patterns)}"
            
            # Create a copy of the pattern
            new_pattern = ActionPattern(new_id, pattern.sequence_length)
            
            # Copy state-action sequence
            for state_features, action in pattern.state_action_sequence:
                new_pattern.add_state_action(state_features.copy(), action)
                
            # Copy other attributes
            new_pattern.context_features = pattern.context_features.copy()
            new_pattern.success_rate = pattern.success_rate
            new_pattern.confidence = pattern.confidence * 0.8  # Slightly lower confidence
            new_pattern.total_reward = pattern.total_reward
            new_pattern.tags = pattern.tags.copy()
            
            # Add metadata tag to indicate sharing
            new_pattern.add_tag('shared')
            new_pattern.add_tag(f'from_{source_agent_id}')
            
            # Store the new pattern
            self.patterns[new_id] = new_pattern
            
        return len(source_patterns)
    
    def integrate_with_personality(self, agent_id: str, personality_traits: Dict[str, float]) -> None:
        """
        Integrate personality traits with pattern recognition.
        
        This allows patterns to be more or less applicable based on personality.
        
        Args:
            agent_id: Agent identifier
            personality_traits: Dictionary of personality trait values
        """
        # Update agent context with personality traits
        if agent_id not in self.agent_contexts:
            self.agent_contexts[agent_id] = {}
            
        # Add personality traits to context
        for trait, value in personality_traits.items():
            self.agent_contexts[agent_id][f'personality_{trait}'] = value
            
        # Determine personality type
        dominant_traits = []
        for trait, value in personality_traits.items():
            if value >= 0.7:
                dominant_traits.append(f'high_{trait}')
            elif value <= 0.3:
                dominant_traits.append(f'low_{trait}')
                
        # Create a personality type string
        if dominant_traits:
            personality_type = '_'.join(sorted(dominant_traits))
            self.agent_contexts[agent_id]['personality_type'] = personality_type
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about pattern recognition performance.
        
        Returns:
            Dictionary of statistics
        """
        # Calculate overall statistics
        total_patterns = len(self.patterns)
        
        # Calculate success rates
        pattern_success_rates = {pattern_id: pattern.success_rate 
                               for pattern_id, pattern in self.patterns.items()}
        
        # Calculate average success rate
        avg_success_rate = (sum(pattern_success_rates.values()) / total_patterns 
                         if total_patterns > 0 else 0.0)
        
        # Calculate pattern usage
        total_usage = sum(self.pattern_usage_stats.values())
        
        # Most commonly used patterns
        most_used_patterns = sorted(self.pattern_usage_stats.items(), 
                                  key=lambda x: x[1], reverse=True)[:10]
        
        # Most successful patterns
        most_successful_patterns = sorted(pattern_success_rates.items(),
                                       key=lambda x: x[1], reverse=True)[:10]
        
        # Success rate by tag
        tag_patterns = defaultdict(list)
        for pattern in self.patterns.values():
            for tag in pattern.get_tags():
                tag_patterns[tag].append(pattern.success_rate)
                
        tag_success_rates = {tag: sum(rates) / len(rates) if rates else 0.0
                           for tag, rates in tag_patterns.items()}
        
        return {
            'total_patterns': total_patterns,
            'average_success_rate': avg_success_rate,
            'total_pattern_usage': total_usage,
            'most_used_patterns': most_used_patterns,
            'most_successful_patterns': most_successful_patterns,
            'tag_success_rates': tag_success_rates,
            'patterns_by_tag': {tag: len(patterns) for tag, patterns in tag_patterns.items()}
        }
        
    def save_to_dict(self) -> Dict[str, Any]:
        """
        Save the pattern recognition system state to a dictionary.
        
        Returns:
            Dictionary representation of the system state
        """
        return {
            'patterns': {p_id: pattern.to_dict() for p_id, pattern in self.patterns.items()},
            'team_patterns': self.team_patterns,
            'personality_patterns': self.personality_patterns,
            'pattern_usage_stats': dict(self.pattern_usage_stats),
            'pattern_success_stats': {k: list(v) for k, v in self.pattern_success_stats.items()}
        }
        
    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Load the pattern recognition system state from a dictionary.
        
        Args:
            data: Dictionary representation of the system state
        """
        # Load patterns
        self.patterns = {}
        for p_id, pattern_data in data['patterns'].items():
            self.patterns[p_id] = ActionPattern.from_dict(pattern_data)
            
        # Load team patterns
        self.team_patterns = data['team_patterns']
        
        # Load personality patterns
        self.personality_patterns = data['personality_patterns']
        
        # Load stats
        self.pattern_usage_stats = defaultdict(int, data['pattern_usage_stats'])
        self.pattern_success_stats = defaultdict(lambda: [0, 0])
        for k, v in data['pattern_success_stats'].items():
            self.pattern_success_stats[k] = v 