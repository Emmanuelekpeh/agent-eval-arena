import unittest
import numpy as np
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from systems.morale.morale_suppression_system import MoraleSuppressionSystem
from systems.core.system_manager import SystemEventType, system_manager

# Mock config for testing
MOCK_CONFIG = {
    "morale_suppression": {
        "INITIAL_MORALE": 0.5,
        "MORALE_MAX": 1.0,
        "MORALE_MIN": 0.0,
        "MORALE_PASSIVE_RATE": 0.01, # Small passive increase
        "SUPPRESSION_MAX": 1.0,
        "SUPPRESSION_DECAY_RATE": 0.2,
        "MORALE_EVENT_MODIFIERS": {
            "kill_enemy": 0.15,
            "ally_death": -0.20,
            "take_damage_major": -0.08,
            "take_damage_minor": -0.02, # Added minor damage case
            "deal_damage": 0.01, # Added for attacker morale boost
            "low_morale_nearby": -0.01, # Added for passive update
            "high_morale_nearby": 0.01 # Added for passive update
        },
        "SUPPRESSION_EVENT_MODIFIERS": {
            "near_miss_bullet": 0.1,
            "nearby_explosion": 0.3
        },
        "PERSONALITY_INFLUENCE_WEIGHTS": {
            "morale_gain": 0.5,
            "morale_loss": 0.5,
            "suppression_gain": 0.5,
            "suppression_decay": 0.5
        }
    }
}

class TestMoraleSuppressionSystem(unittest.TestCase):

    def setUp(self):
        """Set up test environment for each test."""
        # Reset system manager's internal state for isolation if needed
        # system_manager.reset() # Assuming a reset method exists

        # Mock the config object
        self.mock_config = MagicMock()
        self.mock_config.get.side_effect = lambda key, default=None: MOCK_CONFIG.get(key, default) if key == "morale_suppression" else default

        # Patch system_manager.get_shared_state to return mock config
        self.patcher_shared_state = patch('systems.morale.morale_suppression_system.system_manager.get_shared_state')
        self.mock_get_shared_state = self.patcher_shared_state.start()
        self.mock_get_shared_state.return_value = self.mock_config

        # Mock PersonalitySystem
        self.mock_personality_system = MagicMock()
        self.mock_personality_system.get_effect_value.return_value = 0.0 # Default neutral effect

        # Patch system_manager.get_system to return mock personality system
        self.patcher_get_system = patch('systems.morale.morale_suppression_system.system_manager.get_system')
        self.mock_get_system = self.patcher_get_system.start()
        self.mock_get_system.side_effect = lambda name: self.mock_personality_system if name == "PersonalitySystem" else None

        # Create instance of the system under test
        self.system = MoraleSuppressionSystem()
        # Manually call initialize as it's not auto-called by BaseSystem in tests
        self.system._initialize()

    def tearDown(self):
        """Clean up after each test."""
        self.patcher_shared_state.stop()
        self.patcher_get_system.stop()
        # Reset system manager's listeners if needed
        # system_manager.clear_listeners()

    def test_agent_registration(self):
        """Test registering a new agent."""
        agent_id = "agent_1"
        self.system.register_agent(agent_id)
        self.assertIn(agent_id, self.system.agent_morale)
        self.assertIn(agent_id, self.system.agent_suppression)
        self.assertEqual(self.system.agent_morale[agent_id], MOCK_CONFIG["morale_suppression"]["INITIAL_MORALE"])
        self.assertEqual(self.system.agent_suppression[agent_id], 0.0)

    def test_agent_removal(self):
        """Test removing an agent."""
        agent_id = "agent_2"
        self.system.register_agent(agent_id)
        self.system._remove_agent(agent_id)
        self.assertNotIn(agent_id, self.system.agent_morale)
        self.assertNotIn(agent_id, self.system.agent_suppression)

    def test_apply_morale_change_basic(self):
        """Test applying a basic morale change."""
        agent_id = "agent_3"
        self.system.register_agent(agent_id)
        initial_morale = self.system.get_morale(agent_id)

        # Positive change
        self.system.apply_morale_change(agent_id, 0.2, "test_positive")
        self.assertAlmostEqual(self.system.get_morale(agent_id), initial_morale + 0.2)

        # Negative change
        self.system.apply_morale_change(agent_id, -0.3, "test_negative")
        self.assertAlmostEqual(self.system.get_morale(agent_id), initial_morale + 0.2 - 0.3)

    def test_apply_morale_change_clamping(self):
        """Test morale clamping at min/max."""
        agent_id = "agent_4"
        self.system.register_agent(agent_id)

        # Clamp at max
        self.system.apply_morale_change(agent_id, 2.0, "test_clamp_max")
        self.assertEqual(self.system.get_morale(agent_id), MOCK_CONFIG["morale_suppression"]["MORALE_MAX"])

        # Clamp at min
        self.system.apply_morale_change(agent_id, -2.0, "test_clamp_min")
        self.assertEqual(self.system.get_morale(agent_id), MOCK_CONFIG["morale_suppression"]["MORALE_MIN"])

    def test_apply_suppression_increase(self):
        """Test applying suppression increase."""
        agent_id = "agent_5"
        self.system.register_agent(agent_id)
        self.assertEqual(self.system.get_suppression(agent_id), 0.0)

        self.system.apply_suppression_increase(agent_id, 0.3, "test_increase")
        self.assertAlmostEqual(self.system.get_suppression(agent_id), 0.3)

        # Clamp at max
        self.system.apply_suppression_increase(agent_id, 2.0, "test_clamp_max")
        self.assertEqual(self.system.get_suppression(agent_id), MOCK_CONFIG["morale_suppression"]["SUPPRESSION_MAX"])

        # Negative amount should not decrease suppression
        current_suppression = self.system.get_suppression(agent_id)
        self.system.apply_suppression_increase(agent_id, -0.5, "test_negative_increase")
        self.assertEqual(self.system.get_suppression(agent_id), current_suppression)

    def test_suppression_decay(self):
        """Test passive suppression decay."""
        agent_id = "agent_6"
        self.system.register_agent(agent_id)
        self.system.apply_suppression_increase(agent_id, 0.5, "setup")
        self.assertAlmostEqual(self.system.get_suppression(agent_id), 0.5)

        # Simulate time passing (e.g., 1 second)
        delta_time = 1.0
        self.system._update(delta_time)
        expected_decay = MOCK_CONFIG["morale_suppression"]["SUPPRESSION_DECAY_RATE"] * delta_time
        self.assertAlmostEqual(self.system.get_suppression(agent_id), 0.5 - expected_decay)

        # Simulate more time to decay fully
        self.system._update(5.0)
        self.assertEqual(self.system.get_suppression(agent_id), 0.0)

    def test_passive_morale_change(self):
        """Test passive morale change (if enabled in config)."""
        agent_id = "agent_7"
        self.system.register_agent(agent_id)
        initial_morale = self.system.get_morale(agent_id)

        delta_time = 1.0
        self.system._update(delta_time)
        expected_change = MOCK_CONFIG["morale_suppression"]["MORALE_PASSIVE_RATE"] * delta_time
        expected_morale = initial_morale + expected_change
        # Clamp expected value
        expected_morale = max(self.system._morale_min, min(self.system._morale_max, expected_morale))

        self.assertAlmostEqual(self.system.get_morale(agent_id), expected_morale)

    def test_handle_agent_damaged(self):
        """Test the AGENT_DAMAGED event handler."""
        agent_id = "agent_8"
        attacker_id = "attacker_1"
        damage_amount = 25.0
        self.system.register_agent(agent_id)
        initial_morale = self.system.get_morale(agent_id)

        # Mock the apply_morale_change method to check its calls
        self.system.apply_morale_change = MagicMock()

        # Simulate the event
        event_data = {
            'target_id': agent_id,
            'attacker_id': attacker_id,
            'damage': damage_amount,
            'details': {'critical_hit': False} # Add basic details
        }
        self.system._handle_agent_damaged(event_data)

        # Check if apply_morale_change was called
        self.assertEqual(self.system.apply_morale_change.call_count, 2, "Expected apply_morale_change to be called twice (for target and attacker)")

        # Check the arguments it was called with
        # Call 1: Target takes damage
        expected_modifier_key_target = "take_damage_major"
        expected_modifier_value_target = MOCK_CONFIG["morale_suppression"]["MORALE_EVENT_MODIFIERS"].get(expected_modifier_key_target, 0.0)
        # Call 2: Attacker deals damage (assuming a 'deal_damage' modifier exists)
        expected_modifier_key_attacker = "deal_damage" # Assume this key exists
        expected_modifier_value_attacker = MOCK_CONFIG["morale_suppression"]["MORALE_EVENT_MODIFIERS"].get(expected_modifier_key_attacker, 0.0)

        # Check calls using call_args_list
        calls = self.system.apply_morale_change.call_args_list
        # Note: Order of calls might not be guaranteed, so check both possibilities or specific arguments
        expected_call_target = unittest.mock.call(agent_id, expected_modifier_value_target, "took_25.0_damage") # Match the reason string from implementation
        expected_call_attacker = unittest.mock.call(attacker_id, expected_modifier_value_attacker, "dealt_25.0_damage") # Match the reason string

        # Use assertCountEqual to check calls regardless of order
        self.assertCountEqual([expected_call_target, expected_call_attacker], calls)

    # TODO: Add tests for personality influence
    # These tests would involve configuring the mock_personality_system.get_effect_value
    # to return non-zero values and asserting the modified changes.

    def test_apply_morale_change_with_personality(self):
        """Test that personality influences the magnitude of morale changes."""
        agent_id = "agent_9"
        self.system.register_agent(agent_id)
        base_change = 0.2
        reason = "test_personality_positive"

        # --- Configure Personality Mock --- #
        # Simulate a personality trait effect that INCREASES positive morale changes
        # Example: Neuroticism effect is -0.8 (meaning less sensitive to morale changes)
        # We want to test the effect on a *positive* change (morale_gain)
        effect_name_gain = 'neuroticism_morale_impact' # Example effect name
        mock_effect_value = -0.8 # High neuroticism -> Less impact from morale changes
        # Set return_value based on called effect_name using side_effect
        self.mock_personality_system.get_effect_value.side_effect = lambda agent_id, effect_name: mock_effect_value if effect_name == effect_name_gain else 0.0

        # --- Calculate Expected Change --- #
        # Get the weight for morale gain from config
        weight = MOCK_CONFIG["morale_suppression"]["PERSONALITY_INFLUENCE_WEIGHTS"]["morale_gain"]
        # Calculate the personality modifier: 1 + (effect_value * weight)
        # Ensure effect value sign makes sense: Negative effect value should reduce the change magnitude
        personality_modifier = 1.0 + (mock_effect_value * weight)
        # Ensure modifier doesn't make change negative or excessively large (e.g., clamp modifier [0.1, 2.0])
        personality_modifier = max(0.1, min(2.0, personality_modifier))
        expected_actual_change = base_change * personality_modifier

        # --- Mock internal method to capture the *actual* change applied before clamping --- #
        # We need to capture the value passed to np.clip inside apply_morale_change
        # Alternative: Check the final value after applying the expected modified change
        initial_morale = self.system.get_morale(agent_id)
        expected_final_morale = np.clip(
            initial_morale + expected_actual_change,
            self.system._morale_min,
            self.system._morale_max
        )

        # --- Act --- #
        self.system.apply_morale_change(agent_id, base_change, reason)

        # --- Assert --- #
        # Verify get_effect_value was called correctly
        self.mock_personality_system.get_effect_value.assert_called_with(agent_id, effect_name_gain)
        # Assert the final morale matches the expected value after personality modification and clamping
        self.assertAlmostEqual(self.system.get_morale(agent_id), expected_final_morale, places=5)

if __name__ == '__main__':
    unittest.main() 