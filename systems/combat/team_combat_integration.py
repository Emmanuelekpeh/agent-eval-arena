import random
import math
import logging
from typing import Dict, List, Tuple, Optional, Any
# Import system classes directly for type hints
from systems.agents.team_system import TeamSystem
from systems.combat.combat_system import CombatSystem
from systems.agents.agent_system import AgentSystem
from systems.agents.personality_system import PersonalitySystem
from systems.core.system_manager import system_manager # Import the manager

logger = logging.getLogger(__name__)

# Forward declare AgentSystem to resolve circular dependency for type hint if needed
# class AgentSystem: # Not needed if imported above
#     pass

class TeamCombatIntegration:
    """
    Integrates team dynamics with combat, enhancing combat mechanics with
    team-based bonuses, tactics, and coordination.
    """
    
    def __init__(self):
        """
        Initialize the team combat integration.
        Dependencies are fetched lazily.
        """
        # Dependency placeholders
        self._team_system_instance: Optional[TeamSystem] = None
        self._combat_system_instance: Optional[CombatSystem] = None
        self._agent_system_instance: Optional[AgentSystem] = None
        self._personality_system_instance: Optional[PersonalitySystem] = None

        # Team combat stats
        self.team_damage = {}  # {team_id: total_damage}
        self.team_kills = {}   # {team_id: total_kills}
        self.team_abilities_used = {}  # {team_id: {ability: count}}
        
        # Coordination bonuses
        self.coordination_bonus = {
            "damage": 0.2,      # +20% damage for coordinated attacks
            "accuracy": 0.15,   # +15% accuracy for coordinated attacks
            "defense": 0.25     # +25% damage reduction when in formation
        }
        
        logger.info("Team Combat Integration initialized (Dependencies will be loaded lazily)")
        
    # --- Lazy Loading Properties ---
    @property
    def team_system(self) -> Optional[TeamSystem]:
        if self._team_system_instance is None:
            self._team_system_instance = system_manager.get_system("TeamSystem")
            if not self._team_system_instance:
                logger.error("TeamCombatIntegration: TeamSystem not found!")
        return self._team_system_instance

    @property
    def combat_system(self) -> Optional[CombatSystem]:
        if self._combat_system_instance is None:
            self._combat_system_instance = system_manager.get_system("CombatSystem")
            if not self._combat_system_instance:
                logger.error("TeamCombatIntegration: CombatSystem not found!")
        return self._combat_system_instance

    @property
    def agent_system(self) -> Optional[AgentSystem]:
        if self._agent_system_instance is None:
            self._agent_system_instance = system_manager.get_system("AgentSystem")
            if not self._agent_system_instance:
                logger.error("TeamCombatIntegration: AgentSystem not found!")
        return self._agent_system_instance

    @property
    def personality_system(self) -> Optional[PersonalitySystem]:
        if self._personality_system_instance is None:
            self._personality_system_instance = system_manager.get_system("PersonalitySystem")
            # Optional, no error needed if not found
        return self._personality_system_instance

    # --- End Lazy Loading Properties ---

    def register_team(self, team_id):
        """Register a team for combat tracking"""
        if team_id not in self.team_damage:
            self.team_damage[team_id] = 0
            self.team_kills[team_id] = 0
            self.team_abilities_used[team_id] = {}
            
    def update_team_stats(self, agent_id, damage=0, kill=False):
        """Update combat stats for an agent's team"""
        if not self.team_system: return # Check dependency
        team_id = self.team_system.get_team_id_for_agent(agent_id)
        if not team_id:
            return
            
        # Register team if not already tracked
        self.register_team(team_id)
        
        # Update team damage and kills
        self.team_damage[team_id] += damage
        if kill:
            self.team_kills[team_id] += 1
            
    def calculate_team_attack_bonus(self, attacker_id, target_id, attacker_pos, target_pos):
        """
        Calculate attack bonuses based on team formations and coordination.
        
        Args:
            attacker_id: ID of the attacking agent
            target_id: ID of the target agent
            attacker_pos: (x, y) position of attacker
            target_pos: (x, y) position of target
            
        Returns:
            dict: Bonuses for damage, accuracy, critical chance
        """
        if not self.team_system or not self.agent_system: return {"damage": 1.0, "accuracy": 1.0, "critical": 1.0} # Check dependencies
        team_id = self.team_system.get_team_id_for_agent(attacker_id)
        if not team_id:
            return {"damage": 1.0, "accuracy": 1.0, "critical": 1.0}
            
        # Get formation score (how well the team is maintaining formation)
        formation_score = self.team_system.get_formation_score(team_id)
        
        # Base bonuses from formation score
        damage_bonus = 1.0 + (formation_score * self.coordination_bonus["damage"])
        accuracy_bonus = 1.0 + (formation_score * self.coordination_bonus["accuracy"])
        critical_bonus = 1.0 + (formation_score * 0.1)  # +10% critical chance at max formation
        
        # Check for coordinated attacks (multiple team members targeting same enemy)
        target_team_id = self.team_system.get_team_id_for_agent(target_id)
        if target_team_id and target_team_id == team_id:
            # Don't apply bonuses when targeting teammates
            return {"damage": 1.0, "accuracy": 1.0, "critical": 1.0}
            
        # Check how many teammates are also engaging this target
        teammates_attacking = self._count_teammates_attacking(team_id, target_id)
        
        # Additional bonus for coordinated attacks
        if teammates_attacking > 0:
            damage_bonus += teammates_attacking * 0.1  # +10% per teammate attacking
            accuracy_bonus += teammates_attacking * 0.05  # +5% per teammate attacking
            
        # Apply additional bonuses based on agent roles
        role_bonuses = self._calculate_role_bonuses(attacker_id, target_id)
        damage_bonus *= role_bonuses.get("damage", 1.0)
        accuracy_bonus *= role_bonuses.get("accuracy", 1.0)
        critical_bonus *= role_bonuses.get("critical", 1.0)
        
        # --- Integrate Personality Influence ---
        if self.personality_system:
             # Attacker leadership/cooperation might improve bonus
             # ... (logic using self.personality_system) ...
             pass # Placeholder if no specific logic yet
        # Ensure return is outside the if block but at the correct method level
        return {
            "damage": damage_bonus,
            "accuracy": accuracy_bonus,
            "critical": critical_bonus
        }
        
    def _count_teammates_attacking(self, team_id, target_id):
        """Count how many members of a team are attacking the same target using AgentSystem."""
        if not self.team_system or not self.agent_system: return 0 # Check dependencies
        count = 0
        team_members = self.team_system.teams.get(team_id, {}).get("members", [])
        if not team_members:
            return 0

        # Check the agent_system's target dictionary
        if hasattr(self.agent_system, 'agent_targets'):
            for member_id in team_members:
                # Ensure member_id is used correctly if team_members contains dicts
                actual_member_id = member_id if isinstance(member_id, str) else member_id.get('agent_id')
                if not actual_member_id:
                     continue

                if self.agent_system.agent_targets.get(actual_member_id) == target_id:
                    count += 1
        else:
            logger.warning("AgentSystem does not have 'agent_targets' attribute. Cannot count coordinated attacks.")
            # Fallback or return 0
            return 0

        # --- Integrate Personality Influence ---
        if self.personality_system:
            # Defender conscientiousness/loyalty might improve bonus
            # ... (logic using self.personality_system) ...
            pass # Placeholder if no specific logic yet
        # Ensure return is outside the if block but at the correct method level
        return count
        
    def _calculate_role_bonuses(self, attacker_id, target_id):
        """Calculate combat bonuses based on agent roles"""
        if not self.team_system: return {} # Check dependency
        team_id = self.team_system.get_team_id_for_agent(attacker_id)
        if not team_id:
            return {}
            
        # Get agent's role
        team = self.team_system.teams.get(team_id, {})
        agent_role = None
        for member in team.get("members", []):
            if member["agent_id"] == attacker_id:
                agent_role = member.get("role")
                break
                
        if not agent_role:
            return {}
            
        # Apply role-specific bonuses
        bonuses = {}
        
        if agent_role == "attacker":
            bonuses["damage"] = 1.2  # +20% damage for attackers
            bonuses["critical"] = 1.15  # +15% critical chance
            
        elif agent_role == "defender":
            bonuses["damage"] = 0.9  # -10% damage
            bonuses["accuracy"] = 1.1  # +10% accuracy
            
        elif agent_role == "scout":
            bonuses["accuracy"] = 1.15  # +15% accuracy
            bonuses["critical"] = 1.1  # +10% critical chance
            
        elif agent_role == "support":
            bonuses["damage"] = 0.8  # -20% damage
            # Support agents get special team coordination bonuses instead
            
        return bonuses
        
    def calculate_defense_bonus(self, defender_id, attacker_id):
        """
        Calculate defense bonus based on team formation, position, and threat level.
        
        Args:
            defender_id: ID of the defending agent
            attacker_id: ID of the attacking agent
            
        Returns:
            float: Damage reduction multiplier (lower means more reduction)
        """
        if not self.team_system: return 1.0 # Check dependency
        team_id = self.team_system.get_team_id_for_agent(defender_id)
        if not team_id:
            return 1.0
            
        # Get formation score
        formation_score = self.team_system.get_formation_score(team_id)
        
        # Base defense bonus from formation
        defense_bonus = 1.0 - (formation_score * self.coordination_bonus["defense"])
        
        # Check if defender has a "defender" role for additional bonus
        team = self.team_system.teams.get(team_id, {})
        is_defender = False
        for member in team.get("members", []):
            # Ensure member_id is used correctly if team_members contains dicts
            member_id = member if isinstance(member, str) else member.get('agent_id')
            if member_id == defender_id and (member.get("role") if isinstance(member, dict) else None) == "defender":
                is_defender = True
                break
                
        if is_defender:
            defense_bonus *= 0.8  # Additional 20% damage reduction for defenders
            
        # Check threat level from AgentSystem
        threat_level = 0
        if hasattr(self.agent_system, 'agent_threat_level'):
            threat_level = self.agent_system.agent_threat_level.get(defender_id, 0)
        else:
            logger.warning("AgentSystem does not have 'agent_threat_level' attribute. Cannot apply threat penalty.")

        # Apply penalty if attacked by multiple enemies (e.g., reduce effectiveness of defense bonus)
        if threat_level > 1:
            # Example: Reduce the *benefit* of the defense bonus by 10% per extra attacker
            threat_penalty = 1.0 + (threat_level - 1) * 0.10
            # Apply penalty: If bonus was 0.7 (30% reduction), threat 2 makes it 0.7 * 1.1 = 0.77 (23% reduction)
            defense_bonus = min(1.0, defense_bonus * threat_penalty)
        
        # --- Integrate Personality Influence ---
        if self.personality_system:
            # Defender conscientiousness/loyalty might improve bonus
            # ... (logic using self.personality_system) ...
            pass # Placeholder if no specific logic yet
        # Ensure return is outside the if block but at the correct method level
        return max(0.5, defense_bonus)  # Cap at 50% damage reduction
        
    def execute_team_ability(self, team_id, ability_name, initiator_id, target_position=None):
        """
        Execute a team combat ability.
        
        Args:
            team_id: ID of the team using the ability
            ability_name: Name of the ability to use
            initiator_id: ID of the agent initiating the ability
            target_position: Optional target position
            
        Returns:
            bool: True if the ability was used successfully
        """
        if not self.team_system or not self.agent_system or not self.combat_system: return False # Check dependencies
        # Register team if not already tracked
        self.register_team(team_id)
        
        # Check if ability exists and is available
        if not self.team_system.use_team_ability(team_id, ability_name, initiator_id, target_position):
            return False
            
        # Track ability usage
        if ability_name not in self.team_abilities_used[team_id]:
            self.team_abilities_used[team_id][ability_name] = 0
        self.team_abilities_used[team_id][ability_name] += 1
        
        # Apply ability effects based on the ability type
        if ability_name == "coordinated_attack":
            return self._execute_coordinated_attack(team_id, initiator_id, target_position)
        elif ability_name == "defensive_formation":
            return self._execute_defensive_formation(team_id, initiator_id)
        elif ability_name == "flanking_maneuver":
            return self._execute_flanking_maneuver(team_id, initiator_id, target_position)
            
        return False
        
    def _execute_coordinated_attack(self, team_id, initiator_id, target_position):
        """Execute a coordinated team attack by applying a temporary buff to nearby attackers.

           Assumes CombatSystem has apply_status_effect(agent_id, effect_type, duration, strength).
           Assumes TeamSystem has get_team_members(team_id) -> List[str].
           Assumes AgentSystem has agent_positions: Dict[str, Tuple[float, float]].
        """
        logger.info(f"Team {team_id} executing coordinated attack near {target_position}")
        
        attack_radius = 150 # How close teammates need to be to the target position
        effect_duration = 5.0 # Seconds the buff lasts
        damage_boost = 1.3 # 30% damage boost
        accuracy_boost = 1.2 # 20% accuracy boost

        team_members = self.team_system.teams.get(team_id, {}).get("members", [])
        if not team_members:
             return False

        participants = 0
        for member_id_data in team_members:
            member_id = member_id_data if isinstance(member_id_data, str) else member_id_data.get('agent_id')
            if not member_id:
                 continue

            # Get member position from AgentSystem (assuming it exists)
            member_pos = self.agent_system.agent_positions.get(member_id)
            if not member_pos or not target_position:
                continue

            # Check distance to target position
            dist_sq = (member_pos[0] - target_position[0])**2 + (member_pos[1] - target_position[1])**2
            if dist_sq <= attack_radius**2:
                # Apply status effect via CombatSystem
                try:
                     # Apply separate buffs for damage and accuracy if CombatSystem handles them
                     self.combat_system.apply_status_effect(member_id, 'coordinated_damage', effect_duration, damage_boost)
                     self.combat_system.apply_status_effect(member_id, 'coordinated_accuracy', effect_duration, accuracy_boost)
                     logger.debug(f"Applied coordinated attack buff to {member_id}")
                     participants += 1
                except AttributeError:
                     logger.error("CombatSystem missing apply_status_effect method.")
                     return False # Cannot apply effect
                except Exception as e:
                     logger.error(f"Error applying status effect to {member_id}: {e}")

        if participants > 0:
            logger.info(f"Coordinated attack involved {participants} members of team {team_id}.")
            # Optionally emit an event for coordination success
            system_manager.emit_event(SystemEventType.AGENT_ACTION, {
                 'agent_id': initiator_id, # The agent who triggered the ability
                 'action': 'team_coordinated_attack',
                 'team_id': team_id,
                 'participants': participants,
                 'target_position': target_position
            })
            return True
        else:
            logger.warning(f"Team {team_id} coordinated attack failed: no members in range.")
            return False
        
    def _execute_defensive_formation(self, team_id, initiator_id):
        """Execute a defensive formation team ability by applying a defensive buff.

           Assumes CombatSystem has apply_status_effect(agent_id, effect_type, duration, strength).
           Assumes TeamSystem has get_team_members(team_id) -> List[str].
        """
        logger.info(f"Team {team_id} entering defensive formation initiated by {initiator_id}")

        effect_duration = 10.0 # Seconds
        defense_multiplier = 0.7 # Represents 30% damage reduction

        team_members = self.team_system.teams.get(team_id, {}).get("members", [])
        if not team_members:
            return False

        participants = 0
        for member_id_data in team_members:
            member_id = member_id_data if isinstance(member_id_data, str) else member_id_data.get('agent_id')
            if not member_id:
                continue
            
            try:
                self.combat_system.apply_status_effect(member_id, 'defensive_stance', effect_duration, defense_multiplier)
                logger.debug(f"Applied defensive stance buff to {member_id}")
                participants += 1
            except AttributeError:
                logger.error("CombatSystem missing apply_status_effect method.")
                return False
            except Exception as e:
                logger.error(f"Error applying defensive stance to {member_id}: {e}")

        if participants > 0:
            logger.info(f"Defensive formation applied to {participants} members of team {team_id}.")
            system_manager.emit_event(SystemEventType.AGENT_ACTION, {
                 'agent_id': initiator_id,
                 'action': 'team_defensive_formation',
                 'team_id': team_id,
                 'participants': participants
            })
            return True
        else:
            logger.warning(f"Team {team_id} defensive formation failed: no members found?") # Should not happen if team exists
            return False
        
    def _execute_flanking_maneuver(self, team_id, initiator_id, target_position):
        """Execute a flanking maneuver by selecting flankers and assigning target positions.

           Assumes Environment has get_nearby_agents(position, radius).
           Assumes TeamSystem provides roles.
           Assumes AgentSystem provides positions.
           Emits an event for agents to handle movement.
        """
        logger.info(f"Team {team_id} executing flanking maneuver near {target_position} initiated by {initiator_id}")

        # --- Parameters ---
        flank_radius = 50.0 # How far from the target the flanking positions should be
        num_flankers = 2 # How many agents attempt to flank
        max_dist_to_target = 200 # Max distance a flanker can be from the target initially
        effect_duration = 8.0 # Duration for a potential flanking bonus effect
        flanking_bonus_strength = 1.25 # Example: 25% bonus damage
        target_search_radius = flank_radius * 0.5 # Radius to search for the target

        # --- 1. Identify Target --- 
        target_id = None
        actual_target_pos = None
        if hasattr(self.agent_system, 'env') and hasattr(self.agent_system.env, 'get_nearby_agents'):
            # Use the existing get_nearby_agents method
            nearby_agents = self.agent_system.env.get_nearby_agents(
                target_position, radius=target_search_radius
            )
            
            min_dist_sq = float('inf')
            agent_team_id = self.team_system.get_team_id_for_agent(initiator_id) # Get initiator's team ID
            
            for agent_obj in nearby_agents:
                 entity_id = getattr(agent_obj, 'name', None)
                 if not entity_id: continue

                 entity_team_id = self.team_system.get_team_id_for_agent(entity_id)
                 # Check if the agent is hostile (not on the same team)
                 if agent_team_id is None or entity_team_id != agent_team_id:
                      entity_pos = getattr(agent_obj, 'position', None)
                      if not entity_pos:
                           # Try getting position from AgentSystem as fallback
                           entity_pos = self.agent_system.agent_positions.get(entity_id)
                      
                      if entity_pos:
                           dist_sq = (entity_pos[0] - target_position[0])**2 + (entity_pos[1] - target_position[1])**2
                           if dist_sq < min_dist_sq:
                                min_dist_sq = dist_sq
                                target_id = entity_id
                                actual_target_pos = entity_pos # Use the actual agent position
        else:
            logger.warning("Cannot find target for flanking: Environment or get_nearby_agents method not available.")
            return False

        if not target_id or not actual_target_pos:
             logger.warning(f"Flanking maneuver failed for team {team_id}: No suitable target found near {target_position}.")
             return False
        
        # Update target_position to actual target position
        target_position = actual_target_pos

        logger.info(f"Flanking maneuver targeting {target_id} at {target_position}")

        # --- 2. Select Flankers --- 
        team_members = self.team_system.teams.get(team_id, {}).get("members", [])
        team_roles = self.team_system.teams.get(team_id, {}).get("roles", {})
        potential_flankers = []

        for member_id_data in team_members:
            member_id = member_id_data if isinstance(member_id_data, str) else member_id_data.get('agent_id')
            if not member_id or member_id == initiator_id:
                 continue

            role = team_roles.get(member_id)
            if role and ('flanker' in role or 'attacker' in role):
                 member_pos = self.agent_system.agent_positions.get(member_id)
                 if member_pos:
                      dist_sq = (member_pos[0] - target_position[0])**2 + (member_pos[1] - target_position[1])**2
                      if dist_sq <= max_dist_to_target**2:
                           potential_flankers.append((dist_sq, member_id))
        potential_flankers.sort()
        selected_flankers = [fid for dist_sq, fid in potential_flankers[:num_flankers]]

        if not selected_flankers:
             logger.warning(f"Flanking maneuver failed for team {team_id}: No suitable flankers found.")
             return False

        # --- 3. Calculate Flanking Positions ---
        initiator_pos = self.agent_system.agent_positions.get(initiator_id, target_position)
        vec_x = target_position[0] - initiator_pos[0]
        vec_y = target_position[1] - initiator_pos[1]
        dist = math.sqrt(vec_x**2 + vec_y**2)
        if dist < 1e-6: vec_x, vec_y = 1.0, 0.0
        else: vec_x /= dist; vec_y /= dist
        left_perp_x, left_perp_y = -vec_y, vec_x
        right_perp_x, right_perp_y = vec_y, -vec_x
        flank_positions = {}
        if len(selected_flankers) >= 1:
            flank_pos_left = (target_position[0] + left_perp_x * flank_radius, target_position[1] + left_perp_y * flank_radius)
            flank_positions[selected_flankers[0]] = flank_pos_left
        if len(selected_flankers) >= 2:
            flank_pos_right = (target_position[0] + right_perp_x * flank_radius, target_position[1] + right_perp_y * flank_radius)
            flank_positions[selected_flankers[1]] = flank_pos_right

        # --- 4. Emit Event to Command Movement --- 
        system_manager.emit_event(SystemEventType.AGENT_ACTION, {
             'agent_id': initiator_id,
             'action': 'team_flanking_maneuver_start',
             'team_id': team_id,
             'target_id': target_id,
             'target_position': target_position,
             'flankers': flank_positions # Dict mapping flanker_id -> target_pos
        })

        logger.info(f"Flanking maneuver initiated for team {team_id} targeting {target_id} with flankers: {list(flank_positions.keys())}")
        return True
        
    def get_team_combat_stats(self, team_id=None):
        """Get combat statistics for a team or all teams"""
        if not self.team_system: return {} # Check dependency
        if team_id:
            if team_id not in self.team_damage:
                return {}
                
            return {
                "damage_dealt": self.team_damage[team_id],
                "kills": self.team_kills[team_id],
                "abilities_used": self.team_abilities_used.get(team_id, {}),
                "members": self._get_team_member_stats(team_id)
            }
        else:
            # Return stats for all teams
            all_stats = {}
            for tid in self.team_damage:
                all_stats[tid] = self.get_team_combat_stats(tid)
            return all_stats
            
    def _get_team_member_stats(self, team_id):
        """Get combat stats for all members of a team"""
        if not self.team_system or not self.combat_system: return [] # Check dependencies
        team = self.team_system.teams.get(team_id, {})
        member_stats = []
        
        for member in team.get("members", []):
            agent_id = member["agent_id"]
            # Get combat stats for this agent
            combat_stats = self.combat_system.get_combat_stats(agent_id)
            
            # Add role information
            combat_stats["role"] = member.get("role", "member")
            
            member_stats.append({
                "agent_id": agent_id,
                "stats": combat_stats
            })
            
        return member_stats
        
    def calculate_team_effectiveness(self, team_id):
        """Calculate overall combat effectiveness for a team"""
        if not self.team_system or not self.combat_system: return 0.0 # Check dependencies
        team = self.team_system.teams.get(team_id, {})
        if not team:
            return 0.0
            
        # Get formation score
        formation_score = self.team_system.get_formation_score(team_id)
        
        # Calculate average member effectiveness
        members = team.get("members", [])
        if not members:
            return 0.0
            
        total_effectiveness = 0.0
        for member in members:
            agent_id = member["agent_id"]
            effectiveness = self.combat_system.get_agent_effectiveness(agent_id)
            total_effectiveness += effectiveness
            
        avg_effectiveness = total_effectiveness / len(members)
        
        # Calculate overall team effectiveness
        team_kills = self.team_kills.get(team_id, 0)
        team_damage = self.team_damage.get(team_id, 0)
        
        team_effectiveness = (
            avg_effectiveness * 0.4 +  # 40% from individual effectiveness
            formation_score * 0.3 +    # 30% from formation maintenance
            min(1.0, team_kills / 5) * 0.2 +  # 20% from kills (max 5)
            min(1.0, team_damage / 500) * 0.1  # 10% from damage (max 500)
        )
        
        return team_effectiveness 