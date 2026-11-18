import pygame
import numpy as np
import random
from opensimplex import OpenSimplex
from systems.visualization.visualization_system import Color

class TerrainSystem:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.noise = OpenSimplex(seed=random.randint(0, 1000000))
        self.grid_size = 32
        self.terrain_types = {
            'grass': {'color': (34, 139, 34), 'speed_mod': 1.0},
            'water': {'color': (0, 119, 190), 'speed_mod': 0.6},
            'sand': {'color': (238, 214, 175), 'speed_mod': 0.8},
            'rock': {'color': (139, 137, 137), 'speed_mod': 0.7}
        }
        self.terrain_map = self._generate_terrain()
        self.destructible_map = np.ones((width//self.grid_size, height//self.grid_size))

    def _generate_terrain(self):
        terrain = np.zeros((self.width//self.grid_size, self.height//self.grid_size), dtype=object)
        for x in range(terrain.shape[0]):
            for y in range(terrain.shape[1]):
                value = self.noise.noise2(x/10, y/10)
                if value < -0.2:
                    terrain[x,y] = 'water'
                elif value < 0.1:
                    terrain[x,y] = 'sand'
                elif value < 0.5:
                    terrain[x,y] = 'grass'
                else:
                    terrain[x,y] = 'rock'
        return terrain
    
    def get_movement_modifier(self, x, y):
        """
        Get movement speed modifier for the terrain at the given position.
        
        Args:
            x (float): X position
            y (float): Y position
            
        Returns:
            float: Movement speed modifier (0.0-1.0)
        """
        # Convert world position to grid coordinates
        grid_x = int(x // self.grid_size)
        grid_y = int(y // self.grid_size)
        
        # Ensure coordinates are within bounds
        if 0 <= grid_x < self.terrain_map.shape[0] and 0 <= grid_y < self.terrain_map.shape[1]:
            terrain_type = self.terrain_map[grid_x, grid_y]
            return self.terrain_types.get(terrain_type, {}).get('speed_mod', 1.0)
        
        # Default to normal speed for out of bounds
        return 1.0
    
    def is_destructible(self, x, y):
        """
        Check if the terrain at the given position is destructible.
        
        Args:
            x (float): X position
            y (float): Y position
            
        Returns:
            bool: True if destructible, False otherwise
        """
        grid_x = int(x // self.grid_size)
        grid_y = int(y // self.grid_size)
        
        if 0 <= grid_x < self.destructible_map.shape[0] and 0 <= grid_y < self.destructible_map.shape[1]:
            return bool(self.destructible_map[grid_x, grid_y])
        
        return False
    
    def update(self, delta_time):
        """Update the terrain state (placeholder for future dynamic terrain)."""
        pass # Currently, terrain is static after generation
    
    def draw(self, renderer):
        """
        Draw the terrain on the screen using the provided Renderer.
        
        Args:
            renderer: The Renderer instance to use for drawing.
        """
        if not renderer or not renderer.is_initialized():
             # logger.warning("TerrainSystem.draw: Renderer not available or not initialized.") # Reduce noise
             return

        for x in range(self.terrain_map.shape[0]):
            for y in range(self.terrain_map.shape[1]):
                terrain_type = self.terrain_map[x, y]
                color_tuple = self.terrain_types.get(terrain_type, {}).get('color', (100, 100, 100))
                color = Color(*color_tuple) # Create Color object
                
                rect_x = x * self.grid_size
                rect_y = y * self.grid_size

                # Use renderer.draw_rect (assumes world space coordinates)
                renderer.draw_rect(
                    rect_x, rect_y, self.grid_size, self.grid_size,
                    color,
                    filled=True,
                    is_world_space=True # Explicitly state world space
                )
                
                # Add grid lines for visibility using renderer
                grid_color = Color(50, 50, 50, 150) # Slightly transparent grid
                renderer.draw_rect(
                    rect_x, rect_y, self.grid_size, self.grid_size,
                    grid_color,
                    filled=False, # Draw outline only
                    is_world_space=True
                )
