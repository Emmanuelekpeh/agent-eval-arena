import numpy as np
import random
import math
from collections import deque
import logging
from .base_agent import BaseAgent # Assuming BaseAgent is in base_agent.py

logger = logging.getLogger(__name__)

class ConvolutionalAgent(BaseAgent):
    def __init__(self):
        # Base parameters
        super().__init__(name="CNN-Agent") # Initialize BaseAgent
        self.grid_size = 8
        self.kernel_size = 3
        self.learning_rate = 0.01

        # CNN architecture
        self.in_channels = 1
        self.out_channels = 1

        # Calculate feature dimensions
        self.conv_output_size = self.grid_size - self.kernel_size + 1  # 6x6 output
        self.conv_features = self.conv_output_size * self.conv_output_size * self.out_channels
        # NOTE: total_features depends on the state size provided during initialization
        self.total_features = 0 # Will be set in initialize_agent

        # Initialize filters and weights with correct dimensions
        self.conv_filters = np.random.randn(
            self.kernel_size,
            self.kernel_size,
            self.in_channels,
            self.out_channels
        ) * 0.1

        self.weights = None  # Initialize weights on first input

        # Rest remains unchanged (personality should ideally be managed externally or via config)
        self.exploration = 0.2
        # Example personality - consider moving this logic
        self.personality = {
            'aggression': random.uniform(0.7, 1.2),
            'exploration': random.uniform(1.0, 1.5)
        }
        self.last_conv_output = None # Added to store last output

    def initialize_agent(self, state_size: int, action_size: int) -> None:
        """Initialize network weights based on state and action size."""
        self.state_size = state_size
        self.action_size = action_size
        # Assuming the state vector is concatenated with conv features
        self.total_features = self.state_size + self.conv_features
        # Ensure total_features doesn't exceed a practical limit if state_size is huge
        # Example limit (adjust as needed):
        self.total_features = min(self.total_features, 256)

        self.weights = np.random.randn(self.total_features, self.action_size) * 0.1
        logger.info(f"{self.name} initialized with state_size={state_size}, action_size={action_size}, total_features={self.total_features}")


    def get_action(self, state: np.ndarray) -> int:
        """Select an action based on the current state using CNN features."""
        if not isinstance(state, np.ndarray):
             logger.error(f"{self.name} received non-numpy state: {type(state)}")
             state = self.preprocess_state(state) # Attempt conversion

        if self.weights is None:
             logger.warning(f"{self.name} weights not initialized. Initializing with state size {len(state)}.")
             # Assuming default action size 5 if not initialized via initialize()
             self.initialize_agent(len(state), self.action_size or 5)

        if state.shape[0] != self.state_size:
            logger.warning(f"{self.name} received state with unexpected size {state.shape[0]}, expected {self.state_size}. Padding/truncating.")
            processed_state = np.zeros(self.state_size)
            copy_len = min(len(state), self.state_size)
            processed_state[:copy_len] = state[:copy_len]
            state = processed_state

        try:
            # 1. Convert state to grid
            grid = self._state_to_grid(state)

            # 2. Apply convolution
            conv_features = self._convolve(grid).flatten()

            # 3. Combine and truncate to match expected total_features
            combined = np.concatenate([state, conv_features])
            if len(combined) > self.total_features:
                combined = combined[:self.total_features]
            elif len(combined) < self.total_features:
                 # Pad if shorter (shouldn't happen with current logic, but safeguard)
                 padding = np.zeros(self.total_features - len(combined))
                 combined = np.concatenate([combined, padding])

            # 4. Get action values
            action_values = np.dot(combined, self.weights) # combined is 1D, weights is 2D -> result is 1D

            # 5. Apply behavior modifiers (example)
            if self.action_size > 1: action_values[1] *= (1.0 + self.exploration) # Encourage movement
            if self.action_size > 4: action_values[4] *= self.personality['aggression'] # Influence shooting

            return int(np.argmax(action_values))

        except Exception as e:
            logger.error(f"{self.name} Error in get_action: {e}", exc_info=True)
            return 0 # Default to IDLE on error

    def learn(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool = False) -> None:
        """Learn from experience using a simple gradient update."""
        if self.weights is None:
             logger.warning(f"{self.name} attempting to learn without initialized weights.")
             return # Cannot learn without weights

        if not isinstance(state, np.ndarray): state = self.preprocess_state(state)
        if state.shape[0] != self.state_size:
            logger.warning(f"{self.name} received state with unexpected size {state.shape[0]} during learning. Skipping.")
            return

        try:
            # 1. Get CNN features
            grid = self._state_to_grid(state)
            conv_features = self._convolve(grid).flatten()

            # 2. Combine features and truncate/pad
            combined = np.concatenate([state, conv_features])
            if len(combined) > self.total_features:
                combined = combined[:self.total_features]
            elif len(combined) < self.total_features:
                 padding = np.zeros(self.total_features - len(combined))
                 combined = np.concatenate([combined, padding])

            combined = combined.reshape(-1, 1) # Reshape for matrix multiplication (N, 1)

            # 3. Calculate a simple supervised-style update based on reward
            # Create a target vector: assume current action was good if reward > 0
            # This is a very basic learning rule, not proper RL like Q-learning
            targets = np.dot(combined.T, self.weights) # Get current Q-values (1, action_size)
            target_value = reward # Simplistic target: reward itself

            # Update the Q-value for the chosen action towards the target_value
            q_value_current = targets[0, action]
            targets[0, action] = q_value_current + self.learning_rate * (target_value - q_value_current)

            # Calculate error for backpropagation (difference between target and prediction)
            error = targets - np.dot(combined.T, self.weights) # (1, action_size)

            # Calculate weight update (gradient)
            # Gradient = input_activations (combined^T) * error
            gradient = combined @ error # (total_features, 1) @ (1, action_size) -> (total_features, action_size)

            # 4. Apply weight update
            self.weights += self.learning_rate * gradient

        except Exception as e:
            logger.error(f"{self.name} Learning error: {e}", exc_info=True)

    def _state_to_grid(self, state: np.ndarray) -> np.ndarray:
        """Convert the 1D state vector into a 2D grid representation."""
        # This implementation assumes specific indices in the state vector correspond
        # to player position, enemy positions, bullet positions etc.
        # It needs to be adapted based on the actual STATE_VECTOR_SIZE and feature layout
        # defined in agent_system.py
        grid = np.zeros((self.grid_size, self.grid_size, self.in_channels))

        # Example: Map self position (assuming normalized coordinates at indices 0, 1)
        if len(state) > 1:
            px = min(max(0, int(state[0] * self.grid_size)), self.grid_size-1)
            py = min(max(0, int(state[1] * self.grid_size)), self.grid_size-1)
            grid[px, py, 0] = 1.0 # Player marker

        # Example: Map first enemy (assuming normalized coords at indices 5, 6)
        # This needs to align with STATE_VECTOR definition in AgentSystem
        # Let's assume agent features start after SELF_FEATURES(4) + ENV_FEATURES(2) = 6
        agent_feature_start = 6
        agent_features_count = 5 # AGENT_FEATURES in AgentSystem
        enemy_rel_x_idx = agent_feature_start + 0
        enemy_rel_y_idx = agent_feature_start + 1

        if len(state) > enemy_rel_y_idx:
             # Convert relative normalized coords back approximately
             # This is crude, needs actual positions if available
             if state[enemy_rel_x_idx] != 0 or state[enemy_rel_y_idx] != 0: # Check if enemy exists in slot
                 # Placeholder: Just mark a spot based on relative position
                 # A better approach would involve passing absolute positions in state if needed for grid
                 ex_approx = px + int(state[enemy_rel_x_idx] * self.grid_size / 2) # Scaled relative
                 ey_approx = py + int(state[enemy_rel_y_idx] * self.grid_size / 2)
                 ex = min(max(0, ex_approx), self.grid_size-1)
                 ey = min(max(0, ey_approx), self.grid_size-1)
                 grid[ex, ey, 0] = -1.0 # Enemy marker

        # TODO: Map other entities (bullets, pickups, hazards) based on state vector layout
        # ...

        return grid


    def _convolve(self, grid: np.ndarray) -> np.ndarray:
        """Apply convolution operation to the grid."""
        try:
            # Ensure grid has correct shape (H, W, C)
            if grid.ndim == 2:
                 grid = grid.reshape(self.grid_size, self.grid_size, self.in_channels)
            elif grid.shape != (self.grid_size, self.grid_size, self.in_channels):
                 raise ValueError(f"Invalid grid shape for convolution: {grid.shape}")

            output_h = self.grid_size - self.kernel_size + 1
            output_w = self.grid_size - self.kernel_size + 1
            output = np.zeros((output_h, output_w, self.out_channels))

            for k in range(self.out_channels): # Iterate over output channels
                 for i in range(output_h): # Height
                     for j in range(output_w): # Width
                         # Extract the window from the input grid
                         window = grid[i:i+self.kernel_size, j:j+self.kernel_size, :]
                         # Apply the filter for the current output channel k
                         current_filter = self.conv_filters[:, :, :, k]
                         # Perform element-wise multiplication and sum
                         output[i, j, k] = np.sum(window * current_filter)

            # Apply activation function (e.g., ReLU) - optional
            output = np.maximum(0, output) # ReLU activation

            self.last_conv_output = output
            return output # Return the feature map

        except Exception as e:
            logger.error(f"Convolution error: {e}", exc_info=True)
            # Return zero features on error
            output_h = self.grid_size - self.kernel_size + 1
            output_w = self.grid_size - self.kernel_size + 1
            return np.zeros((output_h, output_w, self.out_channels))

    # Need to implement learn method if not inheriting from a base class that does
    # def learn(self, state, action, reward, next_state, done=False):
    #     # Basic learning logic, potentially supervised based on reward
    #     pass # Replace with actual learning mechanism 