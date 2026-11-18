import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
import math

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from systems.combat.team_combat_integration import TeamCombatIntegration
# Need to potentially mock BaseSystem and SystemManager if they are used internally or globally
# from systems.core.system_manager import SystemEventType, system_manager

class TestTeamCombatIntegration(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_team_system = MagicMock()
        self.mock_combat_system = MagicMock()
        self.mock_agent_system = MagicMock()
        self.mock_personality_system = MagicMock() # Optional

        # Mock agent_system attributes needed
        self.mock_agent_system.agent_targets = {}
        self.mock_agent_system.agent_threat_level = {}
        self.mock_agent_system.agent_positions = {}
        # Mock env if needed for flank maneuver target finding
        self.mock_agent_system.env = MagicMock() 

        self.team_combat_integration = TeamCombatIntegration(
            team_system=self.mock_team_system,
            combat_system=self.mock_combat_system,
            agent_system=self.mock_agent_system,
            personality_system=self.mock_personality_system
        )

        # Example team setup for mocks
        self.team1_id = "team_alpha"
        self.agent1_id = "agent_1"
        self.agent2_id = "agent_2"
        self.agent3_id = "agent_3"
        self.enemy1_id = "enemy_1"

        self.mock_team_system.get_team_id_for_agent.side_effect = lambda agent_id: self.team1_id if agent_id in [self.agent1_id, self.agent2_id, self.agent3_id] else None
        self.mock_team_system.teams = {
            self.team1_id: {
                "id": self.team1_id,
                "members": [
                    {'agent_id': self.agent1_id, 'role': 'leader'},
                    {'agent_id': self.agent2_id, 'role': 'attacker'},
                    {'agent_id': self.agent3_id, 'role': 'defender'}
                ],
                 'roles': { # Add roles dict as used by flanking maneuver
                      self.agent1_id: 'leader',
                      self.agent2_id: 'attacker',
                      self.agent3_id: 'defender'
                 }
            }
        }
        # Default mock return values
        self.mock_team_system.get_formation_score.return_value = 0.5 # Default score
        self.mock_combat_system.get_combat_stats.return_value = {'damage': 10, 'kills': 1}
        self.mock_combat_system.get_agent_effectiveness.return_value = 0.7

        # Mock agent positions
        self.mock_agent_system.agent_positions = {
            self.agent1_id: (100, 100),
            self.agent2_id: (110, 110),
            self.agent3_id: (90, 110),
            self.enemy1_id: (200, 100)
        }


    def test_initialization(self):
        """Test basic initialization and system references."""
        self.assertIsNotNone(self.team_combat_integration.team_system)
        self.assertIsNotNone(self.team_combat_integration.combat_system)
        self.assertIsNotNone(self.team_combat_integration.agent_system)
        self.assertEqual(self.team_combat_integration.team_damage, {})
        self.assertEqual(self.team_combat_integration.team_kills, {})

    def test_register_team(self):
        """Test registering a new team."""
        self.team_combat_integration.register_team(self.team1_id)
        self.assertEqual(self.team_combat_integration.team_damage.get(self.team1_id), 0)
        self.assertEqual(self.team_combat_integration.team_kills.get(self.team1_id), 0)
        self.assertEqual(self.team_combat_integration.team_abilities_used.get(self.team1_id), {})

        # Test registering again doesn't reset
        self.team_combat_integration.team_damage[self.team1_id] = 10
        self.team_combat_integration.register_team(self.team1_id)
        self.assertEqual(self.team_combat_integration.team_damage.get(self.team1_id), 10)

    def test_update_team_stats(self):
        """Test updating team stats for damage and kills."""
        # Agent 1 deals damage
        self.team_combat_integration.update_team_stats(self.agent1_id, damage=50)
        self.assertEqual(self.team_combat_integration.team_damage.get(self.team1_id), 50)
        self.assertEqual(self.team_combat_integration.team_kills.get(self.team1_id), 0)

        # Agent 2 gets a kill
        self.team_combat_integration.update_team_stats(self.agent2_id, damage=20, kill=True)
        self.assertEqual(self.team_combat_integration.team_damage.get(self.team1_id), 70)
        self.assertEqual(self.team_combat_integration.team_kills.get(self.team1_id), 1)

        # Agent not on a team
        self.team_combat_integration.update_team_stats("unknown_agent", damage=100)
        self.assertEqual(len(self.team_combat_integration.team_damage), 1) # Should not add new team

    def test_calculate_team_attack_bonus(self):
        """Test calculation of attack bonuses."""
        attacker_id = self.agent2_id # Attacker role
        target_id = self.enemy1_id
        attacker_pos = self.mock_agent_system.agent_positions[attacker_id]
        target_pos = self.mock_agent_system.agent_positions[target_id]

        # --- Test Case 1: Base bonus with formation score 0.5 ---
        self.mock_team_system.get_formation_score.return_value = 0.5
        self.mock_agent_system.agent_targets = {}
        expected_base_dmg_bonus = 1.0 + (0.5 * 0.2) # 1 + (score * coordination_bonus["damage"])
        expected_base_acc_bonus = 1.0 + (0.5 * 0.15) # 1 + (score * coordination_bonus["accuracy"])
        expected_base_crit_bonus = 1.0 + (0.5 * 0.1) # 1 + (score * 0.1)
        # Role bonus for attacker
        role_dmg = 1.2
        role_crit = 1.15
        expected_dmg = expected_base_dmg_bonus * role_dmg
        expected_acc = expected_base_acc_bonus * 1.0 # No acc bonus for attacker role
        expected_crit = expected_base_crit_bonus * role_crit

        bonuses = self.team_combat_integration.calculate_team_attack_bonus(
            attacker_id, target_id, attacker_pos, target_pos
        )
        self.assertAlmostEqual(bonuses['damage'], expected_dmg)
        self.assertAlmostEqual(bonuses['accuracy'], expected_acc)
        self.assertAlmostEqual(bonuses['critical'], expected_crit)

        # --- Test Case 2: Add coordinated attack (1 teammate) ---
        self.mock_agent_system.agent_targets = {self.agent3_id: target_id} # Agent 3 also targets enemy
        teammates_attacking = 1
        coord_dmg_add = teammates_attacking * 0.1
        coord_acc_add = teammates_attacking * 0.05
        expected_dmg_coord = (expected_base_dmg_bonus + coord_dmg_add) * role_dmg
        expected_acc_coord = (expected_base_acc_bonus + coord_acc_add) * 1.0
        expected_crit_coord = expected_base_crit_bonus * role_crit # Coord doesn't affect crit role bonus here

        bonuses_coord = self.team_combat_integration.calculate_team_attack_bonus(
            attacker_id, target_id, attacker_pos, target_pos
        )
        self.assertAlmostEqual(bonuses_coord['damage'], expected_dmg_coord)
        self.assertAlmostEqual(bonuses_coord['accuracy'], expected_acc_coord)
        self.assertAlmostEqual(bonuses_coord['critical'], expected_crit_coord)

        # --- Test Case 3: No bonus if not on team ---
        bonuses_no_team = self.team_combat_integration.calculate_team_attack_bonus(
            "unknown_agent", target_id, (0,0), target_pos
        )
        self.assertAlmostEqual(bonuses_no_team['damage'], 1.0)
        self.assertAlmostEqual(bonuses_no_team['accuracy'], 1.0)
        self.assertAlmostEqual(bonuses_no_team['critical'], 1.0)

        # --- Test Case 4: Attacking teammate (no bonus) ---
        self.mock_team_system.get_team_id_for_agent.side_effect = lambda agent_id: self.team1_id # Ensure target is on team
        bonuses_friendly = self.team_combat_integration.calculate_team_attack_bonus(
            attacker_id, self.agent3_id, attacker_pos, self.mock_agent_system.agent_positions[self.agent3_id]
        )
        self.mock_team_system.get_team_id_for_agent.side_effect = lambda agent_id: self.team1_id if agent_id in [self.agent1_id, self.agent2_id, self.agent3_id] else None # Reset side effect
        self.assertAlmostEqual(bonuses_friendly['damage'], 1.0)
        self.assertAlmostEqual(bonuses_friendly['accuracy'], 1.0)
        self.assertAlmostEqual(bonuses_friendly['critical'], 1.0)


    def test_calculate_defense_bonus(self):
        """Test calculation of defense bonuses."""
        defender_id = self.agent3_id # Defender role
        attacker_id = self.enemy1_id

        # --- Test Case 1: Base defense with formation score 0.8 ---
        self.mock_team_system.get_formation_score.return_value = 0.8
        self.mock_agent_system.agent_threat_level = {defender_id: 1} # Attacked by 1
        expected_base_defense = 1.0 - (0.8 * 0.25) # 1 - (score * coordination_bonus["defense"])
        role_modifier = 0.8 # Defender role reduction
        expected_defense = expected_base_defense * role_modifier
        bonus = self.team_combat_integration.calculate_defense_bonus(defender_id, attacker_id)
        self.assertAlmostEqual(bonus, expected_defense)

        # --- Test Case 2: Add threat level (3 attackers) ---
        self.mock_agent_system.agent_threat_level = {defender_id: 3} # Attacked by 3
        threat_level = 3
        threat_penalty = 1.0 + (threat_level - 1) * 0.10
        expected_defense_threat = min(1.0, expected_defense * threat_penalty)
        # Apply cap
        expected_defense_threat = max(0.5, expected_defense_threat)
        bonus_threat = self.team_combat_integration.calculate_defense_bonus(defender_id, attacker_id)
        self.assertAlmostEqual(bonus_threat, expected_defense_threat)

        # --- Test Case 3: No role bonus if not defender ---
        defender_id_no_role = self.agent1_id # Leader role
        self.mock_agent_system.agent_threat_level = {defender_id_no_role: 1}
        expected_defense_no_role = expected_base_defense # No role modifier
        bonus_no_role = self.team_combat_integration.calculate_defense_bonus(defender_id_no_role, attacker_id)
        self.assertAlmostEqual(bonus_no_role, expected_defense_no_role)

        # --- Test Case 4: No bonus if not on team ---
        bonus_no_team = self.team_combat_integration.calculate_defense_bonus("unknown_agent", attacker_id)
        self.assertAlmostEqual(bonus_no_team, 1.0)

        # --- Test Case 5: Max reduction cap ---
        self.mock_team_system.get_formation_score.return_value = 1.0 # Max formation
        defender_id_max = self.agent3_id # Defender role
        self.mock_agent_system.agent_threat_level = {defender_id_max: 1}
        expected_base_defense_max = 1.0 - (1.0 * 0.25) # 0.75
        expected_defense_max_role = expected_base_defense_max * role_modifier # 0.75 * 0.8 = 0.6
        # Threat penalty shouldn't apply here as threat is 1
        # Apply cap (0.6 is > 0.5, so no cap needed yet)
        bonus_max_uncapped = self.team_combat_integration.calculate_defense_bonus(defender_id_max, attacker_id)
        self.assertAlmostEqual(bonus_max_uncapped, expected_defense_max_role)
        # Now increase threat
        self.mock_agent_system.agent_threat_level = {defender_id_max: 5}
        threat_penalty_max = 1.0 + (5 - 1) * 0.10 # 1.4
        expected_defense_max_threat = expected_defense_max_role * threat_penalty_max # 0.6 * 1.4 = 0.84
        # Recalculate (no cap needed as penalty increased it)
        bonus_max_threat = self.team_combat_integration.calculate_defense_bonus(defender_id_max, attacker_id)
        self.assertAlmostEqual(bonus_max_threat, expected_defense_max_threat)
        # Test scenario where base reduction + role hits cap even without threat
        # Let's say base reduction was 0.6 -> 0.6 * 0.8 = 0.48 -> capped at 0.5
        self.team_combat_integration.coordination_bonus["defense"] = 0.4 # Increase base reduction
        self.mock_team_system.get_formation_score.return_value = 1.0
        self.mock_agent_system.agent_threat_level = {defender_id_max: 1}
        expected_base_defense_cap = 1.0 - (1.0 * 0.4) # 0.6
        expected_defense_cap_role = expected_base_defense_cap * role_modifier # 0.6 * 0.8 = 0.48
        bonus_capped = self.team_combat_integration.calculate_defense_bonus(defender_id_max, attacker_id)
        self.assertAlmostEqual(bonus_capped, 0.5) # Should be capped
        # Reset coordination bonus for subsequent tests if needed
        self.team_combat_integration.coordination_bonus["defense"] = 0.25

    # Patch system_manager at its original source
    @patch('systems.core.system_manager.system_manager')
    def test_execute_team_ability_coordinated_attack(self, mock_system_manager):
        """Test executing the coordinated attack ability."""
        ability_name = "coordinated_attack"
        initiator_id = self.agent1_id
        target_pos = (200, 100)
        duration = 5.0
        damage_boost = 1.3
        accuracy_boost = 1.2

        # Assume ability is available
        self.mock_team_system.use_team_ability.return_value = True

        # Set positions for team members (agent 2 and 3 are close)
        self.mock_agent_system.agent_positions = {
            self.agent1_id: (50, 50),
            self.agent2_id: (180, 90), # Close to target
            self.agent3_id: (210, 120), # Close to target
            "other_agent": (500, 500) # Far away
        }
        # Ensure team members list is correctly formatted
        self.mock_team_system.teams[self.team1_id]["members"] = [self.agent1_id, self.agent2_id, self.agent3_id, "other_agent"]

        result = self.team_combat_integration.execute_team_ability(
            self.team1_id, ability_name, initiator_id, target_pos
        )

        self.assertTrue(result)
        self.mock_team_system.use_team_ability.assert_called_once_with(self.team1_id, ability_name, initiator_id, target_pos)
        # Check that apply_status_effect was called for nearby agents (agent2, agent3)
        expected_calls = [
            call(self.agent2_id, 'coordinated_damage', duration, damage_boost),
            call(self.agent2_id, 'coordinated_accuracy', duration, accuracy_boost),
            call(self.agent3_id, 'coordinated_damage', duration, damage_boost),
            call(self.agent3_id, 'coordinated_accuracy', duration, accuracy_boost)
        ]
        self.mock_combat_system.apply_status_effect.assert_has_calls(expected_calls, any_order=True)
        self.assertEqual(self.mock_combat_system.apply_status_effect.call_count, 4)
        # Check event emission
        mock_system_manager.emit_event.assert_called_once_with(SystemEventType.AGENT_ACTION, {
                 'agent_id': initiator_id,
                 'action': 'team_coordinated_attack',
                 'team_id': self.team1_id,
                 'participants': 2, # agent2 and agent3
                 'target_position': target_pos
            })
        self.assertEqual(self.team_combat_integration.team_abilities_used[self.team1_id][ability_name], 1)

    # Patch system_manager at its original source
    @patch('systems.core.system_manager.system_manager')
    def test_execute_team_ability_defensive_formation(self, mock_system_manager):
        """Test executing the defensive formation ability."""
        ability_name = "defensive_formation"
        initiator_id = self.agent3_id
        duration = 10.0
        defense_multiplier = 0.7

        # Assume ability is available
        self.mock_team_system.use_team_ability.return_value = True
        # Ensure team members list is correctly formatted
        self.mock_team_system.teams[self.team1_id]["members"] = [self.agent1_id, self.agent2_id, self.agent3_id]

        result = self.team_combat_integration.execute_team_ability(
            self.team1_id, ability_name, initiator_id
        )

        self.assertTrue(result)
        self.mock_team_system.use_team_ability.assert_called_once_with(self.team1_id, ability_name, initiator_id, None)
        # Check that apply_status_effect was called for all team members
        expected_calls = [
            call(self.agent1_id, 'defensive_stance', duration, defense_multiplier),
            call(self.agent2_id, 'defensive_stance', duration, defense_multiplier),
            call(self.agent3_id, 'defensive_stance', duration, defense_multiplier)
        ]
        self.mock_combat_system.apply_status_effect.assert_has_calls(expected_calls, any_order=True)
        self.assertEqual(self.mock_combat_system.apply_status_effect.call_count, 3)
        # Check event emission
        mock_system_manager.emit_event.assert_called_once_with(SystemEventType.AGENT_ACTION, {
                 'agent_id': initiator_id,
                 'action': 'team_defensive_formation',
                 'team_id': self.team1_id,
                 'participants': 3
            })
        self.assertEqual(self.team_combat_integration.team_abilities_used[self.team1_id][ability_name], 1)

    # Patch system_manager at its original source
    @patch('systems.core.system_manager.system_manager')
    def test_execute_team_ability_flanking_maneuver(self, mock_system_manager):
        """Test executing the flanking maneuver ability (checks event emission)."""
        ability_name = "flanking_maneuver"
        initiator_id = self.agent1_id
        target_pos = (200, 100)
        target_id = self.enemy1_id # Identified target
        effect_duration = 8.0
        flanking_bonus_strength = 1.25

        # Mock environment query result
        self.mock_agent_system.env.get_nearby_agents.return_value = [
            MagicMock(name=self.enemy1_id, position=(200, 100)),
            MagicMock(name=self.agent1_id, position=(100, 100)) # Self should be ignored
        ]
        # Mock team system call within the method
        self.mock_team_system.get_team_id_for_agent.side_effect = lambda agent_id: self.team1_id if agent_id in [self.agent1_id, self.agent2_id, self.agent3_id] else None

        # Assume ability is available
        self.mock_team_system.use_team_ability.return_value = True
        # Ensure roles are set for flanker selection
        self.mock_team_system.teams[self.team1_id]["roles"] = {self.agent1_id: 'leader', self.agent2_id: 'attacker', self.agent3_id: 'defender'}
        # Agent 2 (attacker) should be selected as flanker
        selected_flanker = self.agent2_id

        result = self.team_combat_integration.execute_team_ability(
            self.team1_id, ability_name, initiator_id, target_pos
        )

        self.assertTrue(result)
        self.mock_team_system.use_team_ability.assert_called_once_with(self.team1_id, ability_name, initiator_id, target_pos)
        # Check that event was emitted with correct flanker data
        # Note: Flanking position calculation is complex to assert exactly without re-implementing
        # We check that the event was called and the flanker ID is correct
        mock_system_manager.emit_event.assert_called_once()
        args, kwargs = mock_system_manager.emit_event.call_args
        self.assertEqual(args[0], SystemEventType.AGENT_ACTION)
        event_data = args[1]
        self.assertEqual(event_data['action'], 'team_flanking_maneuver_start')
        self.assertEqual(event_data['initiator_id'], initiator_id)
        self.assertEqual(event_data['team_id'], self.team1_id)
        self.assertEqual(event_data['target_id'], target_id)
        self.assertIn(selected_flanker, event_data['flankers'])
        self.assertIsInstance(event_data['flankers'][selected_flanker], tuple)
        # Check placeholder bonus application was called
        self.mock_combat_system.apply_status_effect.assert_called_once_with(selected_flanker, 'flanking_bonus', effect_duration, flanking_bonus_strength)
        self.assertEqual(self.team_combat_integration.team_abilities_used[self.team1_id][ability_name], 1)

    def test_execute_team_ability_not_available(self):
        """Test executing an ability when TeamSystem says it's not available."""
        ability_name = "coordinated_attack"
        initiator_id = self.agent1_id
        target_pos = (200, 100)

        # Mock ability not available
        self.mock_team_system.use_team_ability.return_value = False

        result = self.team_combat_integration.execute_team_ability(
            self.team1_id, ability_name, initiator_id, target_pos
        )

        self.assertFalse(result)
        self.mock_team_system.use_team_ability.assert_called_once_with(self.team1_id, ability_name, initiator_id, target_pos)
        self.mock_combat_system.apply_status_effect.assert_not_called()

    def test_get_team_combat_stats(self):
        """Test retrieving team combat stats."""
        # Set some stats first
        self.team_combat_integration.register_team(self.team1_id)
        self.team_combat_integration.team_damage[self.team1_id] = 150
        self.team_combat_integration.team_kills[self.team1_id] = 3
        self.team_combat_integration.team_abilities_used[self.team1_id] = {'coordinated_attack': 2}

        # Mock combat system to return stats for members
        member_stats = {
            self.agent1_id: {'damage_dealt': 50, 'kills': 1, 'accuracy': 0.8},
            self.agent2_id: {'damage_dealt': 70, 'kills': 1, 'accuracy': 0.7},
            self.agent3_id: {'damage_dealt': 30, 'kills': 1, 'accuracy': 0.9}
        }
        self.mock_combat_system.get_combat_stats.side_effect = lambda agent_id: member_stats.get(agent_id, {})

        stats = self.team_combat_integration.get_team_combat_stats(self.team1_id)

        self.assertEqual(stats['damage_dealt'], 150)
        self.assertEqual(stats['kills'], 3)
        self.assertEqual(stats['abilities_used'], {'coordinated_attack': 2})
        self.assertEqual(len(stats['members']), 3)

        # Check member stats structure
        member1_stat = next(m for m in stats['members'] if m['agent_id'] == self.agent1_id)
        self.assertEqual(member1_stat['stats']['damage_dealt'], 50)
        self.assertEqual(member1_stat['stats']['role'], 'leader')

        # Test getting stats for all teams (though we only have one)
        all_stats = self.team_combat_integration.get_team_combat_stats()
        self.assertIn(self.team1_id, all_stats)
        self.assertEqual(all_stats[self.team1_id]['kills'], 3)

        # Test getting stats for non-existent team
        no_stats = self.team_combat_integration.get_team_combat_stats("non_existent_team")
        self.assertEqual(no_stats, {})

    def test_calculate_team_effectiveness(self):
        """Test calculating overall team effectiveness."""
        # Set up stats needed for calculation
        self.team_combat_integration.register_team(self.team1_id)
        self.team_combat_integration.team_damage[self.team1_id] = 600 # > 500 cap
        self.team_combat_integration.team_kills[self.team1_id] = 7 # > 5 cap

        # Mock formation score and member effectiveness
        formation_score = 0.75
        self.mock_team_system.get_formation_score.return_value = formation_score
        member_effectiveness = {
            self.agent1_id: 0.8,
            self.agent2_id: 0.9,
            self.agent3_id: 0.7
        }
        self.mock_combat_system.get_agent_effectiveness.side_effect = lambda agent_id: member_effectiveness.get(agent_id, 0.5)

        avg_effectiveness = (0.8 + 0.9 + 0.7) / 3.0
        kills_contrib = min(1.0, 7 / 5.0) * 0.2 # Capped at 1.0
        damage_contrib = min(1.0, 600 / 500.0) * 0.1 # Capped at 1.0

        expected_effectiveness = (
            avg_effectiveness * 0.4 +
            formation_score * 0.3 +
            kills_contrib +
            damage_contrib
        )

        effectiveness = self.team_combat_integration.calculate_team_effectiveness(self.team1_id)
        self.assertAlmostEqual(effectiveness, expected_effectiveness)

        # Test edge case: no members
        self.mock_team_system.teams[self.team1_id]["members"] = []
        effectiveness_no_members = self.team_combat_integration.calculate_team_effectiveness(self.team1_id)
        self.assertEqual(effectiveness_no_members, 0.0)

        # Test edge case: team doesn't exist
        effectiveness_no_team = self.team_combat_integration.calculate_team_effectiveness("no_team")
        self.assertEqual(effectiveness_no_team, 0.0)

# Final check for main guard
if __name__ == '__main__':
    unittest.main() 