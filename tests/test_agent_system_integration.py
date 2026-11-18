import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
import math
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from systems.agents.agent_system import AgentSystem, ACTION_MOVE_FORWARD, ACTION_ROTATE_LEFT, ACTION_ROTATE_RIGHT
from systems.core.system_manager import SystemEventType, SystemManager # Import real SystemManager for event handling context
from systems.agents.base_agent import BaseAgent # Assuming a concrete BaseAgent exists or use MagicMock

# Mock other systems needed for integration
class MockEnvironment:
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.agents = {}
        self.agent_positions = {}
        self.target_fps = 60
        # Add other attributes AgentSystem might access
        self.safe_zone_center = (width / 2, height / 2)
        self.safe_zone_radius = width
        self.collision_tree = MagicMock()
        self.collision_tree.query_range.return_value = [] # Default empty
        self.agent_health = {}
        self.agent_energy = {}

    def get_terrain_modifier(self, x, y):
        return 1.0 # Assume no terrain effect

class MockCombatSystem:
    def apply_status_effect(self, agent_id, effect_type, duration, strength):
        pass # Just needs to exist for the test

class TestAgentSystemIntegration(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures."""
        # Use a real SystemManager instance for event testing
        self.system_manager = SystemManager()
        # Reset shared instance if necessary (important for independent tests)
        SystemManager._instance = self.system_manager 

        self.mock_env = MockEnvironment()
        self.mock_combat_system = MockCombatSystem()
        self.agent_system = AgentSystem()

        # Manually set system references after AgentSystem init (as it uses global manager)
        self.system_manager.register_system("battle_royale_env", self.mock_env)
        self.system_manager.register_system("CombatSystem", self.mock_combat_system) # Register mock combat system
        self.system_manager.register_system("AgentSystem", self.agent_system) # Register agent system itself

        # Initialize AgentSystem AFTER registering dependencies
        self.agent_system.initialize()

        # Setup agents
        self.flanker1_id = "flanker_1"
        self.target1_id = "target_1"
        self.mock_agent_flanker1 = MagicMock(spec=BaseAgent, name=self.flanker1_id, angle=0.0, radius=10)
        self.mock_agent_target1 = MagicMock(spec=BaseAgent, name=self.target1_id, angle=0.0, radius=10)
        self.mock_env.agents = {self.flanker1_id: self.mock_agent_flanker1, self.target1_id: self.mock_agent_target1}
        self.mock_env.agent_positions = {self.flanker1_id: (100, 100), self.target1_id: (200, 100)}
        self.mock_env.agent_health = {self.flanker1_id: 100, self.target1_id: 100}
        self.mock_env.agent_energy = {self.flanker1_id: 100, self.target1_id: 100}
        # Ensure agent system knows about the agents added *after* its init
        self.agent_system.agent_goals[self.flanker1_id] = {}
        self.agent_system.agent_targets[self.flanker1_id] = None
        self.agent_system.agent_threat_level[self.flanker1_id] = 0
        self.agent_system.agent_goals[self.target1_id] = {}
        self.agent_system.agent_targets[self.target1_id] = None
        self.agent_system.agent_threat_level[self.target1_id] = 0

        # Mock combat system method directly for assertion tracking
        self.mock_combat_system.apply_status_effect = MagicMock()


    def tearDown(self):
         """Clean up after tests."""
         # Reset the singleton manager instance to avoid state leaking between test files
         SystemManager._instance = None

    def test_flanking_maneuver_goal_completion_bonus(self):
        """Test the full flow: event -> goal set -> agent moves -> goal reached -> bonus applied."""
        initiator_id = "initiator_agent" # Doesn't need to exist in env for this test
        team_id = "blue_team"
        flank_target_pos = (200, 150) # Calculated position for the flanker
        flank_context = {'maneuver': 'flank', 'target_id': self.target1_id}
        effect_duration = 8.0
        flanking_bonus_strength = 1.25

        # 1. Simulate the event emission that AgentSystem listens for
        event_data = {
            'agent_id': initiator_id,
            'action': 'team_flanking_maneuver_start',
            'team_id': team_id,
            'target_id': self.target1_id,
            'target_position': self.mock_env.agent_positions[self.target1_id],
            'flankers': {self.flanker1_id: flank_target_pos}
        }
        # Manually call the handler (as if SystemManager routed it)
        self.agent_system._handle_agent_action_event(event_data)

        # Verify goal was set
        self.assertIn(self.flanker1_id, self.agent_system.agent_goals)
        self.assertEqual(self.agent_system.agent_goals[self.flanker1_id]['type'], 'move_to')
        self.assertEqual(self.agent_system.agent_goals[self.flanker1_id]['position'], flank_target_pos)
        self.assertEqual(self.agent_system.agent_goals[self.flanker1_id]['context'], flank_context)

        # 2. Simulate AgentSystem update when agent is NOT yet at goal
        # Agent should be commanded to move/rotate
        # We spy on _execute_action
        with patch.object(self.agent_system, '_execute_action') as mock_execute:
            self.agent_system.update(delta_time=0.1)
            # Check if execute was called for the flanker
            flanker_call = next((c for c in mock_execute.call_args_list if c[0][0] == self.flanker1_id), None)
            self.assertIsNotNone(flanker_call)
            # Check it was a move/rotate action (depending on angle)
            action_called = flanker_call[0][1]
            self.assertIn(action_called, [ACTION_MOVE_FORWARD, ACTION_ROTATE_LEFT, ACTION_ROTATE_RIGHT])
            # Check combat system *not* called yet
            self.mock_combat_system.apply_status_effect.assert_not_called()

        # 3. Manually set agent position *very close* to the goal
        epsilon = 5 # Within arrival threshold (15)
        self.mock_env.agent_positions[self.flanker1_id] = (flank_target_pos[0] + epsilon, flank_target_pos[1])

        # 4. Simulate AgentSystem update AGAIN - agent should reach goal
        self.agent_system.update(delta_time=0.1)

        # 5. Assertions
        # Goal should be cleared
        self.assertEqual(self.agent_system.agent_goals.get(self.flanker1_id, {}), {})
        # CombatSystem should have been called to apply the bonus
        self.mock_combat_system.apply_status_effect.assert_called_once_with(
            self.flanker1_id, 'flanking_bonus', effect_duration, flanking_bonus_strength
        )


if __name__ == '__main__':
    unittest.main() 