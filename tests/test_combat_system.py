import unittest
import sys
import random
from unittest.mock import MagicMock, patch, call
import numpy as np
import os
import math

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from systems.combat.combat_system import CombatSystem, CoverSystem, StatusEffect
from systems.combat.team_combat_integration import TeamCombatIntegration
from systems.personality.personality_system import PersonalitySystem
from systems.environment.hazard_cover_system import HazardCoverSystem
from config.unified_config import UnifiedConfig # Import the actual config class

# Default weapon config data for testing (mirroring parts of unified_config structure)
DEFAULT_WEAPON_DATA = {
    "standard": { "damage": 10, "crit_chance": 0.1, "crit_multiplier": 1.5, "range": 150.0, "status_effect": None },
    "heavy": { "damage": 20, "crit_chance": 0.05, "crit_multiplier": 1.8, "range": 120.0, "status_effect": "slow" },
    "rapid": { "damage": 5, "crit_chance": 0.15, "crit_multiplier": 1.3, "range": 180.0, "status_effect": None },
    "sniper": { "damage": 30, "crit_chance": 0.2, "crit_multiplier": 2.5, "range": 300.0, "status_effect": "disable" }
}

# Default config values potentially needed
DEFAULT_CONFIG = {
    "combat": {
        "CRITICAL_HIT_BASE_MULTIPLIER": 1.5, # Default if weapon doesn't specify
        "MAX_RANGE_PENALTY_FACTOR": 0.5,
        "OUTSIDE_ZONE_VULNERABILITY": 1.2,
        "DEFAULT_WEAPON_STATS": DEFAULT_WEAPON_DATA['standard'],
        "WEAPON_STATS": DEFAULT_WEAPON_DATA,
        "BASE_ACCURACY": 0.85 
    },
    "personality": {
        "NEUROTICISM_DAMAGE_INCREASE_FACTOR": 0.1, # Example value
        "CONSCIENTIOUSNESS_DAMAGE_REDUCTION_FACTOR": 0.05 # Example value
    },
     "team": { # Example values for team bonuses
        "MAX_FORMATION_BONUS": 0.2,
        "MAX_TEAM_ATTACK_BONUS": 0.15,
        "MAX_TEAM_DEFENSE_BONUS": 0.25
    },
    "status_effects": {
         "Frenzy": {"damage_multiplier": 1.3},
         "Weakened": {"damage_multiplier": 0.7},
         "Vulnerable": {"damage_taken_multiplier": 1.4},
         "Fortified": {"damage_taken_multiplier": 0.6}
         # Add other effects as needed for tests
    },
    "environment": {
         "HAZARDS": {
             "acid_pool": {"damage": 5, "effect": "corrode"}
             # Add other hazards if needed
         },
         "WEATHER_EFFECTS": {
             "Fog": {"damage_reduction": 0.1},
             "Storm": {"damage_increase": 0.05}
             # Add other weather effects if needed
         },
         "COVER_PROTECTION_FACTOR": 0.5 # Example value
    }
}

# --- Update WEAPON_STATS in DEFAULT_CONFIG to include range and accuracy_mod ---
DEFAULT_CONFIG["combat"]["WEAPON_STATS"] = {
    "standard": {"damage": 10, "crit_chance": 0.1, "crit_multiplier": 1.5, "range": 150.0, "accuracy_mod": 1.0, "status_effect": None},
    "heavy":    {"damage": 20, "crit_chance": 0.05, "crit_multiplier": 1.8, "range": 120.0, "accuracy_mod": 0.8, "status_effect": "slow"},
    "rapid":    {"damage": 5, "crit_chance": 0.15, "crit_multiplier": 1.3, "range": 180.0, "accuracy_mod": 0.9, "status_effect": None},
    "sniper":   {"damage": 30, "crit_chance": 0.2, "crit_multiplier": 2.5, "range": 300.0, "accuracy_mod": 1.2, "status_effect": "disable"},
    "status_gun": {"damage": 2, "crit_chance": 0.05, "crit_multiplier": 1.0, "range": 100.0, "accuracy_mod": 0.95, "applies_status": {"type": "poison", "duration": 5.0, "strength": 1.0}}
}
# Remove the separate DEFAULT_WEAPON_DATA as it's now embedded

# Mock base class for systems if needed
class MockBaseSystem:
    def get_system(self, name): return None
    def get_shared_state(self, key, default=None): return default

class MockPersonalitySystem:
    def get_effect_value(self, agent_id, effect_name):
        # Return default values for tests, can be overridden
        if effect_name == 'critical_chance_bonus': return 0.0
        if effect_name == 'damage_bonus': return 0.0
        if effect_name == 'damage_reduction': return 0.0
        return 0.0

    def get_agent_traits(self, agent_id):
        return {}

class MockHazardCoverSystem:
    def check_line_of_sight(self, x1, y1, x2, y2):
        # Default: clear line of sight, no protection
        return (True, 0.0)

class MockTeamCombatIntegration:
    def calculate_team_attack_bonus(self, attacker_id, target_id, attacker_pos, target_pos):
        # Default: no bonus
        return {"damage": 1.0, "accuracy": 1.0, "critical": 1.0}

    def calculate_defense_bonus(self, defender_id, attacker_id):
        # Default: no bonus (multiplier is 1.0)
        return 1.0

class TestCoverSystem(unittest.TestCase):
    def setUp(self):
        self.cover_system = CoverSystem()
        self.cover_system.add_cover(100, 100, 100)
        
    def test_add_cover(self):
        self.assertEqual(len(self.cover_system.cover_points), 1)
        self.cover_system.add_cover(200, 200, 200)
        self.assertEqual(len(self.cover_system.cover_points), 2)
        
    def test_check_cover(self):
        # Target directly behind cover from attacker
        self.assertTrue(self.cover_system.check_cover(50, 100, 150, 100))
        
        # Target not behind cover (different angle)
        self.assertFalse(self.cover_system.check_cover(50, 50, 150, 150))
        
        # Cover between attacker and target but too far from line
        self.assertFalse(self.cover_system.check_cover(0, 0, 200, 200))

class TestStatusEffect(unittest.TestCase):
    def setUp(self):
        self.effect = StatusEffect('slow', 3.0, 0.5)
        
    def test_apply_effect(self):
        # Test slow effect (multiplies by 0.5)
        self.assertEqual(self.effect.apply_effect(10), 5)
        
        # Test poison effect (subtracts 1)
        self.assertEqual(self.effect.apply_effect(10, 'poison'), 9)
        
        # Test boost effect (multiplies by 1.5)
        self.assertEqual(self.effect.apply_effect(10, 'boost'), 15)
        
        # Test shield effect (adds 20)
        self.assertEqual(self.effect.apply_effect(10, 'shield'), 30)
        
        # Test unknown effect (returns original value)
        self.assertEqual(self.effect.apply_effect(10, 'unknown'), 10)

class TestCombatSystemDamageCalc(unittest.TestCase):

    @patch('systems.combat.combat_system.config', new_callable=UnifiedConfig)
    def setUp(self, mock_config):
        """Set up test fixtures before each test method."""
        # Mock config values needed for calculations
        mock_config._config = {
            'combat': {
                'BASE_ACCURACY': 0.8,
                'BASE_DAMAGE': 10,
                'CRITICAL_CHANCE': 0.1,
                'CRITICAL_MULTIPLIER': 2.0,
                'CRITICAL_STATUS_CHANCE': 0.3,
                'CRITICAL_STATUS_EFFECTS': [{'type': 'burn', 'duration': 2.0, 'strength': 0.8}],
                'WEAPONS': {
                    'standard': {'damage_multiplier': 1.0, 'crit_chance_mod': 1.0, 'crit_multiplier_mod': 1.0},
                    'heavy': {'damage_multiplier': 1.5, 'crit_chance_mod': 0.8, 'crit_multiplier_mod': 1.1},
                    'sniper': {'damage_multiplier': 2.5, 'crit_chance_mod': 1.5, 'crit_multiplier_mod': 1.2}
                }
            }
        }
        self.mock_config = mock_config

        self.mock_personality = MockPersonalitySystem()
        self.mock_hazard_cover = MockHazardCoverSystem()
        self.mock_team_combat = MockTeamCombatIntegration()

        # Patch system_manager globally for this test module if CombatSystem uses it directly
        self.patcher = patch('systems.combat.combat_system.system_manager')
        self.mock_system_manager = self.patcher.start()
        self.mock_system_manager.get_system.return_value = None # Default to no other systems found

        self.combat_system = CombatSystem(
            personality_system=self.mock_personality,
            hazard_cover_system=self.mock_hazard_cover,
            team_combat_integration=self.mock_team_combat
        )
        # Ensure agents are registered for stat tracking
        self.attacker_id = "attacker_1"
        self.target_id = "target_1"
        self.combat_system.register_agent(self.attacker_id)
        self.combat_system.register_agent(self.target_id)

        self.attacker_pos = (100, 100)
        self.target_pos = (200, 100)
        self.base_damage = 10.0

    def tearDown(self):
        self.patcher.stop()

    def test_base_damage(self):
        """Test damage calculation with no modifiers."""
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage, self.base_damage)
        # Check event emission (optional but good)
        # self.mock_system_manager.emit_event.assert_called_once() 

    def test_weapon_multiplier(self):
        """Test damage modification by weapon type."""
        # Heavy weapon multiplier = 1.5
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='heavy'
        )
        self.assertAlmostEqual(final_damage, self.base_damage * 1.5)

        # Sniper weapon multiplier = 2.5
        final_damage_sniper = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='sniper'
        )
        self.assertAlmostEqual(final_damage_sniper, self.base_damage * 2.5)

        # Unknown weapon type (should use default 1.0 multiplier)
        final_damage_unknown = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='unknown'
        )
        self.assertAlmostEqual(final_damage_unknown, self.base_damage * 1.0)

    @patch('random.random')
    def test_critical_hit_chance_and_multiplier(self, mock_random):
        """Test critical hit calculation including modifiers."""
        # --- Test Case 1: No Crit (random > final chance) ---
        mock_random.return_value = 0.5 # Higher than base 0.1 chance
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage, self.base_damage)
        self.assertEqual(self.combat_system.critical_hits.get(self.attacker_id, 0), 0)

        # --- Test Case 2: Base Crit (random < base chance) ---
        mock_random.return_value = 0.05 # Lower than base 0.1 chance
        expected_crit_damage = self.base_damage * self.mock_config.combat['CRITICAL_MULTIPLIER'] # 10 * 2.0 = 20
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage, expected_crit_damage)
        self.assertEqual(self.combat_system.critical_hits.get(self.attacker_id, 0), 1)
        self.combat_system.critical_hits[self.attacker_id] = 0 # Reset count for next test

        # --- Test Case 3: Weapon Modifier (Sniper) ---
        # Base chance = 0.1, Sniper mod = 1.5 -> final chance = 0.15
        # Base multiplier = 2.0, Sniper mod = 1.2 -> final multiplier = 2.4
        mock_random.return_value = 0.12 # Should crit ( < 0.15)
        expected_sniper_damage = self.base_damage * 2.5 # Weapon base damage mult
        expected_sniper_crit_damage = expected_sniper_damage * (self.mock_config.combat['CRITICAL_MULTIPLIER'] * 1.2)
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='sniper'
        )
        self.assertAlmostEqual(final_damage, expected_sniper_crit_damage)
        self.assertEqual(self.combat_system.critical_hits.get(self.attacker_id, 0), 1)
        self.combat_system.critical_hits[self.attacker_id] = 0

        # --- Test Case 4: Personality Modifier ---
        # Base chance = 0.1. Personality gives +20% bonus (effect_value=0.2) -> final = 0.1 * 1.2 = 0.12
        self.mock_personality.get_effect_value = MagicMock(side_effect=lambda aid, effect: 0.2 if effect == 'critical_chance_bonus' else 0.0)
        mock_random.return_value = 0.11 # Should crit
        expected_crit_damage = self.base_damage * self.mock_config.combat['CRITICAL_MULTIPLIER'] # Base multiplier
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage, expected_crit_damage)
        self.assertEqual(self.combat_system.critical_hits.get(self.attacker_id, 0), 1)
        self.combat_system.critical_hits[self.attacker_id] = 0
        self.mock_personality.get_effect_value = MockPersonalitySystem().get_effect_value # Reset mock

        # --- Test Case 5: Team Modifier ---
        # Base chance = 0.1. Team bonus gives 1.5x crit chance -> final = 0.1 * 1.5 = 0.15
        self.mock_team_combat.calculate_team_attack_bonus = MagicMock(return_value={
            "damage": 1.0, "accuracy": 1.0, "critical": 1.5
        })
        mock_random.return_value = 0.14 # Should crit
        expected_crit_damage = self.base_damage * self.mock_config.combat['CRITICAL_MULTIPLIER'] # Base multiplier
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage, expected_crit_damage)
        self.assertEqual(self.combat_system.critical_hits.get(self.attacker_id, 0), 1)
        self.combat_system.critical_hits[self.attacker_id] = 0
        self.mock_team_combat.calculate_team_attack_bonus = MockTeamCombatIntegration().calculate_team_attack_bonus # Reset mock

        # --- Test Case 6: Combined Modifiers (Sniper + Pers + Team) ---
        # Base=0.1, Weapon=1.5, Pers=1.2, Team=1.5 -> Final = 0.1 * 1.5 * 1.2 * 1.5 = 0.27
        # BaseMult=2.0, Weapon=1.2 -> Final Mult = 2.4
        self.mock_personality.get_effect_value = MagicMock(side_effect=lambda aid, effect: 0.2 if effect == 'critical_chance_bonus' else 0.0)
        self.mock_team_combat.calculate_team_attack_bonus = MagicMock(return_value={
            "damage": 1.0, "accuracy": 1.0, "critical": 1.5 # Assume team only affects crit chance here
        })
        mock_random.return_value = 0.26 # Should crit
        expected_base_sniper_damage = self.base_damage * 2.5 # Sniper base damage
        expected_final_crit_multiplier = self.mock_config.combat['CRITICAL_MULTIPLIER'] * 1.2 # From sniper
        expected_combined_crit_damage = expected_base_sniper_damage * expected_final_crit_multiplier

        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='sniper'
        )
        self.assertAlmostEqual(final_damage, expected_combined_crit_damage)
        self.assertEqual(self.combat_system.critical_hits.get(self.attacker_id, 0), 1)
        self.combat_system.critical_hits[self.attacker_id] = 0
        # Reset mocks
        self.mock_personality.get_effect_value = MockPersonalitySystem().get_effect_value
        self.mock_team_combat.calculate_team_attack_bonus = MockTeamCombatIntegration().calculate_team_attack_bonus

    def test_attacker_status_effect(self):
        """Test damage modification by attacker status effects."""
        # Apply a damage boost effect
        self.combat_system.apply_status_effect(self.attacker_id, 'damage_boost', duration=5.0, strength=1.5)
        # Expected damage = base * boost = 10 * 1.5 = 15
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage, self.base_damage * 1.5)
        # Clear effects for subsequent tests
        self.combat_system.active_status_effects[self.attacker_id] = []

    def test_team_attack_bonus(self):
        """Test damage modification by team attack bonus."""
        # Mock team combat integration to return a damage bonus
        self.mock_team_combat.calculate_team_attack_bonus = MagicMock(return_value={
            "damage": 1.2, "accuracy": 1.0, "critical": 1.0
        })
        # Expected damage = base * bonus = 10 * 1.2 = 12
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage, self.base_damage * 1.2)
        # Reset mock
        self.mock_team_combat.calculate_team_attack_bonus = MockTeamCombatIntegration().calculate_team_attack_bonus

    def test_attacker_personality_bonus(self):
        """Test damage modification by attacker personality."""
        # Mock personality to return a damage bonus (e.g., high aggression)
        self.mock_personality.get_effect_value = MagicMock(side_effect=lambda aid, effect: 0.3 if effect == 'damage_bonus' else 0.0)
        # Expected damage = base * (1 + bonus) = 10 * (1 + 0.3) = 13
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage, self.base_damage * 1.3)
        # Reset mock
        self.mock_personality.get_effect_value = MockPersonalitySystem().get_effect_value

    def test_cover_modifier(self):
        """Test damage reduction from cover."""
        # Mock cover system to return protection
        # Case 1: Partial cover (e.g., 40% protection -> 0.6x damage multiplier)
        self.mock_hazard_cover.check_line_of_sight = MagicMock(return_value=(True, 0.4))
        final_damage_partial = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage_partial, self.base_damage * (1.0 - 0.4))

        # Case 2: LoS blocked (assume 80% protection -> 0.2x damage multiplier)
        self.mock_hazard_cover.check_line_of_sight = MagicMock(return_value=(False, 0.0)) # LoS False
        final_damage_blocked = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage_blocked, self.base_damage * (1.0 - 0.8)) # Uses 80% default block

        # Case 3: No cover
        self.mock_hazard_cover.check_line_of_sight = MagicMock(return_value=(True, 0.0)) # Reset
        final_damage_no_cover = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage_no_cover, self.base_damage)
        # Reset mock
        self.mock_hazard_cover.check_line_of_sight = MockHazardCoverSystem().check_line_of_sight

    def test_team_defense_bonus(self):
        """Test damage reduction from team defense bonus."""
        # Mock team combat integration to return a defense bonus (e.g., 0.7 multiplier)
        self.mock_team_combat.calculate_defense_bonus = MagicMock(return_value=0.7)
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage, self.base_damage * 0.7)
        # Reset mock
        self.mock_team_combat.calculate_defense_bonus = MockTeamCombatIntegration().calculate_defense_bonus

    def test_target_status_effect(self):
        """Test damage modification by target status effects."""
        # Case 1: Defense boost (e.g., 0.6 multiplier)
        self.combat_system.apply_status_effect(self.target_id, 'defense_boost', duration=5.0, strength=0.6)
        final_damage_boost = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage_boost, self.base_damage * 0.6)
        self.combat_system.active_status_effects[self.target_id] = [] # Clear effect

        # Case 2: Vulnerability (e.g., 1.5 multiplier)
        self.combat_system.apply_status_effect(self.target_id, 'vulnerability', duration=5.0, strength=1.5)
        final_damage_vuln = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage_vuln, self.base_damage * 1.5)
        self.combat_system.active_status_effects[self.target_id] = [] # Clear effect

    def test_target_personality_bonus(self):
        """Test damage modification by target personality."""
        # Mock personality to return damage reduction (e.g., high conscientiousness)
        self.mock_personality.get_effect_value = MagicMock(side_effect=lambda aid, effect: 0.2 if aid == self.target_id and effect == 'damage_reduction' else 0.0)
        # Expected damage = base * (1 - reduction) = 10 * (1 - 0.2) = 8
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard'
        )
        self.assertAlmostEqual(final_damage, self.base_damage * 0.8)
        # Reset mock
        self.mock_personality.get_effect_value = MockPersonalitySystem().get_effect_value

    def test_environmental_context(self):
        """Test damage modification by environmental context."""
        # Case 1: Storm (+10% damage)
        env_context_storm = {'weather': 'storm', 'in_damage_zone': False}
        final_damage_storm = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard', environment_context=env_context_storm
        )
        self.assertAlmostEqual(final_damage_storm, self.base_damage * 1.1)

        # Case 2: Damage Zone (+20% damage)
        env_context_zone = {'weather': 'clear', 'in_damage_zone': True}
        final_damage_zone = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard', environment_context=env_context_zone
        )
        self.assertAlmostEqual(final_damage_zone, self.base_damage * 1.2)

        # Case 3: Both (+32% damage: 1.1 * 1.2 = 1.32)
        env_context_both = {'weather': 'storm', 'in_damage_zone': True}
        final_damage_both = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard', environment_context=env_context_both
        )
        self.assertAlmostEqual(final_damage_both, self.base_damage * 1.1 * 1.2)

        # Case 4: No relevant context
        env_context_none = {'weather': 'clear', 'in_damage_zone': False}
        final_damage_none = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type='standard', environment_context=env_context_none
        )
        self.assertAlmostEqual(final_damage_none, self.base_damage)

    @patch('random.random')
    def test_combined_modifiers(self, mock_random):
        """Test a scenario with multiple modifiers active."""
        # --- Setup Modifiers ---
        weapon_type = 'heavy' # dmg=1.5, crit_mult_mod=1.1
        # Attacker:
        self.combat_system.apply_status_effect(self.attacker_id, 'damage_boost', duration=5.0, strength=1.2)
        self.mock_personality.get_effect_value = MagicMock(side_effect=lambda aid, effect: 0.1 if aid == self.attacker_id and effect == 'damage_bonus' else (0.1 if aid == self.target_id and effect == 'damage_reduction' else 0.0))
        self.mock_team_combat.calculate_team_attack_bonus = MagicMock(return_value={"damage": 1.1, "accuracy": 1.0, "critical": 1.0})
        # Target:
        self.mock_hazard_cover.check_line_of_sight = MagicMock(return_value=(True, 0.2)) # 20% protection -> 0.8x mult
        self.mock_team_combat.calculate_defense_bonus = MagicMock(return_value=0.9) # 10% reduction
        self.combat_system.apply_status_effect(self.target_id, 'vulnerability', duration=5.0, strength=1.1) # 1.1x mult
        # Environment:
        env_context = {'weather': 'storm', 'in_damage_zone': False} # 1.1x mult
        # Crit:
        mock_random.return_value = 0.05 # Assume crit happens (base chance 0.1)

        # --- Expected Calculation --- #
        # 1. Base Damage: 10
        # 2. Weapon Mult: 10 * 1.5 = 15
        # 3. Crit: Yes. BaseMult=2.0, WeaponMod=1.1 -> FinalMult=2.2. Damage = 15 * 2.2 = 33
        # 4. Attacker Status: 33 * 1.2 = 39.6
        # 5. Team Attack: 39.6 * 1.1 = 43.56
        # 6. Attacker Pers: 43.56 * (1 + 0.1) = 47.916
        # 7. Cover: 47.916 * (1 - 0.2) = 38.3328
        # 8. Team Defense: 38.3328 * 0.9 = 34.49952
        # 9. Target Status: 34.49952 * 1.1 = 37.949472
        # 10. Target Pers: 37.949472 * (1 - 0.1) = 34.1545248
        # 11. Environment: 34.1545248 * 1.1 = 37.56997728
        # 12. Final (non-negative): 37.56997728
        expected_damage = 37.56997728

        # --- Run Calculation --- #
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id, self.attacker_pos, self.target_pos,
            self.base_damage, weapon_type=weapon_type, environment_context=env_context
        )

        # --- Assert --- #
        self.assertAlmostEqual(final_damage, expected_damage, places=5)

        # Check stats were updated
        self.assertEqual(self.combat_system.critical_hits.get(self.attacker_id, 0), 1)
        self.assertEqual(self.combat_system.hits.get(self.attacker_id, 0), 1)
        self.assertAlmostEqual(self.combat_system.damage_dealt.get(self.attacker_id, 0), expected_damage, places=5)

        # Clean up mocks/state for other tests
        self.combat_system.active_status_effects[self.attacker_id] = []
        self.combat_system.active_status_effects[self.target_id] = []
        self.mock_personality.get_effect_value = MockPersonalitySystem().get_effect_value
        self.mock_team_combat.calculate_team_attack_bonus = MockTeamCombatIntegration().calculate_team_attack_bonus
        self.mock_hazard_cover.check_line_of_sight = MockHazardCoverSystem().check_line_of_sight
        self.mock_team_combat.calculate_defense_bonus = MockTeamCombatIntegration().calculate_defense_bonus

# Add more test methods below...

class TestCombatSystem(unittest.TestCase):
    def setUp(self):
        """Set up the CombatSystem instance and mocks for each test."""
        # Mock dependencies
        self.mock_personality_system = MagicMock(spec=PersonalitySystem)
        self.mock_hazard_cover_system = MagicMock(spec=HazardCoverSystem)
        self.mock_team_system = MagicMock() # Replace with spec if available
        self.mock_team_combat_integration = MagicMock() # Replace with spec if available
        self.mock_config = MagicMock()

        # Configure the mock_config to return specific values using side_effect or configure_mock
        # This setup makes the mock config behave like the UnifiedConfig's get method
        def config_get_side_effect(section, key, default=None):
            if section in DEFAULT_CONFIG and key in DEFAULT_CONFIG[section]:
                return DEFAULT_CONFIG[section][key]
            # Handle nested keys like 'combat.WEAPON_STATS' if necessary, or adjust structure
            # For simplicity here, direct access is assumed based on DEFAULT_CONFIG structure
            return default

        self.mock_config.get.side_effect = config_get_side_effect
        self.mock_config.combat = DEFAULT_CONFIG['combat']
        self.mock_config.personality = DEFAULT_CONFIG['personality']
        self.mock_config.team = DEFAULT_CONFIG['team']
        self.mock_config.status_effects = DEFAULT_CONFIG['status_effects']
        self.mock_config.environment = DEFAULT_CONFIG['environment']


        # Instantiate CombatSystem with mocks
        self.combat_system = CombatSystem(
            personality_system=self.mock_personality_system,
            hazard_cover_system=self.mock_hazard_cover_system,
            config=self.mock_config # Pass the mock config
        )
        # Inject mocks for team systems if CombatSystem uses them directly (adjust as needed)
        self.combat_system.team_system = self.mock_team_system
        self.combat_system.team_combat_integration = self.mock_team_combat_integration

        # Reset stats and effects before each test
        self.combat_system.reset_stats()
        self.combat_system.active_status_effects = {}

        # Common test data
        self.attacker_id = "agent_A"
        self.target_id = "agent_B"
        self.attacker_pos = (100, 100)
        self.target_pos = (150, 100) # 50 units away
        self.environment_context = {"weather": "clear", "is_outside_safe_zone": False}
        self.context = {} # Base context for tests


    def _configure_mocks_for_baseline(self):
        """Helper to configure mocks for a simple baseline scenario."""
        # No personality effects
        self.mock_personality_system.get_agent_traits.return_value = {}
        # Target not in cover
        self.mock_hazard_cover_system.check_line_of_sight.return_value = (True, 1.0) # (los_clear, protection_factor)
        # No team bonuses
        self.mock_team_combat_integration.calculate_team_attack_bonus.return_value = 0.0
        self.mock_team_combat_integration.calculate_defense_bonus.return_value = 0.0
        # No active status effects (handled in setUp, but explicit here)
        self.combat_system.active_status_effects = {}
         # Mock random for predictable critical hits (no crit for baseline)
        patcher = patch('random.random', return_value=0.5) # Guarantees no critical hit if crit_chance < 0.5
        self.mock_random = patcher.start()
        self.addCleanup(patcher.stop)


    def test_calculate_final_damage_baseline(self):
        """Test baseline damage calculation with no modifiers."""
        # --- Arrange ---
        self._configure_mocks_for_baseline()
        weapon = "standard"
        base_damage = DEFAULT_CONFIG["combat"]["WEAPON_STATS"][weapon]['damage'] # 10
        expected_damage = base_damage

        # --- Act ---
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id,
            self.attacker_pos, self.target_pos,
            base_damage, weapon, self.environment_context, self.context
        )

        # --- Assert ---
        self.assertAlmostEqual(final_damage, expected_damage, places=5)
        # Verify mocks were called as expected (optional but good practice)
        self.mock_personality_system.get_agent_traits.assert_any_call(self.attacker_id)
        self.mock_personality_system.get_agent_traits.assert_any_call(self.target_id)
        self.mock_hazard_cover_system.check_line_of_sight.assert_called_once_with(
            self.attacker_pos, self.target_pos
        )


    def test_calculate_final_damage_critical_hit(self):
        """Test damage calculation when a critical hit occurs."""
        # --- Arrange ---
        # Start with baseline mocks
        self._configure_mocks_for_baseline()

        # Override the random patch to guarantee a critical hit
        # Stop the baseline patch and start a new one
        self.mock_random.stop() # Stop the baseline patch
        patcher_crit = patch('random.random', return_value=0.01) # Guarantees crit if chance > 0.01
        mock_random_crit = patcher_crit.start()
        self.addCleanup(patcher_crit.stop)

        weapon = "standard"
        base_damage = DEFAULT_CONFIG["combat"]["WEAPON_STATS"][weapon]['damage'] # 10
        crit_multiplier = DEFAULT_CONFIG["combat"]["WEAPON_STATS"][weapon]['crit_multiplier'] # 1.5
        # Assuming no other multipliers apply in this specific setup
        expected_damage = base_damage * crit_multiplier

        initial_crit_count = self.combat_system.critical_hits.get(self.attacker_id, 0)

        # --- Act ---
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id,
            self.attacker_pos, self.target_pos,
            base_damage, weapon, self.environment_context, self.context
        )

        # --- Assert ---
        self.assertAlmostEqual(final_damage, expected_damage, places=5)
        # Check if critical hit count was incremented
        self.assertEqual(self.combat_system.critical_hits[self.attacker_id], initial_crit_count + 1)
        # Verify random was called for the crit check
        mock_random_crit.assert_called_once()


    def test_calculate_final_damage_heavy_weapon(self):
        """Test damage calculation using a different weapon type ('heavy')."""
        # --- Arrange ---
        self._configure_mocks_for_baseline() # Start with baseline (no crits, no cover etc.)

        weapon = "heavy"
        base_damage = DEFAULT_CONFIG["combat"]["WEAPON_STATS"][weapon]['damage'] # Base damage for heavy
        weapon_multiplier = DEFAULT_CONFIG["combat"]["WEAPON_STATS"][weapon]['damage_multiplier'] # 1.5

        # Expected damage is base * weapon multiplier (no other mods in baseline)
        expected_damage = base_damage * weapon_multiplier

        # --- Act ---
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id,
            self.attacker_pos, self.target_pos,
            base_damage, weapon, self.environment_context, self.context
        )

        # --- Assert ---
        self.assertAlmostEqual(final_damage, expected_damage, places=5)
        # Verify mocks called (optional, but good practice for baseline)
        self.mock_personality_system.get_agent_traits.assert_any_call(self.attacker_id)
        self.mock_personality_system.get_agent_traits.assert_any_call(self.target_id)


    def test_calculate_final_damage_attacker_status_effect(self):
        """Test damage calculation when the attacker has a damage-boosting status effect."""
        # --- Arrange ---
        self._configure_mocks_for_baseline() # Start with baseline
        weapon = "standard"
        base_damage = DEFAULT_CONFIG["combat"]["WEAPON_STATS"][weapon]['damage'] # 10

        # Apply 'Frenzy' status effect to the attacker
        frenzy_effect = StatusEffect(type_name="Frenzy", duration=10.0, strength=1.0)
        self.combat_system.active_status_effects[self.attacker_id] = [frenzy_effect]

        # Get the multiplier from config
        frenzy_multiplier = DEFAULT_CONFIG["status_effects"]["Frenzy"]["damage_multiplier"] # 1.3

        expected_damage = base_damage * frenzy_multiplier # 10 * 1.3 = 13

        # --- Act ---
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id,
            self.attacker_pos, self.target_pos,
            base_damage, weapon, self.environment_context, self.context
        )

        # --- Assert ---
        self.assertAlmostEqual(final_damage, expected_damage, places=5)
        # Verify mocks called
        self.mock_personality_system.get_agent_traits.assert_any_call(self.attacker_id)
        self.mock_personality_system.get_agent_traits.assert_any_call(self.target_id)


    def test_calculate_final_damage_target_status_effect(self):
        """Test damage calculation when the target has a damage-increasing status effect."""
        # --- Arrange ---
        self._configure_mocks_for_baseline() # Start with baseline
        weapon = "standard"
        base_damage = DEFAULT_CONFIG["combat"]["WEAPON_STATS"][weapon]['damage'] # 10

        # Apply 'Vulnerable' status effect to the target
        vulnerable_effect = StatusEffect(type_name="Vulnerable", duration=10.0, strength=1.0)
        self.combat_system.active_status_effects[self.target_id] = [vulnerable_effect]

        # Get the multiplier from config
        vulnerable_multiplier = DEFAULT_CONFIG["status_effects"]["Vulnerable"]["damage_taken_multiplier"] # 1.4

        expected_damage = base_damage * vulnerable_multiplier # 10 * 1.4 = 14

        # --- Act ---
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id,
            self.attacker_pos, self.target_pos,
            base_damage, weapon, self.environment_context, self.context
        )

        # --- Assert ---
        self.assertAlmostEqual(final_damage, expected_damage, places=5)
        # Verify mocks called
        self.mock_personality_system.get_agent_traits.assert_any_call(self.attacker_id)
        self.mock_personality_system.get_agent_traits.assert_any_call(self.target_id)


    def test_calculate_final_damage_target_in_cover(self):
        """Test damage calculation when the target is in cover."""
        # --- Arrange ---
        self._configure_mocks_for_baseline() # Start with baseline
        weapon = "standard"
        base_damage = DEFAULT_CONFIG["combat"]["WEAPON_STATS"][weapon]['damage'] # 10

        # Mock HazardCoverSystem to indicate cover
        # Assume check_line_of_sight returns (False, protection_factor) if LOS is blocked by cover
        protection_factor = DEFAULT_CONFIG["environment"]["COVER_PROTECTION_FACTOR"] # e.g., 0.5
        self.mock_hazard_cover_system.check_line_of_sight.return_value = (False, protection_factor)

        # Expected damage = base * (1 - protection_factor)
        expected_damage = base_damage * (1.0 - protection_factor) # 10 * (1.0 - 0.5) = 5

        # --- Act ---
        final_damage = self.combat_system.calculate_final_damage(
            self.attacker_id, self.target_id,
            self.attacker_pos, self.target_pos,
            base_damage, weapon, self.environment_context, self.context
        )

        # --- Assert ---
        self.assertAlmostEqual(final_damage, expected_damage, places=5)
        # Verify cover check was called
        self.mock_hazard_cover_system.check_line_of_sight.assert_called_once_with(
            self.attacker_pos, self.target_pos
        )


class TestTeamCombatIntegration(unittest.TestCase):
    def setUp(self):
        # Mock team system
        self.team_system = MagicMock()
        self.team_system.get_team_id_for_agent.side_effect = lambda agent_id: 'team1' if agent_id in ['agent1', 'agent2'] else 'team2'
        self.team_system.get_formation_score.return_value = 0.8
        
        # Mock teams data
        self.team_system.teams = {
            'team1': {
                'members': [
                    {'agent_id': 'agent1', 'role': 'attacker'},
                    {'agent_id': 'agent2', 'role': 'defender'}
                ]
            },
            'team2': {
                'members': [
                    {'agent_id': 'agent3', 'role': 'scout'},
                    {'agent_id': 'agent4', 'role': 'support'}
                ]
            }
        }
        
        # Mock combat system
        self.combat_system = MagicMock()
        self.combat_system.get_combat_stats.return_value = {
            'damage_dealt': 100,
            'hits': 10,
            'misses': 2,
            'critical_hits': 3,
            'kills': 2,
            'accuracy': 0.83
        }
        self.combat_system.get_agent_effectiveness.return_value = 0.75
        
        # Create team combat integration
        self.team_combat = TeamCombatIntegration(
            team_system=self.team_system,
            combat_system=self.combat_system
        )
        
    def test_register_team(self):
        self.team_combat.register_team('team1')
        self.assertIn('team1', self.team_combat.team_damage)
        self.assertIn('team1', self.team_combat.team_kills)
        
    def test_update_team_stats(self):
        self.team_combat.update_team_stats('agent1', damage=50)
        self.assertEqual(self.team_combat.team_damage['team1'], 50)
        
        self.team_combat.update_team_stats('agent1', kill=True)
        self.assertEqual(self.team_combat.team_kills['team1'], 1)
        
    def test_calculate_team_attack_bonus(self):
        # Test attacking enemy
        bonuses = self.team_combat.calculate_team_attack_bonus(
            'agent1', 'agent3', [0, 0], [50, 50]
        )
        
        # Verify bonuses are applied based on formation score
        self.assertGreater(bonuses['damage'], 1.0)
        self.assertGreater(bonuses['accuracy'], 1.0)
        self.assertGreater(bonuses['critical'], 1.0)
        
        # Test attacking teammate (should not apply bonuses)
        bonuses = self.team_combat.calculate_team_attack_bonus(
            'agent1', 'agent2', [0, 0], [50, 50]
        )
        
        self.assertEqual(bonuses['damage'], 1.0)
        self.assertEqual(bonuses['accuracy'], 1.0)
        self.assertEqual(bonuses['critical'], 1.0)
        
    def test_calculate_defense_bonus(self):
        # Test defender role gets additional protection
        self.team_combat._calculate_role_bonuses = MagicMock(return_value={})
        
        defense_bonus = self.team_combat.calculate_defense_bonus('agent2', 'agent3')
        self.assertLess(defense_bonus, 1.0)  # Should reduce damage
        
        # Test non-defender role
        defense_bonus = self.team_combat.calculate_defense_bonus('agent1', 'agent3')
        self.assertLess(defense_bonus, 1.0)  # Should still reduce damage, but less
        
    def test_execute_team_ability(self):
        # Mock team_system.use_team_ability to return True
        self.team_system.use_team_ability.return_value = True
        
        # Test executing ability
        result = self.team_combat.execute_team_ability(
            'team1', 'coordinated_attack', 'agent1', [100, 100]
        )
        
        self.assertTrue(result)
        self.assertEqual(self.team_combat.team_abilities_used['team1']['coordinated_attack'], 1)
        
    def test_get_team_combat_stats(self):
        # Set up some stats
        self.team_combat.register_team('team1')
        self.team_combat.team_damage['team1'] = 200
        self.team_combat.team_kills['team1'] = 3
        
        # Get stats
        stats = self.team_combat.get_team_combat_stats('team1')
        
        self.assertEqual(stats['damage_dealt'], 200)
        self.assertEqual(stats['kills'], 3)
        self.assertEqual(len(stats['members']), 2)
        
    def test_calculate_team_effectiveness(self):
        # Set up some stats
        self.team_combat.register_team('team1')
        self.team_combat.team_damage['team1'] = 200
        self.team_combat.team_kills['team1'] = 3
        
        # Calculate effectiveness
        effectiveness = self.team_combat.calculate_team_effectiveness('team1')
        
        # Should consider individual effectiveness, formation, kills, and damage
        self.assertGreater(effectiveness, 0.0)
        self.assertLessEqual(effectiveness, 1.0)

# --- New Test Class for Status Effects --- #

class TestCombatSystemStatusEffects(unittest.TestCase):

    def setUp(self):
        """Set up CombatSystem instance and mocks for status effect tests."""
        # Mock dependencies
        self.mock_personality_system = MagicMock(spec=PersonalitySystem)
        self.mock_hazard_cover_system = MagicMock(spec=HazardCoverSystem)
        # Assuming TeamCombatIntegration doesn't need specific setup for these tests, but mock it
        self.mock_team_combat_integration = MagicMock(spec=TeamCombatIntegration)

        # Mock the config object
        self.mock_config = MagicMock(spec=UnifiedConfig)
        # Configure the mock config to return values from our DEFAULT_CONFIG dictionary
        def config_get_side_effect(section, key, default=None):
            if section in DEFAULT_CONFIG and key in DEFAULT_CONFIG[section]:
                return DEFAULT_CONFIG[section][key]
            # Handle potential nested keys like combat.WEAPONS.standard.damage_multiplier
            parts = key.split('.')
            if len(parts) > 1 and section in DEFAULT_CONFIG:
                base = DEFAULT_CONFIG[section]
                for i, part in enumerate(parts):
                    if isinstance(base, dict) and part in base:
                        if i == len(parts) - 1:
                            return base[part]
                        base = base[part]
                    else:
                        return default # Key path not found
            return default

        self.mock_config.get.side_effect = config_get_side_effect
        # Provide top-level access for convenience if CombatSystem uses it
        # self.mock_config.combat = DEFAULT_CONFIG['combat']
        # self.mock_config.status_effects = DEFAULT_CONFIG['status_effects']

        # Patch the global config object within the combat_system module
        self.config_patcher = patch('systems.combat.combat_system.config', self.mock_config)
        self.config_patcher.start()
        self.addCleanup(self.config_patcher.stop)

        # Instantiate CombatSystem with mocks
        self.combat_system = CombatSystem(
            personality_system=self.mock_personality_system,
            hazard_cover_system=self.mock_hazard_cover_system,
            team_combat_integration=self.mock_team_combat_integration
        )

        # Reset stats and effects before each test
        self.combat_system.reset_stats()
        self.combat_system.active_status_effects = {}

        # Common test data
        self.agent_id_1 = "agent_1"
        self.agent_id_2 = "agent_2"
        # Register agents
        self.combat_system.register_agent(self.agent_id_1)
        self.combat_system.register_agent(self.agent_id_2)

    # --- Test Methods for apply_status_effect --- #
    def test_apply_new_effect(self):
        """Test applying a single status effect to an agent."""
        effect_type = "slow"
        duration = 5.0
        strength = 0.5

        # Act
        applied_effect = self.combat_system.apply_status_effect(
            self.agent_id_1, effect_type, duration, strength
        )

        # Assert
        self.assertIn(self.agent_id_1, self.combat_system.active_status_effects)
        self.assertEqual(len(self.combat_system.active_status_effects[self.agent_id_1]), 1)
        stored_effect = self.combat_system.active_status_effects[self.agent_id_1][0]

        self.assertIsInstance(stored_effect, StatusEffect)
        self.assertEqual(stored_effect.type, effect_type)
        self.assertEqual(stored_effect.duration, duration)
        self.assertEqual(stored_effect.strength, strength)
        # Check if the returned effect matches the stored one (by identity or value)
        self.assertIs(applied_effect, stored_effect)

    def test_apply_multiple_effects(self):
        """Test applying multiple different status effects to the same agent."""
        effect1_type, effect1_dur, effect1_str = "slow", 5.0, 0.5
        effect2_type, effect2_dur, effect2_str = "burn", 3.0, 1.0

        # Act
        self.combat_system.apply_status_effect(self.agent_id_1, effect1_type, effect1_dur, effect1_str)
        self.combat_system.apply_status_effect(self.agent_id_1, effect2_type, effect2_dur, effect2_str)

        # Assert
        self.assertIn(self.agent_id_1, self.combat_system.active_status_effects)
        self.assertEqual(len(self.combat_system.active_status_effects[self.agent_id_1]), 2)

        # Check if both effects are present (order might vary)
        effects = self.combat_system.active_status_effects[self.agent_id_1]
        effect_types_present = {e.type for e in effects}
        self.assertIn(effect1_type, effect_types_present)
        self.assertIn(effect2_type, effect_types_present)

        # Verify details of one effect (e.g., the first one applied)
        slow_effect = next((e for e in effects if e.type == effect1_type), None)
        self.assertIsNotNone(slow_effect)
        self.assertEqual(slow_effect.duration, effect1_dur)
        self.assertEqual(slow_effect.strength, effect1_str)

    def test_apply_stacking_effect(self):
        """Test applying the same status effect type multiple times (assumes stacking)."""
        effect_type = "poison"
        duration1, strength1 = 5.0, 1.0
        duration2, strength2 = 3.0, 1.5 # Different strength/duration

        # Act
        self.combat_system.apply_status_effect(self.agent_id_1, effect_type, duration1, strength1)
        self.combat_system.apply_status_effect(self.agent_id_1, effect_type, duration2, strength2)

        # Assert
        self.assertIn(self.agent_id_1, self.combat_system.active_status_effects)
        # Assuming effects stack as separate instances
        self.assertEqual(len(self.combat_system.active_status_effects[self.agent_id_1]), 2)

        effects = self.combat_system.active_status_effects[self.agent_id_1]
        # Verify both have the same type
        self.assertTrue(all(e.type == effect_type for e in effects))
        # Verify durations/strengths are distinct
        durations = {e.duration for e in effects}
        strengths = {e.strength for e in effects}
        self.assertIn(duration1, durations)
        self.assertIn(duration2, durations)
        self.assertIn(strength1, strengths)
        self.assertIn(strength2, strengths)

    # --- Test Methods for update_status_effects --- #
    def test_duration_decrease(self):
        """Test that effect duration decreases correctly after update."""
        initial_duration = 10.0
        delta_time = 1.5
        expected_duration = initial_duration - delta_time

        self.combat_system.apply_status_effect(self.agent_id_1, "boost", initial_duration, 1.2)

        # Act
        self.combat_system.update_status_effects(delta_time)

        # Assert
        self.assertEqual(len(self.combat_system.active_status_effects[self.agent_id_1]), 1)
        updated_effect = self.combat_system.active_status_effects[self.agent_id_1][0]
        self.assertAlmostEqual(updated_effect.duration, expected_duration, places=5)

    def test_effect_expiration(self):
        """Test that effects are removed when their duration runs out."""
        duration = 2.0
        delta_time_exact = 2.0
        delta_time_over = 2.5

        # Apply effect
        self.combat_system.apply_status_effect(self.agent_id_1, "slow", duration, 0.5)

        # Act (exact time)
        self.combat_system.update_status_effects(delta_time_exact)

        # Assert (should expire exactly at time)
        self.assertEqual(len(self.combat_system.active_status_effects[self.agent_id_1]), 0)

        # Re-apply and test going over time
        self.combat_system.apply_status_effect(self.agent_id_1, "slow", duration, 0.5)
        self.combat_system.update_status_effects(delta_time_over)
        self.assertEqual(len(self.combat_system.active_status_effects[self.agent_id_1]), 0)

    def test_multiple_effects_update(self):
        """Test updating multiple effects with different durations."""
        effect1_dur = 5.0
        effect2_dur = 2.0
        delta_time = 3.0

        self.combat_system.apply_status_effect(self.agent_id_1, "boost", effect1_dur, 1.1)
        self.combat_system.apply_status_effect(self.agent_id_1, "burn", effect2_dur, 1.0)

        # Act
        self.combat_system.update_status_effects(delta_time)

        # Assert
        effects = self.combat_system.active_status_effects[self.agent_id_1]
        self.assertEqual(len(effects), 1) # Burn should expire
        remaining_effect = effects[0]
        self.assertEqual(remaining_effect.type, "boost")
        self.assertAlmostEqual(remaining_effect.duration, effect1_dur - delta_time, places=5)

    def test_update_empty(self):
        """Test calling update when no effects are active."""
        delta_time = 1.0
        # Act & Assert (Should not raise error)
        try:
            self.combat_system.update_status_effects(delta_time)
            # Check that effect dicts are still empty or don't contain the agents
            self.assertNotIn(self.agent_id_1, self.combat_system.active_status_effects or {})
            self.assertNotIn(self.agent_id_2, self.combat_system.active_status_effects or {})
        except Exception as e:
            self.fail(f"update_status_effects raised an exception unexpectedly: {e}")

    def test_update_multiple_agents(self):
        """Test that updates affect agents independently."""
        agent1_dur = 4.0
        agent2_dur = 6.0
        delta_time = 3.0

        self.combat_system.apply_status_effect(self.agent_id_1, "slow", agent1_dur, 0.5)
        self.combat_system.apply_status_effect(self.agent_id_2, "boost", agent2_dur, 1.2)

        # Act
        self.combat_system.update_status_effects(delta_time)

        # Assert Agent 1
        effects_agent1 = self.combat_system.active_status_effects[self.agent_id_1]
        self.assertEqual(len(effects_agent1), 1)
        self.assertAlmostEqual(effects_agent1[0].duration, agent1_dur - delta_time, places=5)

        # Assert Agent 2
        effects_agent2 = self.combat_system.active_status_effects[self.agent_id_2]
        self.assertEqual(len(effects_agent2), 1)
        self.assertAlmostEqual(effects_agent2[0].duration, agent2_dur - delta_time, places=5)

    # --- Test Methods for _get_status_effect --- #
    def test_get_effect_from_weapon_config(self):
        """Test getting a status effect directly defined on a weapon."""
        weapon_type = "status_gun"
        expected_effect = DEFAULT_CONFIG['combat']['WEAPON_STATS'][weapon_type]['applies_status']

        # Act
        result_effect = self.combat_system._get_status_effect(weapon_type, critical=False)
        result_effect_crit = self.combat_system._get_status_effect(weapon_type, critical=True)

        # Assert
        self.assertIsNotNone(result_effect)
        self.assertEqual(result_effect, expected_effect)
        # Should return weapon effect even if critical
        self.assertEqual(result_effect_crit, expected_effect)

    @patch('random.random')
    def test_get_effect_on_crit(self, mock_random):
        """Test getting a status effect on a critical hit based on config chance."""
        weapon_type = "standard" # Assume no direct status effect
        crit_status_chance = DEFAULT_CONFIG['combat']['CRITICAL_STATUS_CHANCE']
        possible_effects = DEFAULT_CONFIG['combat']['CRITICAL_STATUS_EFFECTS']

        # Mock random to ensure effect application
        mock_random.return_value = crit_status_chance - 0.01 # Just below threshold

        # Act
        result_effect = self.combat_system._get_status_effect(weapon_type, critical=True)

        # Assert
        self.assertIsNotNone(result_effect)
        self.assertIn(result_effect, possible_effects) # Check if it's one of the configured effects
        mock_random.assert_called_once()

    @patch('random.random')
    def test_get_effect_on_crit_no_effect(self, mock_random):
        """Test that no effect is applied on crit if random roll fails."""
        weapon_type = "standard"
        crit_status_chance = DEFAULT_CONFIG['combat']['CRITICAL_STATUS_CHANCE']

        # Mock random to ensure NO effect application
        mock_random.return_value = crit_status_chance + 0.01 # Just above threshold

        # Act
        result_effect = self.combat_system._get_status_effect(weapon_type, critical=True)

        # Assert
        self.assertIsNone(result_effect)
        mock_random.assert_called_once()

    def test_get_effect_no_crit_no_weapon_effect(self):
        """Test that no effect is returned for a non-crit with a standard weapon."""
        weapon_type = "standard"

        # Act
        result_effect = self.combat_system._get_status_effect(weapon_type, critical=False)

        # Assert
        self.assertIsNone(result_effect)

    def test_get_effect_config_missing(self):
        """Test graceful handling when critical effect config keys are missing."""
        weapon_type = "standard"

        # Temporarily mock config.get to simulate missing keys for this test
        original_side_effect = self.mock_config.get.side_effect
        def missing_crit_config_get(section, key, default=None):
            if section == 'combat' and key == 'CRITICAL_STATUS_CHANCE':
                return default # Simulate key missing
            if section == 'combat' and key == 'CRITICAL_STATUS_EFFECTS':
                return default # Simulate key missing
            # Fallback to original behavior for other keys
            return original_side_effect(section, key, default)

        self.mock_config.get.side_effect = missing_crit_config_get

        # Act
        result_effect_crit = self.combat_system._get_status_effect(weapon_type, critical=True)
        result_effect_no_crit = self.combat_system._get_status_effect(weapon_type, critical=False)

        # Assert
        self.assertIsNone(result_effect_crit)
        self.assertIsNone(result_effect_no_crit)

        # Restore original mock behavior
        self.mock_config.get.side_effect = original_side_effect

if __name__ == '__main__':
    unittest.main() 