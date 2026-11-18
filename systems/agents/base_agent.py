"""
Base agent implementation for AI Battle Arena.

This module defines the standard interfaces and base functionality for all agent types.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple, Optional, Union
import numpy as np
import json
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Abstract base class for all agent implementations.
    
    Defines the standard interface that all agent types must implement
    and provides common functionality for state processing, action selection,
    and learning mechanisms.
    """
    
    def __init__(self, name: str = None):
        """
        Initialize the base agent.
        
        Args:
            name: Optional agent name (defaults to class name)
        """
        self.name = name or self.__class__.__name__
        self.state_size = 0
        self.action_size = 5  # Default action space size
        self.angle = 0.0 # Initial angle/orientation
        self.training_mode = True
        self.episode_memory = []
        self.total_reward = 0
        self.metrics = {
            'wins': 0,
            'losses': 0,
            'kills': 0,
            'deaths': 0,
            'damage_dealt': 0,
            'damage_taken': 0,
            'survival_time': 0
        }
        
    def initialize(self, state_size: int, action_size: int = 5) -> None:
        """
        Initialize the agent with state and action dimensions.
        
        This method should be called before using the agent.
        
        Args:
            state_size: Dimension of the state vector
            action_size: Number of possible actions
        """
        self.state_size = state_size
        self.action_size = action_size
        
        # Call the agent-specific initialization
        self.initialize_agent(state_size, action_size)
    
    @abstractmethod
    def initialize_agent(self, state_size: int, action_size: int) -> None:
        """
        Initialize agent-specific components.
        
        Args:
            state_size: Dimension of the state vector
            action_size: Number of possible actions
        """
        pass
    
    @abstractmethod
    def get_action(self, state: np.ndarray) -> int:
        """
        Select an action based on the current state.
        
        Args:
            state: Current state observation vector
            
        Returns:
            Selected action index
        """
        pass
    
    @abstractmethod
    def learn(self, state: np.ndarray, action: int, reward: float, 
             next_state: np.ndarray, done: bool = False) -> None:
        """
        Update agent's knowledge from experience.
        
        Args:
            state: Current state observation
            action: Action taken
            reward: Reward received
            next_state: Next state observation
            done: Whether the episode is complete
        """
        pass
    
    def preprocess_state(self, state: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Preprocess the state before decision making.
        
        Args:
            state: Raw state vector
            
        Returns:
            Tuple containing:
                - processed_state (np.ndarray): Processed state vector
                - metadata (Dict[str, Any]): Empty dictionary by default
        """
        is_valid_output = True # Assume valid initially
        input_state_info = f"Input Type: {type(state)}"
        if isinstance(state, np.ndarray):
            input_state_info += f", Shape: {state.shape}"
        elif state is None:
             input_state_info += ", Content: None"

        processed_state = np.zeros(self.state_size) if self.state_size > 0 else np.array([])
        metadata = {}
        
        if state is None:
            is_valid_output = False
            logger.debug(f"{self.name} preprocess_state: Received None state. {input_state_info}. Outputting empty state, valid={is_valid_output}")
            return processed_state, is_valid_output # Return validity flag
            
        # Ensure state is a numpy array
        if not isinstance(state, np.ndarray):
            try:
                state = np.array(state, dtype=np.float32)
            except ValueError:
                 logger.warning(f"Agent {self.name}: Could not convert state of type {type(state)} to numpy array.")
                 is_valid_output = False
                 logger.debug(f"{self.name} preprocess_state: Conversion failed. {input_state_info}. Outputting empty state, valid={is_valid_output}")
                 return processed_state, is_valid_output # Return validity flag
            
        # Ensure correct dimensions (add batch dim if needed for consistency)
        if len(state.shape) == 1:
            processed_state_input = state.reshape(1, -1)
        else:
            processed_state_input = state
            
        # Ensure correct size
        if self.state_size > 0:
             current_size = processed_state_input.shape[1]
             if current_size != self.state_size:
                 # Pad or truncate as needed
                 if current_size < self.state_size:
                     padded = np.zeros((processed_state_input.shape[0], self.state_size))
                     padded[:, :current_size] = processed_state_input
                     processed_state = padded
                 else:
                     processed_state = processed_state_input[:, :self.state_size]
             else:
                  processed_state = processed_state_input
        else: # state_size is 0 or not set
             processed_state = processed_state_input # Return as is
                
        # Final check on output state size
        if processed_state.size == 0 and self.state_size > 0: # Only invalid if expected non-zero
             is_valid_output = False
        output_state_info = f"Output Shape: {processed_state.shape}, Valid: {is_valid_output}"
        logger.debug(f"{self.name} preprocess_state: {input_state_info} -> {output_state_info}")
        return processed_state, is_valid_output # Return validity flag
    
    def remember(self, state: np.ndarray, action: int, reward: float, 
                next_state: np.ndarray, done: bool) -> None:
        """
        Store experience in episode memory.
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Episode complete flag
        """
        if self.training_mode:
            self.episode_memory.append((state, action, reward, next_state, done))
            self.total_reward += reward
            
    def end_episode(self) -> Dict[str, Any]:
        """
        Finalize the current episode and return statistics.
        
        Returns:
            Dictionary of episode statistics
        """
        stats = {
            'total_reward': self.total_reward,
            'episode_length': len(self.episode_memory)
        }
        
        # Reset episode memory
        self.episode_memory = []
        self.total_reward = 0
        
        return stats
    
    def set_training_mode(self, training: bool) -> None:
        """
        Set whether the agent is in training mode.
        
        Args:
            training: True for training, False for evaluation
        """
        self.training_mode = training
    
    def save(self, directory: str = 'saved_models') -> str:
        """
        Save the agent's state to disk.
        
        Args:
            directory: Directory to save the agent
            
        Returns:
            Path to the saved agent file
        """
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"{self.name}.json")
        
        # Create serializable state dictionary
        state = self.get_serializable_state()
        
        # Add metadata
        state['agent_type'] = self.__class__.__name__
        state['state_size'] = self.state_size
        state['action_size'] = self.action_size
        state['metrics'] = self.metrics
        
        # Save to file
        with open(path, 'w') as f:
            json.dump(state, f)
            
        return path
    
    def load(self, path: str) -> bool:
        """
        Load the agent's state from disk.
        
        Args:
            path: Path to the saved agent file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(path, 'r') as f:
                state = json.load(f)
                
            # Verify agent type
            if state.get('agent_type') != self.__class__.__name__:
                print(f"Warning: Loading {state.get('agent_type')} into {self.__class__.__name__}")
                
            # Initialize with saved dimensions
            self.initialize(state.get('state_size', self.state_size),
                           state.get('action_size', self.action_size))
                
            # Load metrics
            if 'metrics' in state:
                self.metrics = state['metrics']
                
            # Load agent-specific state
            self.load_from_state(state)
            
            return True
        except Exception as e:
            print(f"Error loading agent: {str(e)}")
            return False
    
    def get_serializable_state(self) -> Dict[str, Any]:
        """
        Get a serializable representation of agent state.
        
        Returns:
            Dictionary with agent state
        """
        # Base implementation just returns basic info
        # Override in subclasses to add model weights, etc.
        return {
            'name': self.name
        }
    
    def load_from_state(self, state: Dict[str, Any]) -> None:
        """
        Load agent state from a dictionary.
        
        Args:
            state: Dictionary with agent state
        """
        # Override in subclasses to load model weights, etc.
        self.name = state.get('name', self.name)
    
    def update_metrics(self, metrics_update: Dict[str, Any]) -> None:
        """
        Update agent performance metrics.
        
        Args:
            metrics_update: Dictionary with metric updates
        """
        for key, value in metrics_update.items():
            if key in self.metrics:
                self.metrics[key] += value 