import pygame
import math

from .enemy import Enemy, EnemyState # Import base class and state enum

class FastEnemy(Enemy):
    """A faster, more fragile enemy variant."""
    def __init__(self, x, y, screen_width):
        super().__init__(
            x, y, screen_width,
            health=75,          # Lower health
            max_health=75,
            speed=3.5,          # Higher speed
            damage=8,
            points=120,
            chase_range=350,    # Slightly longer chase range
            attack_range=100,   # Shorter attack range (needs to get closer)
            flee_threshold=0.20,# Flees a bit earlier
            shot_cooldown=1500  # Shoots faster
        )
        # Optional: Override state logic if needed
        # def _update_state(self): ...

class TankEnemy(Enemy):
    """A slower, tougher enemy variant."""
    def __init__(self, x, y, screen_width):
        super().__init__(
            x, y, screen_width,
            health=250,         # Higher health
            max_health=250,
            speed=1.0,          # Slower speed
            damage=15,          # Higher damage
            points=200,
            chase_range=250,
            attack_range=120,
            flee_threshold=0.10,# Flees only when very low health
            shot_cooldown=3000  # Shoots slower
        )
        # Adjust visual size (optional, requires draw override or passing size)
        self.width = 40 
        self.height = 40

class SniperEnemy(Enemy):
    """A stationary enemy that attacks from long range."""
    def __init__(self, x, y, screen_width):
        super().__init__(
            x, y, screen_width,
            health=60,          # Low health
            max_health=60,
            speed=0.2,          # Almost stationary, slight repositioning
            damage=30,          # High damage
            points=180,
            chase_range=500,    # Very long detection range
            attack_range=450,   # Long attack range
            flee_threshold=0.30,# Flees earlier due to vulnerability
            shot_cooldown=3500  # Shoots very slowly
        )

    # Override update state to prefer attacking from range
    def _update_state(self):
        """Sniper prefers to stay at range and attack."""
        if self.health / self.max_health < self.flee_threshold:
            self.state = EnemyState.FLEE
            return

        if self.target_player:
            dist_to_player = self._distance_to_target()
            # Attack if within attack range, even if far
            if dist_to_player <= self.attack_range: 
                self.state = EnemyState.ATTACK
            # Chase only if player is within chase range but outside attack range
            elif dist_to_player <= self.chase_range: 
                 # Snipers don't chase aggressively, maybe just turn?
                 # For now, let's transition to ATTACK and let it handle slight movement
                 self.state = EnemyState.ATTACK 
            else:
                self.state = EnemyState.PATROL
                self.target_player = None
        else:
            self.state = EnemyState.PATROL

    # Override chase to prevent actual chasing
    def _update_chase(self):
        """Sniper doesn't chase, remains stationary or repositions slightly."""
        # Minimal movement logic or just face the target
        pass 

    # Override attack to be mostly stationary
    def _update_attack(self):
        """Sniper remains largely stationary while attacking."""
        if not self.target_player: return False
        # Minimal repositioning could be added here if needed
        # Face the target (optional, if angle matters for shooting graphic)
        # dx = self.target_player.x - self.x
        # dy = self.target_player.y - self.y
        # self.angle = math.degrees(math.atan2(-dy, dx))
        return True # Intend to shoot 