import random
import math
import logging
import time
import uuid
from typing import Dict, List, Tuple, Optional, Any, TYPE_CHECKING
from config.unified_config import config
from systems.core.system_manager import SystemManager, SystemEventType, system_manager
# Import system classes directly for type hints if needed
from systems.agents.personality_system import PersonalitySystem
from systems.environment.hazard_cover_system import HazardCoverSystem
from systems.agents.team_system import TeamSystem
from systems.core.base_system import BaseSystem # ADDED IMPORT
from systems.core.event_system import EventType # REMOVED Event import
from systems.utils.object_pool import ObjectPool
from systems.utils.logging import logger
from game_objects.bullet import Bullet # Corrected path
from systems.agents.base_agent import BaseAgent  # Assuming BaseAgent is in systems.agents <-- Path confirmed correct
# from systems.entities.obstacle import Obstacle # Assuming Obstacle is in systems.entities <-- Path incorrect, Obstacle class not found, commenting out
# from systems.actions.action_map import ACTION_FIRE <-- Module/Constant not found, commenting out
from systems.constants import ACTION_SHOOT # <-- ADDED IMPORT
from enum import Enum
from systems.core.performance_monitor import SystemMonitor # Corrected class name
from systems.constants import (
    ACTION_IDLE,
    ACTION_MOVE_FORWARD,
)
import numpy as np

logger = logging.getLogger(__name__)

class StatusEffect:
    def __init__(self, type_name, duration, strength):
        self.type = type_name
        self.duration = duration
        self.strength = strength
        self.effects = {
            'slow': lambda x: x * 0.5,
            'poison': lambda x: x - 1,
            'boost': lambda x: x * 1.5,
            'shield': lambda x: x + 20
        }
        
    def apply_effect(self, value, effect_type=None):
        """Apply the status effect to a given value"""
        effect_type = effect_type or self.type
        if effect_type in self.effects:
            return self.effects[effect_type](value)
        return value

class CombatSystem(BaseSystem): # MODIFIED: Inherit from BaseSystem
    """
    Manages combat interactions between agents, integrating hazards, cover,
    and personality effects.
    """
    
    def __init__(self):
        """Initialize CombatSystem. Dependencies are fetched lazily."""
        super().__init__(name="CombatSystem", priority=70) # ADDED: Call parent init
        # Dependency placeholders
        self._personality_system_instance: Optional[PersonalitySystem] = None
        self._hazard_cover_system_instance: Optional[HazardCoverSystem] = None
        self._team_system_instance: Optional[TeamSystem] = None
        self._team_combat_integration_instance: Optional["TeamCombatIntegration"] = None
        self._env_instance: Optional["BattleRoyaleEnv"] = None # ADDED env placeholder
        # --- ADDED: Placeholders for lazy loading ---
        self._agent_system_instance: Optional["AgentSystem"] = None
        self._morale_suppression_system_instance: Optional["MoraleSuppressionSystem"] = None
        # --------------------------------------------

        # Track combat stats
        self.damage_dealt = {}
        self.critical_hits = {}
        self.hits = {}
        self.misses = {}
        self.kills = {}
        
        # Combat modifiers
        # Get base values from config
        self.base_accuracy = config.get("combat", "BASE_ACCURACY", 0.8)
        self.base_damage = config.get("combat", "BASE_DAMAGE", 10)
        self.critical_chance = config.get("combat", "CRITICAL_CHANCE", 0.1)
        self.critical_multiplier = config.get("combat", "CRITICAL_MULTIPLIER", 2.0)
        
        # Status effect tracking
        self.active_status_effects = {}  # {agent_id: [StatusEffect1, StatusEffect2, ...]}
        
        # Combat events for analysis
        self.combat_events = []
        
        # Bullet Pool - Initialize after dependencies are available (in initialize method)
        self.bullet_pool = None

        # --- Event Subscription moved to initialize ---

        self.logger = logger # <<< ADDED: Initialize instance logger
        self.logger.info("Combat System instance created (Dependencies and subscriptions will be set up in initialize)")
        
    # --- Lazy Loading Properties ---
    @property
    def env(self) -> Optional["BattleRoyaleEnv"]:
        if self._env_instance is None:
            self._env_instance = system_manager.get_system("battle_royale_env")
            if not self._env_instance:
                 logger.error("CombatSystem: Failed to get BattleRoyaleEnv instance!")
        return self._env_instance

    @property
    def personality_system(self) -> Optional[PersonalitySystem]:
        if self._personality_system_instance is None:
            self._personality_system_instance = system_manager.get_system("PersonalitySystem")
        return self._personality_system_instance

    @property
    def hazard_cover_system(self) -> Optional[HazardCoverSystem]:
        if self._hazard_cover_system_instance is None:
            self._hazard_cover_system_instance = system_manager.get_system("HazardCoverSystem")
            if not self._hazard_cover_system_instance:
                 logger.warning("CombatSystem: HazardCoverSystem not found.")
        return self._hazard_cover_system_instance

    @property
    def team_system(self) -> Optional[TeamSystem]:
        if self._team_system_instance is None:
            self._team_system_instance = system_manager.get_system("TeamSystem")
            # Warning might be okay if teams are optional
        return self._team_system_instance

    @property
    def team_combat_integration(self) -> Optional["TeamCombatIntegration"]:
        if self._team_combat_integration_instance is None:
            self._team_combat_integration_instance = system_manager.get_system("TeamCombatIntegration")
            if not self._team_combat_integration_instance:
                 logger.info("CombatSystem: TeamCombatIntegration not found.") # Info level okay
        return self._team_combat_integration_instance

    # --- ADDED: Lazy Loader for AgentSystem ---
    @property
    def agent_system(self) -> Optional["AgentSystem"]:
        # Import locally if needed for type hint, or rely on TYPE_CHECKING
        if not hasattr(self, '_agent_system_instance') or self._agent_system_instance is None:
            # Use the correct name AgentSystem is registered with
            self._agent_system_instance = system_manager.get_system("agent_system") 
            if not self._agent_system_instance:
                 logger.error("CombatSystem: Failed to get AgentSystem instance!")
        return self._agent_system_instance
    # --------------------------------------------

    # --- ADDED: Lazy Loader for MoraleSuppressionSystem ---
    @property
    def morale_suppression_system(self) -> Optional["MoraleSuppressionSystem"]:
        # We need to import it here to avoid circular dependency at module level
        # This assumes the file exists at systems/morale/morale_suppression_system.py
        if not hasattr(self, '_morale_suppression_system_instance') or self._morale_suppression_system_instance is None:
            try:
                from systems.morale.morale_suppression_system import MoraleSuppressionSystem
                self._morale_suppression_system_instance = system_manager.get_system("morale_suppression_system")
                if not self._morale_suppression_system_instance:
                    logger.warning("CombatSystem: MoraleSuppressionSystem not found via system_manager.")
            except ImportError:
                logger.warning("MoraleSuppressionSystem not found/importable.")
                self._morale_suppression_system_instance = None
        return self._morale_suppression_system_instance
    # --------------------------------------------------------

    # --- End Lazy Loading Properties ---

    def register_agent(self, agent_id):
        """Register a new agent with the combat system"""
        if agent_id not in self.damage_dealt:
            self.damage_dealt[agent_id] = 0
            self.critical_hits[agent_id] = 0
            self.hits[agent_id] = 0
            self.misses[agent_id] = 0
            self.kills[agent_id] = 0
            self.active_status_effects[agent_id] = []
        
    def calculate_final_damage(self,
            attacker_id: str,
            target_id: str,
            attacker_pos: Tuple[float, float],
            target_pos: Tuple[float, float],
            base_damage: float,
            weapon_type: str = "standard",
            environment_context: Optional[Dict[str, Any]] = None,
            context: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculates the final damage after considering all modifiers in a specific order.
        This method assumes the hit has already been confirmed.

        Args:
            attacker_id: ID of the attacking agent
            target_id: ID of the target agent
            attacker_pos: (x, y) position of attacker
            target_pos: (x, y) position of target
            base_damage: The initial damage value (e.g., from the bullet)
            weapon_type: Type of weapon used
            environment_context: Context about the environment (weather, zone)
            context: Additional context about the combat situation (unused currently)

        Returns:
            The final calculated damage value (float).
        """
        # 0. Initialization
        self.register_agent(attacker_id) # Ensure agents are registered for stat tracking
        self.register_agent(target_id)
        ax, ay = attacker_pos
        tx, ty = target_pos
        current_damage = base_damage
        critical_hit = False
        in_cover = False
        log_info = {} # For collecting info for the event log
        log_info['base_damage'] = base_damage

        # --- ADDED: Get Morale/Suppression Values Early --- #
        attacker_morale = 0.5 # Default
        target_morale = 0.5 # Default
        target_suppression = 0.0 # Default
        if self.morale_suppression_system:
            attacker_morale = self.morale_suppression_system.get_morale(attacker_id)
            target_morale = self.morale_suppression_system.get_morale(target_id)
            target_suppression = self.morale_suppression_system.get_suppression(target_id)
            log_info['attacker_morale'] = attacker_morale
            log_info['target_morale'] = target_morale
            log_info['target_suppression'] = target_suppression
        # -------------------------------------------------- #

        # 1. Base Damage (already provided as input)

        # 2. Weapon Type Modifiers
        combat_config = config.combat # Get the combat section dict
        weapons_config = combat_config.get("WEAPONS", {}) # Get WEAPONS dict safely
        weapon_data = weapons_config.get(weapon_type, {}) # Get specific weapon data safely

        weapon_damage_multiplier = 1.0
        weapon_crit_chance_mod = 1.0
        weapon_crit_multiplier_mod = 1.0

        # Check if data was actually found
        if not weapon_data: 
            logger.warning(f"Weapon type '{weapon_type}' not found in config. Using default modifiers.")
        else:
            # Use .get() for safe access within weapon_data
            weapon_damage_multiplier = weapon_data.get("damage_multiplier", 1.0)
            weapon_crit_chance_mod = weapon_data.get("crit_chance_mod", 1.0)
            weapon_crit_multiplier_mod = weapon_data.get("crit_multiplier_mod", 1.0)

        current_damage *= weapon_damage_multiplier
        log_info['weapon_multiplier'] = weapon_damage_multiplier

        # 3. Critical Hit Calculation
        base_crit_chance = config.get("combat", "CRITICAL_CHANCE", 0.1)
        final_crit_chance = base_crit_chance * weapon_crit_chance_mod

        # --- Personality Influence on Critical Chance ---
        if self.personality_system:
            aggression = self.personality_system.get_effect_value(attacker_id, "critical_chance_bonus")
            final_crit_chance *= (1.0 + aggression)
            log_info['personality_crit_chance_mod'] = (1.0 + aggression)
        # --- End Personality Influence ---

        # --- Team Bonus Influence on Critical Chance (Part of Attack Bonus) ---
        team_attack_bonuses = {"critical": 1.0} # Default
        if self.team_combat_integration:
             try:
                  team_attack_bonuses = self.team_combat_integration.calculate_team_attack_bonus(
                       attacker_id, target_id, attacker_pos, target_pos
                  )
                  final_crit_chance *= team_attack_bonuses.get("critical", 1.0)
                  log_info['team_crit_chance_mod'] = team_attack_bonuses.get("critical", 1.0)
             except Exception as e:
                  logger.error(f"Error getting team attack bonus for crit chance: {e}")
        # --- End Team Bonus Influence ---

        # --- ADDED: Attacker Morale Influence on Crit Chance? (Optional) --- #
        # Example: Higher morale slightly increases crit chance
        morale_crit_mod = 1.0 + (max(0, attacker_morale - 0.5) * 0.1) # Up to +10% crit chance at max morale
        final_crit_chance *= morale_crit_mod
        log_info['morale_crit_chance_mod'] = morale_crit_mod
        # -------------------------------------------------------------- #

        if random.random() < final_crit_chance:
            critical_hit = True
            base_crit_multiplier = config.get("combat", "CRITICAL_MULTIPLIER", 2.0)
            final_crit_multiplier = base_crit_multiplier * weapon_crit_multiplier_mod
            current_damage *= final_crit_multiplier
            self.critical_hits[attacker_id] = self.critical_hits.get(attacker_id, 0) + 1
            log_info['critical_hit'] = True
            log_info['critical_multiplier'] = final_crit_multiplier
        else:
             log_info['critical_hit'] = False

        # 4. Attacker Status Effects (e.g., damage boost)
        attacker_effects_mod = 1.0
        if attacker_id in self.active_status_effects:
            for effect in self.active_status_effects[attacker_id]:
                if effect.type == 'damage_boost' or effect.type == 'coordinated_damage':
                    attacker_effects_mod *= effect.strength # Strength is the multiplier
                # Add other relevant attacker effects
        current_damage *= attacker_effects_mod
        log_info['attacker_status_mod'] = attacker_effects_mod

        # --- ADDED: Attacker Morale Influence on Damage --- #
        # Example: Morale influences damage output (e.g., +/- 20%)
        morale_damage_mod = 1.0 + ((attacker_morale - 0.5) * 0.4) # Range 0.8 to 1.2 based on 0-1 morale
        current_damage *= morale_damage_mod
        log_info['morale_damage_mod'] = morale_damage_mod
        # ------------------------------------------------ #

        # 5. Team Attack Bonus (Damage Multiplier part)
        if self.team_combat_integration:
             team_damage_mod = team_attack_bonuses.get("damage", 1.0)
             current_damage *= team_damage_mod
             log_info['team_attack_damage_mod'] = team_damage_mod

        # 6. Personality Damage Modifiers (Attacker)
        if self.personality_system:
            aggression_mod = self.personality_system.get_effect_value(attacker_id, "damage_bonus")
            current_damage *= (1.0 + aggression_mod)
            log_info['personality_attack_damage_mod'] = (1.0 + aggression_mod)

        # --- DEFENSIVE MODIFIERS START HERE ---

        # 7. Cover Modifier
        cover_modifier = 1.0
        if self.hazard_cover_system:
            # Check LoS and cover protection
            has_los, protection = self.hazard_cover_system.check_line_of_sight(ax, ay, tx, ty)
            if not has_los:
                # Attack might be completely blocked depending on game rules
                # For now, assume it reduces damage significantly
                protection = max(protection, 0.8) # At least 80% reduction if LoS blocked

            if protection > 0:
                 in_cover = True
                 cover_modifier = (1.0 - protection) # Protection 0.6 -> modifier 0.4
                 log_info['cover_modifier'] = cover_modifier
                 log_info['in_cover'] = True
        current_damage *= cover_modifier

        # --- ADDED: Target Suppression Damage Reduction --- #
        # Example: Suppression slightly reduces incoming damage (e.g., max 15% reduction)
        suppression_reduction_factor = self.morale_suppression_system._config.get("SUPPRESSION_DAMAGE_REDUCTION_MAX", 0.15) if self.morale_suppression_system else 0.15
        suppression_reduction = 1.0 - (target_suppression * suppression_reduction_factor)
        current_damage *= suppression_reduction
        log_info['suppression_damage_reduction'] = suppression_reduction
        # -------------------------------------------------- #

        # 8. Team Defense Bonus (includes formation and threat)
        defense_bonus_multiplier = 1.0
        if self.team_combat_integration:
             try:
                  defense_bonus_multiplier = self.team_combat_integration.calculate_defense_bonus(
                       defender_id=target_id, attacker_id=attacker_id
                  )
                  log_info['team_defense_mod'] = defense_bonus_multiplier
             except Exception as e:
                  logger.error(f"Error getting team defense bonus: {e}")
        current_damage *= defense_bonus_multiplier

        # 9. Target Status Effects (e.g., defense boost, vulnerability)
        target_effects_mod = 1.0
        if target_id in self.active_status_effects:
            for effect in self.active_status_effects[target_id]:
                if effect.type == 'defense_boost' or effect.type == 'defensive_stance':
                    target_effects_mod *= effect.strength # Strength is the reduction multiplier
                elif effect.type == 'vulnerability':
                     target_effects_mod /= effect.strength # Strength makes damage higher
                # Add other relevant target effects
        current_damage *= target_effects_mod
        log_info['target_status_mod'] = target_effects_mod

        # --- ADDED: Target Morale Damage Resistance --- #
        # Example: Higher morale increases resistance (+/- 15% damage taken)
        morale_resistance_mod = 1.0 - ((target_morale - 0.5) * 0.3) # Range 1.15 to 0.85 based on 0-1 morale
        current_damage *= morale_resistance_mod
        log_info['morale_damage_resistance'] = morale_resistance_mod
        # ---------------------------------------------- #

        # 10. Personality Defense Modifiers (Target)
        if self.personality_system:
            defense_mod = self.personality_system.get_effect_value(target_id, "damage_reduction")
            current_damage *= (1.0 - defense_mod) # Reduction modifier
            log_info['personality_defense_mod'] = (1.0 - defense_mod)

        # 11. Environmental Effects (e.g., weather, zone)
        env_mod = 1.0
        if environment_context:
             if environment_context.get('weather') == 'storm':
                  env_mod *= 1.1 # Storms might increase damage?
             if environment_context.get('in_damage_zone', False):
                  env_mod *= 1.2 # Damage zone increases incoming damage
        current_damage *= env_mod
        log_info['environment_mod'] = env_mod

        # 12. Final Damage Calculation
        final_damage = max(0.0, current_damage) # Damage cannot be negative
        log_info['final_damage'] = final_damage

        # --- Record Stats & Events ---
        self.hits[attacker_id] = self.hits.get(attacker_id, 0) + 1
        self.damage_dealt[attacker_id] = self.damage_dealt.get(attacker_id, 0) + final_damage

        # Emit detailed damage event
        system_manager.emit_event(SystemEventType.AGENT_DAMAGED, {
            'attacker_id': attacker_id,
            'target_id': target_id,
            'damage': final_damage,
            'weapon_type': weapon_type,
            'details': log_info # Include calculation breakdown
        })

        return final_damage
    
    def apply_status_effect(self, agent_id, effect_type, duration, strength):
        """Apply a status effect to an agent"""
        if agent_id not in self.active_status_effects:
            self.active_status_effects[agent_id] = []
            
        # Add the new effect
        effect = StatusEffect(effect_type, duration, strength)
        self.active_status_effects[agent_id].append(effect)
        
        logger.debug(f"Applied {effect_type} status effect to agent {agent_id} for {duration}s")
        return effect
        
    def update_status_effects(self, delta_time):
        """Update all active status effects"""
        for agent_id, effects in self.active_status_effects.items():
            # Reduce duration and remove expired effects
            updated_effects = []
            for effect in effects:
                effect.duration -= delta_time
                if effect.duration > 0:
                    updated_effects.append(effect)
            self.active_status_effects[agent_id] = updated_effects
    
    def _get_status_effect(self, weapon_type, critical):
        """Determine if an attack should apply a status effect based on config"""
        # Fetch weapon data from config
        weapon_data = config.get("combat", f"WEAPONS.{weapon_type}", default={})
        
        # Check if weapon directly applies a status effect
        if "applies_status" in weapon_data and isinstance(weapon_data["applies_status"], dict):
            return weapon_data["applies_status"]
        
        # Check for critical hit status effect chance (generic)
        if critical:
             crit_status_chance = config.get("combat", "CRITICAL_STATUS_CHANCE", 0.3) # Default 30% from config
             if random.random() < crit_status_chance:
                 # Get possible effects from config or default
                 possible_effects = config.get("combat", "CRITICAL_STATUS_EFFECTS", [
                     {"type": "burn", "duration": 2.0, "strength": 0.8},
                     {"type": "slow", "duration": 2.0, "strength": 0.5},
                     {"type": "disable", "duration": 1.0, "strength": 1.0}
                 ])
                 if possible_effects: # Ensure list is not empty
                      return random.choice(possible_effects)
                      
        return None
        
    def get_combat_stats(self, agent_id=None):
        """Get combat statistics for an agent or all agents"""
        if agent_id:
            if agent_id not in self.damage_dealt:
                return {}
                
            accuracy = 0
            total_shots = self.hits[agent_id] + self.misses[agent_id]
            if total_shots > 0:
                accuracy = self.hits[agent_id] / total_shots
                
            return {
                "damage_dealt": self.damage_dealt[agent_id],
                "critical_hits": self.critical_hits[agent_id],
                "hits": self.hits[agent_id],
                "misses": self.misses[agent_id],
                "kills": self.kills[agent_id],
                "accuracy": accuracy
            }
        else:
            # Return stats for all agents
            all_stats = {}
            for aid in self.damage_dealt:
                all_stats[aid] = self.get_combat_stats(aid)
            return all_stats
            
    def record_kill(self, killer_id, victim_id):
        """Record a kill"""
        if killer_id in self.kills:
            self.kills[killer_id] += 1
            
        # Record combat event
        self.combat_events.append({
            "type": "kill",
            "killer": killer_id,
            "victim": victim_id,
            "timestamp": time.time()
        })
        
    def reset_stats(self):
        """Reset all combat statistics"""
        for agent_id in self.damage_dealt:
            self.damage_dealt[agent_id] = 0
            self.critical_hits[agent_id] = 0
            self.hits[agent_id] = 0
            self.misses[agent_id] = 0
            self.kills[agent_id] = 0
            
        self.combat_events = []
        
    def get_agent_effectiveness(self, agent_id):
        """Calculate an agent's combat effectiveness score"""
        if agent_id not in self.damage_dealt:
            return 0.0
            
        # Basic effectiveness calculation
        stats = self.get_combat_stats(agent_id)
        
        # Avoid division by zero
        shots = stats["hits"] + stats["misses"]
        accuracy = stats["hits"] / max(1, shots)
        
        # Effectiveness formula
        effectiveness = (
            stats["damage_dealt"] * 0.5 +
            stats["kills"] * 100 +
            accuracy * 50 +
            stats["critical_hits"] * 10
        ) / max(1, shots)
        
        return effectiveness

    # --- ADDED: Event Handler for Collisions from CollisionSystem --- 
    def _handle_entity_collision(self, event_data: Dict[str, Any]) -> None:
        """Handles collision events, specifically bullet-agent collisions for damage."""
        e1_id = event_data.get('entity1_id')
        e2_id = event_data.get('entity2_id')
        e1_type = event_data.get('entity1_type')
        e2_type = event_data.get('entity2_type')
        
        # Identify bullet and agent
        bullet_data = None
        agent_data = None
        bullet_id = None
        agent_id = None
        
        if e1_type == 'bullet' and e2_type == 'agent':
            bullet_data = event_data.get('entity1_data')
            agent_data = event_data.get('entity2_data')
            bullet_id = e1_id
            agent_id = e2_id
        elif e1_type == 'agent' and e2_type == 'bullet':
            bullet_data = event_data.get('entity2_data')
            agent_data = event_data.get('entity1_data')
            bullet_id = e2_id
            agent_id = e1_id
            
        if not bullet_data or not agent_data:
            # Not a bullet-agent collision we need to handle here
            return 

        logger.debug(f"CombatSystem handling collision between bullet {bullet_id} and agent {agent_id}")

        # --- Damage Calculation Logic --- 
        attacker_id = bullet_data.get('owner_id')
        if not attacker_id:
            logger.warning(f"Bullet {bullet_id} involved in collision has no owner_id.")
            return
            
        # Verify attacker and target still exist (using EntityManager)
        if not self.entity_manager:
             logger.error("CombatSystem: EntityManager not available!")
             return
        attacker_data = self.entity_manager.get_entity(attacker_id)
        # Agent data is already passed in event_data, but let's re-get for consistency/freshness
        target_data = self.entity_manager.get_entity(agent_id) 

        if not attacker_data or not target_data:
             logger.warning(f"CombatSystem: Attacker {attacker_id} or Target {agent_id} not found in EntityManager during collision handling.")
             return

        attacker_pos = attacker_data.get('position') # Attacker's current position (or bullet start pos?)
        target_pos = target_data.get('position')
        base_damage = bullet_data.get('damage', 10)
        weapon_type = bullet_data.get('weapon_type', 'standard') # Assuming weapon_type is stored on bullet
        
        if not attacker_pos or not target_pos:
            logger.warning(f"Missing position data for attacker {attacker_id} or target {agent_id}.")
            return

        # Prepare context for damage calculation
        # TODO: Fetch relevant environmental context if needed (e.g., from Env system)
        environment_context = {}

        final_damage = self.calculate_final_damage(
            attacker_id=attacker_id,
            target_id=agent_id,
            attacker_pos=attacker_pos, # Use attacker's current pos? or bullet start pos?
            target_pos=target_pos,
            base_damage=base_damage,
            weapon_type=weapon_type,
            environment_context=environment_context,
            context=None # Any specific combat context?
        )

        if final_damage > 0:
            logger.info(f"Damage calculated via event: {final_damage:.2f} from {attacker_id} to {agent_id}")
            damage_event_data = {
                'target_id': agent_id,
                'attacker_id': attacker_id,
                'damage': final_damage,
                'weapon_type': weapon_type,
                'position': target_pos,
                'critical': False # TODO: Crit check should happen in calculate_final_damage?
            }
            # Emit AGENT_DAMAGED event - AgentSystem or HealthComponent listens for this
            self.emit_event(SystemEventType.AGENT_DAMAGED, damage_event_data)
            
            # --- ADDED: Emit event to destroy the bullet --- 
            self.emit_event(SystemEventType.ENTITY_DESTROYED, {
                'entity_id': bullet_id,
                'entity_type': 'bullet',
                'reason': 'hit_target'
            })
            # --------------------------------------------------

            # Update combat stats for attacker
            # If combat_stats dict is used, initialize it
            if not hasattr(self, 'combat_stats'): self.combat_stats = {}
            if attacker_id not in self.combat_stats: self.combat_stats[attacker_id] = {}
            if agent_id not in self.combat_stats: self.combat_stats[agent_id] = {}

            self.combat_stats[attacker_id]['damage_dealt'] = self.combat_stats[attacker_id].get('damage_dealt', 0) + final_damage
            self.combat_stats[attacker_id]['hits'] = self.combat_stats[attacker_id].get('hits', 0) + 1
            # Update stats for target
            self.combat_stats[agent_id]['damage_taken'] = self.combat_stats[agent_id].get('damage_taken', 0) + final_damage
        else:
             logger.debug(f"Collision between {bullet_id} and {agent_id} resulted in <= 0 damage after calculation.")
        
        # Note: Bullet destruction should be handled by EntityManager based on ENTITY_DESTROYED event
        # or CollisionSystem could emit a specific BULLET_HIT event that triggers destruction.
        # For now, assume bullet destruction is handled elsewhere or implicitly by this collision.

    # --- Weapon Stats --- 
    def get_weapon_stats(self, weapon_type: str) -> Optional[Dict[str, Any]]:
         """Returns the stats for a given weapon type."""
         return self.weapons.get(weapon_type)

    def shutdown(self):
        """Cleanup resources or save state."""
        logger.info("CombatSystem shutting down")
        # Unsubscribe from events?
        # self.unsubscribe_from_event(SystemEventType.ENTITY_COLLISION, self._handle_entity_collision)
        pass

    def initialize(self) -> None: # ADDED initialize method
        """Initialize the CombatSystem, subscribe to events, and set up bullet pool."""
        logger.info("Initializing CombatSystem...")
        # Subscribe to necessary events using the inherited method
        try:
            self.subscribe_to_event(SystemEventType.ENTITY_COLLISION, self._handle_entity_collision)
            logger.info("CombatSystem subscribed to ENTITY_COLLISION events.")
        except Exception as e:
             logger.error(f"Error subscribing CombatSystem to ENTITY_COLLISION: {e}")

        # Initialize Bullet Pool (assuming Bullet class is available)
        pool_size = config.get("combat", "BULLET_POOL_SIZE", 100)
        max_pool_size = config.get("combat", "MAX_BULLET_POOL_SIZE", 200)
        try:
            # --- Ensure ObjectPool is imported ---
            from systems.utils.object_pool import ObjectPool
            # --- Ensure Bullet is imported or defined ---
            from systems.environment.environment import Bullet

            self.bullet_pool = ObjectPool(Bullet, initial_size=pool_size, max_size=max_pool_size)
            logger.info(f"Bullet pool initialized with size {pool_size} (max {max_pool_size}).")
        except ImportError as e:
             logger.error(f"Failed to import required classes for bullet pool: {e}. Bullet pool not initialized.")
             self.bullet_pool = None
        except Exception as e:
            logger.error(f"Failed to initialize bullet pool: {e}", exc_info=True)
            self.bullet_pool = None
