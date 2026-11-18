from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import math
import logging
from dataclasses import dataclass, field # Import dataclass
from systems.core.base_system import BaseSystem
from systems.core.system_manager import SystemEventType, system_manager
# from .formation_system import FormationSystem # REMOVE - This file doesn't exist
from systems.formation_movement import Formation # Corrected import
from .team_agent import TeamAgent, DefenderTeamAgent, AttackerTeamAgent, SupportTeamAgent, ScoutTeamAgent
from .agent_factory import create_agent
from .personality_system import PersonalitySystem, PersonalityTrait

# Configure logger
logger = logging.getLogger('battle_arena')

class TeamSystem(BaseSystem):
    """
    Unified team system that handles formations, coordination, 
    shared abilities, and team relationships.
    
    This system consolidates functionality previously spread across
    multiple files (team_mechanics.py, team_formation.py, team_coordinator.py).
    """
    
    def __init__(self):
        super().__init__("team_system", priority=20)
        
        # Set up logger
        self.logger = logger
        
        # Team abilities
        self.team_abilities = {
            'shield_wall': {
                'energy_cost': 50,
                'duration': 180,
                'radius': 100
            },
            'coordinated_strike': {
                'energy_cost': 75,
                'damage_bonus': 2.0,
                'duration': 120
            },
            'energy_transfer': {
                'energy_cost': 30,
                'efficiency': 0.8
            }
        }
        
        # Team data
        self.teams = {}
        self.team_positions = {}
        self.team_relations = {}
        self.formation_scores = {}
        self.active_abilities = {}
        self.memory = {
            'formations': {},
            'strategy_success': {}
        }
        
        # Formation settings
        self.formation_tolerance = 30
        
        # Personality system
        self.personality_system = None
        
        # ADDED: Reference to FormationMovementSystem
        self.formation_movement_system = None

        # --- ADDED: Morale/Suppression System Reference ---
        self._morale_suppression_system: Optional["MoraleSuppressionSystem"] = None
        # --------------------------------------------------
        
    # --- ADDED: Lazy loader property for MoraleSuppressionSystem ---
    @property
    def morale_suppression_system(self) -> Optional["MoraleSuppressionSystem"]:
        if self._morale_suppression_system is None:
            try:
                from systems.morale.morale_suppression_system import MoraleSuppressionSystem # Import here
            except ImportError:
                 logger.warning("TeamSystem: MoraleSuppressionSystem not found/importable.")
                 return None
            self._morale_suppression_system = system_manager.get_system("morale_suppression_system")
            if not self._morale_suppression_system:
                 logger.warning("TeamSystem: MoraleSuppressionSystem not found via system_manager.")
        return self._morale_suppression_system
    # ------------------------------------------------------------

    def _initialize(self) -> None:
        """Initialize the team system."""
        # Subscribe to relevant events
        system_manager.subscribe(SystemEventType.AGENT_ACTION, self._on_agent_action)
        system_manager.subscribe(SystemEventType.COMBAT_STARTED, self._on_combat_started)
        # ADDED: Subscribe to potential team-level outcome events
        system_manager.subscribe(SystemEventType.TEAM_ACTION_SUCCESS, self._handle_team_outcome)
        system_manager.subscribe(SystemEventType.TEAM_ACTION_FAILURE, self._handle_team_outcome)
        # Add subscriptions for other relevant events like OBJECTIVE_COMPLETE etc. if they exist

        # Get personality system from shared state
        self.personality_system = system_manager.get_shared_state("personality_system")
        if not self.personality_system:
            # If not found, try creating one (assuming PersonalitySystem needs no args)
            try:
                 self.personality_system = PersonalitySystem()
                 system_manager.set_shared_state("personality_system", self.personality_system)
            except Exception as e:
                 # Fallback if creation fails
                 self.logger.warning(f"Could not get or create PersonalitySystem: {e}")
                 self.personality_system = None

        # ADDED: Get FormationMovementSystem reference
        self.formation_movement_system = system_manager.get_system("formation_movement_system")
        if not self.formation_movement_system:
             self.logger.error("TeamSystem could not find required system 'formation_movement_system'. Formation bonus calculations may fail.")
    
    def _update(self, delta_time: float) -> None:
        """
        Update team formations, abilities, and relationships.
        
        Args:
            delta_time: Time since last update
        """
        # Update active abilities
        self._update_abilities(delta_time)
        
        # Update team positions in shared state
        system_manager.set_shared_state('team_positions', self.team_positions)
        system_manager.set_shared_state('team_formations', self.get_current_formations())
    
    def _shutdown(self) -> None:
        """Shutdown the team system."""
        # Unsubscribe from events
        system_manager.unsubscribe(SystemEventType.AGENT_ACTION, self._on_agent_action)
        system_manager.unsubscribe(SystemEventType.COMBAT_STARTED, self._on_combat_started)
        
        # Clean up any resources
        pass
        
    def get_system(self, name: str) -> Any:
        """Get a system from the system manager."""
        return system_manager.get_system(name)
        
    def set_shared_state(self, key: str, value: Any) -> None:
        """Set a value in shared state."""
        system_manager.set_shared_state(key, value)
        
    def get_shared_state(self, key: str, default: Any = None) -> Any:
        """Get a value from shared state."""
        return system_manager.get_shared_state(key, default)
    
    def create_team(self, team_id: str, agent_names: List[str]) -> Dict:
        """
        Create a new team.
        
        Args:
            team_id: Unique team identifier
            agent_names: List of agent names to include in the team
            
        Returns:
            Team data dictionary
        """
        team = {
            'id': team_id,
            'members': agent_names,
            'formation': 'triangle',  # Default formation
            'leader': agent_names[0] if agent_names else None,
            'roles': {},
            'performance': {
                'kills': 0,
                'resources_collected': 0,
                'damage_dealt': 0,
                'formation_score': 0
            }
        }
        
        # Assign team leader based on leadership trait if personality system is available
        if self.personality_system and len(agent_names) > 1:
            # Assuming get_leadership_hierarchy exists and returns sorted list [(agent_id, score)]
            try:
                leadership_hierarchy = self.personality_system.get_leadership_hierarchy(agent_names)
                if leadership_hierarchy:
                    team['leader'] = leadership_hierarchy[0][0]  # Agent with highest leadership score
            except AttributeError:
                 self.logger.warning("PersonalitySystem does not have 'get_leadership_hierarchy' method.")
            except Exception as e:
                 self.logger.warning(f"Error getting leadership hierarchy: {e}")
        
        # Assign roles based on the default formation
        self._assign_roles(team_id)
        
        # Store the team
        self.teams[team_id] = team
        self.team_positions[team_id] = []
        
        # Update team personality in personality system
        if self.personality_system:
            try:
                 self.personality_system.update_team_personalities(team_id, agent_names)
            except AttributeError:
                 self.logger.warning("PersonalitySystem does not have 'update_team_personalities' method.")
            except Exception as e:
                 self.logger.warning(f"Error updating team personalities: {e}")
        
        return team
    
    def _assign_roles(self, team_id: str) -> None:
        """
        Assign roles to team members based on the current formation (fetched from FMS) 
        and personality traits.
        
        Args:
            team_id: ID of the team to assign roles for.
        """
        if team_id not in self.teams:
            self.logger.error(f"Attempted to assign roles for non-existent team {team_id}")
            return
            
        team = self.teams[team_id]
        members = team['members']
        
        # Get formation definition from the FormationMovementSystem library
        formation_type = None
        formation_def = None
        if self.formation_movement_system:
            try:
                # Get current formation type from FMS
                formation_type = self.formation_movement_system.get_team_formation(team_id) # Assumes getter exists
                if formation_type:
                    # Get definition from FMS library
                    formation_def = self.formation_movement_system.library.get_formation(formation_type)
                else:
                    self.logger.warning(f"Could not get current formation type for team {team_id} from FMS.")
            except AttributeError as e:
                self.logger.error(f"Error accessing FMS library/methods in _assign_roles: {e}")

        if not formation_def:
            # Use the last known formation type from TeamSystem state as a fallback for logging?
            last_known_formation = team.get('_last_formation_type_', 'unknown') # Need to store this maybe?
            self.logger.warning(f"Formation definition '{formation_type or last_known_formation}' not found via FMS for team {team_id}. Using default roles.")
            # Fallback roles if formation not found
            roles = [f"member_{i}" for i in range(len(members))]
        else:
            # Extract roles from the FormationPosition objects in the list
            # Ensure enough roles are defined for the members
            defined_roles = [pos.role for pos in formation_def.positions]
            roles = defined_roles + ['member'] * (len(members) - len(defined_roles)) # Pad with 'member' if needed
            roles = roles[:len(members)] # Truncate if more roles defined than members
        
        role_assignments = {}
        
        # If personality system is available, try to assign roles based on traits
        # This part needs careful review based on how traits map to specific roles defined in formations
        if self.personality_system:
            members_with_traits = []
            for member in members:
                personality = None
                try:
                    personality = self.personality_system.get_agent_personality(member)
                except AttributeError:
                     self.logger.warning("PersonalitySystem does not have 'get_agent_personality'.")
                     break # Stop trying if method doesn't exist
                except Exception as e:
                     self.logger.warning(f"Error getting personality for {member}: {e}")
                
                if personality:
                    members_with_traits.append((member, personality))
            
            if members_with_traits:
                 # TODO: Implement or refine personality-based role assignment.
                 # This needs a mapping from traits to role suitability (e.g., high aggression -> attacker)
                 # For now, just assign roles sequentially as defined by formation
                 remaining_roles = list(roles)
                 assigned_members = set()
                 # Example: Assign leader role first based on leadership trait
                 leader_role = next((r for r in remaining_roles if r == 'leader'), None)
                 if leader_role and self.personality_system:
                     try:
                         hierarchy = self.personality_system.get_leadership_hierarchy(members)
                         if hierarchy:
                             leader_agent = hierarchy[0][0]
                             role_assignments[leader_agent] = 'leader'
                             remaining_roles.remove('leader')
                             assigned_members.add(leader_agent)
                     except AttributeError:
                         pass # Ignore if method doesn't exist
                 
                 # Assign remaining roles sequentially to unassigned members
                 member_iter = iter(m[0] for m in members_with_traits if m[0] not in assigned_members)
                 for role in remaining_roles:
                      try:
                           member = next(member_iter)
                           role_assignments[member] = role
                           assigned_members.add(member)
                      except StopIteration:
                           break # No more members to assign roles to
                 # Assign default role to any remaining members
                 for member in members:
                      if member not in assigned_members:
                           role_assignments[member] = 'member' # Default role
            else:
                # Fallback if personality traits couldn't be fetched for any member
                for i, member in enumerate(members):
                    role_assignments[member] = roles[i] if i < len(roles) else 'member'
        else:
            # Default sequential role assignment without personality
            for i, member in enumerate(members):
                 role_assignments[member] = roles[i] if i < len(roles) else 'member'
        
        team['roles'] = role_assignments
        self.logger.debug(f"Assigned roles for team {team_id}: {role_assignments}")
    
    def update_team_positions(self, team_id: str, positions: List[Tuple[float, float]]) -> None:
        """
        Update the current positions of team members.
        
        Args:
            team_id: Team identifier
            positions: List of current positions (x, y) for team members
        """
        if team_id in self.teams:
            self.team_positions[team_id] = positions
    
    def get_formation_bonus(self, team_id: str) -> float:
        """
        Get the combat bonus for maintaining formation, adjusted by personality compatibility.
        Queries FormationMovementSystem for the score and formation definition.
        
        Args:
            team_id: Team identifier
            
        Returns:
            Combat bonus multiplier
        """
        if team_id not in self.teams:
            return 1.0

        # Check if FormationMovementSystem is available
        if not self.formation_movement_system:
             self.logger.warning(f"FormationMovementSystem not available for team {team_id} bonus calculation. Returning 1.0")
             return 1.0
            
        # Get formation score from FormationMovementSystem
        formation_score = 0.0
        try:
             formation_score = self.formation_movement_system.get_formation_score(team_id)
        except AttributeError:
             self.logger.warning(f"FMS missing get_formation_score method for team {team_id}.")
        except Exception as e:
             self.logger.warning(f"Error getting formation score from FMS for {team_id}: {e}")

        # Get formation type and definition from FormationMovementSystem's library
        formation_type = None
        formation_def = None
        try:
             formation_type = self.formation_movement_system.get_team_formation(team_id)
             if formation_type:
                  formation_def = self.formation_movement_system.library.get_formation(formation_type)
             else:
                  self.logger.warning(f"Could not get formation type for team {team_id} from FMS in get_formation_bonus.")
        except AttributeError as e:
             self.logger.error(f"Error accessing FMS library/methods in get_formation_bonus for team {team_id}: {e}")

        if not formation_def:
             base_bonus = 1.0 # No bonus if formation unknown
             self.logger.warning(f"Formation definition '{formation_type or 'unknown'}' not found via FMS for bonus calculation for team {team_id}.")
        else:
             # Assuming formation_def has a 'bonus' attribute or similar
             # Check if tactical_properties exists and contains a relevant bonus key
             tactical_props = getattr(formation_def, 'tactical_properties', {})
             # Define which property contributes to a general combat bonus (e.g., average? specific one?)
             # Let's assume a simple 'combat_bonus' property or default to 1.0
             base_bonus = tactical_props.get('combat_bonus', 1.0)
             # If no specific combat bonus, maybe use average of offensive/defensive?
             if base_bonus == 1.0:
                  offensive = tactical_props.get('offensive', 0.0)
                  defensive = tactical_props.get('defensive', 0.0)
                  if offensive > 0 or defensive > 0:
                       # Map avg(off, def) [0-1] to a bonus [1.0 - 1.x]
                       avg_combat_prop = (offensive + defensive) / 2.0
                       base_bonus = 1.0 + (avg_combat_prop * 0.2) # Example: Max 20% bonus from avg props
        
        bonus = 1.0 + (base_bonus - 1.0) * formation_score # Apply score scaling to the bonus amount
        
        # Apply personality compatibility bonus if available
        if self.personality_system:
            team_members = self.teams[team_id]['members']
            # Assuming calculate_team_compatibility exists and returns score 0-1
            compatibility = 0.5 # Default if calculation fails
            try:
                 compatibility = self.personality_system.calculate_team_compatibility(team_members)
            except AttributeError:
                 self.logger.warning("PersonalitySystem lacks 'calculate_team_compatibility'.")
            except Exception as e:
                 self.logger.warning(f"Error calculating team compatibility: {e}")
            
            # Adjust bonus based on compatibility (e.g., up to 20% additional bonus)
            # Map compatibility (0-1) to a modifier (e.g., 0.8-1.2)
            compatibility_mod = 0.8 + compatibility * 0.4
            bonus *= compatibility_mod
        
        return bonus
    
    def change_formation(self, team_id: str, formation_type: str) -> bool:
        """
        Change a team's formation by requesting the change from FormationMovementSystem.
        Also triggers role reassignment.
        
        Args:
            team_id: Team identifier
            formation_type: New formation type
            
        Returns:
            True if successful, False otherwise
        """
        # Check if FormationMovementSystem is available
        if not self.formation_movement_system:
             self.logger.error("FormationMovementSystem not available. Cannot change formation.")
             return False

        # Check if formation exists in the library via FMS
        formation_def = None
        try:
             formation_def = self.formation_movement_system.library.get_formation(formation_type)
        except AttributeError:
             self.logger.error("FormationMovementSystem missing library or get_formation.")
             return False
        except Exception as e:
             self.logger.error(f"Error checking formation '{formation_type}' in FMS library: {e}")
             return False

        # Removed check: if team_id not in self.teams ... (FMS will handle unknown team)
        if not formation_def:
            self.logger.warning(f"Cannot change team {team_id} to invalid formation '{formation_type}'")
            return False
        
        # REMOVED: team = self.teams[team_id]
        # REMOVED: team['formation'] = formation_type
        
        # Request FormationMovementSystem to set the new formation
        fms_success = False
        try:
             fms_success = self.formation_movement_system.set_team_formation(team_id, formation_type)
             if not fms_success:
                  self.logger.warning(f"Failed to set formation '{formation_type}' in FormationMovementSystem for team {team_id}.")
                  return False # If FMS fails, the change didn't happen
        except AttributeError:
             self.logger.error("FormationMovementSystem missing set_team_formation method.")
             return False
        except Exception as e:
             self.logger.error(f"Error setting formation in FMS for {team_id}: {e}")
             return False

        # If FMS succeeded, reassign roles based on the new formation
        # The roles depend on the formation *now active* in FMS
        self._assign_roles(team_id)

        # Emit formation change event
        self.emit_event(SystemEventType.FORMATION_CHANGED, {
            'team_id': team_id,
            'formation': formation_type
        })
        self.logger.info(f"Team {team_id} changed formation to {formation_type}")
        return True
    
    def use_team_ability(self, team_id: str, ability_name: str, 
                        initiator: str, target_pos: Tuple[float, float]) -> bool:
        """
        Activate a team ability.
        
        Args:
            team_id: Team identifier
            ability_name: Name of the ability to use
            initiator: Name of the agent initiating the ability
            target_pos: Target position for the ability
            
        Returns:
            True if the ability was activated, False otherwise
        """
        if (team_id not in self.teams or 
            ability_name not in self.team_abilities or
            initiator not in self.teams[team_id]['members']):
            return False
            
        ability = self.team_abilities[ability_name]
        
        # Check if the team has enough energy (would need to be tracked elsewhere)
        # For now, just allow the ability to be used
        
        # Create the active ability
        active_ability = {
            'name': ability_name,
            'team_id': team_id,
            'initiator': initiator,
            'target_pos': target_pos,
            'duration': ability['duration'],
            'remaining': ability['duration']
        }
        
        # Add to active abilities
        ability_id = f"{team_id}_{ability_name}_{len(self.active_abilities)}"
        self.active_abilities[ability_id] = active_ability
        
        return True
    
    def _update_abilities(self, delta_time: float) -> None:
        """
        Update active team abilities.
        
        Args:
            delta_time: Time since last update
        """
        # Convert delta_time to frames (assuming 60 FPS for duration counts)
        # TODO: Make duration time-based (seconds) instead of frame-based
        frames = int(delta_time * 60) # This might be inaccurate if FPS varies
        
        # Update ability durations
        for ability_id in list(self.active_abilities.keys()):
            ability = self.active_abilities[ability_id]
            ability['remaining'] -= frames # Decrement by frames for now
            
            if ability['remaining'] <= 0:
                # Ability has expired
                del self.active_abilities[ability_id]
    
    def get_active_abilities(self, team_id: str = None) -> Dict:
        """
        Get all active abilities, optionally filtered by team.
        
        Args:
            team_id: Optional team identifier to filter by
            
        Returns:
            Dictionary of active abilities
        """
        if team_id:
            return {k: v for k, v in self.active_abilities.items() if v['team_id'] == team_id}
        return self.active_abilities
    
    def update_team_relations(self, team_id: str, other_team_id: str, relation_change: float) -> None:
        """
        Update the relationship between two teams.
        
        Args:
            team_id: First team identifier
            other_team_id: Second team identifier
            relation_change: Change in relationship (-1.0 to 1.0)
        """
        if team_id not in self.team_relations:
            self.team_relations[team_id] = {}
            
        if other_team_id not in self.team_relations[team_id]:
            self.team_relations[team_id][other_team_id] = 0.0 # Neutral default
        
        # Update the relationship value, clamping between -1 and 1
        current = self.team_relations[team_id][other_team_id]
        self.team_relations[team_id][other_team_id] = max(-1.0, min(1.0, current + relation_change))
    
    def should_help_ally(self, team_id: str, other_team_id: str) -> bool:
        """
        Determine if one team should help another based on their relationship.
        
        Args:
            team_id: First team identifier
            other_team_id: Second team identifier
            
        Returns:
            True if the first team should help the second
        """
        if team_id not in self.team_relations or other_team_id not in self.team_relations[team_id]:
            return False # No relationship established
        
        # Help if relationship is positive enough (e.g., > 0.3)
        return self.team_relations[team_id][other_team_id] > 0.3
    
    def get_team_color(self, team_id: str) -> Tuple[int, int, int]:
        """
        Get the color associated with a team.
        
        Args:
            team_id: Team identifier
            
        Returns:
            RGB color tuple
        """
        # Generate a consistent color based on the team_id
        if not team_id:
            return (200, 200, 200) # Default grey
        
        # Use hash of team_id to generate color
        try:
             # Use a simpler seeding approach for consistency
             random.seed(team_id)
             r = random.randint(50, 255)
             g = random.randint(50, 255)
             b = random.randint(50, 255)
             # Ensure minimum brightness/saturation to avoid dark/grey colors
             if r+g+b < 300:
                  if r < 100: r += 50
                  if g < 100: g += 50
                  if b < 100: b += 50
             random.seed() # Reset seed
        except Exception as e:
             self.logger.error(f"Error generating team color for {team_id}: {e}")
             return (150, 150, 150) # Fallback color
        
        return (r, g, b)
    
    def get_current_formations(self) -> Dict[str, str]:
        """
        Get the current formation for each team.
        
        Returns:
            Dictionary mapping team IDs to formation types
        """
        return {team_id: team.get('formation', 'unknown') for team_id, team in self.teams.items()} # Use .get() for safety
    
    def get_team_id_for_agent(self, agent_id: str) -> Optional[str]:
        """
        Find the team ID for a given agent ID.

        Args:
            agent_id (str): The unique identifier of the agent.

        Returns:
            Optional[str]: The team ID if the agent is found in a team, otherwise None.
        """
        for team_id, team_data in self.teams.items():
            if agent_id in team_data.get('agents', set()):
                return team_id
        return None
    
    def _on_agent_action(self, data: Dict) -> None:
        """
        Handle events related to agent actions for potential team coordination.
        
        Args:
            data: Event data (e.g., {'agent_id': ..., 'action_type': ..., 'details': ...})
        """
        # Placeholder for future team coordination logic based on individual actions
        pass
    
    def _on_combat_started(self, data: Dict) -> None:
        """
        Handle combat started events. May trigger formation suggestions via FMS.
        
        Args:
            data: Event data ({ 'attacker_id': ..., 'target_id': ..., 'position': ... })
                  or potentially {'team_id': ..., 'enemy_positions': ...}
        """
        # Example: Suggest formations or abilities based on combat situation
        # This requires the event data to contain necessary info like team involved
        # and enemy locations.
        
        # Check if team context is provided
        team_id = None
        enemy_positions = None
        
        # Attempt to find team_id from attacker or target if not directly provided
        if 'attacker_id' in data:
             for tid, team_data in self.teams.items():
                  if data['attacker_id'] in team_data['members']:
                       team_id = tid
                       break
        elif 'target_id' in data:
              for tid, team_data in self.teams.items():
                  if data['target_id'] in team_data['members']:
                       team_id = tid
                       # We might need enemy positions relative to this team
                       break
        
        # If direct enemy positions are provided
        if 'enemy_positions' in data:
             enemy_positions = data['enemy_positions']
        elif 'position' in data and team_id: # Use the combat position as a proxy enemy pos
            enemy_positions = [data['position']]
        
        if team_id and enemy_positions and self.formation_movement_system:
            # Suggest a formation using FormationMovementSystem
            try:
                 # Build context for FMS suggestion
                 context = {
                     'enemy_count': len(enemy_positions),
                     'under_attack': True, # Assume combat started means under attack
                     # Need terrain info if FMS uses it
                     'open_terrain': True # Placeholder
                 }
                 suggested_formation = self.formation_movement_system.suggest_formation(team_id, context) 

                 if suggested_formation:
                      # Optional: TeamSystem could decide whether to actually change formation
                      # based on personality or current state.
                      # For now, just log the suggestion.
                      self.logger.info(f"Combat started for team {team_id}. FMS suggests formation: {suggested_formation}")
                      # Or emit a different event like FORMATION_SUGGESTED
                      # self.emit_event(SystemEventType.FORMATION_SUGGESTED, { ... })
                 else:
                      self.logger.info(f"Combat started for team {team_id}, but FMS provided no formation suggestion.")

            except AttributeError:
                 self.logger.warning("FormationMovementSystem missing suggest_formation method.")
            except Exception as e:
                 self.logger.warning(f"Error getting formation suggestion from FMS for {team_id}: {e}")

        # Original event emission removed - suggestion is handled above
        # self.emit_event(SystemEventType.FORMATION_CHANGED, { ... }) 

    # --- ADDED: Central handler for team outcome events --- #
    def _handle_team_outcome(self, data: Dict) -> None:
        """Handles events indicating team-level success or failure."""
        team_id = data.get('team_id')
        success = data.get('success') # Check if event explicitly defines success/failure
        event_type = data.get('event_type', 'unknown_team_outcome') # Specific type like 'objective_capture'
        reason = f"{event_type}_{ 'success' if success else 'failure' }"

        # Determine success based on event type if 'success' field is absent
        if success is None:
            if event_type.endswith("_SUCCESS"): success = True
            elif event_type.endswith("_FAILURE"): success = False
            else: return # Cannot determine outcome

        if not team_id:
            logger.warning(f"Received team outcome event ({event_type}) without team_id.")
            return

        if team_id not in self.teams:
            logger.warning(f"Received outcome event for unknown team: {team_id}")
            return

        # Determine morale change from config
        # Assumes MoraleSystem config has MORALE_EVENT_MODIFIERS dict
        modifier = 0.0
        if self.morale_suppression_system:
             config_modifiers = self.morale_suppression_system._morale_event_modifiers
             morale_key = "team_victory" if success else "team_defeat"
             # Allow specific event types to override default team win/loss modifiers
             if event_type in config_modifiers:
                  modifier = config_modifiers[event_type]
             else:
                  modifier = config_modifiers.get(morale_key, 0.0)
        else:
            logger.warning("Cannot apply morale change for team outcome: MoraleSuppressionSystem not found.")
            return

        if modifier == 0.0:
             logger.debug(f"No morale modifier defined for team outcome event: {event_type} (success={success})")
             return

        # Apply morale change to all team members
        team_data = self.teams[team_id]
        members = team_data.get("members", [])
        applied_count = 0
        for member_data in members:
            member_id = member_data if isinstance(member_data, str) else member_data.get('agent_id')
            if member_id:
                self.morale_suppression_system.apply_morale_change(member_id, modifier, reason)
                applied_count += 1
        logger.info(f"Applied morale change ({modifier:.2f}) to {applied_count} members of team {team_id} for event: {reason}") 