"""
Agent Factory module for AI Battle Arena.

This module provides factory methods to easily create different agent types.
"""

from typing import Dict, Any, Type, Optional
import inspect # Add inspect import

# Import Base Agent and agents defined in other files
from systems.agents.base_agent import BaseAgent
from systems.agents.perceptron_agent import PerceptronAgent, PerceptronAgent1, PerceptronAgent2 # Assuming these are in perceptron_agent.py
from systems.agents.mlp_agent import MLPAgent, MLPAgent1, MLPAgent2, GradientMLPAgent # Assuming these are in mlp_agent.py

# Import the newly separated agent classes
from .convolutional_agent import ConvolutionalAgent
from .fuzzy_agent import FuzzyAgent
from .evolutionary_agent import EvolutionaryAgent


# Registry of available agent types
AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {
    # Perceptron agents
    "perceptron": PerceptronAgent,
    "perceptron-aggressive": PerceptronAgent1,
    "perceptron-conservative": PerceptronAgent2,

    # MLP agents
    "mlp": MLPAgent,
    "mlp-fast": MLPAgent1,
    "mlp-deep": MLPAgent2,
    "gradient-mlp": GradientMLPAgent,

    # Specialized agents (now imported from their own files)
    "cnn": ConvolutionalAgent,
    "fuzzy": FuzzyAgent,
    "evolutionary": EvolutionaryAgent,

    # Legacy names for compatibility (point to appropriate classes)
    "BasicAgent": PerceptronAgent, # Example: map Basic to Perceptron
    "NeuralAgent": MLPAgent, # Example: map Neural to MLP
    "EvolutionaryAgent": EvolutionaryAgent, # Keep specific mapping
    "FuzzyAgent": FuzzyAgent, # Keep specific mapping
    "RuleBasedAgent": FuzzyAgent, # Example: map RuleBased to Fuzzy
    "ConvolutionalAgent": ConvolutionalAgent, # Keep specific mapping

    # Add new agent types here as they are implemented
}

def create_agent(agent_type: str, name: str = None, config: Optional[Dict[str, Any]] = None) -> BaseAgent:
    """
    Create an agent of the specified type with given configuration.

    Args:
        agent_type: Type of agent to create (from AGENT_REGISTRY)
        name: Optional name for the agent
        config: Optional configuration parameters for the agent

    Returns:
        Instantiated agent

    Raises:
        ValueError: If agent_type is not recognized
    """
    if agent_type not in AGENT_REGISTRY:
        available_types = ", ".join(AGENT_REGISTRY.keys())
        raise ValueError(f"Unknown agent type: {agent_type}. Available types: {available_types}")

    # Get the agent class
    agent_class = AGENT_REGISTRY[agent_type]

    # Create with default config if none provided
    if config is None:
        config = {}

    # Extract name if provided, otherwise use default
    if name is None:
        name = config.pop("name", f"{agent_type}-agent")

    # Create the agent instance conditionally
    try:
        # Check the signature of the __init__ method
        init_signature = inspect.signature(agent_class.__init__)
        if 'name' in init_signature.parameters:
            agent = agent_class(name=name)
        else:
            # Instantiate without name, then try to set it if attribute exists
            agent = agent_class()
            if hasattr(agent, 'name'):
                try:
                    setattr(agent, 'name', name)
                except AttributeError: # Handle potential read-only properties
                    pass
    except TypeError as e:
        # Fallback or handle cases where __init__ might be a built-in or unusual
        # For simplicity, try basic instantiation if inspection fails
        try:
             agent = agent_class()
             if hasattr(agent, 'name'):
                 setattr(agent, 'name', name)
        except Exception as final_e:
             raise ValueError(f"Failed to instantiate agent {agent_type}: {final_e}") from e

    # Apply any remaining config parameters (e.g., learning_rate, hidden_layers)
    # This requires agents to handle these via setters or have them in constructor
    # Example: Applying learning_rate if it exists in config and agent has the attribute
    if 'learning_rate' in config and hasattr(agent, 'learning_rate'):
        agent.learning_rate = config['learning_rate']
    if 'hidden_layers' in config and hasattr(agent, 'hidden_layer_sizes'):
        # Assuming the attribute is hidden_layer_sizes based on MLPAgent
        setattr(agent, 'hidden_layer_sizes', config['hidden_layers'])
        # Potentially re-initialize network if hidden layers change structure
        if hasattr(agent, '_init_network'):
             agent._init_network() # Or a similar method if exists

    # Apply any other config parameters dynamically
    for key, value in config.items():
         # Avoid overwriting name if already set
         if key == "name": continue
         if hasattr(agent, key):
             try:
                 setattr(agent, key, value)
             except AttributeError:
                 # Handle cases where attribute might be read-only
                 pass

    return agent

def get_available_agent_types() -> Dict[str, Type[BaseAgent]]:
    """
    Get a dictionary of all available agent types.

    Returns:
        Dictionary mapping agent type names to their classes
    """
    return AGENT_REGISTRY.copy() 