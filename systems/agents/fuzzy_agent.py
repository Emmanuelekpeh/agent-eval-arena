import numpy as np
import random
import math
from collections import deque
import logging
from typing import Dict, List, Tuple, Optional
from .base_agent import BaseAgent # Assuming BaseAgent is in base_agent.py

logger = logging.getLogger(__name__)


class FuzzyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="FuzzyAgent") # Initialize BaseAgent
        # Rules now need to align with the state vector indices defined in AgentSystem
        # Example assuming state vector layout:
        # state[1]: energy
        # state[7:9]: first enemy relative position (norm_rel_x, norm_rel_y)
        # state[32:72]: bullet features (10 bullets * 4 features)
        # Need to know exact indices for bullets
        self.rules = {
            # CORRECTED Indices:
            'close_to_enemy': lambda s: self._fuzzy_close(s[7:9]) if len(s) > 8 else 0.0,
            'low_energy': lambda s: self._fuzzy_low(s[1]) if len(s) > 1 else 0.0,
            # CORRECTED Indices and Slice End:
            'danger': lambda s: self._fuzzy_danger(s[32:72]) if len(s) > 71 else 0.0,
        }
        self.action_map = {
            'retreat': 2,     # Rotate left to retreat
            'attack': 4,      # Shoot
            'collect': 1,     # Move forward (e.g., towards low energy?)
            'explore': 3      # Rotate right to explore
        }
        self.confidence_threshold = 0.6  # Confidence threshold for action selection
        # Initialize performance memory using action IDs (integers)
        self.performance_memory = {action_id: deque(maxlen=100) for action_id in self.action_map.values()}

    def initialize_agent(self, state_size: int, action_size: int) -> None:
        """Initialize FuzzyAgent specific parameters if needed."""
        self.state_size = state_size
        self.action_size = action_size
        # No network weights to initialize for FuzzyAgent
        logger.info(f"{self.name} initialized with state_size={state_size}, action_size={action_size}")

    def get_action(self, state: np.ndarray) -> int:
        """Select an action based on fuzzy logic rules applied to the state vector."""
        # Preprocess the state and check validity
        processed_state, is_valid = self.preprocess_state(state)
        if not is_valid:
            logger.warning(f"{self.name} received invalid state after preprocessing. Defaulting to Explore.")
            return self.action_map['explore']
        state = processed_state # Use the processed state

        # Ensure state is a numpy array (should be after preprocessing)
        if not isinstance(state, np.ndarray):
             logger.error(f"{self.name} received non-numpy state *after* preprocessing: {type(state)}. This should not happen.")
             return self.action_map['explore'] # Fallback

        # Reshape if necessary (preprocess_state might return with batch dim)
        if len(state.shape) > 1:
             state = state.flatten() # Flatten if it has batch dimension

        # State size check/adjustment (might be redundant if preprocess handles it well)
        if len(state) != self.state_size:
             logger.warning(f"{self.name} state size mismatch after preprocessing: {len(state)} vs {self.state_size}. Attempting resize/pad.")
             if len(state) < self.state_size:
                 padded_state = np.zeros(self.state_size)
                 padded_state[:len(state)] = state
                 state = padded_state
             else:
                 state = state[:self.state_size]

        # Apply fuzzy rules
        actions = {
            'retreat': 0.0,
            'attack': 0.0,
            'collect': 0.0,
            'explore': 0.0
        }

        try:
            is_close = self.rules['close_to_enemy'](state)
            low_energy = self.rules['low_energy'](state)
            danger = self.rules['danger'](state)

            # Fuzzy rule evaluation
            actions['retreat'] = max(danger * 1.2, low_energy) # Prioritize danger, then low energy
            actions['attack'] = is_close * (1.0 - low_energy) * (1.0 - danger * 0.5) # Attack if close, not low energy, not too dangerous
            actions['collect'] = low_energy * (1.0 - danger) * 0.5 # Collect if low energy and not dangerous (lower priority)
            actions['explore'] = max(0.1, (1.0 - is_close) * (1.0 - danger) * (1.0 - low_energy)) # Default explore tendency

            # --- ADDED: Log fuzzy values and action weights ---
            logger.debug(f"{self.name} Fuzzy Values - Close: {is_close:.3f}, LowEnergy: {low_energy:.3f}, Danger: {danger:.3f}")
            logger.debug(f"{self.name} Action Weights - { {name: f'{weight:.3f}' for name, weight in actions.items()} }")
            # --- END REVERTED LOGS ---

        except IndexError as e:
            logger.error(f"{self.name} IndexError accessing state for fuzzy rules: {e}. State size: {len(state)}", exc_info=True)
            # Fallback to exploration if rules fail due to state index issues
            return self.action_map['explore']
        except Exception as e:
            logger.error(f"{self.name} Error applying fuzzy rules: {e}", exc_info=True)
            return self.action_map['explore']

        return self._defuzzify(actions)

    def _fuzzy_close(self, enemy_rel_pos: np.ndarray) -> float:
        """Fuzzify distance based on relative enemy position (norm_rel_x, norm_rel_y)."""
        if len(enemy_rel_pos) < 2 or np.all(enemy_rel_pos == 0): # Check if enemy exists in this slot
            return 0.0
        # Distance is calculated from normalized relative coordinates
        # This assumes state vector provides normalized values directly
        dist = math.sqrt(enemy_rel_pos[0]**2 + enemy_rel_pos[1]**2)
        # Normalize distance check based on typical range (0 to ~1.4 for diagonal)
        # Close if normalized distance < 0.25 (adjust threshold as needed)
        return max(0.0, 1.0 - dist / 0.25)

    def _fuzzy_low(self, energy_level: float) -> float:
        """Fuzzify low energy level (assuming normalized 0-1)."""
        # Consider energy low if below 30%
        return max(0.0, 1.0 - energy_level / 0.3)

    def _fuzzy_danger(self, bullet_features: np.ndarray) -> float:
        """Fuzzify danger level based on nearby bullet features."""
        # Assumes bullet_features is a flattened array of features for multiple bullets
        # E.g., [b1_rel_x, b1_rel_y, b1_dist, b1_hostile, b2_rel_x, ...]
        # Needs BULLET_FEATURES and MAX_NEARBY_BULLETS from AgentSystem
        num_bullets = len(bullet_features) // 4 # Assuming 4 features per bullet
        max_danger = 0.0
        for i in range(num_bullets):
            start_idx = i * 4
            if start_idx + 3 < len(bullet_features):
                rel_x = bullet_features[start_idx]
                rel_y = bullet_features[start_idx + 1]
                dist = bullet_features[start_idx + 2] # Assuming normalized distance
                is_hostile = bullet_features[start_idx + 3] # Assuming 1.0 if hostile

                # Check if this bullet slot is actually populated (dist > 0 or non-zero coords)
                if is_hostile > 0.5 and (rel_x != 0 or rel_y != 0 or dist > 0):
                    # Danger increases sharply if bullet is very close (normalized dist < 0.1)
                    current_danger = max(0.0, 1.0 - dist / 0.1)
                    max_danger = max(max_danger, current_danger)
        return max_danger

    def _defuzzify(self, actions: Dict[str, float]) -> int:
        """Convert fuzzy action strengths into a single discrete action ID."""
        # Select action with the highest confidence, provided it meets the threshold
        best_action_name = max(actions, key=actions.get)
        if actions[best_action_name] >= self.confidence_threshold:
            return self.action_map[best_action_name]
        else:
            # Fallback to exploration if no action has high confidence
            # Could also add randomness or use lowest confidence action
            return self.action_map['explore']

    def learn(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool = False) -> None:
        """Update performance memory based on reward for the taken action."""
        if action in self.performance_memory:
            self.performance_memory[action].append(reward)
            # Optional: Adjust confidence threshold based on average reward for the action
            # self._update_confidence(action)
        else:
             logger.warning(f"{self.name} received learn call for unknown action ID: {action}")

    def _update_confidence(self, action: int) -> None:
        """Adjust confidence threshold based on the performance of an action."""
        # Example: Increase confidence if action consistently yields positive rewards
        if len(self.performance_memory[action]) > 20: # Require some data
             avg_performance = np.mean(self.performance_memory[action])
             if avg_performance < -0.1: # If consistently negative
                 self.confidence_threshold = max(0.1, self.confidence_threshold - 0.02)
             elif avg_performance > 0.2: # If consistently positive
                 self.confidence_threshold = min(0.9, self.confidence_threshold + 0.02)

    # Optional: Method to get success rate for an action
    def _get_action_success_rate(self, action: int) -> float:
        if action not in self.performance_memory or not self.performance_memory[action]:
            return 0.0
        positive_rewards = sum(1 for r in self.performance_memory[action] if r > 0)
        return positive_rewards / len(self.performance_memory[action]) 