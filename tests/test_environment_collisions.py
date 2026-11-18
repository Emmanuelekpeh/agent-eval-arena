import unittest
from unittest.mock import patch, MagicMock, ANY
import numpy as np
import math
import random # Import random directly for patching
from typing import Tuple, List, Dict, Any, Optional

# Add project root to path to allow importing modules
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Modules to test/mock (adjust paths as necessary)
from systems.environment.environment import BattleRoyaleEnv
from systems.core.system_manager import SystemManager, SystemEventType # Mock system_manager instance
from systems.combat.combat_system import CombatSystem
from systems.environment.hazard_cover_system import HazardCoverSystem
from systems.agents.team_system import TeamSystem
from config.unified_config import UnifiedConfig # Mock config instance
from systems.utils.object_pool import ObjectPool
from game_objects.bullet import Bullet # Need Bullet class definition
from systems.agents.base_agent import BaseAgent # Need BaseAgent for type hint/mocking
from systems.spatial_system import QuadTree, AABB # For mocking collision_tree

# Mock BaseAgent for testing purposes
class MockAgent(BaseAgent):
    def __init__(self, agent_id, team_id=None, radius=10, angle=0.0):
        self.id = agent_id
        self.team_id = team_id
        self.radius = radius
        self.angle = angle # Store angle in radians
        # Add other attributes if needed by the code under test
        self.shoot_cooldown = 0
        self.weapon_type = 'standard' # Default weapon

    # Implement abstract methods with basic behavior or MagicMock
    def initialize_agent(self, state_size: int, action_size: int) -> None: pass
    def get_action(self, state: np.ndarray) -> int: return 0 # Default idle
    def learn(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool = False) -> None: pass
    def get_serializable_state(self) -> Dict[str, Any]: return {'id': self.id}
    def load_from_state(self, state: Dict[str, Any]) -> None: pass


class TestEnvironmentCollisions(unittest.TestCase):

    @patch('systems.environment.environment.system_manager', spec=SystemManager) # Mock the singleton instance
    @patch('systems.environment.environment.ObjectPool')
    @patch('systems.environment.environment.QuadTree')
    def setUp(self, MockQuadTree, MockObjectPool, MockSystemManager):
        """Set up mocks and a BattleRoyaleEnv instance for testing."""
        
        # --- Mock System Instances ---
        self.mock_combat_system = MagicMock(spec=CombatSystem)
        self.mock_hazard_cover_system = MagicMock(spec=HazardCoverSystem)
        self.mock_team_system = MagicMock(spec=TeamSystem)
        
        self.mock_system_manager = MockSystemManager # Use the patched instance directly
        self.mock_bullet_pool = MockObjectPool.return_value
        self.mock_collision_tree = MockQuadTree.return_value

        # --- Patch Config Directly for Environment Init --- #
        # Define the necessary config structure needed by BattleRoyaleEnv.__init__
        test_config_data = {
            "environment": {
                "ENEMY_SPAWN_INTERVAL_SEC": 10.0,
                "ENEMY_TYPES": ["MLPAgent1", "PerceptronAgent1"], # CRITICAL DEFAULT
                "ENEMY_SPAWN_WEIGHTS": [0.5, 0.5],
                "INITIAL_SAFE_ZONE_RADIUS": 400,
                "CENTER_X": 500,
                "CENTER_Y": 500,
                "TARGET_SAFE_ZONE_RADIUS": 400,
                "COVER_DENSITY": 0.03,
                "MAX_PICKUPS": 20, # Added constant defaults
                "MAX_HAZARDS": 5,
                "MAX_ENEMIES": 10
            },
            "game": {
                "ROUND_TIME_SECONDS": 60,
                "ROUND_END_DELAY_SECONDS": 3,
                "ZONE_SHRINK_RATE_PER_FRAME": 0.002,
                "ZONE_DAMAGE": 1.0,
                "RESOURCE_SPAWN_INTERVAL_SECONDS": 5,
                "PICKUP_SPAWN_INTERVAL_SECONDS": 10
            },
            "combat": { # Keep combat config for _resolve_hit
                "BASE_ACCURACY": 0.9,
                "WEAPONS": {
                    "standard": {"accuracy": 0.9, "spread": 5.0, "range": 600, "damage_multiplier": 1.0},
                    "shotgun": {"accuracy": 0.6, "spread": 30.0, "range": 200, "damage_multiplier": 0.8},
                    "sniper": {"accuracy": 0.95, "spread": 1.0, "range": 1200, "damage_multiplier": 2.5}
                },
                 "CRITICAL_CHANCE": 0.1,
                 "CRITICAL_MULTIPLIER": 2.0
            }
            # Add other sections if needed by methods under test
        }
        
        # Create a mock config object that supports .get()
        mock_config_object = MagicMock(spec=UnifiedConfig)
        def mock_get(section, key, default=None):
            # Prioritize specific combat weapon logic
            if section == "combat" and '.' in key and key.startswith("WEAPONS."):
                 parts = key.split('.') # e.g., [WEAPONS, standard, accuracy]
                 weapon_type = parts[1]
                 attribute = parts[2]
                 weapon_data = test_config_data.get("combat", {}).get("WEAPONS", {}).get(weapon_type, {})
                 return weapon_data.get(attribute, default)
            # General section.key access
            return test_config_data.get(section, {}).get(key, default)
            
        mock_config_object.get.side_effect = mock_get
        # --- End Patch Config --- #

        # --- Create Environment Instance (Patching the imported config) --- #
        with patch('systems.environment.environment.config', mock_config_object):
             # Also patch config where constants are defined if separate
             # Assuming constants are defined in the same module as BattleRoyaleEnv
             with patch('systems.environment.environment.MAX_PICKUPS', test_config_data["environment"]["MAX_PICKUPS"]), \
                  patch('systems.environment.environment.MAX_HAZARDS', test_config_data["environment"]["MAX_HAZARDS"]), \
                  patch('systems.environment.environment.MAX_ENEMIES', test_config_data["environment"]["MAX_ENEMIES"]):
                  self.env = BattleRoyaleEnv(width=1000, height=1000, target_fps=60)
        
        # Manually assign mocked systems
        self.env.combat_system = self.mock_combat_system
        self.env.hazard_cover_system = self.mock_hazard_cover_system
        self.env.team_system = self.mock_team_system
        self.env.bullet_pool = self.mock_bullet_pool
        self.env.collision_tree = self.mock_collision_tree
        # self.env.system_manager = self.mock_system_manager # Not needed, patched globally

        # --- Default Mock Behaviors ---
        self.mock_collision_tree.query_range.return_value = [] # Default: nothing nearby
        self.mock_combat_system.calculate_final_damage.return_value = 10.0 # Default damage
        self.mock_hazard_cover_system.check_line_of_sight.return_value = (True, 0.0) # Default: clear LoS, no protection
        self.mock_hazard_cover_system.get_cover_by_id.return_value = None # Default: no cover found
        self.mock_hazard_cover_system.damage_cover.return_value = False # Default: cover not destroyed
        self.mock_team_system.get_team_id_for_agent.return_value = None # Default: no team
        self.mock_bullet_pool.release.return_value = None # Mock release

        # --- Add Test Entities ---
        self.agent1 = MockAgent(agent_id="agent_1", team_id="team_A")
        self.agent2 = MockAgent(agent_id="agent_2", team_id="team_B")
        self.agent3 = MockAgent(agent_id="agent_3", team_id="team_A") # Same team as agent1
        
        self.env.agents = {"agent_1": self.agent1, "agent_2": self.agent2, "agent_3": self.agent3}
        self.env.agent_positions = {"agent_1": (100, 100), "agent_2": (200, 100), "agent_3": (100, 200)}
        self.env.agent_health = {"agent_1": 100, "agent_2": 100, "agent_3": 100}
        self.env.agent_energy = {"agent_1": 100, "agent_2": 100, "agent_3": 100} # Add energy if needed

        # Clear active bullets before each test
        self.env.active_bullets = []
        
    def tearDown(self):
        # Clean up any resources if necessary
        pass
        
    def _create_mock_bullet(self, owner_id="agent_1", pos=(150, 100), target_pos=(200, 100), weapon_type="standard", damage=10):
        """Helper to create a mock Bullet object for testing."""
        # Use actual Bullet class for instantiation, but mock its methods if needed later
        bullet = Bullet(x=pos[0], y=pos[1], owner=owner_id, weapon_type=weapon_type)
        bullet.active = True
        bullet.radius = 3
        bullet.damage = damage
        # Calculate angle towards target
        angle_rad = math.atan2(target_pos[1] - pos[1], target_pos[0] - pos[0])
        bullet.angle = math.degrees(angle_rad) # Assuming Bullet uses degrees
        
        # Find attacker start position (use agent's current pos for simplicity in tests)
        attacker_pos = self.env.agent_positions.get(owner_id, (0,0))
        bullet.attacker_start_pos = attacker_pos 
        
        self.env.active_bullets.append(bullet)
        return bullet

    # --- Test Cases ---

    @patch('random.random') # Patch random for accuracy check
    def test_bullet_hits_agent_direct(self, mock_random):
        mock_random.return_value = 0.1 # Ensure accuracy check passes (assuming accuracy > 0.1)
        
        # Setup: Create bullet heading towards agent2
        bullet = self._create_mock_bullet(owner_id="agent_1", pos=(195, 100), target_pos=(200, 100), weapon_type="standard") # Start close
        bullet_id = id(bullet)
        
        # Setup Mocks: Ensure query_range returns agent2 when queried near bullet
        agent2_pos = self.env.agent_positions["agent_2"]
        agent2_radius = self.agent2.radius
        # Mock query_range to return agent2 for any query box around the bullet's position
        self.mock_collision_tree.query_range.return_value = [
            (agent2_pos, "agent_2", agent2_radius, "agent")
        ]
        # Mock team IDs for friendly fire check
        self.mock_team_system.get_team_id_for_agent.side_effect = lambda aid: {"agent_1": "team_A", "agent_2": "team_B"}.get(aid)
        # Mock LoS check to return clear LoS
        self.mock_hazard_cover_system.check_line_of_sight.return_value = (True, 0.0) 

        # Execute
        collided_ids = self.env._check_bullet_collisions()

        # Assert
        self.assertIn(bullet_id, collided_ids, "Bullet ID should be in the set of collided bullets")
        
        # Check specific event emissions
        hit_event_called = False
        damage_event_called = False
        hit_event_data = None
        damage_event_data = None

        for call in self.mock_system_manager.emit_event.call_args_list:
            args, kwargs = call
            event_type = args[0]
            event_data = args[1] if len(args) > 1 else {}

            if event_type == SystemEventType.ATTACK_HIT:
                hit_event_called = True
                hit_event_data = event_data
            elif event_type == SystemEventType.AGENT_DAMAGE:
                damage_event_called = True
                damage_event_data = event_data

        self.assertTrue(hit_event_called, "ATTACK_HIT event was not emitted")
        if hit_event_data:
             self.assertEqual(hit_event_data.get('attacker_id'), 'agent_1')
             self.assertEqual(hit_event_data.get('target_id'), 'agent_2')
             self.assertEqual(hit_event_data.get('weapon_type'), 'standard')
             self.assertEqual(hit_event_data.get('bullet_id'), bullet_id)

        self.assertTrue(damage_event_called, "AGENT_DAMAGE event was not emitted")
        if damage_event_data:
             self.assertGreater(damage_event_data.get('damage', 0), 0, "Damage value should be greater than 0")
             self.assertEqual(damage_event_data.get('target_id'), 'agent_2')
             self.assertEqual(damage_event_data.get('attacker_id'), 'agent_1')

        # Verify damage calculation was called
        self.mock_combat_system.calculate_final_damage.assert_called_once()
        # Optionally check args passed to calculate_final_damage
        damage_call_args = self.mock_combat_system.calculate_final_damage.call_args[1] # Get kwargs
        self.assertEqual(damage_call_args.get('attacker_id'), 'agent_1')
        self.assertEqual(damage_call_args.get('target_id'), 'agent_2')
        self.assertEqual(damage_call_args.get('weapon_type'), 'standard')
        self.assertEqual(damage_call_args.get('attacker_pos'), self.agent1.position if hasattr(self.agent1, 'position') else self.env.agent_positions['agent_1']) # Check attacker pos from bullet


        # Verify bullet release
        self.mock_bullet_pool.release.assert_called_once_with(bullet)
        self.assertFalse(bullet.active, "Bullet should be inactive after collision and release")
        
    @patch('random.random')
    def test_bullet_misses_agent_accuracy(self, mock_random):
        # Standard weapon accuracy is 0.9, make random() return > 0.9
        mock_random.return_value = 0.95 
        
        bullet = self._create_mock_bullet(owner_id="agent_1", pos=(195, 100), target_pos=(200, 100), weapon_type="standard")
        bullet_id = id(bullet)
        
        agent2_pos = self.env.agent_positions["agent_2"]
        agent2_radius = self.agent2.radius
        self.mock_collision_tree.query_range.return_value = [
            (agent2_pos, "agent_2", agent2_radius, "agent")
        ]
        self.mock_team_system.get_team_id_for_agent.side_effect = lambda aid: {"agent_1": "team_A", "agent_2": "team_B"}.get(aid)
        self.mock_hazard_cover_system.check_line_of_sight.return_value = (True, 0.0)

        collided_ids = self.env._check_bullet_collisions()

        self.assertIn(bullet_id, collided_ids)
        
        # Check for ATTACK_MISS event with correct reason
        miss_event_called = False
        miss_event_data = None
        for call in self.mock_system_manager.emit_event.call_args_list:
            args, kwargs = call
            if args[0] == SystemEventType.ATTACK_MISS:
                miss_event_called = True
                miss_event_data = args[1]
                break
                
        self.assertTrue(miss_event_called, "ATTACK_MISS event was not emitted for accuracy miss")
        if miss_event_data:
            self.assertEqual(miss_event_data.get('reason'), 'accuracy')
            self.assertEqual(miss_event_data.get('attacker_id'), 'agent_1')
            self.assertEqual(miss_event_data.get('target_id'), 'agent_2')

        self.mock_combat_system.calculate_final_damage.assert_not_called()
        self.mock_bullet_pool.release.assert_called_once_with(bullet)
        self.assertFalse(bullet.active)

    @patch('random.random')
    def test_bullet_misses_agent_no_los(self, mock_random):
        mock_random.return_value = 0.1 # Ensure accuracy check passes

        bullet = self._create_mock_bullet(owner_id="agent_1", pos=(195, 100), target_pos=(200, 100), weapon_type="standard")
        bullet_id = id(bullet)
        
        agent2_pos = self.env.agent_positions["agent_2"]
        agent2_radius = self.agent2.radius
        self.mock_collision_tree.query_range.return_value = [
            (agent2_pos, "agent_2", agent2_radius, "agent")
        ]
        self.mock_team_system.get_team_id_for_agent.side_effect = lambda aid: {"agent_1": "team_A", "agent_2": "team_B"}.get(aid)
        # Mock LoS check to return NO LoS
        self.mock_hazard_cover_system.check_line_of_sight.return_value = (False, 0.0) 

        collided_ids = self.env._check_bullet_collisions()

        self.assertIn(bullet_id, collided_ids)
        
        # Check for ATTACK_MISS event with correct reason
        miss_event_called = False
        miss_event_data = None
        for call in self.mock_system_manager.emit_event.call_args_list:
            args, kwargs = call
            if args[0] == SystemEventType.ATTACK_MISS:
                miss_event_called = True
                miss_event_data = args[1]
                break

        self.assertTrue(miss_event_called, "ATTACK_MISS event was not emitted for LoS miss")
        if miss_event_data:
            self.assertEqual(miss_event_data.get('reason'), 'no_los')
            self.assertEqual(miss_event_data.get('attacker_id'), 'agent_1')
            self.assertEqual(miss_event_data.get('target_id'), 'agent_2')

        self.mock_combat_system.calculate_final_damage.assert_not_called()
        self.mock_bullet_pool.release.assert_called_once_with(bullet)
        self.assertFalse(bullet.active)

    @patch('random.random')
    def test_bullet_misses_agent_friendly_fire(self, mock_random):
        mock_random.return_value = 0.1 # Ensure accuracy check passes
        
        # Bullet from agent1 targeting agent3 (same team)
        bullet = self._create_mock_bullet(owner_id="agent_1", pos=(100, 195), target_pos=(100, 200), weapon_type="standard")
        bullet_id = id(bullet)
        
        agent3_pos = self.env.agent_positions["agent_3"]
        agent3_radius = self.agent3.radius
        self.mock_collision_tree.query_range.return_value = [
            (agent3_pos, "agent_3", agent3_radius, "agent")
        ]
        # Mock team IDs to be the same
        self.mock_team_system.get_team_id_for_agent.side_effect = lambda aid: {"agent_1": "team_A", "agent_3": "team_A"}.get(aid)
        self.mock_hazard_cover_system.check_line_of_sight.return_value = (True, 0.0)

        collided_ids = self.env._check_bullet_collisions()

        self.assertIn(bullet_id, collided_ids)
        
        # Check for ATTACK_MISS event with correct reason
        miss_event_called = False
        miss_event_data = None
        for call in self.mock_system_manager.emit_event.call_args_list:
            args, kwargs = call
            if args[0] == SystemEventType.ATTACK_MISS:
                miss_event_called = True
                miss_event_data = args[1]
                break

        self.assertTrue(miss_event_called, "ATTACK_MISS event was not emitted for friendly fire")
        if miss_event_data:
            self.assertEqual(miss_event_data.get('reason'), 'friendly_fire')
            self.assertEqual(miss_event_data.get('attacker_id'), 'agent_1')
            self.assertEqual(miss_event_data.get('target_id'), 'agent_3')

        self.mock_combat_system.calculate_final_damage.assert_not_called()
        self.mock_bullet_pool.release.assert_called_once_with(bullet)
        self.assertFalse(bullet.active)

    def test_bullet_hits_destructible_cover(self):
        bullet = self._create_mock_bullet(owner_id="agent_1", pos=(295, 100), target_pos=(300, 100))
        bullet_id = id(bullet)
        
        cover_pos = (300, 100)
        cover_id = "cover_1"
        cover_radius = 5
        cover_data = {'id': cover_id, 'x': cover_pos[0], 'y': cover_pos[1], 'type': 'barricade', 'durability': 50, 'destructible': True, 'protection': 0.7}
        
        self.mock_collision_tree.query_range.return_value = [
            (cover_pos, cover_id, cover_radius, "cover")
        ]
        self.mock_hazard_cover_system.get_cover_by_id.return_value = cover_data

        collided_ids = self.env._check_bullet_collisions()

        self.assertIn(bullet_id, collided_ids)
        self.mock_hazard_cover_system.get_cover_by_id.assert_called_once_with(cover_id)
        # Check that damage_cover was called with the correct cover_id and damage amount
        self.mock_hazard_cover_system.damage_cover.assert_called_once_with(cover_id, bullet.damage, ANY) 
        self.mock_combat_system.calculate_final_damage.assert_not_called()
        
        # Check no hit/miss/damage events emitted
        for call in self.mock_system_manager.emit_event.call_args_list:
            event_type = call.args[0]
            self.assertNotIn(event_type, [SystemEventType.ATTACK_HIT, SystemEventType.ATTACK_MISS, SystemEventType.AGENT_DAMAGE])

        self.mock_bullet_pool.release.assert_called_once_with(bullet)
        self.assertFalse(bullet.active)
        
    def test_bullet_hits_non_destructible_cover(self):
        bullet = self._create_mock_bullet(owner_id="agent_1", pos=(295, 100), target_pos=(300, 100))
        bullet_id = id(bullet)
        
        cover_pos = (300, 100)
        cover_id = "cover_wall_1"
        cover_radius = 5
        cover_data = {'id': cover_id, 'x': cover_pos[0], 'y': cover_pos[1], 'type': 'wall', 'durability': 999, 'destructible': False, 'protection': 1.0}
        
        self.mock_collision_tree.query_range.return_value = [
            (cover_pos, cover_id, cover_radius, "cover")
        ]
        self.mock_hazard_cover_system.get_cover_by_id.return_value = cover_data

        collided_ids = self.env._check_bullet_collisions()

        self.assertIn(bullet_id, collided_ids)
        self.mock_hazard_cover_system.get_cover_by_id.assert_called_once_with(cover_id)
        # Assert damage_cover was NOT called
        self.mock_hazard_cover_system.damage_cover.assert_not_called() 
        self.mock_combat_system.calculate_final_damage.assert_not_called()
        
        # Check no hit/miss/damage events emitted
        for call in self.mock_system_manager.emit_event.call_args_list:
            event_type = call.args[0]
            self.assertNotIn(event_type, [SystemEventType.ATTACK_HIT, SystemEventType.ATTACK_MISS, SystemEventType.AGENT_DAMAGE])

        self.mock_bullet_pool.release.assert_called_once_with(bullet)
        self.assertFalse(bullet.active)

    def test_bullet_hits_hazard(self):
        bullet = self._create_mock_bullet(owner_id="agent_1", pos=(395, 100), target_pos=(400, 100))
        bullet_id = id(bullet)
        
        hazard_pos = (400, 100)
        hazard_id = "fire_pit_1"
        hazard_radius = 15
        
        self.mock_collision_tree.query_range.return_value = [
            (hazard_pos, hazard_id, hazard_radius, "hazard")
        ]

        collided_ids = self.env._check_bullet_collisions()

        self.assertIn(bullet_id, collided_ids)
        self.mock_hazard_cover_system.damage_cover.assert_not_called() 
        self.mock_combat_system.calculate_final_damage.assert_not_called()
        
        # Check no hit/miss/damage events emitted
        for call in self.mock_system_manager.emit_event.call_args_list:
            event_type = call.args[0]
            self.assertNotIn(event_type, [SystemEventType.ATTACK_HIT, SystemEventType.ATTACK_MISS, SystemEventType.AGENT_DAMAGE])
            
        self.mock_bullet_pool.release.assert_called_once_with(bullet)
        self.assertFalse(bullet.active)

    def test_bullet_ignores_owner(self):
        # Bullet starts near owner (agent1)
        owner_pos = self.env.agent_positions["agent_1"]
        bullet = self._create_mock_bullet(owner_id="agent_1", pos=(owner_pos[0] + 1, owner_pos[1]), target_pos=(200, 100))
        bullet_id = id(bullet)
        
        owner_radius = self.agent1.radius
        
        # Mock query_range to return the owner AND the target
        agent2_pos = self.env.agent_positions["agent_2"]
        agent2_radius = self.agent2.radius
        self.mock_collision_tree.query_range.return_value = [
            (owner_pos, "agent_1", owner_radius, "agent"), # Owner
            (agent2_pos, "agent_2", agent2_radius, "agent")  # Target
        ]
        self.mock_team_system.get_team_id_for_agent.side_effect = lambda aid: {"agent_1": "team_A", "agent_2": "team_B"}.get(aid)
        self.mock_hazard_cover_system.check_line_of_sight.return_value = (True, 0.0)
        # Make sure accuracy hits
        with patch('random.random', return_value=0.1): 
            collided_ids = self.env._check_bullet_collisions()

        # Assert bullet collided (with agent2) but not with owner
        self.assertIn(bullet_id, collided_ids)
        # Assert hit/damage events were for agent2, not agent1
        hit_event_called = False
        damage_event_called = False
        for call in self.mock_system_manager.emit_event.call_args_list:
            args, kwargs = call
            event_type = args[0]
            event_data = args[1]
            if event_type == SystemEventType.ATTACK_HIT:
                hit_event_called = True
                self.assertEqual(event_data.get('target_id'), 'agent_2')
            elif event_type == SystemEventType.AGENT_DAMAGE:
                damage_event_called = True
                self.assertEqual(event_data.get('target_id'), 'agent_2')

        self.assertTrue(hit_event_called)
        self.assertTrue(damage_event_called)
        self.mock_combat_system.calculate_final_damage.assert_called_once()
        self.mock_bullet_pool.release.assert_called_once_with(bullet)
        self.assertFalse(bullet.active)
        
    @patch('random.random')
    def test_damage_calculation_context(self, mock_random):
        mock_random.return_value = 0.1 # Hit

        # Setup specific environmental conditions
        self.env.current_weather = 'storm'
        self.env.weather_intensity = 0.8
        self.env.day_time = 1800 # Example time
        # Place target outside safe zone for testing
        self.env.safe_zone_center = (500, 500)
        self.env.safe_zone_radius = 100
        self.env.agent_positions["agent_2"] = (700, 500) # Outside zone

        bullet = self._create_mock_bullet(owner_id="agent_1", pos=(695, 500), target_pos=(700, 500), weapon_type="sniper")
        bullet_id = id(bullet)
        
        agent2_pos = self.env.agent_positions["agent_2"]
        agent2_radius = self.agent2.radius
        self.mock_collision_tree.query_range.return_value = [
            (agent2_pos, "agent_2", agent2_radius, "agent")
        ]
        self.mock_team_system.get_team_id_for_agent.side_effect = lambda aid: {"agent_1": "team_A", "agent_2": "team_B"}.get(aid)
        self.mock_hazard_cover_system.check_line_of_sight.return_value = (True, 0.0)

        collided_ids = self.env._check_bullet_collisions()

        self.assertIn(bullet_id, collided_ids)
        self.mock_combat_system.calculate_final_damage.assert_called_once()

        # Assert the context passed to calculate_final_damage
        call_kwargs = self.mock_combat_system.calculate_final_damage.call_args.kwargs
        env_context = call_kwargs.get('environment_context')

        self.assertIsNotNone(env_context)
        self.assertEqual(env_context.get('weather'), 'storm')
        self.assertEqual(env_context.get('weather_intensity'), 0.8)
        self.assertEqual(env_context.get('time_of_day'), 1800)
        self.assertTrue(env_context.get('is_outside_safe_zone'))
        
        # Verify correct weapon type was passed
        self.assertEqual(call_kwargs.get('weapon_type'), 'sniper')

        # Check events were emitted
        hit_event_called = any(call.args[0] == SystemEventType.ATTACK_HIT for call in self.mock_system_manager.emit_event.call_args_list)
        damage_event_called = any(call.args[0] == SystemEventType.AGENT_DAMAGE for call in self.mock_system_manager.emit_event.call_args_list)
        self.assertTrue(hit_event_called)
        self.assertTrue(damage_event_called)
        
        self.mock_bullet_pool.release.assert_called_once_with(bullet)
        self.assertFalse(bullet.active)

    # TODO: Implement other test scenarios based on the plan...

if __name__ == '__main__':
    unittest.main() 