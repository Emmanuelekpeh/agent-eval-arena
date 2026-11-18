import unittest
import sys
import os
import json
import tempfile
import numpy as np
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from systems.learning.strategy_adaptation_system import StrategyAdaptationSystem

class TestStrategyAdaptationSystem(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.adaptation_rate = 0.05
        self.exploration_factor = 0.2
        self.strategy_memory_size = 10
        self.initial_strategy = {
            "aggression": 0.5,
            "caution": 0.5,
            "coordination": 0.5,
            "persistence": 0.5,
            "adaptability": 0.5
        }
        
        self.strategy_system = StrategyAdaptationSystem(
            adaptation_rate=self.adaptation_rate,
            exploration_factor=self.exploration_factor,
            strategy_memory_size=self.strategy_memory_size,
            initial_strategy=self.initial_strategy
        )
        
        # Sample personality traits for testing
        self.test_personality = {
            "extraversion": 0.8,
            "neuroticism": 0.3,
            "openness": 0.7,
            "conscientiousness": 0.6,
            "agreeableness": 0.5
        }
        
        # Initialize a test agent
        self.test_agent_id = "test_agent_1"
        self.strategy_system.integrate_personality_traits(self.test_agent_id, self.test_personality)

    def test_init(self):
        """Test initialization of the strategy adaptation system."""
        self.assertEqual(self.strategy_system.adaptation_rate, self.adaptation_rate)
        self.assertEqual(self.strategy_system.exploration_factor, self.exploration_factor)
        self.assertEqual(self.strategy_system.strategy_memory_size, self.strategy_memory_size)
        self.assertDictEqual(self.strategy_system.default_strategy, self.initial_strategy)
        self.assertIsInstance(self.strategy_system.agent_strategies, dict)
        self.assertIsInstance(self.strategy_system.strategy_history, dict)
        self.assertIsInstance(self.strategy_system.situation_triggers, dict)
        
        # Check default strategy parameters exist
        self.assertIn("aggression", self.strategy_system.default_strategy)
        self.assertIn("caution", self.strategy_system.default_strategy)
        self.assertIn("coordination", self.strategy_system.default_strategy)
        self.assertIn("persistence", self.strategy_system.default_strategy)
        self.assertIn("adaptability", self.strategy_system.default_strategy)

    def test_integrate_personality_traits(self):
        """Test integration of personality traits for new and existing agents."""
        # Test creation of a new agent strategy
        new_agent_id = "test_agent_new"
        result = self.strategy_system.integrate_personality_traits(new_agent_id, self.test_personality)
        
        # Check if the strategy was created and returned
        self.assertIn(new_agent_id, self.strategy_system.agent_strategies)
        self.assertIsInstance(result, dict)
        
        # Verify personality influence on strategy
        strategy = self.strategy_system.agent_strategies[new_agent_id]
        self.assertGreater(strategy["coordination"], 0.5)  # Extraversion increases coordination
        self.assertGreater(strategy["adaptability"], 0.5)  # Openness increases adaptability
        self.assertGreater(strategy["persistence"], 0.5)   # Conscientiousness increases persistence
        
        # Test updating an existing agent strategy
        original_strategy = dict(strategy)
        
        # Modify personality traits
        modified_personality = dict(self.test_personality)
        modified_personality["extraversion"] = 0.2  # Low extraversion
        
        # Update strategy with new personality
        self.strategy_system.integrate_personality_traits(new_agent_id, modified_personality)
        updated_strategy = self.strategy_system.agent_strategies[new_agent_id]
        
        # Verify strategy was updated based on personality change
        self.assertNotEqual(updated_strategy["coordination"], original_strategy["coordination"])
        self.assertLess(updated_strategy["coordination"], original_strategy["coordination"])
        
        # Verify a history entry was created
        self.assertGreater(len(self.strategy_system.strategy_history[new_agent_id]), 0)
        
    def test_record_outcome_success(self):
        """Test recording a successful outcome."""
        context = {"in_team": True, "under_attack": False}
        initial_strategy = dict(self.strategy_system.agent_strategies[self.test_agent_id])
        
        # Record a successful outcome
        result = self.strategy_system.record_outcome(
            self.test_agent_id, context, success=True, reward=10.0
        )
        
        self.assertTrue(result)
        
        # Success shouldn't change the strategy significantly, just reinforce it
        current_strategy = self.strategy_system.agent_strategies[self.test_agent_id]
        for key in initial_strategy:
            self.assertAlmostEqual(current_strategy[key], initial_strategy[key], delta=0.01)
        
        # Check that effectiveness metrics were updated
        effectiveness = self.strategy_system.get_strategy_effectiveness(self.test_agent_id)
        self.assertEqual(effectiveness["success_count"], 1)
        self.assertEqual(effectiveness["failure_count"], 0)
        self.assertEqual(effectiveness["total_reward"], 10.0)
        self.assertEqual(effectiveness["actions_taken"], 1)
        
        # Verify history was recorded
        self.assertGreater(len(self.strategy_system.strategy_history[self.test_agent_id]), 0)
        latest_history = self.strategy_system.strategy_history[self.test_agent_id][-1]
        self.assertEqual(latest_history["reason"], "experience_adaptation")
        self.assertEqual(latest_history["success"], True)
        self.assertEqual(latest_history["reward"], 10.0)
        
    def test_record_outcome_failure(self):
        """Test recording a failure outcome."""
        context = {"in_team": True, "under_attack": True}
        initial_strategy = dict(self.strategy_system.agent_strategies[self.test_agent_id])
        
        # Make the agent more aggressive to test adaptation
        self.strategy_system.agent_strategies[self.test_agent_id]["aggression"] = 0.8
        
        # Record a failure outcome
        result = self.strategy_system.record_outcome(
            self.test_agent_id, context, success=False, reward=-5.0
        )
        
        self.assertTrue(result)
        
        # Failure should adapt the strategy
        current_strategy = self.strategy_system.agent_strategies[self.test_agent_id]
        
        # Since aggression was high and the agent failed under attack, aggression should decrease
        self.assertLess(current_strategy["aggression"], 0.8)
        
        # Check that effectiveness metrics were updated
        effectiveness = self.strategy_system.get_strategy_effectiveness(self.test_agent_id)
        self.assertEqual(effectiveness["success_count"], 0)
        self.assertEqual(effectiveness["failure_count"], 1)
        self.assertEqual(effectiveness["total_reward"], -5.0)
        self.assertEqual(effectiveness["actions_taken"], 1)
        
        # Verify history was recorded
        self.assertGreater(len(self.strategy_system.strategy_history[self.test_agent_id]), 0)
        latest_history = self.strategy_system.strategy_history[self.test_agent_id][-1]
        self.assertEqual(latest_history["reason"], "experience_adaptation")
        self.assertEqual(latest_history["success"], False)
        self.assertEqual(latest_history["reward"], -5.0)

    def test_get_action_weights(self):
        """Test getting action weights based on agent strategy."""
        state = {"position": [10, 10], "health": 80}
        available_actions = ["attack", "defend", "flee", "heal"]
        
        # Set up a strategy that favors aggressive actions
        self.strategy_system.agent_strategies[self.test_agent_id]["aggression"] = 0.8
        self.strategy_system.agent_strategies[self.test_agent_id]["caution"] = 0.2
        
        weights = self.strategy_system.get_action_weights(
            self.test_agent_id, state, available_actions
        )
        
        # Check that weights were returned for all actions
        self.assertEqual(len(weights), len(available_actions))
        for action in available_actions:
            self.assertIn(action, weights)
            self.assertIsInstance(weights[action], float)
            self.assertGreaterEqual(weights[action], 0.0)
            self.assertLessEqual(weights[action], 1.0)
        
        # With high aggression, attack should be weighted higher than defend or flee
        self.assertGreater(weights["attack"], weights["defend"])
        self.assertGreater(weights["attack"], weights["flee"])

    def test_suggest_action(self):
        """Test suggesting an action based on agent strategy."""
        state = {"position": [10, 10], "health": 80}
        available_actions = ["attack", "defend", "flee", "heal"]
        
        # Set up a strategy that favors aggressive actions
        self.strategy_system.agent_strategies[self.test_agent_id]["aggression"] = 1.0
        self.strategy_system.agent_strategies[self.test_agent_id]["caution"] = 0.0
        
        # With exploration_factor=0, action selection should be deterministic
        with patch.object(self.strategy_system, 'exploration_factor', 0.0):
            selected_action = self.strategy_system.suggest_action(
                self.test_agent_id, state, available_actions
            )
            
            # With max aggression and min caution, attack should be selected
            self.assertEqual(selected_action, "attack")
        
        # Set up a strategy that favors defensive actions
        self.strategy_system.agent_strategies[self.test_agent_id]["aggression"] = 0.0
        self.strategy_system.agent_strategies[self.test_agent_id]["caution"] = 1.0
        
        # With exploration_factor=0, action selection should be deterministic
        with patch.object(self.strategy_system, 'exploration_factor', 0.0):
            selected_action = self.strategy_system.suggest_action(
                self.test_agent_id, state, available_actions
            )
            
            # With min aggression and max caution, defend should be selected
            self.assertIn(selected_action, ["defend", "heal"])  # Both are defensive
        
        # Test with empty actions
        empty_suggestion = self.strategy_system.suggest_action(self.test_agent_id, state, [])
        self.assertIsNone(empty_suggestion)
        
        # Test with unregistered agent
        with patch('logging.Logger.warning') as mock_warning:
            suggestion = self.strategy_system.suggest_action(
                "unknown_agent", 
                state, 
                available_actions
            )
            # Should still return a suggestion using default strategy
            self.assertIn(suggestion["action"], available_actions)
            # Should log a warning
            mock_warning.assert_called_once()

    def test_define_situation_trigger(self):
        """Test defining a situation trigger for strategy adjustment."""
        trigger_name = "low_health_trigger"
        condition = {"health": {"operator": "<", "value": 30}}
        strategy_adjustment = {"caution": 0.3, "aggression": -0.2}
        
        self.strategy_system.define_situation_trigger(
            self.test_agent_id, trigger_name, condition, strategy_adjustment
        )
        
        # Check that the trigger was created
        self.assertIn(trigger_name, self.strategy_system.situation_triggers[self.test_agent_id])
        trigger = self.strategy_system.situation_triggers[self.test_agent_id][trigger_name]
        self.assertEqual(trigger["condition"], condition)
        self.assertEqual(trigger["adjustment"], strategy_adjustment)
        
        # Test for unregistered agent
        with patch('logging.Logger.warning') as mock_warning:
            result = self.strategy_system.define_situation_trigger(
                "unknown_agent",
                trigger_name,
                condition,
                strategy_adjustment
            )
            # Should fail
            self.assertFalse(result)
            # Should log a warning
            mock_warning.assert_called_once()

    def test_apply_situation_triggers(self):
        """Test applying situation triggers to modify strategy."""
        # Define a trigger first
        trigger_name = "low_health_trigger"
        condition = {"health": {"operator": "<", "value": 30}}
        strategy_adjustment = {"caution": 0.3, "aggression": -0.2}
        
        self.strategy_system.define_situation_trigger(
            self.test_agent_id, trigger_name, condition, strategy_adjustment
        )
        
        # State that should trigger the condition
        low_health_state = {"position": [10, 10], "health": 20}
        
        # Get original strategy values
        original_strategy = dict(self.strategy_system.agent_strategies[self.test_agent_id])
        original_caution = original_strategy["caution"]
        original_aggression = original_strategy["aggression"]
        
        # Apply triggers with the state that should match
        adjusted_strategy = self.strategy_system._apply_situation_triggers(
            self.test_agent_id, low_health_state, dict(original_strategy)
        )
        
        # Check that strategy was adjusted according to the trigger
        self.assertGreater(adjusted_strategy["caution"], original_caution)
        self.assertLess(adjusted_strategy["aggression"], original_aggression)
        
        # State that should NOT trigger the condition
        high_health_state = {"position": [10, 10], "health": 80}
        
        # Apply triggers with the state that shouldn't match
        non_adjusted_strategy = self.strategy_system._apply_situation_triggers(
            self.test_agent_id, high_health_state, dict(original_strategy)
        )
        
        # Check that strategy was not adjusted
        self.assertEqual(non_adjusted_strategy["caution"], original_caution)
        self.assertEqual(non_adjusted_strategy["aggression"], original_aggression)

    def test_check_trigger_condition(self):
        """Test checking if a state meets trigger conditions."""
        # Simple condition with single comparison
        condition1 = {"health": {"operator": "<", "value": 30}}
        state1 = {"health": 20, "position": [10, 10]}
        self.assertTrue(self.strategy_system._check_trigger_condition(state1, condition1))
        
        state2 = {"health": 50, "position": [10, 10]}
        self.assertFalse(self.strategy_system._check_trigger_condition(state2, condition1))
        
        # Complex condition with multiple comparisons and AND logic
        condition2 = {
            "health": {"operator": "<", "value": 30},
            "enemies_nearby": {"operator": ">", "value": 2}
        }
        state3 = {"health": 20, "enemies_nearby": 5, "position": [10, 10]}
        self.assertTrue(self.strategy_system._check_trigger_condition(state3, condition2))
        
        state4 = {"health": 20, "enemies_nearby": 1, "position": [10, 10]}
        self.assertFalse(self.strategy_system._check_trigger_condition(state4, condition2))

    def test_get_strategy(self):
        """Test retrieving the current strategy for an agent."""
        # For an existing agent
        strategy = self.strategy_system.get_strategy(self.test_agent_id)
        self.assertIsInstance(strategy, dict)
        self.assertIn("aggression", strategy)
        
        # For a non-existent agent, should create a default strategy
        new_agent_id = "non_existent_agent"
        strategy = self.strategy_system.get_strategy(new_agent_id)
        self.assertIsInstance(strategy, dict)
        self.assertIn("aggression", strategy)
        self.assertIn(new_agent_id, self.strategy_system.agent_strategies)
        
        # Test for unregistered agent
        with patch('logging.Logger.warning') as mock_warning:
            strategy = self.strategy_system.get_strategy("unknown_agent")
            # Should return default strategy
            self.assertEqual(strategy, self.strategy_system.default_strategy)
            # Should log a warning
            mock_warning.assert_called_once()

    def test_get_strategy_effectiveness(self):
        """Test retrieving effectiveness metrics for an agent's strategy."""
        # For an existing agent with no history yet
        effectiveness = self.strategy_system.get_strategy_effectiveness(self.test_agent_id)
        self.assertIsInstance(effectiveness, dict)
        self.assertEqual(effectiveness["success_count"], 0)
        self.assertEqual(effectiveness["failure_count"], 0)
        
        # Add some history
        self.strategy_system.record_outcome(
            self.test_agent_id, context={}, success=True, reward=10.0
        )
        self.strategy_system.record_outcome(
            self.test_agent_id, context={}, success=False, reward=-5.0
        )
        
        # Check updated effectiveness
        effectiveness = self.strategy_system.get_strategy_effectiveness(self.test_agent_id)
        self.assertEqual(effectiveness["success_count"], 1)
        self.assertEqual(effectiveness["failure_count"], 1)
        self.assertEqual(effectiveness["total_reward"], 5.0)
        self.assertEqual(effectiveness["actions_taken"], 2)
        
        # Test for unregistered agent
        effectiveness = self.strategy_system.get_strategy_effectiveness("unknown_agent")
        self.assertIsInstance(effectiveness, dict)
        self.assertEqual(effectiveness["success_count"], 0)

    def test_get_recent_strategy_changes(self):
        """Test retrieving recent strategy changes for an agent."""
        # Add some history by recording outcomes
        self.strategy_system.record_outcome(
            self.test_agent_id, context={"in_team": True}, success=True, reward=10.0
        )
        self.strategy_system.record_outcome(
            self.test_agent_id, context={"under_attack": True}, success=False, reward=-5.0
        )
        
        # Get recent changes
        recent_changes = self.strategy_system.get_recent_strategy_changes(self.test_agent_id, limit=5)
        
        # Should have at least 3 entries (initial + 2 outcomes)
        self.assertGreaterEqual(len(recent_changes), 3)
        
        # Check structure of history entries
        for entry in recent_changes:
            self.assertIn("timestamp", entry)
            self.assertIn("old_strategy", entry)
            self.assertIn("new_strategy", entry)
            self.assertIn("reason", entry)

    def test_share_strategy(self):
        """Test sharing strategy between agents."""
        # Create a second agent with different strategy
        second_agent_id = "test_agent_2"
        second_personality = {
            "extraversion": 0.2,  # Very different from test_agent_1
            "neuroticism": 0.7,
            "openness": 0.4,
            "conscientiousness": 0.3,
            "agreeableness": 0.6
        }
        self.strategy_system.integrate_personality_traits(second_agent_id, second_personality)
        
        # Ensure strategies are different
        strategy1 = self.strategy_system.get_strategy(self.test_agent_id)
        strategy2 = self.strategy_system.get_strategy(second_agent_id)
        self.assertNotEqual(strategy1["coordination"], strategy2["coordination"])
        
        # Share strategy from first agent to second
        result = self.strategy_system.share_strategy(self.test_agent_id, second_agent_id, second_personality)
        self.assertTrue(result)
        
        # Get updated strategy for second agent
        updated_strategy2 = self.strategy_system.get_strategy(second_agent_id)
        
        # Strategy should now be a blend, moving toward the first agent's values
        self.assertNotEqual(updated_strategy2["coordination"], strategy2["coordination"])
        
        # Test sharing with non-existent agent
        result = self.strategy_system.share_strategy(self.test_agent_id, "non_existent_agent")
        self.assertFalse(result)
        
        result = self.strategy_system.share_strategy("non_existent_agent", self.test_agent_id)
        self.assertFalse(result)

    def test_save_load_system_state(self):
        """Test saving and loading the system state."""
        # Add some data to save
        self.strategy_system.record_outcome(
            self.test_agent_id, context={"in_team": True}, success=True, reward=10.0
        )
        
        second_agent_id = "test_agent_2"
        self.strategy_system.integrate_personality_traits(
            second_agent_id, {"extraversion": 0.2, "openness": 0.4}
        )
        
        # Create a temporary directory for the test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save state
            self.strategy_system.save_system_state(temp_dir)
            
            # Create a new system and load the state
            new_system = StrategyAdaptationSystem()
            load_result = new_system.load_system_state(temp_dir)
            
            self.assertTrue(load_result)
            
            # Check that state was restored correctly
            self.assertEqual(
                len(new_system.agent_strategies), 
                len(self.strategy_system.agent_strategies)
            )
            
            for agent_id in self.strategy_system.agent_strategies:
                self.assertIn(agent_id, new_system.agent_strategies)
                
                # Compare strategy values
                original_strategy = self.strategy_system.agent_strategies[agent_id]
                loaded_strategy = new_system.agent_strategies[agent_id]
                
                for key in original_strategy:
                    self.assertAlmostEqual(
                        original_strategy[key], loaded_strategy[key], delta=0.0001
                    )
                
                # Compare effectiveness metrics
                original_effectiveness = self.strategy_system.get_strategy_effectiveness(agent_id)
                loaded_effectiveness = new_system.get_strategy_effectiveness(agent_id)
                
                self.assertEqual(
                    original_effectiveness["success_count"],
                    loaded_effectiveness["success_count"]
                )

if __name__ == '__main__':
    unittest.main() 