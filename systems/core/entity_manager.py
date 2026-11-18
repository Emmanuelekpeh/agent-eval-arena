from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict
import logging

from systems.core.base_system import BaseSystem, SystemEventType
# Import spatial partitioning classes
from systems.spatial_system import QuadTree, AABB 
from systems.utils.config import config # For world dimensions

logger = logging.getLogger(__name__)

class EntityManager(BaseSystem):
    """Manages the lifecycle and core state of all entities in the simulation."""

    def __init__(self, name: str = "EntityManager", priority: int = 5):
        super().__init__(name, priority)
        # Core storage for entity data {entity_id: {data}}
        self._entities: Dict[str, Dict[str, Any]] = {}
        # Index for quick lookup by type {entity_type: set(entity_id)}
        self._entities_by_type: Dict[str, set[str]] = defaultdict(set)
        
        # Initialize spatial partitioning structure
        world_width = config.display.get('SCREEN_WIDTH', 1200)
        world_height = config.display.get('SCREEN_HEIGHT', 800)
        world_boundary = AABB(center_x=world_width / 2, center_y=world_height / 2, 
                              half_width=world_width / 2, half_height=world_height / 2)
        # TODO: Make capacity configurable?
        self.spatial_partition = QuadTree(boundary=world_boundary, capacity=4) 
        logger.info(f"EntityManager initialized with boundary: {world_boundary}")

    def _initialize(self) -> None:
        # Clear state on re-initialization if needed
        self._entities.clear()
        self._entities_by_type.clear()
        # Clear spatial partition
        self.spatial_partition.clear() 
        logger.info("EntityManager internal state cleared")

    def _shutdown(self) -> None:
        logger.info("EntityManager shutting down")
        self._entities.clear()
        self._entities_by_type.clear()
        self.spatial_partition.clear() # Ensure partition is cleared

    def register_entity(self, entity_id: str, entity_type: str, position: Tuple[float, float], 
                          radius: float = 0.0, initial_state: Optional[Dict[str, Any]] = None) -> bool:
        """Registers a new entity with the manager."""
        if entity_id in self._entities:
            logger.warning(f"Attempted to register entity with existing ID: {entity_id}")
            return False

        entity_data = {
            'id': entity_id,
            'type': entity_type,
            'position': position,
            'radius': radius,
        }
        if initial_state:
            entity_data.update(initial_state) # Merge additional state

        self._entities[entity_id] = entity_data
        self._entities_by_type[entity_type].add(entity_id)

        # Add entity to spatial partition
        try:
           # Assuming QuadTree insert takes: point tuple, entity_id, entity_radius, entity_type
           success = self.spatial_partition.insert(position, entity_id, radius, entity_type) 
           if not success:
                logger.warning(f"Failed to insert entity {entity_id} into spatial partition (possibly out of bounds? Position: {position})")
        except Exception as e:
           logger.error(f"Error adding entity {entity_id} to spatial partition: {e}", exc_info=True)
           # Should we unregister the entity if spatial insert fails?
           # For now, let it be registered but log error.
        
        logger.debug(f"Registered entity: {entity_id} (Type: {entity_type})")
        self.emit_event(SystemEventType.ENTITY_CREATED, {'entity_id': entity_id, 'entity_type': entity_type, 'data': entity_data.copy()})
        return True

    def unregister_entity(self, entity_id: str) -> bool:
        """Removes an entity from the manager."""
        if entity_id not in self._entities:
            # logger.warning(f"Attempted to unregister non-existent entity: {entity_id}") # Can be noisy if events trigger multiple times
            return False

        entity_data = self._entities.pop(entity_id)
        entity_type = entity_data.get('type')
        position = entity_data.get('position') # Get position before removing

        if entity_type and entity_id in self._entities_by_type.get(entity_type, set()):
            self._entities_by_type[entity_type].remove(entity_id)
            if not self._entities_by_type[entity_type]: # Remove type entry if set is empty
                 del self._entities_by_type[entity_type]
        
        # Remove entity from spatial partition
        # Assuming QuadTree doesn't have a dedicated remove, we might need to rebuild or just ignore?
        # QuadTree often relies on re-insertion/clearing. For simplicity, we might just leave the old point
        # if removal isn't directly supported or needed for query correctness (queries check against current _entities)
        # If QuadTree had a remove: 
        # try:
        #    self.spatial_partition.remove(entity_id, position) 
        # except Exception as e:
        #    logger.error(f"Error removing entity {entity_id} from spatial partition: {e}")
        logger.debug(f"Unregistered entity: {entity_id}")
        self.emit_event(SystemEventType.ENTITY_DESTROYED, {'entity_id': entity_id, 'entity_type': entity_type, 'data': entity_data.copy()})
        return True

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the data for a specific entity."""
        # Return a copy to prevent external modification of internal state
        return self._entities.get(entity_id, {}).copy() 

    def update_entity_position(self, entity_id: str, new_position: Tuple[float, float]) -> bool:
        """Updates the position of an existing entity."""
        entity_data = self._entities.get(entity_id)
        if not entity_data:
            # logger.warning(f"Attempted to update position for non-existent entity: {entity_id}") # Can be noisy
            return False
        
        old_position = entity_data.get('position')
        if old_position == new_position:
            return True # No change needed
            
        entity_data['position'] = new_position

        # Update entity position in spatial partition
        # QuadTree often requires remove + re-insert for updates.
        # Remove first (ignore result if remove isn't implemented/needed)
        # try:
        #    self.spatial_partition.remove(entity_id, old_position)
        # except Exception as e:
        #    logger.warning(f"Could not remove entity {entity_id} from old position {old_position} during update: {e}")

        # Re-insert at new position
        try:
            radius = entity_data.get('radius', 0.0)
            entity_type = entity_data.get('type')
            # We need to re-insert to update its location in the QuadTree structure
            # If the QuadTree doesn't support remove, this might lead to duplicates 
            # in the structure IF the old point isn't pruned/ignored during query. 
            # Assuming insert handles updates or query handles validity check against self._entities.
            success = self.spatial_partition.insert(new_position, entity_id, radius, entity_type) 
            if not success:
                logger.warning(f"Failed to (re)insert entity {entity_id} into spatial partition during update (Position: {new_position})")
                # Revert position change on error?
                # entity_data['position'] = old_position 
                # return False
        except Exception as e:
            logger.error(f"Error updating entity {entity_id} in spatial partition: {e}", exc_info=True)
            # Revert position change on error?
            # entity_data['position'] = old_position 
            # return False

        # Consider emitting an ENTITY_MOVED event if needed by other systems
        # self.emit_event(SystemEventType.ENTITY_MOVED, {'entity_id': entity_id, 'new_position': new_position})
        return True

    # --- Query Methods (Implemented with spatial partitioning) ---

    def get_all_entities_of_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """Gets data for all entities of a specific type."""
        entity_ids = self._entities_by_type.get(entity_type, set())
        # Return copies
        return [self._entities.get(eid, {}).copy() for eid in entity_ids if eid in self._entities]

    def get_entities_in_range(self, position: Tuple[float, float], radius: float, 
                                entity_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Gets entities within a certain range of a position, optionally filtered by type."""
        # logger.warning("get_entities_in_range - Spatial query not yet implemented. Falling back to simple distance check.")
        
        # Define query range box (AABB)
        # Use radius for both half-width/height for simplicity, assumes circular range query
        query_box = AABB(center_x=position[0], center_y=position[1], half_width=radius, half_height=radius)
        
        # Query the spatial partition
        # This returns points: List[Tuple(x, y, entity_id, entity_radius, entity_type)]
        potential_points = self.spatial_partition.query_range(query_box) 
        
        nearby_entities_data = []
        px, py = position
        radius_sq = radius * radius
        
        potential_ids = set(p[2] for p in potential_points) # Extract unique IDs

        for entity_id in potential_ids:
            # Crucially, check if the entity ID found by QuadTree STILL exists in our main dictionary
            # This handles cases where an entity was removed but QuadTree removal is complex/not done.
            entity_data = self._entities.get(entity_id)
            if not entity_data:
                continue # Entity no longer exists, ignore point from QuadTree
            
            # Optional: Filter by type
            if entity_types and entity_data.get('type') not in entity_types:
                continue
                
            # Optional: Perform precise distance check if query_range is approximate (AABB vs Circle)
            ex, ey = entity_data.get('position', (None, None))
            if ex is not None:
                dist_sq = (px - ex)**2 + (py - ey)**2
                if dist_sq <= radius_sq:
                    nearby_entities_data.append(entity_data.copy())
                         
        return nearby_entities_data

    def get_entity_count(self) -> int:
        """Returns the total number of managed entities."""
        return len(self._entities)

    def get_entity_count_by_type(self, entity_type: str) -> int:
        """Returns the number of entities of a specific type."""
        return len(self._entities_by_type.get(entity_type, set()))

    def get_all_entities(self) -> List[Dict[str, Any]]:
        """Returns data for all managed entities. Use with caution for performance."""
        return [data.copy() for data in self._entities.values()] 