import unittest
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from systems.agents.agent_system import * # Removed wildcard import
from systems.agents.mlp_agent import MLPAgent1, MLPAgent2
from systems.agents.perceptron_agent import PerceptronAgent1, PerceptronAgent2
from game_with_ai import PerceptronAgent3
from systems.agents.convolutional_agent import ConvolutionalAgent # Added import
from systems.agents.evolutionary_agent import EvolutionaryAgent # Added import
from systems.agents.fuzzy_agent import FuzzyAgent # Added import

class TestAgents(unittest.TestCase):
    def setUp(self):
        self.state_size = 30
        self.test_state = np.random.rand(self.state_size)
        
    def test_mlp_agents(self):
        agents = [MLPAgent1(), MLPAgent2()]
        for agent in agents:
            if hasattr(agent, 'initialize_agent'):
                 agent.initialize_agent(self.state_size, 5)
            action = agent.get_action(self.test_state)
            self.assertIn(action, range(5))
            
    def test_perceptron_agents(self):
        agents = [PerceptronAgent1(), PerceptronAgent2(), PerceptronAgent3()]
        for agent in agents:
            if hasattr(agent, 'initialize_agent'):
                 agent.initialize_agent(self.state_size, 5)
            action = agent.get_action(self.test_state)
            self.assertIn(action, range(5))
            
    def test_specialized_agents(self):
        agents = [ConvolutionalAgent(), EvolutionaryAgent(), FuzzyAgent()]
        for agent in agents:
            if hasattr(agent, 'initialize_agent'):
                agent.initialize_agent(self.state_size, 5)
            action = agent.get_action(self.test_state)
            self.assertIn(action, range(5))

if __name__ == '__main__':
    unittest.main()
