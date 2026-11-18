import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from systems.team_agent_integration import TeamAgentManager
from systems.agents.team_system import TeamSystem
from systems.agents.team_agent import (
    TeamAgent, 
    DefenderTeamAgent, 
    AttackerTeamAgent,
    SupportTeamAgent
)

class TestTeamAgentManager(unittest.TestCase):
    """Test cases for the TeamAgentManager class."""
    
    def setUp(self):
        """Set up mocks for testing TeamAgentManager."""
        # Mock the TeamSystem dependency
        self.team_system = MagicMock(spec=TeamSystem)
        self.team_system.teams = {
            'team1': {'id': 'team1', 'members': ['agent1', 'agent2'], 'roles': {'agent1': 'leader', 'agent2': 'support'}, 'formation': 'triangle'}
        }
        # Mock get_team_color to return a default color
        self.team_system.get_team_color.return_value = (100, 100, 255)
        
        # Mock the PersonalitySystem dependency (optional, used for role assignment)
        self.personality_system = MagicMock()
        
        # Mock get_agent_personality to return a default profile
        mock_profile = MagicMock()
        mock_profile.get_trait.side_effect = lambda trait: 0.5 # Default trait value
        self.personality_system.get_agent_personality.return_value = mock_profile
        
        # Mock get_leadership_hierarchy
        self.personality_system.get_leadership_hierarchy.return_value = [('agent1', 0.9), ('agent2', 0.4)]
        
        # Mock the SystemManager to return our mocks
        self.mock_system_manager = MagicMock()
        def get_system_side_effect(name):
            if name == 'TeamSystem':
                return self.team_system
            if name == 'PersonalitySystem':
                return self.personality_system
            return None
        self.mock_system_manager.get_system.side_effect = get_system_side_effect
        # Inject the mock manager into the global singleton location if needed by the code under test
        # This is tricky and might require patching the singleton directly where it's imported/used
        # For now, assume TeamAgentManager gets dependencies explicitly or via a passed-in manager
        
        # Mock the AgentFactory
        self.mock_agent_factory = patch('systems.agents.team_agent_integration.create_agent').start()
        self.addCleanup(patch.stopall)
        
        # Mock BaseAgent subclasses to return specific mock agents
        self.mock_attacker = MagicMock(spec=AttackerTeamAgent)
        self.mock_defender = MagicMock(spec=DefenderTeamAgent)
        self.mock_support = MagicMock(spec=SupportTeamAgent)
        self.mock_scout = MagicMock()
        self.mock_base_agent = MagicMock()

        def create_agent_side_effect(agent_type, **kwargs):
            if agent_type == 'AttackerTeamAgent': return self.mock_attacker
            if agent_type == 'DefenderTeamAgent': return self.mock_defender
            if agent_type == 'SupportTeamAgent': return self.mock_support
            if agent_type == 'ScoutTeamAgent': return self.mock_scout
            # Add other types if needed
            return self.mock_base_agent # Default mock
        
        self.mock_agent_factory.side_effect = create_agent_side_effect
        
        # Instantiate the TeamAgentManager with the mocked TeamSystem
        self.manager = TeamAgentManager(self.team_system, self.personality_system)
    
    def test_create_team_with_agents(self):
        """Test creating a team with specialized agents."""
        team = self.manager.create_team_with_agents('team2', 3, 'square')
        
        # Check that team system was called correctly
        self.team_system.create_team.assert_called_with('team2', ['team2_agent_0', 'team2_agent_1', 'team2_agent_2'])
        self.team_system.change_formation.assert_called_with('team2', 'square')
        
        # Check that agents were created
        self.assertIn('team2', self.manager.team_agents)
        self.assertEqual(len(self.manager.team_agents['team2']), 3)
        
        # Verify agent positions were initialized
        self.assertIn('team2_agent_0', self.manager.agent_positions)
        self.assertEqual(self.manager.agent_positions['team2_agent_0'], (0.0, 0.0))
    
    def test_specialized_agent_creation(self):
        """Test that specialized agents are created based on roles."""
        # Create a team with roles that map to specialized agents
        self.team_system.create_team.return_value = {
            'id': 'team3',
            'members': ['team3_agent_0', 'team3_agent_1', 'team3_agent_2', 'team3_agent_3'],
            'formation': 'square',
            'leader': 'team3_agent_0',
            'roles': {
                'team3_agent_0': 'leader',
                'team3_agent_1': 'defender',
                'team3_agent_2': 'attacker',
                'team3_agent_3': 'support'
            }
        }
        
        team = self.manager.create_team_with_agents('team3', 4, 'square')
        
        # Check that specialized agents were created
        agents = self.manager.team_agents['team3']
        self.assertIsInstance(agents['team3_agent_0'], TeamAgent)  # Leader
        self.assertIsInstance(agents['team3_agent_1'], DefenderTeamAgent)  # Defender
        self.assertIsInstance(agents['team3_agent_2'], AttackerTeamAgent)  # Attacker
        self.assertIsInstance(agents['team3_agent_3'], SupportTeamAgent)  # Support
    
    def test_get_agent(self):
        """Test getting an agent by ID."""
        # Create a team first
        self.manager.create_team_with_agents('team1', 3)
        
        # Get an agent
        agent = self.manager.get_agent('team1_agent_1')
        
        # Verify it's the right agent
        self.assertIsNotNone(agent)
        self.assertEqual(agent.name, 'team1_agent_1')
        self.assertEqual(agent.team_id, 'team1')
        
        # Test getting non-existent agent
        agent = self.manager.get_agent('nonexistent')
        self.assertIsNone(agent)
    
    def test_update_agent_position(self):
        """Test updating an agent's position."""
        # Create a team first
        self.manager.create_team_with_agents('team1', 3)
        
        # Update an agent's position
        self.manager.update_agent_position('team1_agent_0', (100, 200))
        
        # Verify position was updated
        self.assertEqual(self.manager.agent_positions['team1_agent_0'], (100, 200))
        
        # Verify team positions were updated in team system
        self.team_system.update_team_positions.assert_called()
    
    def test_update_formation_targets(self):
        """Test updating formation targets."""
        # Create a team first
        self.manager.create_team_with_agents('team1', 3)
        
        # Update leader position
        self.manager.update_agent_position('team1_agent_0', (100, 100))
        
        # Update formation targets
        self.manager.update_formation_targets('team1')
        
        # Verify formation positions were requested from team system
        self.team_system.get_formation_positions.assert_called_with('team1', (100, 100))
        
        # Verify each agent had its formation target updated
        agents = self.manager.team_agents['team1']
        self.assertEqual(agents['team1_agent_0'].formation_target, (0, 0))
        self.assertEqual(agents['team1_agent_1'].formation_target, (50, 50))
        self.assertEqual(agents['team1_agent_2'].formation_target, (100, 0))
        
        # Verify formation bonus was updated
        for agent in agents.values():
            self.assertEqual(agent.formation_bonus, 1.2)
    
    def test_update_all_teams(self):
        """Test updating all teams."""
        # Create multiple teams
        self.manager.create_team_with_agents('team1', 3)
        self.manager.create_team_with_agents('team2', 3)
        
        # Update all teams
        self.manager.update_all_teams()
        
        # Verify formation targets were updated for both teams
        self.assertEqual(self.team_system.get_formation_positions.call_count, 2)
    
    def test_suggest_team_ability(self):
        """Test suggesting team abilities."""
        # Create a team with specialized agents
        self.team_system.create_team.return_value = {
            'id': 'team4',
            'members': ['team4_agent_0', 'team4_agent_1', 'team4_agent_2'],
            'formation': 'triangle',
            'leader': 'team4_agent_0',
            'roles': {
                'team4_agent_0': 'leader',
                'team4_agent_1': 'defender',
                'team4_agent_2': 'attacker'
            }
        }
        
        team = self.manager.create_team_with_agents('team4', 3)
        
        # Set positions
        self.manager.update_agent_position('team4_agent_0', (0, 0))
        self.manager.update_agent_position('team4_agent_1', (50, 50))
        self.manager.update_agent_position('team4_agent_2', (100, 0))
        
        # Patch random to always return 0.05 (below threshold)
        with patch('random.random', return_value=0.05):
            # Get ability suggestion
            suggestion = self.manager.suggest_team_ability('team4')
            
            # Should suggest an ability since random is below threshold
            self.assertIsNotNone(suggestion)
            
            # Since 'team4_agent_1' is a defender, expect shield_wall
            ability, initiator, target = suggestion
            if initiator == 'team4_agent_1':
                self.assertEqual(ability, 'shield_wall')
            elif initiator == 'team4_agent_2':
                self.assertEqual(ability, 'coordinated_strike')
    
    def test_execute_team_ability(self):
        """Test executing team abilities."""
        # Create a team
        self.manager.create_team_with_agents('team1', 3)
        
        # Execute an ability
        result = self.manager.execute_team_ability(
            'team1', 'shield_wall', 'team1_agent_1', (50, 50)
        )
        
        # Verify team system was called
        self.team_system.use_team_ability.assert_called_with(
            'team1', 'shield_wall', 'team1_agent_1', (50, 50)
        )
        
        # Should return the result from team system
        self.assertTrue(result)
    
    def test_handle_combat_event(self):
        """Test handling combat events."""
        # Create a team
        self.manager.create_team_with_agents('team1', 3)
        
        # Create combat event data
        combat_data = {
            'teams': ['team1'],
            'enemy_positions': [(200, 200), (250, 250)]
        }
        
        # Handle combat event
        self.manager.handle_combat_event(combat_data)
        
        # Verify team system was called to suggest formation
        self.team_system.suggest_formation.assert_called_with('team1', [(200, 200), (250, 250)])
        
        # Verify formation was changed
        self.team_system.change_formation.assert_called_with('team1', 'arrow')

if __name__ == "__main__":
    unittest.main() 