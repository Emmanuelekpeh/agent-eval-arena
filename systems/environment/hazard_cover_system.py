import pygame
import random
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
import time
import math
import logging

# Import SystemManager for event emission
from systems.core.system_manager import system_manager, SystemEventType
from systems.visualization.visualization_system import Color

logger = logging.getLogger(__name__)

class HazardCoverSystem:
    """
    System for managing hazards and cover objects in the environment.
    Hazards are dangerous areas that can apply status effects to agents.
    Cover objects provide protection against damage.
    """
    
    def __init__(self, width: int, height: int):
        """
        Initialize the hazard and cover system.
        
        Args:
            width (int): Environment width
            height (int): Environment height
        """
        self.width = width
        self.height = height
        
        # Cover objects (store as dict with unique IDs)
        self.cover_objects: Dict[str, Dict[str, Any]] = {}
        self._cover_id_counter = 0
        
        # Hazard areas (store as dict with unique IDs)
        self.hazard_areas: Dict[str, Dict[str, Any]] = {}
        self._hazard_id_counter = 0
        
        # Cover types
        self.cover_types = {
            "wall": {
                "durability": 100,
                "protection": 0.8,
                "destructible": True,
                "color": (100, 100, 100)
            },
            "rock": {
                "durability": 200,
                "protection": 0.9,
                "destructible": False,
                "color": (80, 80, 80)
            },
            "crate": {
                "durability": 50,
                "protection": 0.7,
                "destructible": True,
                "color": (139, 69, 19)
            },
            "tree": {
                "durability": 80,
                "protection": 0.6,
                "destructible": True,
                "color": (34, 139, 34)
            }
        }
        
        # Hazard types
        self.hazard_types = {
            "fire": {
                "damage": 5,
                "radius": 50,
                "duration": 300,  # frames
                "color": (255, 100, 0),
                "effect": "burning"
            },
            "radiation": {
                "damage": 2,
                "radius": 100,
                "duration": 600,  # frames
                "color": (0, 255, 0, 128),
                "effect": "poisoned"
            },
            "ice": {
                "damage": 1,
                "radius": 70,
                "duration": 450,  # frames
                "color": (0, 200, 255),
                "effect": "slowed"
            },
            "electricity": {
                "damage": 8,
                "radius": 40,
                "duration": 180,  # frames
                "color": (255, 255, 0),
                "effect": "stunned"
            }
        }
        
        logger.info(f"HazardCoverSystem initialized with dimensions {width}x{height}")
        
    def generate_cover(self, density: float = 0.05):
        """
        Generate cover objects based on density parameter and emit creation events.
        
        Args:
            density (float): Density of cover objects (0.0 to 1.0)
        """
        # Clear existing cover (need to emit destroy events)
        for cover_id in list(self.cover_objects.keys()):
             self._destroy_cover(cover_id)
             
        self.cover_objects = {}
        # Reset counter if needed, or let it grow
        # self._cover_id_counter = 0 
        
        # Calculate number of cover objects
        grid_size = 50
        cols = self.width // grid_size
        rows = self.height // grid_size
        
        total_cells = cols * rows
        num_cover = int(total_cells * density)
        
        # Keep track of occupied cells to avoid overlapping
        occupied_cells = set()
        
        for _ in range(num_cover):
            # Try to find an unoccupied cell
            for attempt in range(10):
                col = random.randint(0, cols - 1)
                row = random.randint(0, rows - 1)
                cell_key = (col, row)
                
                if cell_key not in occupied_cells:
                    occupied_cells.add(cell_key)
                    
                    # Calculate position
                    x = col * grid_size + random.randint(10, grid_size - 10)
                    y = row * grid_size + random.randint(10, grid_size - 10)
                    
                    # Randomly select cover type
                    cover_type = random.choice(list(self.cover_types.keys()))
                    
                    # Random size (keep it smaller than grid size)
                    width = random.randint(20, grid_size - 10)
                    height = random.randint(20, grid_size - 10)
                    
                    # --- Add cover object and Emit Event --- #
                    self._add_cover_object(
                         cover_type=cover_type,
                         x=x, y=y,
                         width=width, height=height
                    )
                    break
        logger.info(f"Generated {len(self.cover_objects)} cover objects.")

    def _add_cover_object(self, cover_type: str, x: float, y: float, width: float, height: float) -> str:
        """Adds a single cover object and emits an event."""
        self._cover_id_counter += 1
        cover_id = f"cover_{self._cover_id_counter}"
        props = self.cover_types[cover_type]
        
        # Calculate center and effective radius for collision tree
        center_x = x + width / 2
        center_y = y + height / 2
        # Use diagonal length / 2 as effective radius (approximation)
        radius = math.sqrt(width**2 + height**2) / 2 
        
        cover = {
            "id": cover_id,
            "type": cover_type,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "center_x": center_x,
            "center_y": center_y,
            "radius": radius, # Effective radius
            "durability": props["durability"],
            "protection": props["protection"],
            "destructible": props["destructible"],
            "color": props["color"]
        }
        
        self.cover_objects[cover_id] = cover
        
        # Emit creation event for collision system
        system_manager.emit_event(SystemEventType.ENTITY_CREATED, {
             'entity_id': cover_id,
             'entity_type': 'cover',
             'position': (center_x, center_y), # Use center for tree
             'radius': radius,
             'data': cover # Include full data if needed by env
        })
        return cover_id

    def _destroy_cover(self, cover_id: str):
         """Removes a cover object and emits destroy event."""
         if cover_id in self.cover_objects:
              del self.cover_objects[cover_id]
              system_manager.emit_event(SystemEventType.ENTITY_DESTROYED, {
                   'entity_id': cover_id,
                   'entity_type': 'cover',
                   'reason': 'destroyed'
              })
              return True
         return False

    def add_hazard(self, hazard_type: str, x: float, y: float):
        """
        Add a hazard area to the environment and emit creation event.
        
        Args:
            hazard_type (str): Type of hazard
            x (float): X position (center)
            y (float): Y position (center)
        """
        if hazard_type not in self.hazard_types:
            logger.warning(f"Unknown hazard type: {hazard_type}")
            return None
        
        hazard_props = self.hazard_types[hazard_type]
        self._hazard_id_counter += 1
        hazard_id = f"hazard_{self._hazard_id_counter}"
        
        hazard = {
            "id": hazard_id,
            "type": hazard_type,
            "x": x, # Center position
            "y": y,
            "radius": hazard_props["radius"],
            "damage": hazard_props["damage"],
            "effect": hazard_props["effect"],
            "color": hazard_props["color"],
            "duration": hazard_props["duration"],
            "remaining": hazard_props["duration"]
        }
        
        self.hazard_areas[hazard_id] = hazard
        
        # Emit creation event
        system_manager.emit_event(SystemEventType.ENTITY_CREATED, {
            'entity_id': hazard_id,
            'entity_type': 'hazard',
            'position': (x, y), # Use center for tree
            'radius': hazard['radius'],
            'entity_instance': hazard
        })
        return hazard_id
    
    def is_position_in_cover(self, x: float, y: float) -> bool:
        """
        Check if a position is inside any cover object's bounding box.
        """
        for cover in self.cover_objects.values():
            if (cover["x"] <= x <= cover["x"] + cover["width"] and
                cover["y"] <= y <= cover["y"] + cover["height"]):
                return True
        
        return False
    
    def get_cover_at_position(self, x: float, y: float) -> Optional[Dict[str, Any]]:
        """
        Get cover object at a position (based on bounding box).
        Returns the cover object dict if found, else None.
        """
        for cover_id, cover in self.cover_objects.items():
            if (cover["x"] <= x <= cover["x"] + cover["width"] and
                cover["y"] <= y <= cover["y"] + cover["height"]):
                return cover
        
        return None
    
    def damage_cover(self, cover_id: str, damage: float) -> bool:
        """
        Damage a specific cover object by its ID.
        Emits destroy event if cover is destroyed.
        
        Args:
            cover_id (str): ID of the cover object
            damage (float): Amount of damage
            
        Returns:
            bool: True if cover was destroyed
        """
        if cover_id not in self.cover_objects:
            return False
            
        cover = self.cover_objects[cover_id]
        
        if cover["destructible"]:
            cover["durability"] -= damage
            logger.debug(f"Cover {cover_id} took {damage:.1f} damage, {cover['durability']:.1f} remaining.")
            
            if cover["durability"] <= 0:
                logger.info(f"Cover {cover_id} destroyed.")
                # Remove and emit destroy event
                self._destroy_cover(cover_id)
                return True
        
        return False
    
    def get_protection_factor(self, x: float, y: float) -> float:
        """
        Get protection factor at a position.
        
        Args:
            x (float): X position
            y (float): Y position
            
        Returns:
            float: Protection factor (0.0 to 1.0)
        """
        cover = self.get_cover_at_position(x, y)
        
        if cover:
            return cover["protection"]
        
        return 0.0
    
    def check_line_of_sight(self, x1: float, y1: float, x2: float, y2: float) -> Tuple[bool, float]:
        """
        Check line of sight between two points, considering cover objects.
        
        Args:
            x1, y1: First point coordinates
            x2, y2: Second point coordinates
            
        Returns:
            Tuple[bool, float]: (has_line_of_sight, obstruction_factor)
        """
        # Vector from point 1 to point 2
        dx = x2 - x1
        dy = y2 - y1
        distance = (dx**2 + dy**2)**0.5
        
        if distance == 0:
            return True, 0.0
        
        # Normalize direction vector
        dx /= distance
        dy /= distance
        
        # Check multiple points along the line
        check_points = min(20, int(distance / 10))
        
        for i in range(1, check_points + 1):
            check_dist = distance * i / check_points
            check_x = x1 + dx * check_dist
            check_y = y1 + dy * check_dist
            
            if self.is_position_in_cover(check_x, check_y):
                cover = self.get_cover_at_position(check_x, check_y)
                return False, cover["protection"] if cover else 0.8
        
        return True, 0.0
    
    def check_hazard_effects(self, x: float, y: float) -> List[Dict[str, Any]]:
        """
        Check for hazard effects at a position.
        
        Args:
            x (float): X position
            y (float): Y position
            
        Returns:
            List[Dict]: List of active hazard effects
        """
        active_hazards = []
        
        for hazard in self.hazard_areas.values():
            # Calculate distance to hazard center
            distance = ((x - hazard["x"])**2 + (y - hazard["y"])**2)**0.5
            
            if distance <= hazard["radius"]:
                # Calculate effect intensity based on distance (closer = stronger)
                intensity = 1.0 - (distance / hazard["radius"])
                
                # Add active hazard effect
                effect = {
                    "type": hazard["type"],
                    "effect": hazard["effect"],
                    "damage": hazard["damage"] * intensity,
                    "intensity": intensity
                }
                
                active_hazards.append(effect)
        
        return active_hazards
    
    def update(self, delta_time: float):
        """
        Update hazard durations and remove expired hazards.
        
        Args:
            delta_time (float): Time since the last update (unused currently, but required by SystemManager).
        """
        expired_hazards = []
        for hazard_id, hazard in self.hazard_areas.items():
            if hazard["remaining"] > 0:
                hazard["remaining"] -= 1
            else:
                expired_hazards.append(hazard_id)
        
        for hazard_id in expired_hazards:
            del self.hazard_areas[hazard_id]
    
    def draw(self, renderer):
        """Draw cover objects and hazard areas using the provided Renderer."""
        if not renderer or not renderer.is_initialized():
            # logger.warning("HazardCoverSystem.draw: Renderer not available.")
            return
            
        # Draw cover objects
        for cover_id, cover in self.cover_objects.items():
            color_tuple = cover.get('color', (100, 100, 100))
            color = Color(*color_tuple)
            x = cover['x']
            y = cover['y']
            width = cover['width']
            height = cover['height']
            # Draw rectangle for cover - Use x,y as top-left for rect draw
            renderer.draw_rect(x, y, width, height, color)
            
            # Draw durability bar if destructible
            if cover.get('destructible', False):
                max_hp = cover.get('max_durability', 100)
                current_hp = cover.get('durability', 100)
                hp_pct = current_hp / max_hp if max_hp > 0 else 0
                bar_width = width
                bar_height = 5
                bar_x = x # Align with cover's left edge
                bar_y = y + height + 2 # Position below cover
                renderer.draw_rect(bar_x, bar_y, bar_width, bar_height, Color(50, 50, 50)) # Background
                renderer.draw_rect(bar_x, bar_y, bar_width * hp_pct, bar_height, Color(0, 200, 0)) # Health fill
        
        # Draw hazard areas
        for hazard_id, hazard in self.hazard_areas.items():
            color_tuple = hazard.get('color', (255, 0, 0))
            alpha = hazard.get('alpha', 100) # Get alpha or default
            color = Color(*color_tuple).with_alpha(alpha) # Apply alpha
            x, y = hazard['position']
            radius = hazard['radius']
            # Draw circle for hazard area
            renderer.draw_circle(x, y, radius, color, filled=True)

        # Apply effects of active hazards
        pass # TODO: Apply actual effects like damage over time, slowing, etc. 