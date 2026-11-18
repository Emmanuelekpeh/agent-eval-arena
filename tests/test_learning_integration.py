import unittest
from unittest.mock import MagicMock, patch, ANY
import numpy as np
import os
import tempfile
import sys # Added for path manipulation

# Ensure the project root is in the path
# Adjust the number of os.path.dirname calls based on the test file location relative to project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Assume these imports are possible based on project structure
from systems.learning.learning_integration import LearningIntegration, EvolutionManager
from systems.agents.base_agent import BaseAgent
# Use the actual constants if available, otherwise define placeholders
try:
    from systems.agents.agent_system import STATE_VECTOR_SIZE, ACTION_IDLE
except ImportError:
    print("Warning: Using placeholder values for STATE_VECTOR_SIZE and ACTION_IDLE")
    STATE_VECTOR_SIZE = 10 # Placeholder
    ACTION_IDLE = 0 # Placeholder

class TestLearningIntegration(unittest.TestCase):

    def setUp(self):
        """Set up common mocks for tests."""
        self.mock_env = MagicMock()
        self.mock_personality_system = MagicMock()
        self.mock_pattern_system_cls = MagicMock()
        self.mock_strategy_system_cls = MagicMock()
        self.mock_visualizer_cls = MagicMock()

        # Patch the dependencies within the learning_integration module
        self.patcher_pattern = patch('systems.learning.learning_integration.PatternRecognitionSystem', self.mock_pattern_system_cls)
        self.patcher_strategy = patch('systems.learning.learning_integration.StrategyAdaptationSystem', self.mock_strategy_system_cls)
        self.patcher_visualizer = patch('systems.learning.learning_integration.LearningVisualizer', self.mock_visualizer_cls)

        self.mock_pattern_system_instance = self.patcher_pattern.start()()
        self.mock_strategy_system_instance = self.patcher_strategy.start()()
        self.mock_visualizer_instance = self.patcher_visualizer.start()()

        self.addCleanup(self.patcher_pattern.stop)
        self.addCleanup(self.patcher_strategy.stop)
        self.addCleanup(self.patcher_visualizer.stop)

    def test_initialization_no_evolution(self):
        """Test initialization without the EvolutionManager (population size 0)."""
        learning_integration = LearningIntegration(
            env=self.mock_env,
            personality_system=self.mock_personality_system,
            evo_population_size=0 # Explicitly disable evolution
        )

        self.assertIs(learning_integration.env, self.mock_env)
        self.assertIs(learning_integration.personality_system, self.mock_personality_system)
        self.mock_pattern_system_cls.assert_called_once_with() # Check if constructor was called
        self.mock_strategy_system_cls.assert_called_once_with()
        self.mock_visualizer_cls.assert_called_once_with()
        self.assertIsNone(learning_integration.evo_manager, "EvolutionManager should not be initialized when population size is 0")
        self.assertIsInstance(learning_integration.registered_agents, dict)
        self.assertEqual(learning_integration.evo_population_size, 0)

    @patch('systems.learning.learning_integration.EvolutionManager')
    def test_initialization_with_evolution(self, MockEvolutionManager):
        """Test initialization enabling the EvolutionManager."""
        pop_size = 50
        learning_integration = LearningIntegration(
            env=self.mock_env,
            personality_system=self.mock_personality_system,
            evo_population_size=pop_size,
            evo_mutation_rate=0.05,
            evo_crossover_rate=0.6,
            evo_elite_fraction=0.05
        )

        self.assertIs(learning_integration.env, self.mock_env)
        self.assertEqual(learning_integration.evo_population_size, pop_size)

        # Check if EvolutionManager was initialized with correct parameters
        MockEvolutionManager.assert_called_once_with(
            population_size=pop_size,
            state_size=STATE_VECTOR_SIZE, # Assuming this constant is correct
            action_size=5, # As hardcoded in LearningIntegration.__init__
            mutation_rate=0.05,
            crossover_rate=0.6,
            elite_fraction=0.05
        )
        self.assertIsNotNone(learning_integration.evo_manager)
        self.assertIsInstance(learning_integration.evo_manager, MagicMock) # Assert it's a mock instance

# Add other test methods for T11 below...

if __name__ == '__main__':
    # Add basic logging setup for tests if needed
    # import logging
    # logging.basicConfig(level=logging.DEBUG)
    unittest.main()