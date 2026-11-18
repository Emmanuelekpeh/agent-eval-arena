import unittest
import numpy as np
from unittest.mock import MagicMock, patch
import math

from systems.agents.team_agent import (
    TeamAgent, 
    DefenderTeamAgent, 
    AttackerTeamAgent,
    SupportTeamAgent,
    ScoutTeamAgent
)

class TestTeamAgent(unittest.TestCase):
    """Test cases for the TeamAgent class."""
    
    def setUp(self):
        """Set up the test environment before each test."""
        self.agent = TeamAgent(name="TestTeamAgent", team_id="team1", role="leader")
        self.agent.initialize(state_size=10, action_size=5)
        
        # Mock the underlying model
        self.agent.model.get_action = MagicMock(return_value=1)  # Forward
        self.agent.model.learn = MagicMock()
        
    def test_initialization(self):
        """Test that the TeamAgent initializes correctly."""
        self.assertEqual(self.agent.name, "TestTeamAgent")
        self.assertEqual(self.agent.team_id, "team1")
        self.assertEqual(self.agent.role, "leader")
        self.assertEqual(self.agent.state_size, 10)
        self.assertEqual(self.agent.action_size, 5)
        
        # Check default parameters
        self.assertEqual(self.agent.coordination_weight, 0.8)
        self.assertIsNone(self.agent.formation_target)
        self.assertEqual(self.agent.formation_bonus, 1.0)
        
    def test_team_info_update(self):
        """Test updating team information."""
        self.agent.set_team_info("team2", "support")
        self.assertEqual(self.agent.team_id, "team2")
        self.assertEqual(self.agent.role, "support")
        
    def test_formation_target_update(self):
        """Test updating formation target."""
        self.agent.update_formation_target((100, 200))
        self.assertEqual(self.agent.formation_target, (100, 200))
        
    def test_teammate_positions_update(self):
        """Test updating teammate positions."""
        positions = [(0, 0), (100, 100), (200, 0)]
        self.agent.update_teammate_positions(positions)
        self.assertEqual(self.agent.teammate_positions, positions)
        
    def test_formation_bonus_update(self):
        """Test updating formation bonus."""
        self.agent.set_formation_bonus(1.5)
        self.assertEqual(self.agent.formation_bonus, 1.5)
        
    def test_get_action_without_formation(self):
        """Test get_action without formation information."""
        state = np.array([0.1, 0.2, 0.3, 0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        
        # Without formation target, should use base action
        action = self.agent.get_action(state)
        
        # Should use the mock's return value
        self.assertEqual(action, 1)
        self.agent.model.get_action.assert_called_once()
        
    def test_get_action_with_formation(self):
        """Test get_action with formation information."""
        state = np.array([0.1, 0.2, 0.3, 0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        
        # Set formation target far from current position
        self.agent.update_formation_target((1000, 1000))
        
        # With formation target far away, should adjust action to move toward target
        action = self.agent.get_action(state)
        
        # Should still call the base model
        self.agent.model.get_action.assert_called_once()
        
    def test_learn_adjusts_reward(self):
        """Test that learn adjusts reward based on team factors."""
        state = np.array([0.1, 0.2, 0.3, 0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        next_state = np.array([0.2, 0.3, 0.4, 0.1, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1])
        
        # Without formation target
        self.agent.learn(state, 1, 0.5, next_state)
        
        # Should pass the original reward
        self.agent.model.learn.assert_called_with(state, 1, 0.5, next_state, False)
        
        # Reset mock
        self.agent.model.learn.reset_mock()
        
        # With formation target
        self.agent.update_formation_target((100, 100))
        self.agent.learn(state, 1, 0.5, next_state)
        
        # Should have called learn, but the reward might be adjusted
        # We can't easily test the exact value without duplicating the logic
        self.agent.model.learn.assert_called_once()
        
    def test_extract_team_factors(self):
        """Test extraction of team factors from state."""
        state = np.array([0.1, 0.2, 0.3, 0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        self.agent.update_formation_target((100, 100))
        self.agent.teammate_positions = [(0, 0), (100, 100), (200, 0)]
        
        factors = self.agent._extract_team_factors(state)
        
        # Check that required factors are present
        self.assertIn('role_params', factors)
        self.assertIn('formation_distance', factors)
        self.assertIn('team_spread', factors)
        self.assertIn('formation_bonus', factors)
        self.assertIn('coordination_weight', factors)
        
        # Check role params
        self.assertEqual(factors['role_params'], self.agent.role_params['leader'])
        
    def test_serialization(self):
        """Test serialization and deserialization."""
        # Get serializable state
        state = self.agent.get_serializable_state()
        
        # Check that required fields are present
        self.assertEqual(state['name'], "TestTeamAgent")
        self.assertEqual(state['team_id'], "team1")
        self.assertEqual(state['role'], "leader")
        self.assertEqual(state['coordination_weight'], 0.8)
        
        # Create new agent and load state
        new_agent = TeamAgent()
        new_agent.load_from_state(state)
        
        # Check that state was loaded correctly
        self.assertEqual(new_agent.team_id, "team1")
        self.assertEqual(new_agent.role, "leader")
        self.assertEqual(new_agent.coordination_weight, 0.8)
    
    def test_role_specific_behavior(self):
        """Test that different roles have different behavior parameters."""
        # Create agents with different roles
        leader = TeamAgent(name="Leader", role="leader")
        defender = TeamAgent(name="Defender", role="defender")
        attacker = TeamAgent(name="Attacker", role="attacker")
        
        # Extract role parameters
        leader_params = leader.role_params["leader"]
        defender_params = defender.role_params["defender"]
        attacker_params = attacker.role_params["attacker"]
        
        # Assert different roles have different parameters
        self.assertNotEqual(leader_params['aggression_factor'], defender_params['aggression_factor'])
        self.assertNotEqual(defender_params['defense_factor'], attacker_params['defense_factor'])
        self.assertLess(defender_params['exploration_factor'], attacker_params['exploration_factor'])
        self.assertGreater(defender_params['defense_factor'], attacker_params['defense_factor'])


class TestSpecializedTeamAgents(unittest.TestCase):
    """Test cases for specialized team agent subclasses."""
    
    def test_defender_agent(self):
        """Test the DefenderTeamAgent."""
        defender = DefenderTeamAgent()
        
        # Check specialized parameters
        self.assertEqual(defender.role, "defender")
        self.assertEqual(defender.coordination_weight, 0.9)
        self.assertTrue(hasattr(defender, "shield_ability_threshold"))
        
    def test_attacker_agent(self):
        """Test the AttackerTeamAgent."""
        attacker = AttackerTeamAgent()
        
        # Check specialized parameters
        self.assertEqual(attacker.role, "attacker")
        self.assertEqual(attacker.coordination_weight, 0.7)
        self.assertTrue(hasattr(attacker, "strike_ability_threshold"))
        
    def test_support_agent(self):
        """Test the SupportTeamAgent."""
        support = SupportTeamAgent()
        
        # Check specialized parameters
        self.assertEqual(support.role, "support")
        self.assertEqual(support.coordination_weight, 1.0)
        self.assertTrue(hasattr(support, "energy_transfer_threshold"))
        
    def test_scout_agent(self):
        """Test the ScoutTeamAgent."""
        scout = ScoutTeamAgent()
        
        # Check specialized parameters
        self.assertEqual(scout.role, "scout")
        self.assertEqual(scout.coordination_weight, 0.5)
        self.assertTrue(hasattr(scout, "exploration_radius"))


class TestTeamAgentIntegration(unittest.TestCase):
    """Integration tests for TeamAgent with TeamSystem."""
    
    @patch('systems.agents.team_system.TeamSystem')
    def test_integration_with_team_system(self, mock_team_system):
        """Test integration with the TeamSystem."""
        # Create a team system mock
        team_system = mock_team_system.return_value
        team_system.get_formation_positions.return_value = [(0, 0), (100, 100), (200, 0)]
        team_system.get_formation_bonus.return_value = 1.2
        
        # Create team agent
        agent = TeamAgent(name="TeamMember", team_id="team1", role="support")
        agent.initialize(10, 5)
        
        # Set formation target using team system
        positions = team_system.get_formation_positions("team1", (0, 0))
        agent.update_formation_target(positions[1])  # Second position for this agent
        
        # Update formation bonus using team system
        bonus = team_system.get_formation_bonus("team1")
        agent.set_formation_bonus(bonus)
        
        # Verify the agent has updated values
        self.assertEqual(agent.formation_target, (100, 100))
        self.assertEqual(agent.formation_bonus, 1.2)
    
    @patch('systems.agents.team_system.TeamSystem')
    def test_formation_adjustment(self, mock_team_system):
        """Test action adjustment based on formation."""
        # Create a team system mock
        team_system = mock_team_system.return_value
        team_system.get_formation_positions.return_value = [(0, 0), (100, 0), (0, 100)]
        
        # Create team agent with formation target far from current position
        agent = TeamAgent(name="TeamMember", team_id="team1", role="support")
        agent.initialize(10, 5)
        agent.update_formation_target((100, 0))  # Target is directly to the right
        
        # Mock the underlying model
        agent.model.get_action = MagicMock(return_value=0)  # Idle
        
        # Create a test state where agent is at (0,0) facing north (angle π/2)
        state = np.zeros(10)
        state[0] = 0      # x = 0
        state[1] = 0      # y = 0
        state[3] = math.pi/2  # Facing north
        
        # Get action - should adjust to move toward formation target
        action = agent.get_action(state)
        
        # Since target is to the right and we're facing north, should rotate right
        self.assertEqual(action, 3)  # Rotate right


if __name__ == "__main__":
    unittest.main() 