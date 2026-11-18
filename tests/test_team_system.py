import sys
import os
import unittest
from unittest.mock import Mock

# Add parent directory to path to import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from systems.agents.team_system import TeamSystem
from systems.core.system_manager import SystemEventType

class TestTeamSystem(unittest.TestCase):
    def setUp(self):
        # Create a fresh team system for each test
        self.team_system = TeamSystem()
    
    def test_create_team(self):
        # Test creating a team
        team_id = "team1"
        agent_names = ["agent1", "agent2", "agent3"]
        
        team = self.team_system.create_team(team_id, agent_names)
        
        # Check that the team was created with correct properties
        self.assertEqual(team['id'], team_id)
        self.assertEqual(team['members'], agent_names)
        self.assertEqual(team['formation'], 'triangle')  # Default formation
        self.assertEqual(team['leader'], 'agent1')
        
        # Check that roles were assigned
        self.assertIn('roles', team)
        self.assertEqual(len(team['roles']), 3)
        
        # Check that the team is stored in the system
        self.assertIn(team_id, self.team_system.teams)
        self.assertIn(team_id, self.team_system.team_positions)
    
    def test_get_formation_positions(self):
        # Create a team
        team_id = "team1"
        agent_names = ["agent1", "agent2", "agent3"]
        self.team_system.create_team(team_id, agent_names)
        
        # Get formation positions
        leader_pos = (100, 100)
        positions = self.team_system.get_formation_positions(team_id, leader_pos)
        
        # Check the number of positions
        self.assertEqual(len(positions), 3)
        
        # Check the leader position (should be the first one)
        self.assertEqual(positions[0], leader_pos)
        
        # Check that other positions are offset from the leader
        self.assertNotEqual(positions[1], leader_pos)
        self.assertNotEqual(positions[2], leader_pos)
    
    def test_formation_score(self):
        # Create a team
        team_id = "team1"
        agent_names = ["agent1", "agent2", "agent3"]
        self.team_system.create_team(team_id, agent_names)
        
        # Set up perfect formation positions
        leader_pos = (100, 100)
        ideal_positions = self.team_system.get_formation_positions(team_id, leader_pos)
        
        # Update team positions to match ideal positions
        self.team_system.update_team_positions(team_id, ideal_positions)
        
        # Calculate formation score
        score = self.team_system.get_formation_score(team_id)
        
        # Perfect formation should have score 1.0
        self.assertEqual(score, 1.0)
        
        # Now test with imperfect formation
        imperfect_positions = [
            (100, 100),  # Leader
            (ideal_positions[1][0] + 10, ideal_positions[1][1] + 5),  # Slightly off
            (ideal_positions[2][0] - 15, ideal_positions[2][1] + 8)   # More off
        ]
        
        self.team_system.update_team_positions(team_id, imperfect_positions)
        
        # Calculate formation score again
        score = self.team_system.get_formation_score(team_id)
        
        # Score should be less than 1.0 but still positive
        self.assertLess(score, 1.0)
        self.assertGreater(score, 0.0)
    
    def test_formation_bonus(self):
        # Create a team
        team_id = "team1"
        agent_names = ["agent1", "agent2", "agent3"]
        self.team_system.create_team(team_id, agent_names)
        
        # Get the base formation bonus for triangle formation
        formation_type = 'triangle'
        base_bonus = self.team_system.formations[formation_type]['bonus']
        
        # Set up perfect formation positions
        leader_pos = (100, 100)
        ideal_positions = self.team_system.get_formation_positions(team_id, leader_pos)
        self.team_system.update_team_positions(team_id, ideal_positions)
        
        # Get the combat bonus
        bonus = self.team_system.get_formation_bonus(team_id)
        
        # Perfect formation should give full bonus
        self.assertEqual(bonus, base_bonus)
        
        # Now test with imperfect formation
        imperfect_positions = [
            (100, 100),  # Leader
            (ideal_positions[1][0] + 50, ideal_positions[1][1] + 50),  # Way off
            (ideal_positions[2][0] - 50, ideal_positions[2][1] + 50)   # Way off
        ]
        
        self.team_system.update_team_positions(team_id, imperfect_positions)
        
        # Get the combat bonus again
        bonus = self.team_system.get_formation_bonus(team_id)
        
        # Bonus should be reduced but still above 1.0
        self.assertLess(bonus, base_bonus)
        self.assertGreater(bonus, 1.0)
    
    def test_change_formation(self):
        # Create a team
        team_id = "team1"
        agent_names = ["agent1", "agent2", "agent3", "agent4"]
        team = self.team_system.create_team(team_id, agent_names)
        
        # Check default formation
        self.assertEqual(team['formation'], 'triangle')
        
        # Change to square formation
        result = self.team_system.change_formation(team_id, 'square')
        
        # Check that the formation was changed
        self.assertTrue(result)
        self.assertEqual(self.team_system.teams[team_id]['formation'], 'square')
        
        # Check that roles were updated
        roles = self.team_system.teams[team_id]['roles']
        square_roles = self.team_system.formations['square']['roles']
        
        for i, agent in enumerate(agent_names):
            expected_role = square_roles[i] if i < len(square_roles) else 'member'
            self.assertEqual(roles[agent], expected_role)
        
        # Try to change to an invalid formation
        result = self.team_system.change_formation(team_id, 'invalid_formation')
        
        # Check that the formation was not changed
        self.assertFalse(result)
        self.assertEqual(self.team_system.teams[team_id]['formation'], 'square')
    
    def test_suggest_formation(self):
        # Create a team
        team_id = "team1"
        agent_names = ["agent1", "agent2", "agent3"]
        self.team_system.create_team(team_id, agent_names)
        
        # Test with no enemies
        formation = self.team_system.suggest_formation(team_id, [])
        self.assertEqual(formation, 'line')  # Good for exploration
        
        # Test with one enemy
        formation = self.team_system.suggest_formation(team_id, [(200, 200)])
        self.assertEqual(formation, 'triangle')  # Good for focusing on a single enemy
        
        # Test with two enemies
        formation = self.team_system.suggest_formation(team_id, [(200, 200), (300, 300)])
        self.assertEqual(formation, 'arrow')  # Good for offense
        
        # Test with many enemies
        formation = self.team_system.suggest_formation(team_id, 
                                                     [(200, 200), (300, 300), 
                                                      (400, 400), (500, 500)])
        self.assertEqual(formation, 'circle')  # Good for defense
    
    def test_team_abilities(self):
        # Create a team
        team_id = "team1"
        agent_names = ["agent1", "agent2", "agent3"]
        self.team_system.create_team(team_id, agent_names)
        
        # Use a team ability
        target_pos = (200, 200)
        result = self.team_system.use_team_ability(team_id, 'shield_wall', 'agent1', target_pos)
        
        # Check that the ability was activated
        self.assertTrue(result)
        
        # Check that the ability is in active abilities
        active_abilities = self.team_system.get_active_abilities(team_id)
        self.assertEqual(len(active_abilities), 1)
        
        ability = list(active_abilities.values())[0]
        self.assertEqual(ability['name'], 'shield_wall')
        self.assertEqual(ability['initiator'], 'agent1')
        self.assertEqual(ability['target_pos'], target_pos)
        
        # Try to use an invalid ability
        result = self.team_system.use_team_ability(team_id, 'invalid_ability', 'agent1', target_pos)
        
        # Check that the ability was not activated
        self.assertFalse(result)
        
        # Update abilities with a large delta time to expire the active ability
        self.team_system._update_abilities(10.0)  # 10 seconds should be enough
        
        # Check that the ability was expired
        active_abilities = self.team_system.get_active_abilities(team_id)
        self.assertEqual(len(active_abilities), 0)
    
    def test_team_relations(self):
        # Create two teams
        team1_id = "team1"
        team2_id = "team2"
        
        self.team_system.create_team(team1_id, ["agent1", "agent2"])
        self.team_system.create_team(team2_id, ["agent3", "agent4"])
        
        # Initially, they should have no relationship
        self.assertFalse(team1_id in self.team_system.team_relations)
        
        # Update the relationship positively
        self.team_system.update_team_relations(team1_id, team2_id, 0.5)
        
        # Check that the relationship was updated
        self.assertIn(team1_id, self.team_system.team_relations)
        self.assertIn(team2_id, self.team_system.team_relations[team1_id])
        self.assertEqual(self.team_system.team_relations[team1_id][team2_id], 0.5)
        
        # Check shouldHelpAlly
        should_help = self.team_system.should_help_ally(team1_id, team2_id)
        self.assertTrue(should_help)
        
        # Update the relationship negatively
        self.team_system.update_team_relations(team1_id, team2_id, -0.8)
        
        # Relationship should now be negative
        self.assertEqual(self.team_system.team_relations[team1_id][team2_id], -0.3)
        
        # Should not help anymore
        should_help = self.team_system.should_help_ally(team1_id, team2_id)
        self.assertFalse(should_help)
    
    def test_event_handling(self):
        # Create a mock for the emit_event method
        original_emit_event = self.team_system.emit_event
        self.team_system.emit_event = Mock()
        
        # Create a team
        team_id = "team1"
        self.team_system.create_team(team_id, ["agent1", "agent2"])
        
        # Trigger the combat_started event handler
        event_data = {
            'team_id': team_id,
            'enemy_positions': [(200, 200), (300, 300)]
        }
        self.team_system._on_combat_started(event_data)
        
        # Check that emit_event was called with the right parameters
        self.team_system.emit_event.assert_called_once()
        args, kwargs = self.team_system.emit_event.call_args
        
        # First argument should be FORMATION_CHANGED
        self.assertEqual(args[0], SystemEventType.FORMATION_CHANGED)
        
        # Second argument should be a dictionary with team_id and suggested_formation
        self.assertEqual(args[1]['team_id'], team_id)
        self.assertEqual(args[1]['suggested_formation'], 'arrow')
        
        # Restore original method
        self.team_system.emit_event = original_emit_event

if __name__ == "__main__":
    unittest.main() 