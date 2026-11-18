import numpy as np
import logging
from typing import Dict, List, Tuple, Any, Optional, Union
from collections import defaultdict
import time
import math
import random
from systems.core.system_manager import system_manager
from typing import TYPE_CHECKING
from systems.agents.personality_system import PersonalityTrait

# Forward references for type hints
if TYPE_CHECKING:
    from systems.agents.personality_system import PersonalitySystem
    from systems.agents.relationship_system import RelationshipSystem

class PatternRecognitionSystem:
    """
    System for recognizing patterns in agent behavior and outcomes.
    
    This system learns from agent experiences and suggests actions based on
    similar states it has seen before, factoring in personality traits to 
    personalize the learning process.
    """
    
    def __init__(self, max_patterns: int = 1000, min_confidence_threshold: float = 0.6, 
                 learning_rate: float = 0.1, state_similarity_threshold: float = 0.9,
                 personality_system_override: Optional["PersonalitySystem"] = None,
                 relationship_system_override: Optional["RelationshipSystem"] = None):
        """
        Initialize the pattern recognition system.
        
        Args:
            max_patterns: Maximum number of patterns to store per agent
            min_confidence_threshold: Minimum confidence required to suggest an action
            learning_rate: Rate at which to update existing patterns with new experiences
            state_similarity_threshold: Threshold for considering states to be similar (0-1)
            personality_system_override: Optionally inject a specific PersonalitySystem instance.
            relationship_system_override: Optionally inject a specific RelationshipSystem instance.
        """
        self.patterns = defaultdict(list)  # agent_id -> list of patterns
        self.max_patterns = max_patterns
        self.min_confidence_threshold = min_confidence_threshold
        self.learning_rate = learning_rate
        self.state_similarity_threshold = state_similarity_threshold
        self.logger = logging.getLogger(__name__)
        
        # System Dependencies (Lazy Loaded)
        self._personality_system_instance = personality_system_override
        self._relationship_system_instance = relationship_system_override

        # Pattern outcome tracking
        self.success_patterns = defaultdict(list)  # agent_id -> list of successful patterns
        self.failure_patterns = defaultdict(list)  # agent_id -> list of failed patterns
        self.pattern_outcomes = defaultdict(lambda: {"success": 0, "failure": 0, "neutral": 0})  # pattern_id -> outcome counts
        
    # --- Lazy Loading Properties ---
    @property
    def personality_system(self) -> Optional["PersonalitySystem"]:
        if self._personality_system_instance is None:
            self._personality_system_instance = system_manager.get_system("PersonalitySystem")
            if not self._personality_system_instance:
                self.logger.info("PersonalitySystem not found via SystemManager in PatternRecognitionSystem.")
        return self._personality_system_instance

    @property
    def relationship_system(self) -> Optional["RelationshipSystem"]:
        if self._relationship_system_instance is None:
            self._relationship_system_instance = system_manager.get_system("RelationshipSystem")
            if not self._relationship_system_instance:
                self.logger.info("RelationshipSystem not found via SystemManager in PatternRecognitionSystem.")
        return self._relationship_system_instance
    # --- End Lazy Loading Properties ---
    
    def record_experience(self, agent_id: str, state: np.ndarray, action: int, 
                         reward: float, context: Dict[str, Any]) -> None:
        """
        Record an agent's experience for pattern recognition.
        
        Args:
            agent_id: The unique identifier for the agent
            state: The state the agent was in
            action: The action the agent took
            reward: The reward the agent received
            context: Additional contextual information
        """
        if not self.personality_system or not self.personality_system.get_agent_personality(agent_id):
            self.logger.info(f"Agent {agent_id} has no personality traits registered.")
            return
            
        # Check if we have a similar state already
        similar_pattern_idx = self._find_similar_pattern(agent_id, state, context)
        
        if similar_pattern_idx is not None:
            # Update existing pattern
            pattern = self.patterns[agent_id][similar_pattern_idx]
            self._update_pattern(pattern, state, action, reward, context)
            
            # Track pattern outcome based on reward
            pattern_id = f"{agent_id}_{similar_pattern_idx}"
            self._track_pattern_outcome(pattern_id, pattern, reward)
        else:
            # Create new pattern
            new_pattern = self._create_new_pattern(agent_id, state, action, reward, context)
            
            # Assign initial outcome based on reward
            pattern_id = f"{agent_id}_{len(self.patterns[agent_id]) - 1}"
            self._track_pattern_outcome(pattern_id, new_pattern, reward)
            
        # Ensure we don't exceed max patterns per agent
        if len(self.patterns[agent_id]) > self.max_patterns:
            # Remove the oldest or least successful pattern
            self._prune_patterns(agent_id)
    
    def suggest_action(self, agent_id: str, state: np.ndarray, 
                     context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[int], float]:
        """
        Suggest an action based on recognized patterns.
        
        Args:
            agent_id: The unique identifier for the agent
            state: The current state of the agent
            context: Additional contextual information (optional)
            
        Returns:
            A tuple of (suggested_action, confidence) or (None, 0.0) if no action can be suggested
        """
        if agent_id not in self.patterns or len(self.patterns[agent_id]) == 0:
            return None, 0.0
            
        context = context or {}
        
        # Find patterns with similar states and contexts
        similar_patterns = []
        for idx, pattern in enumerate(self.patterns[agent_id]):
            state_similarity = self._calculate_state_similarity(pattern["state"], state)
            context_similarity = self._calculate_context_similarity(pattern["context"], context)
            
            # Calculate combined similarity (REMOVE personality_weight for threshold check)
            # personality_weight = 1.0 
            # agent_personality = self.personality_system.get_agent_personality(agent_id) if self.personality_system else None
            # if agent_personality:
            #      openness = agent_personality.get_trait(PersonalityTrait.OPENNESS) 
            #      personality_weight = openness 
            
            # combined_similarity = (state_similarity * 0.7 + context_similarity * 0.3) * personality_weight
            combined_similarity_for_check = state_similarity * 0.7 + context_similarity * 0.3
            
            # if combined_similarity >= self.state_similarity_threshold:
            if combined_similarity_for_check >= self.state_similarity_threshold:
                # --- Calculate full similarity including personality for ranking/confidence --- 
                personality_weight = 1.0
                agent_personality = self.personality_system.get_agent_personality(agent_id) if self.personality_system else None
                if agent_personality:
                    try:
                        openness = agent_personality.get_trait(PersonalityTrait.OPENNESS)
                        personality_weight = openness
                    except Exception as e: # Catch potential errors from mock/real object
                        self.logger.warning(f"Could not get OPENNESS trait for {agent_id}: {e}")
                full_combined_similarity = combined_similarity_for_check * personality_weight
                # --- End calculation --- 

                # Check if this is a known failure pattern
                pattern_id = f"{agent_id}_{idx}"
                pattern_outcome = self._get_pattern_outcome_assessment(pattern_id)
                
                # Avoid suggesting failure patterns with high probability
                caution = 0.5 # Default caution
                if agent_personality:
                    # Assume Neuroticism influences caution
                    neuroticism = agent_personality.get_trait(PersonalityTrait.NEUROTICISM)
                    caution = neuroticism # Higher neuroticism = more caution

                if pattern_outcome == "failure" and caution > 0.6:
                    # Cautious agents avoid failure patterns
                    continue
                
                similar_patterns.append({
                    "pattern": pattern,
                    # Use the full similarity (with personality) for sorting/confidence later
                    "similarity": full_combined_similarity, 
                    "success_rate": pattern["success_rate"],
                    "pattern_id": pattern_id,
                    "outcome": pattern_outcome
                })
        
        if not similar_patterns:
            return None, 0.0
        
        # Prioritize success patterns for risk-averse agents
        risk_tolerance = 0.5 # Default
        agent_personality = self.personality_system.get_agent_personality(agent_id) if self.personality_system else None
        if agent_personality:
             risk_tolerance = agent_personality.get_trait(PersonalityTrait.RISK_TOLERANCE)

        if risk_tolerance < 0.4:  # Risk-averse
            # Filter to keep only success or neutral patterns if available
            success_patterns = [p for p in similar_patterns if p["outcome"] in ["success", "neutral"]]
            if success_patterns:
                similar_patterns = success_patterns
        
        # Sort by combination of similarity, success rate, and outcome preference
        similar_patterns.sort(
            key=lambda p: (
                p["similarity"] * 0.5 + 
                p["success_rate"] * 0.3 + 
                (0.2 if p["outcome"] == "success" else 0.1 if p["outcome"] == "neutral" else 0)
            ), 
            reverse=True
        )
        
        # Get the best pattern
        best_pattern = similar_patterns[0]
        # --- MODIFIED: Use base similarity (before personality weight) for confidence? ---
        # Or perhaps confidence should have a different formula?
        # Let's try using the similarity score *before* personality weighting was applied.
        # Need to retrieve that original score again or store it alongside.
        # For simplicity, let's recalculate the base similarity for the best pattern:
        state_sim = self._calculate_state_similarity(best_pattern['pattern']["state"], state)
        context_sim = self._calculate_context_similarity(best_pattern['pattern']["context"], context)
        base_combined_similarity = state_sim * 0.7 + context_sim * 0.3
        
        # confidence = best_pattern["similarity"] * best_pattern["success_rate"]
        confidence = base_combined_similarity * best_pattern["success_rate"]
        # --- END MODIFICATION ---
        
        # Only suggest if confidence exceeds threshold
        if confidence >= self.min_confidence_threshold:
            return best_pattern["pattern"]["action"], confidence
        
        return None, 0.0
    
    def get_success_patterns(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get a list of patterns that have been identified as successful.
        
        Args:
            agent_id: The agent ID to get successful patterns for
            
        Returns:
            List of successful patterns with their contexts
        """
        if agent_id not in self.patterns:
            return []
            
        success_patterns = []
        for idx, pattern in enumerate(self.patterns[agent_id]):
            pattern_id = f"{agent_id}_{idx}"
            if self._get_pattern_outcome_assessment(pattern_id) == "success":
                success_patterns.append({
                    "pattern": pattern,
                    "pattern_id": pattern_id,
                    "success_rate": pattern["success_rate"],
                    "context": pattern["context"]
                })
                
        # Sort by success rate
        success_patterns.sort(key=lambda p: p["success_rate"], reverse=True)
        return success_patterns
    
    def get_failure_patterns(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get a list of patterns that have been identified as failures.
        
        Args:
            agent_id: The agent ID to get failure patterns for
            
        Returns:
            List of failure patterns with their contexts
        """
        if agent_id not in self.patterns:
            return []
            
        failure_patterns = []
        for idx, pattern in enumerate(self.patterns[agent_id]):
            pattern_id = f"{agent_id}_{idx}"
            if self._get_pattern_outcome_assessment(pattern_id) == "failure":
                failure_patterns.append({
                    "pattern": pattern,
                    "pattern_id": pattern_id,
                    "success_rate": pattern["success_rate"],
                    "context": pattern["context"]
                })
                
        # Sort by negative success rate (most failure first)
        failure_patterns.sort(key=lambda p: p["success_rate"])
        return failure_patterns
    
    def analyze_pattern_factors(self, agent_id: str, pattern_type: str = "success") -> Dict[str, Any]:
        """
        Analyze patterns to identify common factors leading to success or failure.
        
        Args:
            agent_id: The agent ID to analyze patterns for
            pattern_type: Either "success" or "failure"
            
        Returns:
            Dictionary of common factors found in the specified pattern type
        """
        patterns = self.get_success_patterns(agent_id) if pattern_type == "success" else self.get_failure_patterns(agent_id)
        
        if not patterns:
            return {}
            
        # Analyze context factors
        context_factors = defaultdict(lambda: defaultdict(int))
        
        for pattern_data in patterns:
            pattern = pattern_data["pattern"]
            context = pattern["context"]
            
            # Count occurrences of context values
            for key, value in context.items():
                if isinstance(value, bool):
                    context_factors[key][str(value)] += 1
                elif isinstance(value, (int, float)):
                    # Discretize numerical values for counting
                    discretized = "high" if value > 0.7 else "medium" if value > 0.3 else "low"
                    context_factors[key][discretized] += 1
                else:
                    context_factors[key][str(value)] += 1
                    
        # Find common actions
        action_counts = defaultdict(int)
        for pattern_data in patterns:
            pattern = pattern_data["pattern"]
            action_counts[pattern["action"]] += 1
            
        # Calculate dominant values for each factor
        dominant_factors = {}
        for factor, values in context_factors.items():
            total = sum(values.values())
            if total > 0:
                # Find value with highest percentage
                dominant_value, dominant_count = max(values.items(), key=lambda x: x[1])
                if dominant_count / total > 0.6:  # Only include if >60% dominant
                    dominant_factors[factor] = {
                        "value": dominant_value,
                        "percentage": dominant_count / total
                    }
                    
        # Add most common action
        if action_counts:
            dominant_action, action_count = max(action_counts.items(), key=lambda x: x[1])
            dominant_factors["action"] = {
                "value": dominant_action,
                "percentage": action_count / len(patterns)
            }
            
        return dominant_factors
    
    def share_patterns(self, source_agent_id: str, target_agent_id: str) -> int:
        """
        Share patterns from one agent to another.
        
        Args:
            source_agent_id: The agent sharing its patterns
            target_agent_id: The agent receiving the patterns
            
        Returns:
            Number of patterns successfully shared
        """
        if source_agent_id not in self.patterns or target_agent_id not in self.patterns:
            return 0
            
        source_patterns = self.patterns[source_agent_id]
        target_patterns = self.patterns[target_agent_id]
        
        # Personality traits affect how patterns are shared
        sharing_effectiveness = 0.5 # Default
        source_personality = self.personality_system.get_agent_personality(source_agent_id) if self.personality_system else None
        target_personality = self.personality_system.get_agent_personality(target_agent_id) if self.personality_system else None

        if source_personality and target_personality:
            source_openness = source_personality.get_trait(PersonalityTrait.OPENNESS)
            target_openness = target_personality.get_trait(PersonalityTrait.OPENNESS)
            extraversion = source_personality.get_trait(PersonalityTrait.EXTRAVERSION)
            sharing_effectiveness = (source_openness + target_openness) / 2 * extraversion

        # ---> ADD Relationship Check HERE <--- (To be implemented next)
        relationship_modifier = 1.0
        if self.relationship_system:
             relationship = self.relationship_system.get_relationship(source_agent_id, target_agent_id)
             if relationship:
                 # Example: Increase sharing for teammates/high trust
                 if relationship.relationship_type == RelationshipType.TEAMMATE:
                     relationship_modifier *= 1.5
                 trust = relationship.get_metric(RelationshipMetric.TRUST)
                 relationship_modifier *= (1.0 + (trust - 50) / 100) # +50% at max trust, -50% at min trust

        # Prioritize sharing successful patterns
        patterns_to_share = []
        for idx, pattern in enumerate(source_patterns):
            pattern_id = f"{source_agent_id}_{idx}"
            pattern_outcome = self._get_pattern_outcome_assessment(pattern_id)
            
            # Share successful patterns with higher probability
            share_probability = sharing_effectiveness * relationship_modifier # Apply relationship mod
            if pattern_outcome == "success":
                share_probability *= 1.5
            elif pattern_outcome == "failure":
                # Share failure patterns only if target is open to learning from mistakes
                target_openness_trait = target_personality.get_trait(PersonalityTrait.OPENNESS) if target_personality else 0.5
                if target_openness_trait > 0.7:
                    share_probability *= 0.5
                else:
                    continue
                    
            if pattern["success_rate"] > 0.6 or pattern_outcome == "success":
                if np.random.random() < share_probability:
                    # Create a copy of the pattern with some adaptation based on target's personality
                    shared_pattern = self._adapt_pattern_for_target(pattern, target_agent_id) # Pass ID
                    patterns_to_share.append({
                        "pattern": shared_pattern,
                        "outcome": pattern_outcome
                    })
        
        # Add shared patterns to target, without exceeding max patterns
        shared_count = 0
        for pattern_data in patterns_to_share:
            pattern = pattern_data["pattern"]
            if len(target_patterns) >= self.max_patterns:
                # Remove lowest success rate pattern
                target_patterns.sort(key=lambda p: p["success_rate"])
                target_patterns.pop(0)
            
            # Check for duplicates before adding
            if not any(self._is_duplicate_pattern(pattern, p) for p in target_patterns):
                target_patterns.append(pattern)
                
                # Track outcome for this shared pattern
                pattern_id = f"{target_agent_id}_{len(target_patterns) - 1}"
                if pattern_data["outcome"] == "success":
                    self.pattern_outcomes[pattern_id]["success"] += 1
                elif pattern_data["outcome"] == "failure":
                    self.pattern_outcomes[pattern_id]["failure"] += 1
                    
                shared_count += 1
        
        return shared_count
    
    def save_to_dict(self) -> Dict[str, Any]:
        """
        Save the pattern recognition system state to a dictionary.
        
        Returns:
            A dictionary representation of the system state
        """
        serialized_patterns = {}
        for agent_id, agent_patterns in self.patterns.items():
            serialized_patterns[agent_id] = []
            for pattern in agent_patterns:
                # Convert numpy arrays to lists for serialization
                serialized_pattern = {
                    "state": pattern["state"].tolist(),
                    "action": pattern["action"],
                    "reward_history": pattern["reward_history"],
                    "success_rate": pattern["success_rate"],
                    "context": pattern["context"],
                    "timestamp": pattern["timestamp"],
                    "use_count": pattern["use_count"]
                }
                serialized_patterns[agent_id].append(serialized_pattern)
        
        # Serialize pattern outcomes
        serialized_outcomes = {}
        for pattern_id, outcomes in self.pattern_outcomes.items():
            serialized_outcomes[pattern_id] = dict(outcomes)
        
        return {
            "patterns": serialized_patterns,
            "agent_personalities": self.agent_personalities,
            "max_patterns": self.max_patterns,
            "min_confidence_threshold": self.min_confidence_threshold,
            "learning_rate": self.learning_rate,
            "state_similarity_threshold": self.state_similarity_threshold,
            "pattern_outcomes": serialized_outcomes
        }
    
    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Load the pattern recognition system state from a dictionary.
        
        Args:
            data: Dictionary containing system state
        """
        # Load system parameters
        self.max_patterns = data.get("max_patterns", self.max_patterns)
        self.min_confidence_threshold = data.get("min_confidence_threshold", self.min_confidence_threshold)
        self.learning_rate = data.get("learning_rate", self.learning_rate)
        self.state_similarity_threshold = data.get("state_similarity_threshold", self.state_similarity_threshold)
        
        # Load agent personalities
        self.agent_personalities = data.get("agent_personalities", {})
        
        # Load patterns
        serialized_patterns = data.get("patterns", {})
        self.patterns = defaultdict(list)
        
        for agent_id, agent_patterns in serialized_patterns.items():
            for pattern_data in agent_patterns:
                # Convert lists back to numpy arrays
                pattern = {
                    "state": np.array(pattern_data["state"]),
                    "action": pattern_data["action"],
                    "reward_history": pattern_data["reward_history"],
                    "success_rate": pattern_data["success_rate"],
                    "context": pattern_data["context"],
                    "timestamp": pattern_data["timestamp"],
                    "use_count": pattern_data["use_count"]
                }
                self.patterns[agent_id].append(pattern)
        
        # Load pattern outcomes
        serialized_outcomes = data.get("pattern_outcomes", {})
        self.pattern_outcomes = defaultdict(lambda: {"success": 0, "failure": 0, "neutral": 0})
        for pattern_id, outcomes in serialized_outcomes.items():
            self.pattern_outcomes[pattern_id].update(outcomes)
    
    def get_pattern_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        Get statistics about the patterns for an agent.
        
        Args:
            agent_id: The agent ID to get stats for
            
        Returns:
            Dictionary with pattern statistics
        """
        if agent_id not in self.patterns:
            return {
                "total_patterns": 0,
                "avg_success_rate": 0.0,
                "highest_success_rate": 0.0,
                "avg_use_count": 0,
                "most_common_action": None,
                "success_patterns": 0,
                "failure_patterns": 0,
                "neutral_patterns": 0
            }
        
        patterns = self.patterns[agent_id]
        total_patterns = len(patterns)
        
        if total_patterns == 0:
            return {
                "total_patterns": 0,
                "avg_success_rate": 0.0,
                "highest_success_rate": 0.0,
                "avg_use_count": 0,
                "most_common_action": None,
                "success_patterns": 0,
                "failure_patterns": 0,
                "neutral_patterns": 0
            }
        
        # Calculate stats
        success_rates = [p["success_rate"] for p in patterns]
        use_counts = [p["use_count"] for p in patterns]
        
        # Find most common action
        action_counts = defaultdict(int)
        for p in patterns:
            action_counts[p["action"]] += 1
        
        most_common_action = max(action_counts.items(), key=lambda x: x[1])[0] if action_counts else None
        
        # Count pattern outcomes
        success_patterns = 0
        failure_patterns = 0
        neutral_patterns = 0
        
        for idx in range(total_patterns):
            pattern_id = f"{agent_id}_{idx}"
            outcome = self._get_pattern_outcome_assessment(pattern_id)
            if outcome == "success":
                success_patterns += 1
            elif outcome == "failure":
                failure_patterns += 1
            else:
                neutral_patterns += 1
        
        return {
            "total_patterns": total_patterns,
            "avg_success_rate": sum(success_rates) / total_patterns,
            "highest_success_rate": max(success_rates),
            "avg_use_count": sum(use_counts) / total_patterns,
            "most_common_action": most_common_action,
            "success_patterns": success_patterns,
            "failure_patterns": failure_patterns,
            "neutral_patterns": neutral_patterns
        }
    
    def analyze_success_failure_patterns(self, agent_id: str) -> Dict[str, Any]:
        """
        Analyze the agent's patterns to identify factors that contribute to success or failure.
        
        Args:
            agent_id: The agent's unique identifier
            
        Returns:
            Dictionary with analysis results including:
            - success_factors: Common factors in successful patterns
            - failure_factors: Common factors in failed patterns
            - high_risk_states: State characteristics that frequently lead to failure
            - high_reward_states: State characteristics that frequently lead to success
        """
        if agent_id not in self.patterns or not self.patterns[agent_id]:
            return {
                "success_factors": {},
                "failure_factors": {},
                "high_risk_states": [],
                "high_reward_states": []
            }
        
        patterns = self.patterns[agent_id]
        success_patterns = []
        failure_patterns = []
        
        # Classify patterns based on outcome assessment
        for idx, pattern in enumerate(patterns):
            pattern_id = f"{agent_id}_{idx}"
            outcome = self._get_pattern_outcome_assessment(pattern_id)
            
            if outcome == "success":
                success_patterns.append(pattern)
            elif outcome == "failure":
                failure_patterns.append(pattern)
        
        # Extract common context factors in successful patterns
        success_factors = self._extract_common_factors(success_patterns)
        
        # Extract common context factors in failure patterns
        failure_factors = self._extract_common_factors(failure_patterns)
        
        # Identify high-risk and high-reward state characteristics
        high_risk_states = self._extract_state_characteristics(failure_patterns)
        high_reward_states = self._extract_state_characteristics(success_patterns)
        
        return {
            "success_factors": success_factors,
            "failure_factors": failure_factors,
            "high_risk_states": high_risk_states,
            "high_reward_states": high_reward_states
        }

    def _extract_common_factors(self, patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract common factors from a list of patterns.
        
        Args:
            patterns: List of pattern dictionaries
            
        Returns:
            Dictionary of common factors and their frequency
        """
        if not patterns:
            return {}
        
        factor_counts = defaultdict(lambda: defaultdict(int))
        total_patterns = len(patterns)
        
        # Count occurrences of each context factor
        for pattern in patterns:
            for key, value in pattern["context"].items():
                # For categorical values
                if isinstance(value, (str, bool)) or (isinstance(value, (int, float)) and value.is_integer()):
                    factor_counts[key][value] += 1
                # For numerical values, discretize into ranges
                elif isinstance(value, (int, float)):
                    # Create range buckets for numerical values
                    bucket = round(value * 2) / 2  # Round to nearest 0.5
                    factor_counts[key][bucket] += 1
        
        # Extract factors that appear in at least 40% of patterns
        common_factors = {}
        for key, value_counts in factor_counts.items():
            factor_values = {}
            for value, count in value_counts.items():
                frequency = count / total_patterns
                if frequency >= 0.4:  # At least 40% occurrence
                    factor_values[value] = frequency
            
            if factor_values:
                common_factors[key] = factor_values
        
        return common_factors

    def _extract_state_characteristics(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract common state vector characteristics from patterns.
        
        Args:
            patterns: List of pattern dictionaries
            
        Returns:
            List of state characteristic dictionaries
        """
        if not patterns or len(patterns) < 3:
            return []
        
        # Stack all state vectors into a matrix
        states = np.stack([p["state"] for p in patterns])
        
        # Calculate mean and standard deviation for each dimension
        mean_state = np.mean(states, axis=0)
        std_state = np.std(states, axis=0)
        
        # Identify dimensions with low standard deviation (consistent values)
        consistent_dims = np.where(std_state < 0.15)[0]
        
        # Create characteristic entries for consistent dimensions
        characteristics = []
        for dim in consistent_dims:
            mean_value = mean_state[dim]
            characteristics.append({
                "dimension": int(dim),
                "value": float(mean_value),
                "std_dev": float(std_state[dim])
            })
        
        return characteristics

    def suggest_action_with_risk_assessment(self, agent_id: str, state: np.ndarray, 
                                          context: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """
        Suggest an action based on pattern recognition with risk assessment.
        
        Args:
            agent_id: The agent's unique identifier
            state: The current state vector
            context: The current context dictionary
            
        Returns:
            Tuple containing:
            - The suggested action
            - A dictionary with risk assessment information:
                - confidence: Confidence in the suggestion (0-1)
                - outcome_prediction: Expected outcome ("success", "neutral", "failure")
                - risk_level: Estimated risk level (0-1)
                - similar_pattern_count: Number of similar patterns found
        """
        if agent_id not in self.patterns or not self.patterns[agent_id]:
            # No patterns available, return random action
            return np.random.randint(0, 10), {
                "confidence": 0.0,
                "outcome_prediction": "neutral",
                "risk_level": 0.5,
                "similar_pattern_count": 0
            }
        
        patterns = self.patterns[agent_id]
        similar_patterns = []
        
        # Find all similar patterns above threshold
        for i, pattern in enumerate(patterns):
            state_similarity = self._calculate_state_similarity(pattern["state"], state)
            context_similarity = self._calculate_context_similarity(pattern["context"], context)
            
            # Combined similarity score
            combined_similarity = state_similarity * 0.7 + context_similarity * 0.3
            
            if combined_similarity >= self.state_similarity_threshold * 0.8:  # Use lower threshold to collect more
                pattern_id = f"{agent_id}_{i}"
                outcome = self._get_pattern_outcome_assessment(pattern_id)
                similar_patterns.append({
                    "pattern": pattern,
                    "similarity": combined_similarity,
                    "outcome": outcome
                })
        
        # Adjust based on personality
        openness = 0.5
        risk_taking = 0.5
        if agent_id in self.agent_personalities:
            openness = self.agent_personalities[agent_id].get("openness", 0.5)
            risk_taking = self.agent_personalities[agent_id].get("risk_taking", 0.5)
        
        # If we have similar patterns, use them to suggest an action
        if similar_patterns:
            # Sort by similarity
            similar_patterns.sort(key=lambda p: p["similarity"], reverse=True)
            
            # Count outcomes
            outcome_counts = {"success": 0, "neutral": 0, "failure": 0}
            for p in similar_patterns:
                outcome_counts[p["outcome"]] += 1
            
            total_patterns = len(similar_patterns)
            success_ratio = outcome_counts["success"] / total_patterns
            failure_ratio = outcome_counts["failure"] / total_patterns
            
            # Calculate risk level
            risk_level = failure_ratio
            
            # Determine if agent should avoid high risk
            risk_tolerance = risk_taking
            
            # If risk is high and agent is risk-averse, avoid this action
            if risk_level > 0.6 and risk_tolerance < 0.4:
                # Find alternative pattern with lower risk
                alternative_patterns = [p for p in self.patterns[agent_id] 
                                     if p not in [sp["pattern"] for sp in similar_patterns]]
                
                if alternative_patterns:
                    # Choose random alternative
                    alt_pattern = random.choice(alternative_patterns)
                    return alt_pattern["action"], {
                        "confidence": 0.2,
                        "outcome_prediction": "neutral",
                        "risk_level": 0.3,
                        "similar_pattern_count": 0,
                        "note": "Avoiding high risk pattern"
                    }
            
            # Consider high openness agents trying new actions occasionally
            if openness > 0.7 and random.random() < 0.2 * openness:
                # Try a random action 
                return np.random.randint(0, 10), {
                    "confidence": 0.2,
                    "outcome_prediction": "neutral",
                    "risk_level": 0.5,
                    "similar_pattern_count": len(similar_patterns),
                    "note": "Exploring new action due to high openness"
                }
            
            # Weight patterns by similarity and success rate
            weighted_patterns = []
            for p in similar_patterns:
                weight = p["similarity"]
                
                # Adjust weight based on outcome
                if p["outcome"] == "success":
                    weight *= 1.5
                elif p["outcome"] == "failure":
                    weight *= 0.5
                
                weighted_patterns.append((p["pattern"], weight))
            
            # Normalize weights
            total_weight = sum(w for _, w in weighted_patterns)
            if total_weight > 0:
                probs = [w / total_weight for _, w in weighted_patterns]
                selected_pattern = weighted_patterns[np.random.choice(len(weighted_patterns), p=probs)][0]
            else:
                selected_pattern = weighted_patterns[0][0]
            
            # Determine outcome prediction
            if success_ratio > 0.6:
                prediction = "success"
            elif failure_ratio > 0.6:
                prediction = "failure"
            else:
                prediction = "neutral"
            
            return selected_pattern["action"], {
                "confidence": similar_patterns[0]["similarity"],
                "outcome_prediction": prediction,
                "risk_level": risk_level,
                "similar_pattern_count": len(similar_patterns)
            }
        
        # No similar patterns, return random action with low confidence
        return np.random.randint(0, 10), {
            "confidence": 0.0,
            "outcome_prediction": "neutral",
            "risk_level": 0.5,
            "similar_pattern_count": 0
        }

    def get_pattern_feedback(self, agent_id: str, pattern_id: str) -> Dict[str, Any]:
        """
        Get feedback about a specific pattern's performance history.
        
        Args:
            agent_id: The agent's unique identifier
            pattern_id: The pattern identifier
            
        Returns:
            Dictionary with pattern feedback
        """
        pattern_index = int(pattern_id.split('_')[1])
        if agent_id not in self.patterns or pattern_index >= len(self.patterns[agent_id]):
            return {"error": "Pattern not found"}
        
        pattern = self.patterns[agent_id][pattern_index]
        outcomes = self.pattern_outcomes.get(pattern_id, {"success": 0, "failure": 0, "neutral": 0})
        total_uses = outcomes["success"] + outcomes["failure"] + outcomes["neutral"]
        
        if total_uses == 0:
            return {
                "pattern_id": pattern_id,
                "success_rate": 0,
                "failure_rate": 0,
                "total_uses": 0,
                "outcome": "neutral",
                "average_reward": 0,
                "confidence": 0
            }
        
        success_rate = outcomes["success"] / total_uses
        failure_rate = outcomes["failure"] / total_uses
        avg_reward = sum(pattern["reward_history"]) / len(pattern["reward_history"])
        
        return {
            "pattern_id": pattern_id,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "total_uses": total_uses,
            "outcome": self._get_pattern_outcome_assessment(pattern_id),
            "average_reward": avg_reward,
            "confidence": min(1.0, total_uses / 10)  # Confidence increases with more uses, caps at 1.0
        }

    # Internal helper methods
    
    def _find_similar_pattern(self, agent_id: str, state: np.ndarray, 
                             context: Dict[str, Any]) -> Optional[int]:
        """Find index of a similar pattern for this state and context."""
        if agent_id not in self.patterns:
            return None # No patterns for this agent yet
        patterns = self.patterns[agent_id]
        
        for i, pattern in enumerate(patterns):
            state_similarity = self._calculate_state_similarity(pattern["state"], state)
            context_similarity = self._calculate_context_similarity(pattern["context"], context)
            
            # Combined similarity score
            combined_similarity = state_similarity * 0.7 + context_similarity * 0.3
            
            print(f"DEBUG [PRS._find_similar_pattern] Agent: {agent_id}, PatternIdx: {i}, StateSim: {state_similarity:.4f}, CtxSim: {context_similarity:.4f}, Combined: {combined_similarity:.4f}, Threshold: {self.state_similarity_threshold}")

            if combined_similarity >= self.state_similarity_threshold:
                return i
                
        return None
    
    def _create_new_pattern(self, agent_id: str, state: np.ndarray, action: int, 
                           reward: float, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new pattern from an experience."""
        pattern = {
            "state": state.copy(),
            "action": action,
            "reward_history": [reward],
            "success_rate": 1.0 if reward > 0 else 0.0,
            "context": context.copy(),
            "timestamp": time.time(),
            "use_count": 1
        }
        
        self.patterns[agent_id].append(pattern)
        return pattern
    
    def _update_pattern(self, pattern: Dict[str, Any], state: np.ndarray, action: int, 
                       reward: float, context: Dict[str, Any]) -> None:
        """Update an existing pattern with new experience."""
        # Only update if the action matches
        if pattern["action"] != action:
            return
            
        # Update the state using learning rate (weighted average)
        pattern["state"] = (
            (1 - self.learning_rate) * pattern["state"] + 
            self.learning_rate * state
        )
        
        # Update reward history
        pattern["reward_history"].append(reward)
        if len(pattern["reward_history"]) > 10:  # Keep last 10 rewards
            pattern["reward_history"] = pattern["reward_history"][-10:]
            
        # Update success rate
        positive_rewards = sum(1 for r in pattern["reward_history"] if r > 0)
        pattern["success_rate"] = positive_rewards / len(pattern["reward_history"])
        
        # Update context with new information, keeping the structure
        for key, value in context.items():
            if key in pattern["context"]:
                # For numerical values, use weighted average
                if isinstance(value, (int, float)) and isinstance(pattern["context"][key], (int, float)):
                    pattern["context"][key] = (
                        (1 - self.learning_rate) * pattern["context"][key] + 
                        self.learning_rate * value
                    )
                else:
                    # For non-numeric, use most recent
                    pattern["context"][key] = value
            else:
                # Add new context keys
                pattern["context"][key] = value
                
        # Update timestamp and use count
        pattern["timestamp"] = time.time()
        pattern["use_count"] += 1
    
    def _track_pattern_outcome(self, pattern_id: str, pattern: Dict[str, Any], reward: float) -> None:
        """
        Track whether a pattern leads to success or failure based on rewards.
        
        Args:
            pattern_id: Unique identifier for the pattern
            pattern: The pattern data
            reward: The reward received
        """
        # Increment appropriate outcome counter
        if reward > 0.5:  # Significant positive reward
            self.pattern_outcomes[pattern_id]["success"] += 1
        elif reward < -0.5:  # Significant negative reward
            self.pattern_outcomes[pattern_id]["failure"] += 1
        else:  # Neutral
            self.pattern_outcomes[pattern_id]["neutral"] += 1
    
    def _get_pattern_outcome_assessment(self, pattern_id: str) -> str:
        """
        Assess whether a pattern is considered success, failure, or neutral.
        
        Args:
            pattern_id: Unique identifier for the pattern
            
        Returns:
            "success", "failure", or "neutral"
        """
        outcomes = self.pattern_outcomes[pattern_id]
        total = outcomes["success"] + outcomes["failure"] + outcomes["neutral"]
        
        if total == 0:
            return "neutral"
            
        success_rate = outcomes["success"] / total
        failure_rate = outcomes["failure"] / total
        
        # Pattern needs at least 3 instances to be classified
        if total < 3:
            return "neutral"
            
        # Classify based on highest rate, with a minimum threshold
        if success_rate > 0.6 and success_rate > failure_rate:
            return "success"
        elif failure_rate > 0.6 and failure_rate > success_rate:
            return "failure"
        else:
            return "neutral"
    
    def _prune_patterns(self, agent_id: str) -> None:
        """Remove the least useful patterns to stay under max_patterns limit."""
        patterns = self.patterns[agent_id]
        
        if len(patterns) <= self.max_patterns:
            return
            
        # Calculate utility score for each pattern
        # Considers: success rate, recency, and use count
        current_time = time.time()
        for idx, pattern in enumerate(patterns):
            pattern_id = f"{agent_id}_{idx}"
            outcome = self._get_pattern_outcome_assessment(pattern_id)
            
            # Factor in outcome assessment
            outcome_factor = 1.2 if outcome == "success" else 0.8 if outcome == "failure" else 1.0
            
            recency = 1.0 / (1.0 + (current_time - pattern["timestamp"]) / 86400)  # Days factor
            pattern["utility"] = (
                pattern["success_rate"] * 0.4 * outcome_factor + 
                recency * 0.3 + 
                min(1.0, pattern["use_count"] / 10) * 0.3
            )
        
        # Sort by utility and keep only the top max_patterns
        patterns.sort(key=lambda p: p["utility"], reverse=True)
        self.patterns[agent_id] = patterns[:self.max_patterns]
        
        # Clean up pattern_outcomes for pruned patterns
        for idx in range(len(patterns), len(patterns) + self.max_patterns):
            pattern_id = f"{agent_id}_{idx}"
            if pattern_id in self.pattern_outcomes:
                del self.pattern_outcomes[pattern_id]
    
    def _calculate_state_similarity(self, state1: np.ndarray, state2: np.ndarray) -> float:
        """Calculate similarity between two state vectors."""
        if state1.shape != state2.shape:
            return 0.0
            
        # Calculate Euclidean distance, normalized by vector length
        distance = np.linalg.norm(state1 - state2)
        max_distance = np.linalg.norm(np.ones_like(state1) * 2)  # Assuming normalized [-1,1] range
        
        # Convert distance to similarity (1.0 = identical, 0.0 = completely different)
        similarity = 1.0 - min(1.0, distance / max_distance)
        return similarity
    
    def _calculate_context_similarity(self, context1: Dict[str, Any], 
                                    context2: Dict[str, Any]) -> float:
        """Calculate similarity between two context dictionaries."""
        if not context1 or not context2:
            return 1.0 if context1 == context2 else 0.0
            
        all_keys = set(context1.keys()) | set(context2.keys())
        total_similarity = 0.0
        comparison_keys = 0
        
        for key in all_keys:
            if key not in context1 or key not in context2:
                # Key missing in one context, contributes 0 similarity for this key
                comparison_keys += 1
                continue
                
            comparison_keys += 1
            val1 = context1[key]
            val2 = context2[key]
            similarity = 0.0
            
            # --- Start: Handle nearby_agents --- 
            if key == 'nearby_agents':
                if isinstance(val1, list) and isinstance(val2, list):
                    # Compare number of agents
                    len1 = len(val1)
                    len2 = len(val2)
                    count_similarity = 1.0 - abs(len1 - len2) / max(1, len1 + len2)
                    
                    # Compare average position if agents are present
                    pos_similarity = 0.0
                    if len1 > 0 and len2 > 0:
                        avg_pos1 = np.mean([a.get('position', (0,0)) for a in val1 if a.get('position') is not None], axis=0)
                        avg_pos2 = np.mean([a.get('position', (0,0)) for a in val2 if a.get('position') is not None], axis=0)
                        if not np.isnan(avg_pos1).any() and not np.isnan(avg_pos2).any():
                            dist = np.linalg.norm(avg_pos1 - avg_pos2)
                            # Normalize distance (e.g., max expected distance 500 units -> 0 similarity)
                            pos_similarity = max(0.0, 1.0 - dist / 500.0)
                    elif len1 == 0 and len2 == 0:
                        pos_similarity = 1.0 # Both empty is similar
                    
                    # Combine similarities (e.g., 50% count, 50% position)
                    similarity = 0.5 * count_similarity + 0.5 * pos_similarity
                else:
                    similarity = 0.0 # Incompatible types
            # --- End: Handle nearby_agents ---
            elif isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                # Numeric comparison (normalized difference)
                diff = abs(val1 - val2)
                range_val = max(abs(val1), abs(val2), 1) # Avoid division by zero
                similarity = max(0.0, 1.0 - diff / range_val)
            elif isinstance(val1, bool) and isinstance(val2, bool):
                similarity = 1.0 if val1 == val2 else 0.0
            elif isinstance(val1, str) and isinstance(val2, str):
                similarity = 1.0 if val1 == val2 else 0.0
            elif isinstance(val1, (list, tuple)) and isinstance(val2, (list, tuple)):
                # Simple list/tuple comparison (e.g., check overlap or length)
                # Avoid comparing potentially complex nested structures directly
                len1 = len(val1)
                len2 = len(val2)
                similarity = 1.0 - abs(len1 - len2) / max(1, len1 + len2)
            elif isinstance(val1, dict) and isinstance(val2, dict):
                # Simple dictionary comparison (e.g., key overlap)
                common_keys = len(set(val1.keys()) & set(val2.keys()))
                max_keys = max(len(val1), len(val2))
                similarity = common_keys / max_keys if max_keys > 0 else 1.0
            else:
                # Incompatible types
                similarity = 0.0
                
            total_similarity += similarity
        
        return total_similarity / max(1, comparison_keys)
    
    def _get_personality_weight(self, agent_id: str, trait: str) -> float:
        """Helper to get a personality trait value, handling missing system/agent."""
        if not self.personality_system:
            return 0.5 # Default neutral value if no system
        personality = self.personality_system.get_agent_personality(agent_id)
        if not personality:
            return 0.5 # Default neutral value if no personality profile
        # Assuming PersonalityTrait enum exists and trait is a valid member name string
        try:
             trait_enum = PersonalityTrait[trait.upper()]
             return personality.get_trait(trait_enum)
        except KeyError:
             self.logger.warning(f"Invalid trait '{trait}' requested in _get_personality_weight for agent {agent_id}")
             return 0.5
    
    def _adapt_pattern_for_target(self, pattern: Dict[str, Any], 
                                 target_agent_id: str) -> Dict[str, Any]:
        """Adapt a pattern for sharing with another agent based on personality."""
        # Create a copy of the pattern
        adapted_pattern = {
            "state": pattern["state"].copy(),
            "action": pattern["action"],
            "reward_history": pattern["reward_history"].copy(),
            "success_rate": pattern["success_rate"],
            "context": pattern["context"].copy(),
            "timestamp": time.time(),
            "use_count": 1  # Reset use count for the new agent
        }
        
        # Apply adaptation based on target's personality
        target_personality = self.personality_system.get_agent_personality(target_agent_id) if self.personality_system else None
        if target_personality:
            # Get relevant personality traits using get_trait
            conscientiousness = target_personality.get_trait(PersonalityTrait.CONSCIENTIOUSNESS)
            
            # More conscientious agents are more precise about state representations
            if conscientiousness > 0.7:
                # Less state smoothing
                pass  # Keep original state
            else:
                # Add some noise to state
                noise_scale = 0.1 * (1.0 - conscientiousness)
                adapted_pattern["state"] += np.random.normal(0, noise_scale, size=pattern["state"].shape)
                
            # Adjust success rate based on agreeableness
            agreeableness = target_personality.get_trait(PersonalityTrait.AGREEABLENESS)
            if agreeableness > 0.7:
                # More agreeable agents are more optimistic about patterns
                optimism_factor = 0.1 * (agreeableness - 0.7) / 0.3
                adapted_pattern["success_rate"] = min(1.0, adapted_pattern["success_rate"] + optimism_factor)
                
        return adapted_pattern
    
    def _is_duplicate_pattern(self, pattern1: Dict[str, Any], pattern2: Dict[str, Any]) -> bool:
        """Check if two patterns are essentially duplicates."""
        state_similarity = self._calculate_state_similarity(pattern1["state"], pattern2["state"])
        action_match = pattern1["action"] == pattern2["action"]
        
        return state_similarity > 0.95 and action_match 