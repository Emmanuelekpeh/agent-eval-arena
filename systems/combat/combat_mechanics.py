class PowerUpSystem:
    def __init__(self):
        self.powerups = {
            'damage_boost': {'duration': 300, 'multiplier': 1.5},
            'speed_boost': {'duration': 240, 'multiplier': 1.3},
            'shield_boost': {'duration': 180, 'capacity': 50},
            'energy_boost': {'duration': 120, 'amount': 100}
        }

class AdvancedComboSystem:
    def __init__(self):
        self.combo_patterns = {
            'rapid_fire': {'hits': 3, 'time_window': 60, 'bonus': 1.5},
            'precision': {'accuracy': 0.8, 'hits': 2, 'bonus': 2.0},
            'team_combo': {'ally_hits': 2, 'bonus': 2.5}
        }

class TeamAbilitySystem:
    def __init__(self):
        self.shared_cooldowns = {}
        self.team_abilities = {
            'shield_wall': {'energy': 50, 'duration': 180},
            'coordinated_strike': {'energy': 40, 'damage_bonus': 2.0},
            'energy_transfer': {'cost': 30, 'efficiency': 0.8}
        }