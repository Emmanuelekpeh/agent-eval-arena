import random
import math
import pygame

class WeaponSystem:
    def __init__(self):
        self.weapons = {
            'standard': {
                'damage': 10,
                'speed': 7,
                'energy_cost': 10,
                'cooldown': 500,
                'spread': 0
            },
            'shotgun': {
                'damage': 8,
                'speed': 6,
                'energy_cost': 25,
                'cooldown': 1000,
                'spread': 30,
                'pellets': 5
            },
            'sniper': {
                'damage': 25,
                'speed': 12,
                'energy_cost': 35,
                'cooldown': 1500,
                'spread': 0
            },
            'rapid': {
                'damage': 5,
                'speed': 8,
                'energy_cost': 5,
                'cooldown': 250,
                'spread': 5
            }
        }

    def apply_weapon_effects(self, weapon_type, damage):
        effects = {
            'standard': {'knockback': 0, 'stun': 0},
            'shotgun': {'knockback': 5, 'stun': 0.1},
            'sniper': {'knockback': 10, 'stun': 0.3},
            'rapid': {'knockback': 1, 'stun': 0}
        }
        return damage * (1 + effects[weapon_type].get('stun', 0)), effects[weapon_type]

class ComboSystem:
    def __init__(self):
        self.combos = {}
        self.max_combo = 8
        self.combo_timeout = 180  # 3 seconds at 60 FPS
        
    def add_hit(self, player_name, hit_type='normal'):
        if player_name not in self.combos:
            self.combos[player_name] = {
                'count': 0,
                'timer': 0,
                'multiplier': 1.0
            }
        
        combo = self.combos[player_name]
        combo['count'] += 1
        combo['timer'] = self.combo_timeout
        combo['multiplier'] = min(self.max_combo, 1.0 + (combo['count'] * 0.2))
        
    def update(self):
        for player_name in list(self.combos.keys()):
            combo = self.combos[player_name]
            combo['timer'] -= 1
            if combo['timer'] <= 0:
                combo['count'] = 0
                combo['multiplier'] = 1.0

class ShieldSystem:
    def __init__(self):
        self.shields = {}
        
    def add_shield(self, player_name, capacity=50):
        self.shields[player_name] = {
            'current': capacity,
            'max': capacity,
            'regen_rate': 0.1,
            'regen_delay': 60,
            'regen_timer': 0
        }
    
    def update(self, delta_time: float = 0.0):
        for shield in self.shields.values():
            if shield['regen_timer'] > 0:
                shield['regen_timer'] -= 1
            elif shield['current'] < shield['max']:
                shield['current'] = min(
                    shield['max'], 
                    shield['current'] + shield['regen_rate']
                )
    
    def take_damage(self, player_name, damage):
        if player_name not in self.shields:
            return damage
            
        shield = self.shields[player_name]
        shield_damage = min(shield['current'], damage)
        remaining_damage = damage - shield_damage
        
        shield['current'] -= shield_damage
        shield['regen_timer'] = shield['regen_delay']
        
        return remaining_damage

    def handle_shield_collision(self, shield, damage_type):
        modifiers = {
            'energy': 1.5,    # Shields strong against energy
            'physical': 0.8,  # Weak against physical
            'explosive': 0.5  # Very weak against explosive
        }
        return shield * modifiers.get(damage_type, 1.0)
