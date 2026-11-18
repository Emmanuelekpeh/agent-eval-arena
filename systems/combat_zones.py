import pygame
import numpy as np
import random

class CombatZone:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.zones = []
        self.shrink_rate = 0.99
        self.damage_outside = 1
        self.warning_time = 180
        self.next_shrink = 0
        self.safe_zones = []
        self.hazard_zones = []
        
    def create_zone(self, x, y, radius, zone_type='safe'):
        zone = {
            'x': x, 'y': y,
            'radius': radius,
            'type': zone_type,
            'active': True,
            'warning': 0,
            'effect': self._get_zone_effect(zone_type)
        }
        if zone_type == 'safe':
            self.safe_zones.append(zone)
        else:
            self.hazard_zones.append(zone)
    
    def _get_zone_effect(self, zone_type):
        effects = {
            'safe': {'healing': 0.1},
            'damage': {'damage': 0.5},
            'speed': {'boost': 1.5},
            'energy': {'regen': 0.2}
        }
        return effects.get(zone_type, {})
    
    def update(self):
        self.next_shrink -= 1
        if self.next_shrink <= 0:
            for zone in self.safe_zones + self.hazard_zones:
                if zone['active']:
                    zone['radius'] *= self.shrink_rate
                    if zone['radius'] < 10:
                        zone['active'] = False
            self.next_shrink = 60
    
    def check_player_in_zone(self, x, y):
        effects = {'damage': 0, 'healing': 0, 'boost': 1.0, 'regen': 0}
        
        for zone in self.safe_zones + self.hazard_zones:
            if not zone['active']:
                continue
                
            dist = np.sqrt((x - zone['x'])**2 + (y - zone['y'])**2)
            if dist <= zone['radius']:
                for effect_type, value in zone['effect'].items():
                    effects[effect_type] += value
        
        return effects
    
    def draw(self, screen):
        for zone in self.safe_zones:
            if zone['active']:
                pygame.draw.circle(screen, (0, 255, 0, 128), 
                                (int(zone['x']), int(zone['y'])), 
                                int(zone['radius']), 2)
                
        for zone in self.hazard_zones:
            if zone['active']:
                pygame.draw.circle(screen, (255, 0, 0, 128),
                                (int(zone['x']), int(zone['y'])),
                                int(zone['radius']), 2)
