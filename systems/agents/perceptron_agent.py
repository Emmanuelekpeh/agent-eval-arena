import logging

# Set up logging for this module
logger = logging.getLogger(__name__)

"""
Perceptron agent implementation for AI Battle Arena.

This module provides a simple perceptron-based agent that learns through direct experience.
"""

import numpy as np
from typing import Dict, List, Any, Tuple, Optional

from systems.agents.base_agent import BaseAgent

class PerceptronAgent(BaseAgent):
    """
    Perceptron-based agent implementation.
    
    Uses a simple single-layer neural network to learn state-action mappings.
    Can optionally use suggestions from a learning integration system.
    """
    
    def __init__(self, name: str = "Perceptron-Agent", learning_rate: float = 0.05, suggestion_confidence_threshold: float = 0.7):
        """
        Initialize the perceptron agent.
        
        Args:
            name: Agent name
            learning_rate: Speed of weight updates
            suggestion_confidence_threshold: Minimum confidence required to accept an action suggestion.
        """
        super().__init__(name)
        
        # Network parameters
        self.weights = None
        self.bias = None
        self.learning_rate = learning_rate
        self.suggestion_confidence_threshold = suggestion_confidence_threshold
        
        # Exploration parameters
        self.exploration_rate = 1.0
        self.exploration_decay = 0.995
        self.exploration_min = 0.01
        
        # Performance tracking
        self.recent_rewards = []
        self.reward_history_size = 100
        self.training_mode = True # Set to False for evaluation
        self.learning_system = None # ADDED: Initialize learning_system attribute
    
    def initialize_agent(self, state_size: int, action_size: int) -> None:
        """
        Initialize perceptron with state and action dimensions.
        
        Args:
            state_size: Dimension of the state vector
            action_size: Number of possible actions
        """
        self.state_size = state_size
        self.action_size = action_size
        
        # Initialize weights with small random values
        self.weights = np.random.randn(state_size, action_size) * 0.1
        self.bias = np.zeros(action_size)
        
        # --- ADDED: Get reference to LearningIntegration system ---
        try:
            # Attempt to get the LearningIntegration system from the system manager
            # Assumes system_manager is accessible or passed appropriately.
            # If PerceptronAgent doesn't have direct access, this might need adjustment.
            from systems.core.system_manager import system_manager # Import locally if needed
            self.learning_system = system_manager.get_system("LearningIntegration")
            if self.learning_system:
                logger.info(f"{self.name} found and linked LearningIntegration system.")
            else:
                logger.info(f"{self.name} did not find LearningIntegration system.")
        except ImportError:
            logger.warning(f"{self.name}: Could not import system_manager to find LearningIntegration.")
            self.learning_system = None
        except Exception as e:
            logger.error(f"{self.name}: Error getting LearningIntegration system: {e}")
            self.learning_system = None
        # --- END ADDED ---
        
        logger.info(f"{self.name} initialized with state_size={state_size}, action_size={action_size}")
    
    def get_action(self, state: np.ndarray) -> int:
        """
        Select action using perceptron prediction, potentially overridden by learning system suggestion.
        
        Args:
            state: Current state vector (or dict)
            
        Returns:
            Selected action index
        """
        suggested_action_id = None
        suggestion_confidence = 0.0
        
        try:
            # 1. Get suggestion from Learning System (pass original state)
            if self.learning_system:
                # Pass context if needed, e.g., {'agent_pos': self.position} if available
                # context = {} 
                suggestion_result = self.learning_system.suggest_action(self.name, state) # Pass raw state
                
                if suggestion_result:
                    suggestion, confidence = suggestion_result
                    suggestion_confidence = confidence if confidence is not None else 0.0
                    
                    # Handle dictionary vs simple ID suggestion
                    if isinstance(suggestion, dict):
                        suggested_action_id = suggestion.get('action')
                        # We might store target_id here if needed later:
                        # suggested_target_id = suggestion.get('target_id') 
                    elif isinstance(suggestion, (int, np.integer)):
                        suggested_action_id = suggestion
                    else:
                         logger.warning(f"{self.name} received unexpected suggestion format: {type(suggestion)}")
            
            # 2. Preprocess state for internal calculation
            processed_state, is_valid = self.preprocess_state(state)
            
            if not is_valid or processed_state.size == 0:
                 logger.warning(f"{self.name} received invalid/empty state after preprocessing. Defaulting to IDLE.")
                 return 0 # Return idle if state processing failed
                
            # 3. Exploration Check
            if self.training_mode and np.random.random() < self.exploration_rate:
                logger.debug(f"{self.name} exploring: choosing random action.")
                return np.random.randint(0, self.action_size)
            
            # 4. Calculate Perceptron's Action
            # Ensure weights are initialized
            if self.weights is None or self.bias is None:
                 logger.error(f"{self.name} weights or bias not initialized in get_action. Defaulting to IDLE.")
                 return 0 
                 
            # Reshape processed_state if it came out flat but weights expect 2D
            if processed_state.ndim == 1 and self.weights.shape[0] == processed_state.shape[0]:
                 # Should already be handled by preprocess_state returning (1, size)
                 pass 
            elif processed_state.shape[1] != self.weights.shape[0]:
                  logger.error(f"{self.name} shape mismatch: processed_state {processed_state.shape} vs weights {self.weights.shape}. Defaulting to IDLE.")
                  return 0
                  
            activations = np.dot(processed_state, self.weights) + self.bias
            # Activation result should be (1, action_size), argmax works on the last axis
            perceptron_action = np.argmax(activations[0]) 
            
            # 5. Decide: Use Suggestion or Perceptron Action?
            if suggested_action_id is not None and suggestion_confidence >= self.suggestion_confidence_threshold:
                logger.debug(f"{self.name} using suggested action {suggested_action_id} (Confidence: {suggestion_confidence:.2f} >= {self.suggestion_confidence_threshold:.2f})")
                return suggested_action_id
            else:
                if suggested_action_id is not None:
                     logger.debug(f"{self.name} using perceptron action {perceptron_action}. Suggestion {suggested_action_id} ignored (Confidence: {suggestion_confidence:.2f} < {self.suggestion_confidence_threshold:.2f})")
                else:
                     logger.debug(f"{self.name} using perceptron action {perceptron_action}. No suggestion received.")
                return perceptron_action
            
        except Exception as e:
            logger.error(f"{self.name} error in get_action: {str(e)}", exc_info=True)
            return 0 # Default to IDLE on error
    
    def learn(self, state: np.ndarray, action: int, reward: float, 
             next_state: np.ndarray, done: bool = False) -> None:
        """
        Update perceptron weights based on experience.
        
        Uses a simple version of Q-learning with single-step updates.
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Whether the episode is complete
        """
        if not self.training_mode:
            return
            
        try:
            # Track rewards
            self.recent_rewards.append(reward)
            if len(self.recent_rewards) > self.reward_history_size:
                self.recent_rewards.pop(0)
            
            # Preprocess states - Correctly unpack tuples
            processed_state, is_valid_state = self.preprocess_state(state)
            processed_next_state, is_valid_next_state = self.preprocess_state(next_state)
            
            # Ensure processed states are valid
            if not is_valid_state or processed_state.size == 0 or \
               not is_valid_next_state or processed_next_state.size == 0:
                 logger.warning(f"{self.name} received invalid/empty state(s) in learn. Skipping update.")
                 return # Cannot learn if states are invalid
            
            # Current Q-value prediction
            current_prediction = np.dot(processed_state, self.weights) + self.bias
            
            # Target calculation
            target = np.copy(current_prediction)
            if done:
                target[action] = reward
            else:
                next_prediction = np.dot(processed_next_state, self.weights) + self.bias
                target[action] = reward + 0.95 * np.max(next_prediction)
            
            # Calculate error
            error = target - current_prediction
            
            # Update weights for the chosen action
            delta = self.learning_rate * error[action] * processed_state.flatten() # Flatten state for element-wise multiply
            # Ensure delta has the correct shape for broadcasting if weights are (state_size, action_size)
            if delta.shape[0] == self.weights.shape[0]:
                 self.weights[:, action] += delta
            else:
                 logger.error(f"Shape mismatch during Perceptron learn: delta {delta.shape}, weights {self.weights.shape}")
            
            self.bias[action] += self.learning_rate * error[action]
            
            # Decay exploration rate
            self.exploration_rate = max(
                self.exploration_min, 
                self.exploration_rate * self.exploration_decay
            )
            
        except Exception as e:
            print(f"PerceptronAgent error in learn: {str(e)}")
    
    def get_serializable_state(self) -> Dict[str, Any]:
        """
        Get agent state for serialization.
        
        Returns:
            Dictionary with serializable agent state
        """
        state = super().get_serializable_state()
        
        # Add perceptron parameters
        state.update({
            'learning_rate': self.learning_rate,
            'exploration_rate': self.exploration_rate,
            'exploration_decay': self.exploration_decay,
            'exploration_min': self.exploration_min,
            'weights': self.weights.tolist() if self.weights is not None else None,
            'bias': self.bias.tolist() if self.bias is not None else None,
            'recent_rewards': self.recent_rewards
        })
        
        return state
    
    def load_from_state(self, state: Dict[str, Any]) -> None:
        """
        Load agent state from serialized data.
        
        Args:
            state: Dictionary with agent state
        """
        super().load_from_state(state)
        
        # Load perceptron parameters
        self.learning_rate = state.get('learning_rate', self.learning_rate)
        self.exploration_rate = state.get('exploration_rate', self.exploration_rate)
        self.exploration_decay = state.get('exploration_decay', self.exploration_decay)
        self.exploration_min = state.get('exploration_min', self.exploration_min)
        self.recent_rewards = state.get('recent_rewards', [])
        
        # Load weights and bias if available
        if 'weights' in state and state['weights']:
            self.weights = np.array(state['weights'])
            
        if 'bias' in state and state['bias']:
            self.bias = np.array(state['bias'])
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for this agent.
        
        Returns:
            Dictionary with performance metrics
        """
        metrics = super().get_performance_metrics()
        
        # Add perceptron-specific metrics
        if self.recent_rewards:
            metrics.update({
                'average_reward': sum(self.recent_rewards) / len(self.recent_rewards),
                'max_reward': max(self.recent_rewards),
                'min_reward': min(self.recent_rewards),
                'reward_variance': np.var(self.recent_rewards) if len(self.recent_rewards) > 1 else 0
            })
        
        return metrics
    
    def preprocess_state(self, state: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Preprocess state for perceptron input.
        
        Args:
            state: Raw state data
            
        Returns:
            Tuple of (processed_state, is_valid)
        """
        processed_state, is_valid = super().preprocess_state(state)
        
        # If the base preprocessing failed, return immediately
        if not is_valid:
            return processed_state, False
            
        # Flatten state if needed
        if len(processed_state.shape) > 1:
            processed_state = processed_state.flatten()
            
        # Return the processed state and the validity flag from base
        return np.array([processed_state]), is_valid


class PerceptronAgent1(PerceptronAgent):
    """
    Aggressive variant of the perceptron agent with faster learning.
    
    This agent learns quickly but may oscillate more.
    """
    
    def __init__(self, name: str = "Perceptron-Agent-1"):
        """Initialize with high learning rate and exploration."""
        super().__init__(name, learning_rate=0.1)
        
        # Higher exploration to try more actions
        self.exploration_rate = 0.3
        self.exploration_decay = 0.99  # Slower decay
        self.exploration_min = 0.05    # Higher minimum exploration
        
    def initialize_agent(self, state_size: int, action_size: int) -> None:
        """Initialize with more aggressive starting weights."""
        super().initialize_agent(state_size, action_size)
        
        # Initialize with larger weights for more decisive initial behavior
        self.weights = np.random.randn(state_size, action_size) * 0.2
        

class PerceptronAgent2(PerceptronAgent):
    """
    Conservative variant of the perceptron agent with careful learning.
    
    This agent learns more slowly but is more stable.
    """
    
    def __init__(self, name: str = "Perceptron-Agent-2"):
        """Initialize with low learning rate and exploration."""
        super().__init__(name, learning_rate=0.02)
        
        # Lower exploration for more exploitation
        self.exploration_rate = 0.15
        self.exploration_decay = 0.998  # Faster decay
        self.exploration_min = 0.01     # Lower minimum exploration
        
        # Increase reward history for more stable performance tracking
        self.reward_history_size = 200
        
    def learn(self, state: np.ndarray, action: int, reward: float,
             next_state: np.ndarray, done: bool = False) -> None:
        """
        Modified learning method with gradient clipping for stability.
        """
        if not self.training_mode:
            return
            
        try:
            # Track rewards
            self.recent_rewards.append(reward)
            if len(self.recent_rewards) > self.reward_history_size:
                self.recent_rewards.pop(0)
            
            # Preprocess states - Correctly unpack tuples
            processed_state, is_valid_state = self.preprocess_state(state)
            processed_next_state, is_valid_next_state = self.preprocess_state(next_state)
            
            # Ensure processed states are valid
            if not is_valid_state or processed_state.size == 0 or \
               not is_valid_next_state or processed_next_state.size == 0:
                 logger.warning(f"{self.name} received invalid/empty state(s) in learn. Skipping update.")
                 return # Cannot learn if states are invalid
            
            # Current Q-value prediction
            current_prediction = np.dot(processed_state, self.weights) + self.bias
            
            # Target calculation with higher discount factor for long-term rewards
            target = np.copy(current_prediction)
            if done:
                target[action] = reward
            else:
                next_prediction = np.dot(processed_next_state, self.weights) + self.bias
                target[action] = reward + 0.98 * np.max(next_prediction)  # Higher discount
            
            # Calculate error
            error = target - current_prediction
            
            # Update weights with gradient clipping
            delta = self.learning_rate * error[action] * processed_state.flatten() # Flatten state
            
            # Clip gradients to prevent explosive updates
            max_grad_norm = 1.0
            delta_norm = np.linalg.norm(delta)
            if delta_norm > max_grad_norm:
                delta = delta * (max_grad_norm / delta_norm)
            
            # Apply update
            if delta.shape[0] == self.weights.shape[0]:
                 self.weights[:, action] += delta
            else:
                 logger.error(f"Shape mismatch during Perceptron2 learn: delta {delta.shape}, weights {self.weights.shape}")
                 
            self.bias[action] += self.learning_rate * error[action]
            
            # Decay exploration rate
            self.exploration_rate = max(
                self.exploration_min, 
                self.exploration_rate * self.exploration_decay
            )
            
        except Exception as e:
            print(f"PerceptronAgent2 error in learn: {str(e)}") 