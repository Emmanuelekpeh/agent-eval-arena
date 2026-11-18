"""
Multi-Layer Perceptron agent implementations for AI Battle Arena.

This module provides MLP-based agent implementations with varying architectures.
"""

import numpy as np
from typing import Dict, List, Any, Tuple, Optional, Union
import json
import random
from collections import deque
import logging

from systems.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class SimpleExperienceMemory:
    """Simple experience replay memory for testing the MLPAgent."""
    
    def __init__(self, capacity=10000):
        """Initialize memory with given capacity."""
        self.memory = deque(maxlen=capacity)
        self.capacity = capacity
    
    def add(self, experience):
        """Add experience to memory."""
        self.memory.append(experience)
    
    def sample(self, batch_size):
        """Sample a batch of experiences from memory."""
        batch_size = min(batch_size, len(self.memory))
        return random.sample(list(self.memory), batch_size)
    
    def __len__(self):
        """Return the current size of memory."""
        return len(self.memory)
    
    def get_params(self):
        """Get parameters for serialization."""
        return {'capacity': self.capacity}
    
    def set_params(self, params):
        """Set parameters from serialization."""
        self.capacity = params.get('capacity', self.capacity)
        self.memory = deque(maxlen=self.capacity)

class PrioritizedExperienceMemory:
    """Prioritized experience replay memory for MLPAgent."""
    
    def __init__(self, capacity=10000, alpha=0.6, beta=0.4):
        """
        Initialize prioritized memory.
        
        Args:
            capacity: Maximum capacity of the memory
            alpha: Priority exponent (0 = uniform, 1 = full prioritization)
            beta: Importance sampling correction factor
        """
        self.memory = []
        self.priorities = []
        self.capacity = capacity
        self.alpha = alpha
        self.beta = beta
        self.position = 0
        self.max_priority = 1.0
    
    def add(self, experience):
        """Add experience with maximum priority."""
        if len(self.memory) < self.capacity:
            self.memory.append(experience)
            self.priorities.append(self.max_priority)
        else:
            # Replace old experiences using circular buffer approach
            self.memory[self.position] = experience
            self.priorities[self.position] = self.max_priority
            
        self.position = (self.position + 1) % self.capacity
    
    def sample(self, batch_size):
        """
        Sample a batch of experiences based on priorities.
        
        Returns:
            Tuple of (experiences, indices, importance weights)
        """
        if len(self.memory) == 0:
            return [], [], []
        
        # Convert to numpy arrays for vectorized operations
        priorities = np.array(self.priorities)
        probabilities = priorities**self.alpha / sum(priorities**self.alpha)
        
        # Sample indices based on priorities
        indices = np.random.choice(
            len(self.memory), 
            min(batch_size, len(self.memory)), 
            replace=False, 
            p=probabilities
        )
        
        # Get experiences
        experiences = [self.memory[idx] for idx in indices]
        
        # Calculate importance sampling weights
        weights = (len(self.memory) * probabilities[indices])**(-self.beta)
        weights /= weights.max()  # Normalize
        
        return experiences, indices, weights
    
    def update_priorities(self, indices, priorities):
        """Update priorities for specific experiences."""
        for idx, priority in zip(indices, priorities):
            # Ensure priority is positive and update max priority
            priority = max(1e-6, priority)
            self.max_priority = max(self.max_priority, priority)
            
            # Update the priority at the specified index
            if 0 <= idx < len(self.priorities):
                self.priorities[idx] = priority
    
    def __len__(self):
        """Return current size of memory."""
        return len(self.memory)
    
    def get_params(self):
        """Get parameters for serialization."""
        return {
            'capacity': self.capacity,
            'alpha': self.alpha,
            'beta': self.beta,
            'max_priority': self.max_priority
        }
    
    def set_params(self, params):
        """Set parameters from serialization."""
        self.capacity = params.get('capacity', self.capacity)
        self.alpha = params.get('alpha', self.alpha)
        self.beta = params.get('beta', self.beta)
        self.max_priority = params.get('max_priority', self.max_priority)

class MLPAgent(BaseAgent):
    """
    Base Multi-Layer Perceptron agent implementation.
    
    Uses a neural network with multiple layers to process state information
    and select actions.
    """
    
    def __init__(self, input_size=None, output_size=None, hidden_layer_sizes=(64, 64),
                 learning_rate=0.001, discount_factor=0.99, exploration_rate=1.0,
                 exploration_min=0.01, exploration_decay=0.995, memory_size=10000,
                 batch_size=64, use_prioritized_replay=False, use_adam=True,
                 adam_beta1=0.9, adam_beta2=0.999, adam_epsilon=1e-8,
                 personality_traits=None, name=None):
        """
        Initialize the MLP Agent.
        
        Args:
            input_size: Size of the input state vector
            output_size: Number of possible actions
            hidden_layer_sizes: Tuple with sizes of hidden layers
            learning_rate: Learning rate for optimization
            discount_factor: Discount factor for future rewards (gamma)
            exploration_rate: Initial exploration rate (epsilon)
            exploration_min: Minimum exploration rate
            exploration_decay: Rate at which to decay exploration
            memory_size: Maximum size of experience replay memory
            batch_size: Batch size for training
            use_prioritized_replay: Whether to use prioritized experience replay
            use_adam: Whether to use Adam optimizer instead of SGD
            adam_beta1: Beta1 parameter for Adam optimizer
            adam_beta2: Beta2 parameter for Adam optimizer
            adam_epsilon: Epsilon parameter for Adam optimizer
            personality_traits: Dictionary of personality traits
            name: Optional name for the agent
        """
        # Initialize the base agent
        super().__init__(name=name)
        
        # Store state and action sizes (can be None initially)
        self.state_size = input_size
        self.action_size = output_size
        
        # Store network and learning parameters
        self.input_size = input_size
        self.output_size = output_size
        self.hidden_layer_sizes = hidden_layer_sizes
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.exploration_min = exploration_min
        self.exploration_decay = exploration_decay
        self.memory_size = memory_size
        self.batch_size = batch_size
        self.use_prioritized_replay = use_prioritized_replay
        
        # Store personality traits
        self.personality_traits = personality_traits or {}
        
        # Adam optimizer parameters
        self.use_adam = use_adam
        self.adam_beta1 = adam_beta1
        self.adam_beta2 = adam_beta2
        self.adam_epsilon = adam_epsilon
        
        # Initialize memory with prioritized replay if needed
        if use_prioritized_replay:
            self.memory = PrioritizedExperienceMemory(memory_size, alpha=0.6, beta=0.4)
        else:
            self.memory = SimpleExperienceMemory(memory_size)
        
        # DO NOT Initialize the neural network here - Moved to initialize_agent
        # self._init_network() 
        self.weights = None # Initialize weights/biases to None
        self.biases = None
        
        # Training metrics
        self.training_loss_history = []
        self.total_training_steps = 0
    
    def initialize_agent(self, state_size, action_size):
        """
        Initialize agent-specific components.
        
        Args:
            state_size: Dimension of the state vector
            action_size: Number of possible actions
        """
        # Update sizes if they were provided
        self.input_size = state_size
        self.output_size = action_size
        self.state_size = state_size
        self.action_size = action_size
        
        # Re-initialize the network with the new dimensions
        self._init_network()
    
    def select_action(self, state):
        """
        Select an action using epsilon-greedy policy.
        
        Args:
            state: Current state of the environment
            
        Returns:
            Selected action index
        """
        # Exploration: random action
        if np.random.random() < self.exploration_rate:
            return np.random.randint(0, self.output_size)
        
        # Exploitation: best action according to Q-values
        q_values, _ = self._forward(state)
        return np.argmax(q_values[0])
    
    def remember_experience(self, state, action, reward, next_state, done):
        """
        Store experience in memory for replay.
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Whether episode ended
        """
        experience = (state, action, reward, next_state, done)
        
        if self.use_prioritized_replay:
            # Calculate initial priority based on TD error
            q_values, _ = self._forward(state)
            next_q_values, _ = self._forward(next_state)
            max_next_q = np.max(next_q_values[0]) if not done else 0
            td_error = abs(reward + self.discount_factor * max_next_q - q_values[0, action])
            
            # Add experience with priority
            self.memory.add_experience(experience, priority=td_error)
        else:
            # Add to standard experience replay memory
            self.memory.append(experience)
            if len(self.memory) > self.memory_size:
                self.memory.pop(0)  # Remove oldest experience when full
    
    def learn(self, state, action, reward, next_state, done=False):
        """
        Update agent's knowledge from a single experience.
        
        Args:
            state: Current state observation
            action: Action taken
            reward: Reward received
            next_state: Next state observation
            done: Whether the episode is complete
        
        Returns:
            Loss value if training occurred, None otherwise
        """
        # --- ADDED: Log reward received ---
        logger.debug(f"MLPAgent {self.name}: learn called - Action: {action}, Reward: {reward:.4f}, Done: {done}")
        # --- END ADDED ---
        
        # Add experience to memory
        self.memory.add((state, action, reward, next_state, done))
        
        # Only train if we have enough samples
        if len(self.memory) >= self.batch_size:
            return self.learn_from_batch()
        
        return None

    def learn_from_batch(self):
        """
        Learn from experiences in memory using gradient-based learning.
        
        Returns:
            Average loss for the batch or None if not enough samples
        """
        # Check if enough experiences are available
        if len(self.memory) < self.batch_size:
            return None
        
        # Sample batch of experiences
        if self.use_prioritized_replay:
            batch, indices, weights = self.memory.sample(self.batch_size)
            states, actions, rewards, next_states, dones = zip(*batch)
            weights = np.array(weights)
        else:
            batch = self.memory.sample(self.batch_size)
            states, actions, rewards, next_states, dones = zip(*batch)
            weights = np.ones(self.batch_size)  # Equal weights when not using prioritized replay
        
        # Train on batch using gradient-based learning
        loss = self._train_on_batch(states, actions, rewards, next_states, dones)
        
        # Update priorities if using prioritized replay
        if self.use_prioritized_replay:
            # Calculate TD errors for priority updates
            current_q, _ = self._forward(np.array(states))
            next_q, _ = self._forward(np.array(next_states))
            
            td_errors = []
            for i in range(self.batch_size):
                if dones[i]:
                    td_error = abs(rewards[i] - current_q[i, actions[i]])
                else:
                    td_error = abs(rewards[i] + self.discount_factor * np.max(next_q[i]) - current_q[i, actions[i]])
                td_errors.append(td_error)
            
            # Update priorities based on TD errors
            self.memory.update_priorities(indices, td_errors)
        
        # Decay exploration rate
        self.exploration_rate = max(self.exploration_min, 
                                   self.exploration_rate * self.exploration_decay)
        
        # Record training metrics
        self.training_loss_history.append(loss)
        self.total_training_steps += 1
        
        return loss
    
    def update(self, state, action, reward, next_state, done):
        """Stores experience and triggers learning from batch."""
        # Store experience in memory
        experience_tuple = (state, action, reward, next_state, done)
        self.memory.add(experience_tuple)

        # Learn from a batch of experiences if enough are available
        if len(self.memory) >= self.batch_size:
            self.learn_from_batch()

        # Update exploration rate
        if self.exploration_rate > self.exploration_min:
            self.exploration_rate *= self.exploration_decay

    def _forward_pass(self, state: np.ndarray) -> List[np.ndarray]:
        """
        Perform forward pass through the network.
        
        Args:
            state: Input state vector
            
        Returns:
            List of activations for each layer
        """
        activations = [state]
        
        # Forward through hidden layers (ReLU activation)
        for i in range(len(self.weights) - 1):
            z = np.dot(activations[-1], self.weights[i]) + self.biases[i]
            a = np.maximum(0, z)  # ReLU activation
            activations.append(a)
        
        # Output layer (linear activation)
        z = np.dot(activations[-1], self.weights[-1]) + self.biases[-1]
        activations.append(z)
        
        return activations
    
    def _init_network(self):
        """
        Initialize the neural network with Xavier/Glorot weight initialization.
        Creates appropriate sizes for weights and biases based on the architecture.
        """
        # Build full architecture including input and output layer
        layer_sizes = [self.input_size] + list(self.hidden_layer_sizes) + [self.output_size]
        
        # Initialize weights and biases with Xavier/Glorot initialization for better gradient flow
        self.weights = []
        self.biases = []
        
        for i in range(len(layer_sizes) - 1):
            # Xavier/Glorot initialization: scale is determined by input and output dimensions
            scale = np.sqrt(2.0 / (layer_sizes[i] + layer_sizes[i+1]))
            self.weights.append(np.random.randn(layer_sizes[i], layer_sizes[i+1]) * scale)
            self.biases.append(np.zeros(layer_sizes[i+1]))
        
        # Initialize Adam optimizer parameters if used
        if self.use_adam:
            self.adam_m = [np.zeros_like(w) for w in self.weights]
            self.adam_v = [np.zeros_like(w) for w in self.weights]
            self.adam_t = 0
        
        # Initialize metrics tracking
        self.training_loss_history = []
    
    def _forward(self, state, return_activations=True):
        """
        Forward pass through the neural network. Can handle batch or single state.
        
        Args:
            state: Input state or batch of states as array
            return_activations: Whether to return activations (needed for backprop)
        
        Returns:
            Q-values for each action and activations if return_activations is True
        """
        # Ensure state is 2D: if single state, add batch dimension
        if state.ndim == 1:
            state = state.reshape(1, -1)
        
        # Forward propagation through all layers
        activations = [state]  # List to store all layer activations including input
        
        for i in range(len(self.weights)):
            # Linear transformation: Z = X*W + b
            z = np.dot(activations[-1], self.weights[i]) + self.biases[i]
            
            # Apply ReLU activation to all hidden layers but not the output layer
            if i < len(self.weights) - 1:
                a = np.maximum(0, z)  # ReLU activation
            else:
                a = z  # Linear activation for output layer
            
            activations.append(a)
        
        # Return Q-values and activations if needed
        if return_activations:
            return activations[-1], activations
        else:
            return activations[-1]
    
    def _train_on_batch(self, states, actions, rewards, next_states, dones):
        """
        Train the neural network on a batch of experiences using backpropagation.
        Implements gradient-based learning for efficient updates.
        
        Args:
            states: Batch of states
            actions: Batch of actions taken
            rewards: Batch of rewards received
            next_states: Batch of next states
            dones: Batch of done flags (True if episode ended)
        
        Returns:
            Loss value for the batch
        """
        # Convert inputs to numpy arrays
        states = np.array(states)
        next_states = np.array(next_states)
        rewards = np.array(rewards)
        actions = np.array(actions)
        dones = np.array(dones, dtype=np.float32)
        
        # Forward pass for current states
        current_q_values, activations = self._forward(states)
        
        # Forward pass for next states
        next_q_values = self._forward(next_states, return_activations=False)
        
        # Calculate target Q-values using the Bellman equation
        target_q_values = current_q_values.copy()
        
        for i in range(len(states)):
            # For terminal states, target is just the reward
            if dones[i]:
                target_q_values[i, actions[i]] = rewards[i]
            else:
                # For non-terminal states, use bootstrapped estimate
                target_q_values[i, actions[i]] = rewards[i] + self.discount_factor * np.max(next_q_values[i])
        
        # Compute loss (Mean Squared Error)
        loss = np.mean(np.square(target_q_values - current_q_values))
        
        # Backward pass (backpropagation)
        # Initialize gradient for output layer
        dA = 2.0 * (current_q_values - target_q_values) / len(states)
        
        # Backpropagate through layers
        dW = []  # Weight gradients
        dB = []  # Bias gradients
        
        for layer_idx in reversed(range(len(self.weights))):
            # Current layer's activation (input to this layer)
            A_prev = activations[layer_idx]
            
            # Compute gradients for weights and biases
            dW_layer = np.dot(A_prev.T, dA)
            dB_layer = np.sum(dA, axis=0)
            
            # Store gradients
            dW.insert(0, dW_layer)
            dB.insert(0, dB_layer)
            
            # Propagate error to previous layer, only if not at input layer
            if layer_idx > 0:
                dZ = np.dot(dA, self.weights[layer_idx].T)
                # Apply ReLU derivative: gradient is 0 where activation was <= 0
                dA = dZ * (activations[layer_idx] > 0)
        
        # Apply gradients with optimization method
        if self.use_adam:
            # Adam optimization update
            self.adam_t += 1
            
            for i in range(len(self.weights)):
                # Update biased first moment estimate
                self.adam_m[i] = self.adam_beta1 * self.adam_m[i] + (1 - self.adam_beta1) * dW[i]
                # Update biased second raw moment estimate
                self.adam_v[i] = self.adam_beta2 * self.adam_v[i] + (1 - self.adam_beta2) * np.square(dW[i])
                
                # Compute bias-corrected first moment estimate
                m_corrected = self.adam_m[i] / (1 - self.adam_beta1 ** self.adam_t)
                # Compute bias-corrected second raw moment estimate
                v_corrected = self.adam_v[i] / (1 - self.adam_beta2 ** self.adam_t)
                
                # Update weights
                self.weights[i] -= self.learning_rate * m_corrected / (np.sqrt(v_corrected) + self.adam_epsilon)
                # Update biases (simpler update rule)
                self.biases[i] -= self.learning_rate * dB[i]
        else:
            # Standard gradient descent update
            for i in range(len(self.weights)):
                self.weights[i] -= self.learning_rate * dW[i]
                self.biases[i] -= self.learning_rate * dB[i]
        
        return loss
    
    def get_serializable_state(self) -> Dict[str, Any]:
        """
        Get agent state for serialization.
        
        Returns:
            Dictionary with serializable agent state
        """
        state = super().get_serializable_state()
        
        # Add MLP parameters
        state.update({
            'hidden_layers': self.hidden_layer_sizes,
            'learning_rate': self.learning_rate,
            'discount_factor': self.discount_factor,
            'exploration_rate': self.exploration_rate,
            'exploration_decay': self.exploration_decay,
            'exploration_min': self.exploration_min,
            'weights': [w.tolist() for w in self.weights] if self.weights else None,
            'biases': [b.tolist() for b in self.biases] if self.biases else None,
            'use_adam': self.use_adam,
            'beta1': self.adam_beta1,
            'beta2': self.adam_beta2,
            'training_iterations': self.training_iterations
        })
        
        if self.use_adam:
            state.update({
                'adam_m': [m.tolist() for m in self.adam_m] if self.adam_m else None,
                'adam_v': [v.tolist() for v in self.adam_v] if self.adam_v else None,
                'adam_t': self.adam_t
            })
        
        return state
    
    def load_from_state(self, state: Dict[str, Any]) -> None:
        """
        Load agent state from serialized data.
        
        Args:
            state: Dictionary with agent state
        """
        super().load_from_state(state)
        
        # Load MLP parameters
        self.hidden_layer_sizes = state.get('hidden_layers', self.hidden_layer_sizes)
        self.learning_rate = state.get('learning_rate', self.learning_rate)
        self.discount_factor = state.get('discount_factor', self.discount_factor)
        self.exploration_rate = state.get('exploration_rate', self.exploration_rate)
        self.exploration_decay = state.get('exploration_decay', self.exploration_decay)
        self.exploration_min = state.get('exploration_min', self.exploration_min)
        self.use_adam = state.get('use_adam', self.use_adam)
        self.adam_beta1 = state.get('beta1', self.adam_beta1)
        self.adam_beta2 = state.get('beta2', self.adam_beta2)
        self.training_iterations = state.get('training_iterations', self.training_iterations)
        
        # Load weights and biases if available
        if 'weights' in state and state['weights']:
            self.weights = [np.array(w) for w in state['weights']]
            
        if 'biases' in state and state['biases']:
            self.biases = [np.array(b) for b in state['biases']]
        
        # Load Adam parameters if available and using Adam
        if self.use_adam:
            if 'adam_m' in state and state['adam_m']:
                self.adam_m = [np.array(m) for m in state['adam_m']]
            
            if 'adam_v' in state and state['adam_v']:
                self.adam_v = [np.array(v) for v in state['adam_v']]
                
            self.adam_t = state.get('adam_t', 0)

    def save(self, file_path):
        """
        Save agent state to file.
        
        Args:
            file_path: Path to save the agent state
        """
        state = {
            'weights': [w.tolist() for w in self.weights],
            'biases': [b.tolist() for b in self.biases],
            'exploration_rate': self.exploration_rate,
            'input_size': self.input_size,
            'output_size': self.output_size,
            'hidden_layer_sizes': self.hidden_layer_sizes,
            'learning_rate': self.learning_rate,
            'discount_factor': self.discount_factor,
            'adam_params': {
                'beta1': self.adam_beta1,
                'beta2': self.adam_beta2,
                'epsilon': self.adam_epsilon,
                't': self.adam_t
            } if self.use_adam else None
        }
        
        with open(file_path, 'w') as f:
            json.dump(state, f)

    def load(self, file_path):
        """
        Load agent state from file.
        
        Args:
            file_path: Path to load the agent state from
        """
        with open(file_path, 'r') as f:
            state = json.load(f)
        
        # Load weights and biases
        self.weights = [np.array(w) for w in state['weights']]
        self.biases = [np.array(b) for b in state['biases']]
        
        # Load other parameters
        self.exploration_rate = state['exploration_rate']
        self.input_size = state['input_size']
        self.output_size = state['output_size']
        self.hidden_layer_sizes = state['hidden_layer_sizes']
        self.learning_rate = state['learning_rate']
        self.discount_factor = state['discount_factor']
        
        # Load Adam parameters if applicable
        if self.use_adam and 'adam_params' in state and state['adam_params']:
            self.adam_beta1 = state['adam_params']['beta1']
            self.adam_beta2 = state['adam_params']['beta2']
            self.adam_epsilon = state['adam_params']['epsilon']
            self.adam_t = state['adam_params']['t']

    def predict(self, state):
        """
        Predict Q-values for all actions given a state.
        
        Args:
            state: The current state
            
        Returns:
            Array of Q-values for each action
        """
        # Forward pass through network (without returning activations)
        q_values = self._forward(state, return_activations=False)
        return q_values

    def act(self, state):
        """
        Select an action using epsilon-greedy policy.
        
        Args:
            state: The current state
            
        Returns:
            Selected action index
        """
        # With probability epsilon, select random action (exploration)
        if np.random.random() < self.exploration_rate:
            return np.random.randint(self.output_size)
        
        # Otherwise, select best action based on predicted Q-values (exploitation)
        q_values = self.predict(state)
        
        # Log Q-values for the first agent of this type for debugging
        if self.name.startswith("BasicAgent-") or self.name.startswith("NeuralAgent-"):
            # Log only once per few steps for brevity for a specific agent (e.g., the first one found)
            if not hasattr(self, '_logged_q_values_agent') or self._logged_q_values_agent == self.name:
                if not hasattr(self, '_log_q_step_counter'):
                    self._log_q_step_counter = 0
                
                if self._log_q_step_counter % 50 == 0: # Log every 50 steps for this agent
                    q_values_formatted = {self.action_map_rev.get(i, f"UnknownAction({i})"): f"{v:.3f}" for i, v in enumerate(q_values[0].cpu().numpy())}
                    logger.debug(f"{self.name} Q-Values: {q_values_formatted}, Exploration Rate: {self.exploration_rate:.3f}")
                    self._logged_q_values_agent = self.name # Remember which agent we logged last time
                self._log_q_step_counter += 1
            elif self._logged_q_values_agent != self.name and not hasattr(self, '_logged_q_values_agent'):
                # If we haven't logged any agent yet, log the first Basic/Neural one we find
                self._log_q_step_counter = 0
                q_values_formatted = {self.action_map_rev.get(i, f"UnknownAction({i})"): f"{v:.3f}" for i, v in enumerate(q_values[0].cpu().numpy())}
                logger.debug(f"{self.name} Q-Values: {q_values_formatted}, Exploration Rate: {self.exploration_rate:.3f}")
                self._logged_q_values_agent = self.name
                self._log_q_step_counter += 1
        
        # Handle batch vs single prediction
        if q_values.ndim > 1:
            return np.argmax(q_values[0])
        else:
            return np.argmax(q_values)

    def get_state(self):
        """
        Return a serializable dictionary representing the agent's state.
        
        Returns:
            Dict containing all necessary information to reconstruct the agent's state
        """
        state = {
            'input_size': self.input_size,
            'output_size': self.output_size,
            'hidden_layer_sizes': self.hidden_layer_sizes,
            'learning_rate': self.learning_rate,
            'discount_factor': self.discount_factor,
            'exploration_rate': self.exploration_rate,
            'exploration_min': self.exploration_min,
            'exploration_decay': self.exploration_decay,
            'batch_size': self.batch_size,
            'use_prioritized_replay': self.use_prioritized_replay,
            'use_adam': self.use_adam,
            'weights': [w.tolist() for w in self.weights],
            'biases': [b.tolist() for b in self.biases],
            'training_loss_history': self.training_loss_history,
            'total_training_steps': self.total_training_steps
        }
        
        if self.use_adam:
            state.update({
                'adam_m': [m.tolist() for m in self.adam_m],
                'adam_v': [v.tolist() for v in self.adam_v],
                'adam_t': self.adam_t,
                'adam_beta1': self.adam_beta1,
                'adam_beta2': self.adam_beta2,
                'adam_epsilon': self.adam_epsilon
            })
        
        # We don't serialize the entire memory, just its parameters
        if hasattr(self.memory, 'get_params'):
            state['memory_params'] = self.memory.get_params()
        
        return state

    def load_state(self, state):
        """
        Load the agent's state from a serialized dictionary.
        
        Args:
            state: Dict containing the agent's state information
        """
        # Load basic hyperparameters
        self.input_size = state.get('input_size', self.input_size)
        self.output_size = state.get('output_size', self.output_size)
        self.hidden_layer_sizes = state.get('hidden_layer_sizes', self.hidden_layer_sizes)
        self.learning_rate = state.get('learning_rate', self.learning_rate)
        self.discount_factor = state.get('discount_factor', self.discount_factor)
        self.exploration_rate = state.get('exploration_rate', self.exploration_rate)
        self.exploration_min = state.get('exploration_min', self.exploration_min)
        self.exploration_decay = state.get('exploration_decay', self.exploration_decay)
        self.batch_size = state.get('batch_size', self.batch_size)
        self.use_prioritized_replay = state.get('use_prioritized_replay', self.use_prioritized_replay)
        self.use_adam = state.get('use_adam', self.use_adam)
        
        # Load weights and biases if present
        if 'weights' in state and 'biases' in state:
            self.weights = [np.array(w) for w in state['weights']]
            self.biases = [np.array(b) for b in state['biases']]
        
        # Load Adam parameters if available and using Adam
        if self.use_adam:
            if 'adam_m' in state and state['adam_m']:
                self.adam_m = [np.array(m) for m in state['adam_m']]
            
            if 'adam_v' in state and state['adam_v']:
                self.adam_v = [np.array(v) for v in state['adam_v']]
                
            self.adam_t = state.get('adam_t', 0)
            self.adam_beta1 = state.get('adam_beta1', 0.9)
            self.adam_beta2 = state.get('adam_beta2', 0.999)
            self.adam_epsilon = state.get('adam_epsilon', 1e-8)
        
        # Load training metrics
        self.training_loss_history = state.get('training_loss_history', [])
        self.total_training_steps = state.get('total_training_steps', 0)
        
        # Initialize/reset memory with parameters if available
        if 'memory_params' in state and hasattr(self.memory, 'set_params'):
            self.memory.set_params(state['memory_params'])

    def get_action(self, state):
        """
        Get action based on current state.
        Alias for act method.
        """
        # Preprocess state first
        processed_state, is_valid = self.preprocess_state(state)
        
        # Handle cases where preprocessing might fail or return invalid data
        if not is_valid:
             # Use print instead of logger
             print(f"{self.name}: Invalid state received by get_action after preprocessing. Defaulting to action 0.")
             return 0 # Example: return default action (e.g., IDLE)
             
        # Select action based on the processed state
        return self.act(processed_state)

class MLPAgent1(MLPAgent):
    """First variant of MLP agent with smaller network and faster learning"""
    
    def __init__(self, name: str = "MLPAgent1"):
        super().__init__(name, hidden_layer_sizes=[32, 16])
        self.learning_rate = 0.02
        self.exploration_rate = 0.15

class MLPAgent2(MLPAgent):
    """Second variant of MLP agent with deeper network and more cautious learning"""
    
    def __init__(self, name: str = "MLPAgent2"):
        super().__init__(name, hidden_layer_sizes=[64, 32, 16])
        self.learning_rate = 0.008
        self.exploration_decay = 0.998
        self.discount_factor = 0.98

# Add a new agent with optimized configuration for gradient-based learning
class GradientMLPAgent(MLPAgent):
    """MLP agent optimized for gradient-based learning with Adam optimizer"""
    
    def __init__(self, name: str = "GradientMLPAgent"):
        super().__init__(name, hidden_layer_sizes=[64, 64, 32])
        self.learning_rate = 0.001  # Lower learning rate for Adam
        self.use_adam = True
        self.beta1 = 0.9
        self.beta2 = 0.999
        self.batch_size = 64  # Larger batch size for more stable gradients
        self.min_replay_size = 1000
        self.training_iterations = 10  # More training iterations for better convergence 