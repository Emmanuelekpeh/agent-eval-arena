"""
System for handling collision detection between entities.
"""

import math
from typing import List, Tuple, Dict, Any, Optional
import logging
import time 

from systems.core.base_system import BaseSystem, SystemEventType
from systems.core.system_manager import SystemManager
from systems.core.entity_manager import EntityManager
from systems.spatial_system import QuadTree, AABB # Assuming QuadTree is here
from systems.utils.logging import logger

# Constants (Consider moving to config)
AGENT_TYPE = 'agent'
BULLET_TYPE = 'bullet'
OBSTACLE_TYPE = 'obstacle' # Assuming cover/hazards are obstacles
RESOURCE_TYPE = 'resource'
PICKUP_TYPE = 'pickup'

class CollisionSystem(BaseSystem):
    """
    Handles collision detection between entities using a QuadTree.
    Relies on BattleRoyaleEnv to maintain the QuadTree and entity data.
    """
    def __init__(self, priority: int = 40):
        super().__init__(name="CollisionSystem", priority=priority)
        self.env = None # Reference to the environment
        self._entity_manager: Optional[EntityManager] = None
        self._last_collision_check_time = 0
        # TODO: Make collision check frequency configurable
        self._collision_check_interval = 1.0 / 30.0 # Check at roughly 30 Hz
        
        # Store recent collisions to avoid duplicate events within one frame/short interval
        self._recent_collisions: set[tuple[str, str]] = set()

    def _initialize(self) -> None:
        """Get reference to environment and its QuadTree."""
        self.env = self.get_shared_state('environment')
        if not self.env:
            self.logger.error("Environment not found in shared state during CollisionSystem initialization.")
            return
        if not hasattr(self.env, 'collision_tree'):
            self.logger.error("Environment does not have a 'collision_tree' attribute.")
            self.env = None # Disable system if tree is missing
            return

        # No need to subscribe to entity events here, Env handles tree updates
        # self.subscribe_to_event(SystemEventType.ENTITY_MOVED, self._handle_entity_moved)
        # self.subscribe_to_event(SystemEventType.ENTITY_CREATED, self._handle_entity_created)
        # self.subscribe_to_event(SystemEventType.ENTITY_DESTROYED, self._handle_entity_destroyed)

        self.logger.info("CollisionSystem initialized, using Environment's QuadTree.")

        self._entity_manager = self.get_system("entity_manager")
        if not self._entity_manager:
            self.logger.error("EntityManager not found!")
        self._last_collision_check_time = time.time()
        self._recent_collisions.clear()

    def _update(self, delta_time: float) -> None:
        """Checks for collisions between known entities."""
        if not self.env:
            return # System disabled

        # --- OPTIONAL: Rebuild QuadTree if needed --- #
        # If QuadTree removal is inefficient, rebuild it here based on current env state
        if getattr(self.env, '_quadtree_needs_rebuild', False):
             self.env.collision_tree.clear()
             # Re-insert all known entities (agents, bullets, pickups, cover, hazards)
             entities_to_insert = []
             for agent_id, agent_data in self.env.agents.items():
                  player = agent_data.get('player')
                  if player and getattr(player, 'alive', True):
                       pos = self.env.agent_positions.get(agent_id)
                       radius = getattr(player, 'radius', 10)
                       if pos: entities_to_insert.append((pos, agent_id, radius, 'agent'))
             for bullet in self.env.active_bullets:
                  if bullet.active:
                       entities_to_insert.append(((bullet.x, bullet.y), id(bullet), bullet.radius, 'bullet'))
             for pickup in self.env.pickups:
                  pos = pickup.get('position')
                  pid = pickup.get('id')
                  radius = pickup.get('radius', 5)
                  if pos and pid: entities_to_insert.append((pos, pid, radius, 'pickup'))
             for cover_id, cover in self.env.cover_data.items():
                  entities_to_insert.append(((cover['center_x'], cover['center_y']), cover_id, cover['radius'], 'cover'))
             for hazard_id, hazard in self.env.hazard_data.items():
                   entities_to_insert.append(((hazard['x'], hazard['y']), hazard_id, hazard['radius'], 'hazard'))
             # Insert all collected entities
             for pos, eid, rad, etype in entities_to_insert:
                  try: self.env.collision_tree.insert(pos, eid, rad, etype)
                  except Exception as e: self.logger.error(f"Error re-inserting {etype} {eid} into QuadTree: {e}")
             self.env._quadtree_needs_rebuild = False # Reset flag
             # self.logger.debug("Rebuilt Collision QuadTree.")
        # ---------------------------------------------- #

        current_time = time.time()
        if current_time - self._last_collision_check_time >= self._collision_check_interval:
             self._recent_collisions.clear() # Clear recent collision cache
             if self._entity_manager:
                  self._check_collisions()
             self._last_collision_check_time = current_time

    def _check_collisions(self) -> None:
        """Detects collisions between relevant entities using the EntityManager's spatial partition."""
        if not self._entity_manager or not self._entity_manager.spatial_partition:
            self.logger.warning("Cannot check collisions: EntityManager or spatial partition unavailable.")
            return

        checked_pairs = set() # Avoid checking A-B and B-A
        entities_to_query = []

        # --- Gather Entities to Query Around ---
        # Focus on active entities like agents and bullets
        agents_data = self._entity_manager.get_all_entities_of_type(AGENT_TYPE)
        bullets_data = self._entity_manager.get_all_entities_of_type(BULLET_TYPE)

        # Could add other types like moving hazards if necessary
        entities_to_query.extend(agents_data)
        entities_to_query.extend(bullets_data)

        if not entities_to_query:
            # self.logger.debug("No active entities (agents/bullets) found to check collisions for.")
            return

        # --- Perform Collision Checks ---
        for entity1_data in entities_to_query:
            entity1_id = entity1_data.get('id')
            entity1_type = entity1_data.get('type')
            entity1_pos = entity1_data.get('position')
            entity1_radius = entity1_data.get('radius', 0)
            # TODO: Support AABB or other shapes if available in entity_data
            # entity1_aabb = entity1_data.get('aabb') 

            if not entity1_id or not entity1_pos or entity1_radius <= 0:
                # self.logger.debug(f"Skipping entity {entity1_id} due to missing data (pos/radius).")
                continue # Cannot collide without position and size

            # Query nearby entities using the spatial partition
            # Query radius should be large enough to catch interactions
            # For simplicity, using twice the radius. More sophisticated: radius + max_expected_other_radius
            query_radius = entity1_radius * 2.5 # Increased slightly for better catching
            try:
                 nearby_entities_data = self._entity_manager.get_entities_in_range(entity1_pos, query_radius)
            except Exception as e:
                 self.logger.error(f"Error querying EntityManager for entities near {entity1_id} at {entity1_pos} (radius {query_radius}): {e}")
                 continue

            for entity2_data in nearby_entities_data:
                entity2_id = entity2_data.get('id')
                if entity1_id == entity2_id:
                    continue # Don't collide with self

                # Avoid duplicate checks (A-B vs B-A)
                pair = tuple(sorted((str(entity1_id), str(entity2_id)))) # Ensure IDs are strings for sorting
                if pair in checked_pairs:
                     continue

                entity2_type = entity2_data.get('type')
                entity2_pos = entity2_data.get('position')
                entity2_radius = entity2_data.get('radius', 0)
                 # entity2_aabb = entity2_data.get('aabb')

                if not entity2_id or not entity2_pos or entity2_radius <= 0:
                     # self.logger.debug(f"Skipping nearby entity {entity2_id} for collision with {entity1_id} due to missing data.")
                     continue

                # --- Perform Collision Check ---
                # Simple Circle-Circle Check (Default)
                # TODO: Add AABB checks if available
                dist_sq = (entity1_pos[0] - entity2_pos[0])**2 + (entity1_pos[1] - entity2_pos[1])**2
                radii_sum_sq = (entity1_radius + entity2_radius)**2

                collision_occurred = dist_sq <= radii_sum_sq

                # --- Handle Collision ---
                if collision_occurred:
                    # self.logger.debug(f"Collision detected between {entity1_type} {entity1_id} and {entity2_type} {entity2_id}")
                    self._emit_collision_event(entity1_data, entity2_data, pair)
                    checked_pairs.add(pair) # Add pair after confirming collision and emitting event
                    # Break inner loop? Maybe not, entity1 might collide with multiple things.
                    # But the pair check prevents redundant events for this specific pair.

    def _emit_collision_event(self, entity1_data: Dict, entity2_data: Dict, collision_pair: tuple[str, str]) -> None:
        """Determines the type of collision and emits the appropriate event."""
        
        # Avoid emitting duplicate events rapidly
        if collision_pair in self._recent_collisions:
            return
        self._recent_collisions.add(collision_pair)

        e1_id = entity1_data['id']
        e2_id = entity2_data['id']
        e1_type = entity1_data.get('type')
        e2_type = entity2_data.get('type')

        event_type = SystemEventType.ENTITY_COLLISION # Default generic event
        payload = {
            'entity1_id': e1_id,
            'entity1_data': entity1_data,
            'entity1_type': e1_type,
            'entity2_id': e2_id,
            'entity2_data': entity2_data,
            'entity2_type': e2_type
        }
        specific_event_emitted = False

        # --- Specific Event Logic --- 
        if BULLET_TYPE in [e1_type, e2_type]:
            if AGENT_TYPE in [e1_type, e2_type]:
                event_type = SystemEventType.BULLET_HIT_AGENT
                # Ensure payload identifies bullet and agent clearly if needed by listeners
                if e1_type == BULLET_TYPE:
                    payload['bullet_id'] = e1_id
                    payload['agent_id'] = e2_id
                    payload['bullet_data'] = entity1_data # redundant but clear
                    payload['agent_data'] = entity2_data  # redundant but clear
                else:
                    payload['bullet_id'] = e2_id
                    payload['agent_id'] = e1_id
                    payload['bullet_data'] = entity2_data
                    payload['agent_data'] = entity1_data
                specific_event_emitted = True
            elif OBSTACLE_TYPE in [e1_type, e2_type]:
                event_type = SystemEventType.BULLET_HIT_OBSTACLE
                if e1_type == BULLET_TYPE:
                    payload['bullet_id'] = e1_id
                    payload['obstacle_id'] = e2_id
                else:
                    payload['bullet_id'] = e2_id
                    payload['obstacle_id'] = e1_id
                specific_event_emitted = True
            # Consider BULLET_HIT_BULLET if needed

        elif [e1_type, e2_type] == [AGENT_TYPE, AGENT_TYPE]:
            event_type = SystemEventType.AGENT_AGENT_COLLISION
            specific_event_emitted = True

        elif [e1_type, e2_type] == [AGENT_TYPE, PICKUP_TYPE]:
            event_type = SystemEventType.AGENT_PICKUP_COLLISION
            if e1_type == AGENT_TYPE:
                payload['agent_id'] = e1_id
                payload['pickup_id'] = e2_id
            else:
                payload['agent_id'] = e2_id
                payload['pickup_id'] = e1_id
            specific_event_emitted = True

        elif [e1_type, e2_type] == [AGENT_TYPE, RESOURCE_TYPE]:
            event_type = SystemEventType.AGENT_RESOURCE_COLLISION # If interaction happens on collision
            # Add specific agent/resource IDs if needed
            specific_event_emitted = True

        elif [e1_type, e2_type] == [AGENT_TYPE, OBSTACLE_TYPE]:
            event_type = SystemEventType.AGENT_OBSTACLE_COLLISION
            specific_event_emitted = True

        # --- Emit Event --- 
        logger.debug(f"Emitting collision event: {event_type.name} between {e1_type} ({e1_id}) and {e2_type} ({e2_id})")
        self.emit_event(event_type, payload)

        # Optionally emit the generic ENTITY_COLLISION as well, 
        # if some systems only care about generic collisions.
        # if specific_event_emitted:
        #     self.emit_event(SystemEventType.ENTITY_COLLISION, payload)

    # --- Remove local event handlers as Env now manages the tree --- #
    # def _handle_entity_moved(self, event_data: Dict[str, Any]) -> None:
    #     ...
    # def _handle_entity_created(self, event_data: Dict[str, Any]) -> None:
    #     ...
    # def _handle_entity_destroyed(self, event_data: Dict[str, Any]) -> None:
    #     ...

    def _shutdown(self) -> None:
        """Clean up resources."""
        self.env = None # Clear env reference
        self.logger.info("CollisionSystem shut down.")
        self._entity_manager = None
        self._recent_collisions.clear()
