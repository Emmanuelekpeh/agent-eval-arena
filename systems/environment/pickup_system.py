"""
System responsible for handling pickup interactions.
"""

import logging
from typing import Dict, Optional

from systems.core.base_system import BaseSystem
from systems.core.system_manager import SystemEventType, system_manager
# Assuming constants are defined for entity types
from systems.constants import AGENT_TYPE, PICKUP_TYPE 

logger = logging.getLogger(__name__)

class PickupSystem(BaseSystem):
    """Handles the logic when an agent collides with a pickup item."""

    def __init__(self, priority: int = 60):
        """Initialize the PickupSystem."""
        super().__init__(name="PickupSystem", priority=priority)
        self._entity_manager = None
        logger.info("PickupSystem initialized.")

    @property
    def entity_manager(self) -> Optional["EntityManager"]:
        """Lazy load EntityManager."""
        if self._entity_manager is None:
             # Use the correct name EntityManager is registered with
            self._entity_manager = system_manager.get_system("EntityManager") 
            if not self._entity_manager:
                logger.error(f"{self.name}: EntityManager not found!")
        return self._entity_manager

    def initialize(self) -> None:
        """Subscribe to relevant events."""
        try:
            # Subscribe to the specific collision event defined in CollisionSystem
            self.subscribe_to_event(SystemEventType.AGENT_PICKUP_COLLISION, self._handle_agent_pickup_collision)
            logger.info("PickupSystem subscribed to AGENT_PICKUP_COLLISION events.")
        except Exception as e:
            logger.error(f"Error subscribing PickupSystem to events: {e}")

    def _handle_agent_pickup_collision(self, event_data: Dict) -> None:
        """Handles the collision event between an agent and a pickup."""
        agent_id = event_data.get('agent_id')
        pickup_id = event_data.get('pickup_id')
        
        if not agent_id or not pickup_id:
            logger.warning("Received AGENT_PICKUP_COLLISION event with missing agent_id or pickup_id.")
            return

        if not self.entity_manager:
            logger.error("Cannot handle pickup collision: EntityManager unavailable.")
            return
            
        # 1. Get pickup details
        pickup_data = self.entity_manager.get_entity(pickup_id)
        if not pickup_data:
            # Pickup might have been collected by another system/agent simultaneously
            logger.debug(f"Pickup {pickup_id} not found in EntityManager, possibly already collected.")
            return
            
        pickup_type = pickup_data.get('pickup_type', 'unknown') # e.g., 'health_pack', 'ammo', 'weapon_upgrade'
        pickup_effect = pickup_data.get('effect', {}) # e.g., {'stat': 'health', 'value': 50} or {'weapon': 'shotgun'}

        logger.info(f"Agent {agent_id} collided with pickup {pickup_id} (Type: {pickup_type}).")

        # 2. Apply effect to agent (emit an event for another system, e.g., AgentSystem or a dedicated EffectSystem)
        # Example: Emitting a generic APPLY_EFFECT event
        effect_payload = {
            'target_id': agent_id,
            'effect_type': pickup_type, # Use pickup type as effect type? Or define specific effect types?
            'effect_details': pickup_effect,
            'source': f'pickup_{pickup_id}'
        }
        # TODO: Define a specific SystemEventType for applying effects/pickups if needed
        # self.emit_event(SystemEventType.APPLY_PICKUP_EFFECT, effect_payload) 
        # For now, just log that the effect *would* be applied
        logger.info(f"Applying effect from pickup {pickup_id} to agent {agent_id}: {pickup_effect}")

        # 3. Destroy the pickup entity
        destroy_payload = {
            'entity_id': pickup_id,
            'entity_type': PICKUP_TYPE,
            'reason': f'collected_by_{agent_id}'
        }
        self.emit_event(SystemEventType.ENTITY_DESTROYED, destroy_payload)
        logger.debug(f"Emitted ENTITY_DESTROYED event for pickup {pickup_id}.")

    def update(self, delta_time: float) -> None:
        """Update logic for the PickupSystem (if any needed)."""
        pass # Currently driven by events

    def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("PickupSystem shutting down.")
        # Unsubscribe if necessary, though SystemManager might handle this
        # try:
        #     self.unsubscribe_from_event(SystemEventType.AGENT_PICKUP_COLLISION, self._handle_agent_pickup_collision)
        # except Exception as e:
        #     logger.error(f"Error unsubscribing PickupSystem: {e}")
        self._entity_manager = None 