import pygame
import numpy as np
import random
from opensimplex import OpenSimplex
import math

class Terrain:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.noise = OpenSimplex()
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
        terrain = np.zeros((self.width//self.grid_size, self.height//self.grid_size), dtype=str)
        for x in range(terrain.shape[0]):
            for y in range(terrain.shape[1]):
                value = self.noise.noise2d(x/10, y/10)
                if value < -0.2:
                    terrain[x,y] = 'water'
                elif value < 0.1:
                    terrain[x,y] = 'sand'
                elif value < 0.5:
                    terrain[x,y] = 'grass'
                else:
                    terrain[x,y] = 'rock'
        return terrain

class WeatherSystem:
    def __init__(self):
        self.conditions = ['clear', 'rain', 'fog', 'storm']
        self.current = 'clear'
        self.intensity = 0.0
        self.transition_time = 0
        self.particles = []
        
    def update(self):
        if random.random() < 0.001:
            self.change_weather()
            
    def get_visibility(self):
        return {
            'clear': 1.0,
            'rain': 0.7,
            'fog': 0.4,
            'storm': 0.3
        }.get(self.current, 1.0) * (1 - self.intensity * 0.5)

class TimeSystem:
    def __init__(self):
        self.time = 0
        self.day_length = 3600
        self.lighting = 1.0
        
    def update(self):
        self.time = (self.time + 1) % self.day_length
        self.lighting = 0.3 + 0.7 * math.sin(math.pi * self.time / self.day_length)

class Environment:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.terrain = Terrain(width, height)
        self.weather = WeatherSystem()
        self.time = TimeSystem()
        self.hazards = []
        self.spawn_points = []
        self.update_interval = 60  # Update every second at 60 FPS
        
    def update(self):
        self.weather.update()
        self.time.update()
        self._update_hazards()
        
    def get_terrain_modifier(self, x, y):
        return self.terrain.get_movement_modifier(x, y)
        
    def get_visibility(self):
        return self.weather.get_visibility() * self.time.get_lighting()
    
    def _update_hazards(self):
        # Update environmental hazards
        pass
