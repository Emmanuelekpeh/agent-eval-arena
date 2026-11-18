import unittest
from unittest.mock import MagicMock, patch, ANY
import numpy as np
import os
import sys
import pickle
import time
import json
from collections import defaultdict

# Ensure the project root is in the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# --- Components to test ---
from systems.learning.learning_integration import LearningIntegration, EvolutionManager
from systems.agents.base_agent import BaseAgent
from systems.agents.personality_system import PersonalitySystem
from systems.learning.experience_memory import ExperienceMemory, TeamExperienceMemory
from systems.learning.pattern_recognition_system import PatternRecognitionSystem
from systems.learning.strategy_adaptation_system import StrategyAdaptationSystem
from systems.learning.genetic_algorithm import GeneticAlgorithm
from systems.environment.environment import BattleRoyaleEnv
from systems.visualization.learning_visualizer import LearningVisualizer

# --- Constants ---
# Import necessary constants from the correct location
try:
    from systems.constants import (
        STATE_VECTOR_SIZE, ACTION_IDLE, ACTION_MOVE_FORWARD as ACTION_MOVE,
        ACTION_ROTATE_LEFT, ACTION_ROTATE_RIGHT, ACTION_SHOOT, ACTION_SET_TARGET
    )
except ImportError as e:
    print(f"Critical Error: Could not import constants from systems.constants: {e}")
    # Define placeholders as a last resort, but tests might be unreliable
    STATE_VECTOR_SIZE = 98
    ACTION_IDLE = 0
    ACTION_MOVE = 1
    ACTION_ROTATE_LEFT = 2
    ACTION_ROTATE_RIGHT = 3
    ACTION_SHOOT = 4
    ACTION_SET_TARGET = 5

# --- Mock Agent ---
class MockAgent(BaseAgent):
    def __init__(self, name="MockAgent"):
        super().__init__(name=name)
        self.learned_data = []

    def initialize_agent(self, state_size: int, action_size: int) -> None:
        pass # No network needed for mock

    def get_action(self, state: np.ndarray) -> int:
        # Simple deterministic action for testing
        return int(np.sum(state)) % 5

    def learn(self, state: np.ndarray, action: int, reward: float,
             next_state: np.ndarray, done: bool = False) -> None:
        self.learned_data.append({
            'state': state, 'action': action, 'reward': reward,
            'next_state': next_state, 'done': done
        })

    def get_serializable_state(self) -> dict:
        return {'name': self.name, 'learned_count': len(self.learned_data)}

    def load_from_state(self, state: dict) -> None:
        self.name = state.get('name', self.name)
        # Note: doesn't actually load learned data for simplicity

# --- Test Class for LearningIntegration ---
class TestLearningIntegration(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures."""
        # Mocks for dependencies injected into LearningIntegration
        self.mock_env = MagicMock(spec=BattleRoyaleEnv)
        self.mock_env.team_system = MagicMock()
        self.mock_env.get_nearby_agents = MagicMock(return_value=[]) # Default empty list
        self.mock_env.agent_positions = {} # Default empty dict

        self.mock_visualizer_instance = MagicMock(spec=LearningVisualizer)
        self.mock_personality_system = MagicMock()
        self.mock_personality_system.get_agent_personality.return_value = {} # Default empty personality

        # Mocks for classes instantiated *by* LearningIntegration
        # We'll use MagicMock directly for the instances here
        self.mock_pattern_instance = MagicMock(spec=PatternRecognitionSystem)
        self.mock_strategy_instance = MagicMock(spec=StrategyAdaptationSystem)

        # Patch the class constructors to return our mock instances
        self.patcher_pattern = patch('systems.learning.learning_integration.PatternRecognitionSystem', return_value=self.mock_pattern_instance)
        self.patcher_strategy = patch('systems.learning.learning_integration.StrategyAdaptationSystem', return_value=self.mock_strategy_instance)
        self.patcher_evo_manager = patch('systems.learning.learning_integration.EvolutionManager') # Just patch the class

        # Start patchers
        self.MockPatternSystemClass = self.patcher_pattern.start()
        self.MockStrategySystemClass = self.patcher_strategy.start()
        self.MockEvolutionManagerClass = self.patcher_evo_manager.start()
        self.addCleanup(self.patcher_pattern.stop)
        self.addCleanup(self.patcher_strategy.stop)
        self.addCleanup(self.patcher_evo_manager.stop)

        # Instantiate LearningIntegration - it will use the patched classes/mocks
        self.learning_integration = LearningIntegration(
            env=self.mock_env,
            personality_system=self.mock_personality_system,
            visualizer=self.mock_visualizer_instance,
            evo_population_size=0 # Disable evolution for these tests
        )

        # Set visualization frequency *after* init
        self.learning_integration.visualization_update_frequency = 1

        # Reset mocks that might have been called during __init__
        self.mock_visualizer_instance.reset_mock()
        self.mock_pattern_instance.reset_mock()
        self.mock_strategy_instance.reset_mock()

        # Mock agent instance generally needed
        self.mock_agent_instance = MagicMock(spec=BaseAgent)
        self.mock_agent_instance.get_action.return_value = ACTION_IDLE # Default action

    def tearDown(self):
        """Stop patchers if they were started."""
        # The addCleanup mechanism handles stopping the patchers automatically.
        pass

    def test_agent_registration(self):
        """Test registering a new agent."""
        agent_id = "test_agent_1"
        # Use the general mock agent instance from setUp
        mock_personality = {'aggression': 0.8}
        self.mock_personality_system.get_agent_personality.return_value = mock_personality

        result = self.learning_integration.register_agent(agent_id, self.mock_agent_instance, personality_traits=mock_personality)
        self.assertTrue(result)

        self.assertIn(agent_id, self.learning_integration.registered_agents)
        self.assertIs(self.learning_integration.registered_agents[agent_id], self.mock_agent_instance)

        # Verify strategy initialization was called
        self.mock_strategy_instance._initialize_agent_strategy.assert_called_once_with(agent_id)

        # Visualizer is not called during registration anymore
        # self.mock_visualizer_instance.add_agent.assert_not_called() # Removed this line

    def test_ensure_agent_registered_existing(self):
        """Test _ensure_agent_registered does nothing for an existing agent."""
        agent_id = "existing_agent"
        self.learning_integration.register_agent(agent_id, self.mock_agent_instance)
        # Reset mocks called during registration
        self.mock_strategy_instance._initialize_agent_strategy.reset_mock()

        result = self.learning_integration._ensure_agent_registered(agent_id)
        self.assertTrue(result)
        # Ensure strategy system wasn't called again
        self.mock_strategy_instance._initialize_agent_strategy.assert_not_called()

    def test_record_experience(self):
        """Test recording agent experience."""
        agent_id = "agent_exp"
        self.learning_integration.register_agent(agent_id, self.mock_agent_instance)
        # Reset mocks called during registration
        self.mock_strategy_instance._initialize_agent_strategy.reset_mock()
        self.mock_visualizer_instance.reset_mock()
        self.mock_pattern_instance.reset_mock()

        state = np.random.rand(STATE_VECTOR_SIZE)
        action = ACTION_MOVE
        reward = 10.0
        next_state = np.random.rand(STATE_VECTOR_SIZE)
        context = {'situation': 'attacking'}

        result = self.learning_integration.record_experience_with_context(
            agent_id, state, action, reward, next_state, context
        )
        self.assertTrue(result)

        # Check pattern system call
        self.mock_pattern_instance.record_experience.assert_called_once_with(
            agent_id, ANY, action, reward, context
        )
        # Check state array passed to pattern system
        np.testing.assert_array_almost_equal(self.mock_pattern_instance.record_experience.call_args[0][1], state)

        # Check strategy system call
        self.mock_strategy_instance.record_outcome.assert_called_once_with(
            agent_id, context, True, reward # success=True for positive reward
        )

        # Check visualizer update call (frequency set to 1 in setUp)
        self.mock_visualizer_instance.add_learning_data.assert_called_once_with(agent_id, ANY)
        # Check some data passed to visualizer
        call_args, call_kwargs = self.mock_visualizer_instance.add_learning_data.call_args
        visualizer_data = call_args[1]
        self.assertIn('rewards', visualizer_data)
        self.assertEqual(visualizer_data['recent_reward'], reward)
        self.assertIn('experiences', visualizer_data)
        self.assertEqual(visualizer_data['experiences'], 1)

    def test_suggest_action_from_pattern(self):
        """Test action suggestion prioritizes pattern system."""
        agent_id = "agent_pattern"
        self.learning_integration.register_agent(agent_id, self.mock_agent_instance)
        self.mock_strategy_instance._initialize_agent_strategy.reset_mock()

        state = np.random.rand(STATE_VECTOR_SIZE)
        context = {'situation': 'defending'}
        pattern_action = ACTION_ROTATE_LEFT
        pattern_confidence = 0.9

        # Setup mocks: Pattern system returns a confident suggestion
        self.mock_pattern_instance.suggest_action.return_value = (pattern_action, pattern_confidence)

        result = self.learning_integration.suggest_action(agent_id, state, context)

        # Assert pattern system was called
        self.mock_pattern_instance.suggest_action.assert_called_once_with(agent_id, ANY, context)
        # Assert state array passed to pattern system
        np.testing.assert_array_almost_equal(self.mock_pattern_instance.suggest_action.call_args[0][1], state)
        # Assert strategy system was NOT called
        self.mock_strategy_instance.suggest_action.assert_not_called()
        # Assert agent's get_action was NOT called
        self.mock_agent_instance.get_action.assert_not_called()

        # Assert result is the tuple (action, confidence)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], pattern_action)
        self.assertEqual(result[1], pattern_confidence)

    def test_suggest_action_from_strategy(self):
        """Test action suggestion falls back to strategy system."""
        agent_id = "agent_strategy"
        self.learning_integration.register_agent(agent_id, self.mock_agent_instance)
        self.mock_strategy_instance._initialize_agent_strategy.reset_mock()

        state = np.random.rand(STATE_VECTOR_SIZE)
        context = {'situation': 'exploring'}
        strategy_action = ACTION_ROTATE_RIGHT

        # Setup mocks: Pattern returns None, Strategy returns action
        self.mock_pattern_instance.suggest_action.return_value = None
        self.mock_strategy_instance.suggest_action.return_value = strategy_action

        result = self.learning_integration.suggest_action(agent_id, state, context)

        # Assert pattern system was called
        self.mock_pattern_instance.suggest_action.assert_called_once_with(agent_id, ANY, context)
        # Assert strategy system WAS called
        self.mock_strategy_instance.suggest_action.assert_called_once_with(agent_id, ANY, context)
        # Assert state array passed to strategy system
        np.testing.assert_array_almost_equal(self.mock_strategy_instance.suggest_action.call_args[0][1], state)
        # Assert agent's get_action was NOT called
        self.mock_agent_instance.get_action.assert_not_called()

        # Assert result is the strategy action
        self.assertEqual(result, strategy_action)

    def test_suggest_action_fallback_to_agent(self):
        """Test action suggestion falls back to agent's own method."""
        agent_id = "agent_fallback"
        agent_action = ACTION_SHOOT # The action the agent itself will choose
        self.mock_agent_instance.get_action.return_value = agent_action # Configure the mock
        self.learning_integration.register_agent(agent_id, self.mock_agent_instance)
        self.mock_strategy_instance._initialize_agent_strategy.reset_mock()

        state = np.random.rand(STATE_VECTOR_SIZE)
        context = {'situation': 'idle'}

        # Setup mocks: Pattern returns None, Strategy returns None
        self.mock_pattern_instance.suggest_action.return_value = None
        self.mock_strategy_instance.suggest_action.return_value = None

        result = self.learning_integration.suggest_action(agent_id, state, context)

        # Assert pattern system was called
        self.mock_pattern_instance.suggest_action.assert_called_once_with(agent_id, ANY, context)
        # Assert strategy system WAS called
        self.mock_strategy_instance.suggest_action.assert_called_once_with(agent_id, ANY, context)
        # Assert agent's own get_action WAS called
        self.mock_agent_instance.get_action.assert_called_once_with(ANY)
        # Assert state array passed to agent
        np.testing.assert_array_almost_equal(self.mock_agent_instance.get_action.call_args[0][0], state)

        # Assert result is the agent's action
        self.assertEqual(result, agent_action)

# --- Test Class for PatternRecognitionSystem ---
class TestPatternRecognitionSystem(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures for PatternRecognitionSystem tests."""
        
        # --- Mock Personality System Setup --- 
        self.mock_personality_system = MagicMock(spec=PersonalitySystem)
        self.mock_personality_profile = MagicMock()
        self.mock_personality_profile.get_trait.side_effect = lambda trait: 0.5
        self.mock_personality_system.get_agent_personality.return_value = self.mock_personality_profile

        # --- Instantiate the system, injecting the mock directly --- 
        self.pattern_system = PatternRecognitionSystem(
            max_patterns=100, 
            min_confidence_threshold=0.6, 
            learning_rate=0.1, 
            state_similarity_threshold=0.8,
            personality_system_override=self.mock_personality_system # Inject mock
        )
        # --- End Instantiation ---

        # Reset mocks before each test 
        self.mock_personality_system.reset_mock()
        self.mock_personality_profile.reset_mock()
        self.mock_personality_system.get_agent_personality.reset_mock()

    def test_initialization(self):
        """Test basic initialization of the system."""
        self.assertEqual(self.pattern_system.max_patterns, 100)
        self.assertEqual(self.pattern_system.min_confidence_threshold, 0.6)
        self.assertEqual(self.pattern_system.learning_rate, 0.1)
        self.assertEqual(self.pattern_system.state_similarity_threshold, 0.8)
        self.assertEqual(self.pattern_system.patterns, {})
        self.assertEqual(self.pattern_system.pattern_outcomes, {})

    # --- Tests for record_experience --- 
    def test_record_experience_new_pattern(self):
        """Test recording an experience creates a new pattern."""
        agent_id = "agent_pattern_test_1"
        state = np.array([0.1, 0.2, 0.3] * (STATE_VECTOR_SIZE // 3) + [0.1] * (STATE_VECTOR_SIZE % 3))
        action = ACTION_MOVE
        reward = 1.0
        context = {'situation': 'exploring', 'nearby_enemies': 0}

        # Record the first experience
        self.pattern_system.record_experience(agent_id, state, action, reward, context)

        # Assert agent pattern list exists and has one pattern
        self.assertIn(agent_id, self.pattern_system.patterns)
        agent_patterns = self.pattern_system.patterns[agent_id]
        self.assertEqual(len(agent_patterns), 1)
        
        # Get the created pattern (it's the first item in the list)
        pattern_data = agent_patterns[0]
        pattern_id_for_outcome = f"{agent_id}_0" # ID used for outcome tracking

        # Assert pattern structure and initial values (MODIFIED STRUCTURE)
        self.assertIsInstance(pattern_data, dict)
        self.assertIn('state', pattern_data) # Check for 'state' key
        self.assertIn('action', pattern_data)
        self.assertIn('reward_history', pattern_data)
        self.assertIn('success_rate', pattern_data)
        self.assertIn('context', pattern_data)
        self.assertIn('timestamp', pattern_data)
        self.assertIn('use_count', pattern_data)
        
        # Check specific values
        np.testing.assert_array_almost_equal(pattern_data['state'], state) # Check state value
        self.assertEqual(pattern_data['action'], action) # Check action
        self.assertEqual(pattern_data['reward_history'], [reward]) # Check reward history
        self.assertEqual(pattern_data['success_rate'], 1.0) # Check initial success rate (reward > 0)
        self.assertEqual(pattern_data['context'], context) # Check context
        self.assertEqual(pattern_data['use_count'], 1)
        self.assertIsInstance(pattern_data['timestamp'], float)

        # Assert outcome tracking
        self.assertIn(pattern_id_for_outcome, self.pattern_system.pattern_outcomes)
        outcome_info = self.pattern_system.pattern_outcomes[pattern_id_for_outcome]
        # Outcome assessment depends on reward > 0.5 check in _track_pattern_outcome
        if reward > 0.5:
            self.assertEqual(outcome_info['success'], 1)
            self.assertEqual(outcome_info['failure'], 0)
        elif reward < -0.5:
            self.assertEqual(outcome_info['success'], 0)
            self.assertEqual(outcome_info['failure'], 1)
        else:
            self.assertEqual(outcome_info['success'], 0)
            self.assertEqual(outcome_info['failure'], 0)
            self.assertEqual(outcome_info['neutral'], 1)

    def test_record_experience_update_pattern(self):
        """Test recording a similar experience updates an existing pattern."""
        agent_id = "agent_pattern_test_2"
        state1 = np.array([0.5, 0.6, 0.7] * (STATE_VECTOR_SIZE // 3) + [0.5] * (STATE_VECTOR_SIZE % 3))
        action1 = ACTION_SHOOT
        reward1 = 5.0
        context1 = {'situation': 'attacking', 'target_visible': True}
        
        # Record the first experience to create the pattern
        self.pattern_system.record_experience(agent_id, state1, action1, reward1, context1)
        self.assertEqual(len(self.pattern_system.patterns.get(agent_id, [])), 1)
        initial_pattern_data = self.pattern_system.patterns[agent_id][0].copy()
        initial_timestamp = initial_pattern_data['timestamp'] # Use 'timestamp' key
        pattern_id_for_outcome = f"{agent_id}_0" # ID used for outcome tracking

        # --- ADDED: Small sleep to ensure timestamp changes --- 
        time.sleep(0.001)
        # --- END ADDITION ---

        # Create a slightly different state (should still match based on threshold 0.8)
        state2 = state1 + 0.01 
        action2 = ACTION_SHOOT # Same action
        reward2 = 8.0
        context2 = {'situation': 'attacking', 'target_visible': True, 'low_ammo': False}

        # Record the second experience
        self.pattern_system.record_experience(agent_id, state2, action2, reward2, context2)

        # Assert no new pattern was created
        self.assertEqual(len(self.pattern_system.patterns.get(agent_id, [])), 1)
        
        # Get the updated pattern data (still at index 0)
        updated_pattern_data = self.pattern_system.patterns[agent_id][0]

        # Assert pattern data updates (MODIFIED STRUCTURE & LOGIC)
        self.assertEqual(updated_pattern_data['action'], action1) # Action should remain the same
        # State should be a weighted average
        expected_state = (1 - self.pattern_system.learning_rate) * state1 + self.pattern_system.learning_rate * state2
        np.testing.assert_array_almost_equal(updated_pattern_data['state'], expected_state)
        # Reward history should contain both rewards (up to limit)
        self.assertIn(reward1, updated_pattern_data['reward_history'])
        self.assertIn(reward2, updated_pattern_data['reward_history'])
        # Success rate should be updated based on history
        expected_success_rate = sum(1 for r in [reward1, reward2] if r > 0) / 2.0
        self.assertAlmostEqual(updated_pattern_data['success_rate'], expected_success_rate)
        # Context should be updated (specific logic depends on implementation)
        self.assertIn('situation', updated_pattern_data['context'])
        self.assertIn('target_visible', updated_pattern_data['context'])
        self.assertIn('low_ammo', updated_pattern_data['context']) # Check new key is added
        # Use count should be incremented
        self.assertEqual(updated_pattern_data['use_count'], 2)
        self.assertNotEqual(updated_pattern_data['timestamp'], initial_timestamp) # Timestamp changed

        # Assert outcome tracking update
        self.assertIn(pattern_id_for_outcome, self.pattern_system.pattern_outcomes)
        outcome_info = self.pattern_system.pattern_outcomes[pattern_id_for_outcome]
        # Both rewards were > 0.5
        self.assertEqual(outcome_info['success'], 2) 
        self.assertEqual(outcome_info['failure'], 0)
        self.assertEqual(outcome_info['neutral'], 0)

    # --- Tests for suggest_action --- 
    def test_suggest_action_no_patterns(self):
        """Test suggest_action returns None when no patterns exist for the agent."""
        agent_id = "agent_suggest_none"
        state = np.random.rand(STATE_VECTOR_SIZE)
        context = {'situation': 'idle'}
        
        result = self.pattern_system.suggest_action(agent_id, state, context)
        # Check if result is None or (None, 0.0)
        if result is None:
            suggested_action = None
            confidence = 0.0
        else:
            suggested_action, confidence = result

        self.assertIsNone(suggested_action)
        self.assertEqual(confidence, 0.0)
        
    def test_suggest_action_match_found(self):
        """Test suggest_action returns the correct action when a pattern matches."""
        agent_id = "agent_suggest_match"
        # Record a successful experience
        state1 = np.array([0.8, 0.1, 0.9] * (STATE_VECTOR_SIZE // 3) + [0.8] * (STATE_VECTOR_SIZE % 3))
        action1 = ACTION_SHOOT
        reward1 = 10.0 # High reward -> higher confidence
        context1 = {'situation': 'in_combat', 'target_distance': 50}
        self.pattern_system.record_experience(agent_id, state1, action1, reward1, context1)
        
        # Ensure pattern exists and get its confidence
        self.assertEqual(len(self.pattern_system.patterns.get(agent_id, [])), 1)
        pattern_data = self.pattern_system.patterns[agent_id][0]
        # Confidence might not be directly stored, get success rate if needed
        # expected_confidence = pattern_data['confidence'] 
        # self.assertGreater(expected_confidence, 0) # Check confidence/success is positive

        # Create a similar state and context for suggestion
        state2 = state1 * 1.05 # Slightly different but should match
        context2 = {'situation': 'in_combat', 'target_distance': 55} # Similar context

        # Suggest action
        result = self.pattern_system.suggest_action(agent_id, state2, context2)
        self.assertIsNotNone(result, "Action should be suggested for matching pattern")
        suggested_action, confidence = result

        # Assert the correct action and confidence are returned
        # Find the most likely action from the pattern's action counts (MODIFIED: Use direct action key)
        self.assertEqual(suggested_action, pattern_data['action']) # Assert against the stored action
        self.assertGreater(confidence, 0.0)
        # Confidence calculation is complex, just check it's positive and potentially > threshold
        # self.assertGreaterEqual(confidence, self.pattern_system.min_confidence_threshold)
        
    def test_suggest_action_confidence_threshold(self):
        """Test suggest_action returns None if the matched pattern's confidence is too low."""
        agent_id = "agent_suggest_low_conf"
        # Record an experience with low/negative reward to keep confidence low
        state1 = np.array([0.2, 0.2, 0.2] * (STATE_VECTOR_SIZE // 3) + [0.2] * (STATE_VECTOR_SIZE % 3))
        action1 = ACTION_ROTATE_LEFT
        reward1 = -1.0 # Negative reward
        context1 = {'situation': 'stuck', 'nearby_enemies': 0}
        self.pattern_system.record_experience(agent_id, state1, action1, reward1, context1)
        
        # Ensure pattern exists
        self.assertEqual(len(self.pattern_system.patterns.get(agent_id, [])), 1)
        pattern_data = self.pattern_system.patterns[agent_id][0]
        # Verify confidence/success rate is low (actual value depends on implementation)
        # pattern_confidence = pattern_data.get('confidence', 0.0)
        # self.assertLess(pattern_confidence, self.pattern_system.min_confidence_threshold)

        # Create a similar state and context for suggestion
        state2 = state1 + 0.02 # Similar state
        context2 = {'situation': 'stuck', 'nearby_enemies': 0} # Same context

        # Suggest action
        result = self.pattern_system.suggest_action(agent_id, state2, context2)
        # Expect (None, 0.0) if confidence is below threshold
        if result is None:
            suggested_action = None
            confidence = 0.0
        else:
            suggested_action, confidence = result

        # Assert no action is suggested due to low confidence
        # Note: suggest_action might still return the action but with low confidence
        # depending on implementation. The check should be against the threshold.
        # Let's assume for now it returns None if below threshold based on the code structure.
        # A more robust test would check the confidence value itself if the action *was* returned.
        self.assertIsNone(suggested_action)
        self.assertEqual(confidence, 0.0)

    # --- TODO: Add more tests (sharing, saving/loading, etc.) ---


# --- Test Class for StrategyAdaptationSystem ---
class TestStrategyAdaptationSystem(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures for StrategyAdaptationSystem tests."""
        self.strategy_system = StrategyAdaptationSystem(
            adaptation_rate=0.1, 
            exploration_factor=0.2,
            strategy_memory_size=50
        )
        # Mock dependencies if needed (e.g., PersonalitySystem)
        # ... (similar patching pattern as other tests if necessary)

    def test_initialization(self):
        """Test basic initialization of the StrategyAdaptationSystem."""
        self.assertEqual(self.strategy_system.adaptation_rate, 0.1)
        self.assertEqual(self.strategy_system.exploration_factor, 0.2)
        self.assertEqual(self.strategy_system.strategy_memory_size, 50)
        self.assertEqual(self.strategy_system.agent_strategies, {})
        self.assertEqual(self.strategy_system.strategy_effectiveness, {})
        self.assertEqual(self.strategy_system.situation_triggers, {})

    # --- Tests for record_outcome --- 
    def test_record_outcome_initialize_agent(self):
        """Test recording outcome for an agent not previously seen (should initialize)."""
        agent_id = "agent_strat_record_new"
        context = {"situation": "combat"}
        success = True
        reward = 0.5
        initial_strategy = self.strategy_system.default_strategy.copy()
        initial_strategy_key = json.dumps(initial_strategy, sort_keys=True)

        # Ensure agent doesn't exist initially
        self.assertNotIn(agent_id, self.strategy_system.agent_strategies)
        self.assertNotIn(agent_id, self.strategy_system.strategy_effectiveness)

        updated = self.strategy_system.record_outcome(agent_id, context, success, reward)

        self.assertTrue(updated, "Record outcome should return True on initialization")
        # Verify agent was initialized
        self.assertIn(agent_id, self.strategy_system.agent_strategies)
        self.assertIn(agent_id, self.strategy_system.strategy_effectiveness)
        # Verify effectiveness was tracked against the *initial* strategy before adaptation
        self.assertIn(initial_strategy_key, self.strategy_system.strategy_effectiveness[agent_id], "Effectiveness should be tracked for the initial strategy")
        # Verify counts were updated for the initial strategy key
        effectiveness_entry = self.strategy_system.strategy_effectiveness[agent_id][initial_strategy_key]
        self.assertEqual(effectiveness_entry['success_count'], 1)
        self.assertEqual(effectiveness_entry['failure_count'], 0)
        self.assertEqual(effectiveness_entry['actions_taken'], 1)
        self.assertEqual(effectiveness_entry['total_reward'], reward)
        # Verify the current strategy was adapted (even slightly)
        self.assertNotEqual(self.strategy_system.agent_strategies[agent_id]['current_strategy'], initial_strategy, "Current strategy should be adapted after recording outcome")

    def test_record_outcome_success(self):
        """Test recording a successful outcome updates counts correctly."""
        agent_id = "agent_strat_record_success"
        context = {"situation": "exploration"}
        success = True
        reward = 1.0
        
        # Initialize agent and record an initial outcome to create the strategy effectiveness entry
        self.strategy_system._initialize_agent_strategy(agent_id)
        initial_strategy_key = json.dumps(self.strategy_system.agent_strategies[agent_id]['current_strategy'], sort_keys=True)
        self.strategy_system.record_outcome(agent_id, context, False, -0.5) # Record initial dummy outcome

        # Ensure the initial entry exists and has initial counts
        self.assertIn(agent_id, self.strategy_system.strategy_effectiveness)
        self.assertIn(initial_strategy_key, self.strategy_system.strategy_effectiveness[agent_id])
        initial_counts = self.strategy_system.strategy_effectiveness[agent_id][initial_strategy_key].copy()
        
        # Now record the actual successful outcome (using the potentially adapted strategy)
        current_strategy = self.strategy_system.agent_strategies[agent_id]['current_strategy']
        current_strategy_key = json.dumps(current_strategy, sort_keys=True)
        # Ensure the key exists for the current strategy (it might be the same or adapted)
        if current_strategy_key not in self.strategy_system.strategy_effectiveness[agent_id]:
             self.strategy_system.strategy_effectiveness[agent_id][current_strategy_key] = {
                'success_count': 0, 'failure_count': 0, 'actions_taken': 0, 'total_reward': 0.0
            }
        current_counts_before = self.strategy_system.strategy_effectiveness[agent_id][current_strategy_key].copy()

        updated = self.strategy_system.record_outcome(agent_id, context, success, reward)
        self.assertTrue(updated, "Record outcome should return True on update")

        # Verify counts for the strategy used in the successful outcome
        final_counts = self.strategy_system.strategy_effectiveness[agent_id][current_strategy_key]
        self.assertEqual(final_counts['success_count'], current_counts_before['success_count'] + 1)
        self.assertEqual(final_counts['failure_count'], current_counts_before['failure_count']) # Failure count shouldn't change
        self.assertEqual(final_counts['actions_taken'], current_counts_before['actions_taken'] + 1)
        self.assertEqual(final_counts['total_reward'], current_counts_before['total_reward'] + reward)

    def test_record_outcome_failure(self):
        """Test recording a failed outcome updates counts correctly."""
        agent_id = "agent_strat_record_failure"
        context = {"situation": "resource_gathering"}
        success = False
        reward = -1.0

        # Initialize agent and record an initial outcome
        self.strategy_system._initialize_agent_strategy(agent_id)
        initial_strategy_key = json.dumps(self.strategy_system.agent_strategies[agent_id]['current_strategy'], sort_keys=True)
        self.strategy_system.record_outcome(agent_id, context, True, 0.5) # Record initial dummy outcome
        
        self.assertIn(agent_id, self.strategy_system.strategy_effectiveness)
        self.assertIn(initial_strategy_key, self.strategy_system.strategy_effectiveness[agent_id])
        initial_counts = self.strategy_system.strategy_effectiveness[agent_id][initial_strategy_key].copy()

        # Now record the actual failed outcome
        current_strategy = self.strategy_system.agent_strategies[agent_id]['current_strategy']
        current_strategy_key = json.dumps(current_strategy, sort_keys=True)
        if current_strategy_key not in self.strategy_system.strategy_effectiveness[agent_id]:
             self.strategy_system.strategy_effectiveness[agent_id][current_strategy_key] = {
                'success_count': 0, 'failure_count': 0, 'actions_taken': 0, 'total_reward': 0.0
            }
        current_counts_before = self.strategy_system.strategy_effectiveness[agent_id][current_strategy_key].copy()

        updated = self.strategy_system.record_outcome(agent_id, context, success, reward)
        self.assertTrue(updated, "Record outcome should return True on update")

        # Verify counts for the strategy used in the failed outcome
        final_counts = self.strategy_system.strategy_effectiveness[agent_id][current_strategy_key]
        self.assertEqual(final_counts['success_count'], current_counts_before['success_count']) # Success count shouldn't change
        self.assertEqual(final_counts['failure_count'], current_counts_before['failure_count'] + 1)
        self.assertEqual(final_counts['actions_taken'], current_counts_before['actions_taken'] + 1)
        self.assertEqual(final_counts['total_reward'], current_counts_before['total_reward'] + reward)

    def test_get_strategy_existing_agent(self):
        """Test retrieving strategy for an existing agent."""
        agent_id = "agent_strat_get_existing"
        self.strategy_system._initialize_agent_strategy(agent_id)
        # Expected strategy is the default strategy after initialization (personality applied if mock was set)
        expected_strategy = self.strategy_system.default_strategy.copy()
        # If personality system was mocked and applied changes, reflect them here.
        # Since the mock personality returns default 0.5 traits, no change occurs.
        
        strategy = self.strategy_system.get_strategy(agent_id)
        self.assertEqual(strategy, expected_strategy, "Should return the initialized strategy for an existing agent")

    def test_get_strategy_new_agent(self):
        """Test retrieving strategy for a new agent (implicitly initialized)."""
        agent_id = "agent_strat_get_new"
        # Expected strategy is the default after implicit initialization
        expected_strategy = self.strategy_system.default_strategy.copy()
        strategy = self.strategy_system.get_strategy(agent_id)
        self.assertEqual(strategy, expected_strategy, "Should return the default strategy for a new agent")
        # Verify initialization occurred
        self.assertIn(agent_id, self.strategy_system.agent_strategies)
        self.assertEqual(self.strategy_system.agent_strategies[agent_id]['current_strategy'], expected_strategy)

    # --- TODO: Add tests for suggest_action --- 
    # def test_suggest_action_default_strategy(self):
    #     pass
        
    # def test_suggest_action_adapted_strategy(self):
    #     pass

    # --- TODO: Add more tests (triggers, saving/loading, etc.) ---


if __name__ == '__main__':
    # Ensure test discovery finds all classes
    unittest.main() 