import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from systems.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class EvolutionaryAgent(BaseAgent):
    """Agent whose behavior is determined by a weight matrix, 
       intended to be managed by an external evolutionary algorithm."""
    def __init__(self, name: str = "EvoAgent"):
        super().__init__(name=name)
        self.weights: Optional[np.ndarray] = None # Weights set externally
        # Removed ES-specific attributes
        
        # Action mapping indices (assuming standard actions 0-4)
        self.action_idle_idx = 0
        self.action_move_idx = 1
        self.action_rotate_left_idx = 2
        self.action_rotate_right_idx = 3
        self.action_shoot_idx = 4

    def initialize_agent(self, state_size: int, action_size: int) -> None:
        """Initialize the agent structure, potentially with random weights as a default."""
        self.state_size = state_size
        self.action_size = action_size
        # Initialize weights - can be overwritten by set_weights
        if self.weights is None: # Initialize only if not already set
            scale = np.sqrt(2.0 / (state_size + action_size)) if state_size + action_size > 0 else 0.1
            self.weights = np.random.randn(self.state_size, self.action_size) * scale
            logger.info(f"{self.name} initialized with state_size={state_size}, action_size={action_size}, and random weights.")
        else:
            logger.info(f"{self.name} already had weights set. State/Action sizes confirmed: state_size={state_size}, action_size={action_size}.")
            # Optional: Add check if self.weights.shape matches (state_size, action_size)

    def set_weights(self, weights: np.ndarray) -> None:
        """Set the agent's weight matrix externally."""
        if weights.shape == (self.state_size, self.action_size):
            self.weights = weights
            logger.debug(f"{self.name} weights updated externally.")
        else:
            logger.error(f"{self.name} received weights with incorrect shape. Expected {(self.state_size, self.action_size)}, got {weights.shape}. Weights not updated.")

    def get_action(self, state: np.ndarray) -> int:
        """Select an action based on the current weights and state."""
        # Log input state type and content for debugging
        state_info = f"Type: {type(state)}"
        if isinstance(state, np.ndarray):
            state_info += f", Shape: {state.shape}, Content snippet: {state[:5]}..."
        elif state is None:
            state_info += ", Content: None"
        else:
            state_info += f", Content: {str(state)[:100]}..." # Truncate long strings
        logger.debug(f"{self.name} get_action received state - {state_info}")

        if self.weights is None:
            logger.error(f"{self.name} weights not initialized. Cannot get action.")
            return self.action_idle_idx # Default to IDLE

        # Process the state using the base class method
        processed_state, is_valid = self.preprocess_state(state)

        if not is_valid or processed_state.size == 0:
            logger.error(f"{self.name} received invalid or empty state after preprocessing.")
            return self.action_idle_idx # Default to IDLE on error
            
        try:
            # Calculate action preferences using dot product
            state_row = processed_state.flatten().reshape(1, -1) # Ensure 2D for dot product
            # Ensure state_row columns match weight rows
            if state_row.shape[1] != self.weights.shape[0]:
                logger.error(f"{self.name} state dimension ({state_row.shape[1]}) does not match weight dimension ({self.weights.shape[0]})")
                return self.action_idle_idx
                
            output = np.dot(state_row, self.weights).flatten() # Output shape: (action_size,)

            # No internal mutation/noise added here
            
            # Return the action with the highest score
            return int(np.argmax(output))

        except Exception as e:
            logger.error(f"{self.name} Error in get_action: {e}", exc_info=True)
            logger.error(f"State shape after flatten: {state_row.shape if 'state_row' in locals() else 'N/A'}, Weights shape: {self.weights.shape}")
            return self.action_idle_idx # Default to IDLE on error

    def learn(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool = False) -> None:
        """Passive learn method. Evolution is handled externally."""
        # This agent's weights are updated by an external process (e.g., GeneticAlgorithm)
        # This method could potentially log data if needed for external fitness calculation
        # logger.debug(f"{self.name} received learn call: reward={reward}, done={done}")
        pass # No internal learning mechanism

    # Removed _evolve_step and _adapt_mutation_strength methods

    def get_serializable_state(self) -> Dict[str, Any]:
        """Return state for saving, including weights."""
        state = super().get_serializable_state()
        state.update({
            'weights': self.weights.tolist() if self.weights is not None else None,
            # Removed ES-specific parameters from state
        })
        return state

    def load_from_state(self, state: Dict[str, Any]) -> None:
        """Load state from dictionary, primarily the weights."""
        super().load_from_state(state)
        weights_list = state.get('weights')
        loaded_weights = np.array(weights_list) if weights_list is not None else None

        # Need state_size and action_size from base class state before validating/setting weights
        expected_shape = (self.state_size, self.action_size)
        
        if loaded_weights is not None:
            if loaded_weights.shape == expected_shape:
                self.weights = loaded_weights
                logger.info(f"{self.name} weights loaded successfully.")
            else:
                logger.warning(f"{self.name}: Loaded weights shape {loaded_weights.shape} does not match expected {expected_shape}. Reinitializing weights.")
                # Reinitialize weights if shape mismatch
                self.initialize_agent(self.state_size, self.action_size) 
        else:
             # If weights are None in the state, ensure they are None or reinitialized
             if self.state_size > 0 and self.action_size > 0:
                 logger.warning(f"{self.name}: Weights were None in loaded state. Reinitializing weights.")
                 self.initialize_agent(self.state_size, self.action_size)
             else:
                 self.weights = None # Set to None if state/action size not yet known

        # Removed loading of ES-specific parameters

