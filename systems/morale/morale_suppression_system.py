import logging
import math
import random
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict

from systems.core.base_system import BaseSystem
from systems.core.system_manager import SystemEventType, system_manager
# Import necessary config later if needed
# from config.unified_config import config 
# Import other systems lazily for type hints if needed
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from systems.agents.personality_system import PersonalitySystem

logger = logging.getLogger(__name__)

class MoraleSuppressionSystem(BaseSystem):
    """
    Manages agent morale and suppression levels based on events, time, and personality.
    """
    def __init__(self):
        super().__init__(name="morale_suppression_system", priority=55) # Example priority

        # State storage
        self.agent_morale: Dict[str, float] = {}
        self.agent_suppression: Dict[str, float] = {}

        # Configuration Cache (To be loaded in _initialize)
        self._config: Dict[str, Any] = {}
        self._morale_min: float = 0.0
        self._morale_max: float = 1.0
        self._morale_passive_rate: float = 0.0
        self._suppression_max: float = 1.0
        self._suppression_decay_rate: float = 0.1
        self._morale_event_modifiers: Dict[str, float] = {}
        self._suppression_event_modifiers: Dict[str, float] = {}
        self._personality_influence: Dict[str, float] = {}

        # Lazy-loaded system references
        self._personality_system_instance: Optional["PersonalitySystem"] = None

        logger.info("MoraleSuppressionSystem object created (not initialized yet).")

    @property
    def personality_system(self) -> Optional["PersonalitySystem"]:
        if self._personality_system_instance is None:
            self._personality_system_instance = system_manager.get_system("PersonalitySystem")
        return self._personality_system_instance

    def _load_config(self) -> None:
        """Load relevant configuration values from global config or use defaults."""
        # Attempt to get config from system_manager first
        config_obj = system_manager.get_shared_state('config')
        cfg_section = {}
        if config_obj and hasattr(config_obj, 'get'):
             cfg_section = config_obj.get("morale_suppression", {})
             if not cfg_section:
                  logger.warning("Morale/Suppression config section missing. Using defaults.")
        else:
             logger.warning("Global config object not found in shared state. Using defaults.")

        # Load values with defaults
        self._morale_min = float(cfg_section.get("MORALE_MIN", 0.0))
        self._morale_max = float(cfg_section.get("MORALE_MAX", 1.0))
        self._morale_passive_rate = float(cfg_section.get("MORALE_PASSIVE_RATE", 0.0))
        self._suppression_max = float(cfg_section.get("SUPPRESSION_MAX", 1.0))
        self._suppression_decay_rate = float(cfg_section.get("SUPPRESSION_DECAY_RATE", 0.15))
        self._morale_event_modifiers = cfg_section.get("MORALE_EVENT_MODIFIERS", {
            "deal_damage_minor": 0.01, "deal_damage_major": 0.05, "take_damage_minor": -0.02,
            "take_damage_major": -0.08, "kill_enemy": 0.15, "ally_death": -0.20,
            "team_victory": 0.3, "team_defeat": -0.3, "receive_heal": 0.05,
            "objective_complete": 0.2, "objective_fail": -0.15
        })
        self._suppression_event_modifiers = cfg_section.get("SUPPRESSION_EVENT_MODIFIERS", {
             "near_miss_bullet": 0.1, "direct_hit_no_damage": 0.05,
             "nearby_explosion": 0.3
        })
        self._personality_influence = cfg_section.get("PERSONALITY_INFLUENCE_WEIGHTS", {
             "morale_gain": 0.6, "morale_loss": 0.7, "suppression_gain": 0.5, "suppression_decay": 0.4
        })
        self._config = cfg_section # Store for potential future use
        logger.info(f"Morale/Suppression config loaded: Morale [{self._morale_min}-{self._morale_max}], Suppression Decay {self._suppression_decay_rate}")

    def _initialize(self) -> None:
        """Load configuration and subscribe to events."""
        self._load_config()

        # Define expected event types (ensure these exist in SystemEventType)
        events_to_subscribe = [
            SystemEventType.ENTITY_CREATED,
            SystemEventType.ENTITY_DESTROYED,
            SystemEventType.AGENT_DAMAGED, # Specific damage event
            SystemEventType.ATTACK_MISS, # Assuming exists and provides proximity
            # Placeholders for team/objective events - replace with actual event types if they exist
            # SystemEventType.TEAM_VICTORY, SystemEventType.TEAM_DEFEAT,
            # SystemEventType.OBJECTIVE_COMPLETE, SystemEventType.OBJECTIVE_FAIL
            # SystemEventType.AGENT_HEALED # If healing events exist
            SystemEventType.NEAR_MISS_DETECTED, # Prefer a dedicated event if possible
            SystemEventType.EXPLOSION_NEAR_AGENT, # Prefer a dedicated event
            SystemEventType.TEAM_ACTION_SUCCESS, # Generic placeholder
            SystemEventType.TEAM_ACTION_FAILURE # Generic placeholder
        ]

        # Map event types to handler methods
        event_handler_map = {
            SystemEventType.ENTITY_CREATED: self._handle_entity_created,
            SystemEventType.ENTITY_DESTROYED: self._handle_entity_destroyed,
            SystemEventType.AGENT_DAMAGED: self._handle_agent_damaged,
            SystemEventType.ATTACK_MISS: self._handle_attack_miss,
            SystemEventType.NEAR_MISS_DETECTED: self._handle_attack_miss, # Use same handler for now
            SystemEventType.EXPLOSION_NEAR_AGENT: self._handle_explosion, # Need a handler
            SystemEventType.TEAM_ACTION_SUCCESS: self._handle_team_action,
            SystemEventType.TEAM_ACTION_FAILURE: self._handle_team_action,
        }

        # Subscribe to existing events
        subscribed_count = 0
        for event_type in events_to_subscribe:
            if hasattr(SystemEventType, event_type.name): # Check if event exists in Enum
                 handler = event_handler_map.get(event_type)
                 if handler:
                      system_manager.subscribe(event_type, handler)
                      subscribed_count += 1
                 else:
                      logger.warning(f"No handler defined for event type: {event_type.name}")
            else:
                 logger.warning(f"Event type {event_type.name} not found in SystemEventType Enum. Cannot subscribe.")

        logger.info(f"MoraleSuppressionSystem initialized. Subscribed to {subscribed_count} event types.")

    def _update(self, delta_time: float) -> None:
        """Apply passive decay/recovery."""
        # Implementation for M01.4
        agents_to_process = list(self.agent_suppression.keys()) # Iterate over copy of keys

        for agent_id in agents_to_process:
            # Check agent existence (optional, depends if removal is guaranteed by event)
            # Example check:
            # agent_exists = system_manager.get_shared_state(f"agent_{agent_id}_exists", True)
            # if not agent_exists:
            #     self._remove_agent(agent_id) # Clean up if agent disappeared unexpectedly
            #     continue

            # Apply Suppression Decay
            current_suppression = self.agent_suppression.get(agent_id, 0.0)
            if current_suppression > 0:
                decay_mod = 1.0
                # Fetch personality modifier for suppression decay
                if self.personality_system:
                    try:
                        # Example: Adaptability increases decay rate
                        # Need specific effect name defined in PersonalitySystem
                        adaptability_bonus = self.personality_system.get_effect_value(agent_id, "suppression_decay_bonus")
                        # Apply influence weight from config
                        influence = self._personality_influence.get("suppression_decay", 0.4)
                        decay_mod *= (1.0 + adaptability_bonus * influence)
                    except AttributeError:
                        logger.debug(f"PersonalitySystem missing get_effect_value for agent {agent_id}")
                    except Exception as e:
                        logger.warning(f"Error getting personality effect for {agent_id} suppression decay: {e}")

                decay_amount = self._suppression_decay_rate * decay_mod * delta_time
                new_suppression = max(0.0, current_suppression - decay_amount)
                if new_suppression != current_suppression:
                    self.agent_suppression[agent_id] = new_suppression
                    # Optionally emit event MORALE_SUPPRESSION_CHANGED

            # Apply Passive Morale Change (if configured)
            if self._morale_passive_rate != 0.0 and agent_id in self.agent_morale:
                current_morale = self.agent_morale[agent_id]
                change_mod = 1.0 # Personality could influence passive rate too
                # Example: Maybe Conscientiousness affects passive stability?

                change = self._morale_passive_rate * change_mod * delta_time
                new_morale = max(self._morale_min, min(self._morale_max, current_morale + change))
                if new_morale != current_morale:
                    self.agent_morale[agent_id] = new_morale
                    # Optionally emit event MORALE_SUPPRESSION_CHANGED

    def register_agent(self, agent_id: str) -> None:
        """Initialize morale and suppression for a newly registered agent."""
        # Implementation for M01.3
        if agent_id not in self.agent_morale:
            initial_morale = self._config.get("INITIAL_MORALE", (self._morale_min + self._morale_max) / 2)
            self.agent_morale[agent_id] = float(initial_morale)
            self.agent_suppression[agent_id] = 0.0
            logger.debug(f"Registered agent {agent_id} with initial morale {self.agent_morale[agent_id]:.3f}.")
        else:
            logger.warning(f"Agent {agent_id} already registered in MoraleSuppressionSystem.")

    def _remove_agent(self, agent_id: str) -> None:
        """Remove agent data when destroyed."""
        # Implementation for M01.3
        removed = False
        if agent_id in self.agent_morale:
             del self.agent_morale[agent_id]
             removed = True
        if agent_id in self.agent_suppression:
             del self.agent_suppression[agent_id]
             removed = True
        if removed:
             logger.debug(f"Removed morale/suppression data for agent {agent_id}.")

    def get_morale(self, agent_id: str) -> float:
        """Get current morale level for an agent."""
        # Placeholder implementation
        return self.agent_morale.get(agent_id, (self._morale_min + self._morale_max) / 2)

    def get_suppression(self, agent_id: str) -> float:
        """Get current suppression level for an agent."""
        # Placeholder implementation
        return self.agent_suppression.get(agent_id, 0.0)

    def apply_morale_change(self, agent_id: str, change: float, reason: str) -> None:
        """Directly apply a morale change (e.g., from ability or event)."""
        # Implementation for M01.5
        if agent_id not in self.agent_morale:
            self.register_agent(agent_id) # Ensure agent is registered
            # If register_agent failed or agent doesn't exist, morale won't be in dict
            if agent_id not in self.agent_morale:
                logger.warning(f"Cannot apply morale change to unregistered or invalid agent {agent_id}")
                return

        current_morale = self.agent_morale[agent_id]
        base_change = change

        # Apply personality modifiers
        if self.personality_system:
            # Determine effect name based on positive/negative change
            if change > 0:
                # effect_name = "agreeableness_morale_impact" # Incorrect based on test
                effect_name = "neuroticism_morale_impact" # Assuming Neuroticism affects gain sensitivity per PersonalitySystem
                weight_key = "morale_gain"
            else:
                effect_name = "neuroticism_morale_impact"
                weight_key = "morale_loss"
            
            # Fetch the effect value and weight
            effect_value = self.personality_system.get_effect_value(agent_id, effect_name)
            influence_weight = self._personality_influence.get(weight_key, 0.5)
            personality_mod = 1.0 + (effect_value * influence_weight)

        final_change = base_change * personality_mod
        new_morale = max(self._morale_min, min(self._morale_max, current_morale + final_change))

        if new_morale != current_morale:
            self.agent_morale[agent_id] = new_morale
            logger.debug(f"Morale change for {agent_id}: {final_change:.3f} ({reason}). New morale: {self.agent_morale[agent_id]:.3f}")
            # Optionally emit event MORALE_SUPPRESSION_CHANGED
        else:
            logger.debug(f"Morale change {final_change:.3f} ({reason}) for {agent_id} resulted in no state change (clamped). Current: {current_morale:.3f}")

    def apply_suppression_increase(self, agent_id: str, amount: float, reason: str) -> None:
        """Directly apply a suppression increase."""
        # Implementation for M01.5
        if agent_id not in self.agent_suppression:
            self.register_agent(agent_id) # Ensure agent is registered
            if agent_id not in self.agent_suppression:
                logger.warning(f"Cannot apply suppression increase to unregistered or invalid agent {agent_id}")
                return

        # Amount should always be positive for an increase
        base_increase = max(0.0, amount)
        if base_increase == 0: return # Nothing to apply

        current_suppression = self.agent_suppression[agent_id]

        # Apply personality modifiers
        influence_weight = self._personality_influence.get("suppression_gain", 0.5)
        personality_mod = 1.0
        if self.personality_system:
            try:
                # Example: Neuroticism increases suppression gain
                # Need specific effect name defined in PersonalitySystem
                neuroticism_effect = self.personality_system.get_effect_value(agent_id, "neuroticism_suppression_impact")
                personality_mod = 1.0 + (neuroticism_effect * influence_weight)
            except AttributeError:
                 logger.debug(f"PersonalitySystem missing get_effect_value for agent {agent_id} suppression gain")
            except Exception as e:
                 logger.warning(f"Error getting personality effect for {agent_id} suppression gain: {e}")

        final_increase = base_increase * personality_mod
        new_suppression = min(self._suppression_max, current_suppression + final_increase)

        if new_suppression != current_suppression:
            self.agent_suppression[agent_id] = new_suppression
            logger.debug(f"Suppression increase for {agent_id}: {final_increase:.3f} ({reason}). New suppression: {self.agent_suppression[agent_id]:.3f}")
            # Optionally emit event MORALE_SUPPRESSION_CHANGED
        else:
            logger.debug(f"Suppression increase {final_increase:.3f} ({reason}) for {agent_id} resulted in no state change (clamped). Current: {current_suppression:.3f}")

    # --- Event Handlers ---
    def _handle_entity_created(self, data: Dict) -> None:
        # Implementation for M01.6
        if data.get('entity_type') == 'agent' and 'agent_id' in data:
             # Call self.register_agent(data['agent_id']) when implemented
             self.register_agent(data['agent_id'])

    def _handle_entity_destroyed(self, data: Dict) -> None:
        # Implementation for M01.6
        victim_id = data.get('entity_id')
        if data.get('entity_type') == 'agent' and victim_id:
             # Call self._remove_agent(data['entity_id']) when implemented
             self._remove_agent(victim_id)
        # Handle morale changes for killer/victim's team
        killer_id = data.get('killer_id')
        if killer_id:
            self.apply_morale_change(killer_id, self._morale_event_modifiers.get("kill_enemy", 0.15), f"killed_{victim_id}")

        # Find victim's team and apply penalty (needs TeamSystem access)
        team_system = system_manager.get_system("TeamSystem")
        if team_system:
            victim_team_id = team_system.get_team_id_for_agent(victim_id) # Assumes method exists
            if victim_team_id:
                victim_team = team_system.teams.get(victim_team_id)
                if victim_team:
                    for member_data in victim_team.get("members", []):
                        member_id = member_data if isinstance(member_data, str) else member_data.get('agent_id')
                        if member_id and member_id != victim_id:
                            self.apply_morale_change(member_id, self._morale_event_modifiers.get("ally_death", -0.20), f"ally_{victim_id}_killed")

    def _handle_agent_damaged(self, data: Dict) -> None:
        # Implementation for M01.6
        target_id = data.get('target_id')
        attacker_id = data.get('attacker_id')
        damage = data.get('damage', 0)
        # details = data.get('details', {}) # Details might contain info like max_health

        if target_id:
            # Apply morale loss for taking damage
            # TODO: Scale loss based on damage percentage of max health? Requires agent health info.
            loss_key = "take_damage_major" if damage > 20 else "take_damage_minor" # Example threshold: 20 damage
            change = self._morale_event_modifiers.get(loss_key, -0.02)
            self.apply_morale_change(target_id, change, f"took_{damage:.1f}_damage")

        if attacker_id:
            # Apply morale gain for dealing damage
            gain_key = "deal_damage_major" if damage > 20 else "deal_damage_minor"
            change = self._morale_event_modifiers.get(gain_key, 0.01)
            self.apply_morale_change(attacker_id, change, f"dealt_{damage:.1f}_damage")

    def _handle_attack_miss(self, data: Dict) -> None:
        # Implementation for M01.6
        # Handles both ATTACK_MISS and NEAR_MISS_DETECTED events for now
        target_id = data.get('target_id') # ID of the agent that was missed
        # Need proximity data from the event
        proximity = data.get('proximity') # Distance the shot missed by
        # Alternatively, bullet position and target position could be used to calculate proximity here

        if target_id and proximity is not None:
             # Configurable threshold for what counts as a near miss for suppression
             near_miss_threshold = self._config.get("SUPPRESSION_NEAR_MISS_THRESHOLD", 15.0)
             if proximity < near_miss_threshold:
                  # Scale suppression based on how close the miss was
                  base_increase = self._suppression_event_modifiers.get("near_miss_bullet", 0.1)
                  # Closer miss = more suppression (linear scaling)
                  scaling_factor = max(0, 1.0 - (proximity / near_miss_threshold))
                  suppression_amount = base_increase * scaling_factor
                  self.apply_suppression_increase(target_id, suppression_amount, f"near_miss_{proximity:.1f}u")

    def _handle_explosion(self, data: Dict) -> None:
        """Handle nearby explosion events for suppression."""
        agent_id = data.get('agent_id') # Assume event identifies affected agent
        distance = data.get('distance') # Assume event provides distance to explosion
        max_radius = data.get('max_radius', 50.0) # Assume event provides effective radius

        if agent_id and distance is not None:
             if distance < max_radius:
                 # Apply suppression based on explosion proximity/intensity if available
                 base_increase = self._suppression_event_modifiers.get("nearby_explosion", 0.3)
                 # Closer explosion = more suppression (linear scaling)
                 scaling_factor = max(0, 1.0 - (distance / max_radius))
                 suppression_amount = base_increase * scaling_factor
                 self.apply_suppression_increase(agent_id, suppression_amount, f"nearby_explosion_{distance:.1f}u")

    def _handle_team_action(self, data: Dict) -> None:
        # Implementation for M01.7
        """Handle generic team success/failure events."""
        team_id = data.get('team_id')
        success = data.get('success', True) # Default to success if not specified
        event_type = data.get('event_type', 'unknown_team_action') # e.g., 'objective_capture'

        if team_id:
            # Determine morale modifier based on success/failure and potentially event type
            if success:
                # Use specific modifier if available (e.g., objective_complete), else default team_victory
                morale_key = self._config.get("MORALE_EVENT_MAP", {}).get(event_type, "team_victory")
            else:
                morale_key = self._config.get("MORALE_EVENT_MAP", {}).get(event_type, "team_defeat")

            change = self._morale_event_modifiers.get(morale_key, 0.0)

            if change != 0.0:
                # Find team members (needs TeamSystem access)
                team_system = system_manager.get_system("TeamSystem")
                if team_system:
                    team_data = team_system.teams.get(team_id)
                    if team_data:
                        members = team_data.get("members", [])
                        for member_data in members:
                            member_id = member_data if isinstance(member_data, str) else member_data.get('agent_id')
                            if member_id:
                                self.apply_morale_change(member_id, change, f"{event_type}_{'success' if success else 'failure'}")
                    else:
                         logger.warning(f"Team {team_id} not found in TeamSystem during team action event.")
                else:
                     logger.warning("TeamSystem not found during team action event.")
            else:
                 logger.debug(f"No morale modifier defined for team action: {event_type} (success={success})")

    # Note: Handling "heavy_fire_volume" suppression likely requires a different approach.
    # It might involve agents tracking incoming fire rate locally or the environment
    # system detecting high-density bullet zones and emitting specific events or state changes.
    # A simple event handler might not be sufficient.

    def _shutdown(self) -> None:
        """Unsubscribe from events."""
        # Reuse the map and list from _initialize to unsubscribe
        # Need to store the map or list if they aren't instance variables
        # Example (assuming event_handler_map is self.event_handler_map):
        unsubscribed_count = 0
        if hasattr(self, 'event_handler_map'): # Check if map exists
            for event_type, handler in self.event_handler_map.items():
                if hasattr(SystemEventType, event_type.name):
                    try:
                        system_manager.unsubscribe(event_type, handler)
                        unsubscribed_count += 1
                    except Exception as e:
                        logger.error(f"Error unsubscribing from {event_type.name}: {e}")

        logger.info(f"MoraleSuppressionSystem shut down. Unsubscribed from {unsubscribed_count} event types.") 