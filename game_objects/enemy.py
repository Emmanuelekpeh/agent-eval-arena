import pygame
import math
import random
from enum import Enum, auto

# Assume Player class might be needed for type hinting
# from .player import Player # Could cause circular import if Player imports Enemy

class EnemyState(Enum):
    PATROL = auto()
    CHASE = auto()
    ATTACK = auto()
    FLEE = auto()

class Enemy:
    def __init__(self, x, y, screen_width,
                 health=100, max_health=100, speed=2, 
                 damage=10, points=100, 
                 chase_range=300, attack_range=150, flee_threshold=0.25,
                 shot_cooldown=2000): 
        self.x = x
        self.y = y
        self.width = 30
        self.height = 30
        self.speed = speed
        self.screen_width = screen_width
        
        self.health = health
        self.max_health = max_health
        self.damage = damage
        self.points = points
        self.is_alive = True

        # Behavior parameters
        self.state = EnemyState.PATROL
        self.chase_range = chase_range
        self.attack_range = attack_range
        self.flee_threshold = flee_threshold # Flee when health % is below this
        self.target_player = None  # Reference to the Player object being targeted
        self.patrol_target_x = random.randint(50, screen_width - 50)
        self.direction = random.choice([-1, 1]) # For patrol movement

        # Combat parameters
        self.last_shot_time = 0
        self.shot_cooldown = shot_cooldown 

        # Environment reference (set externally)
        self.env = None 

    def update(self):
        """Update enemy state and behavior based on the state machine."""
        if not self.is_alive: 
            return False # No updates if not alive

        # 1. Update Target
        self.find_nearest_living_player()

        # 2. State Transitions
        self._update_state()

        # 3. Execute Behavior based on State
        should_shoot = False
        if self.state == EnemyState.PATROL:
            self._update_patrol()
        elif self.state == EnemyState.CHASE:
            self._update_chase()
        elif self.state == EnemyState.ATTACK:
            should_shoot = self._update_attack()
        elif self.state == EnemyState.FLEE:
            self._update_flee()
        
        # 4. Shooting Logic (independent of state, based on cooldown)
        can_shoot_now = self._can_shoot()
        
        # Return True if the enemy intends to shoot based on its state AND cooldown allows
        return should_shoot and can_shoot_now

    def _update_state(self):
        """Determine the current state based on health and player proximity."""
        if self.health / self.max_health < self.flee_threshold:
            self.state = EnemyState.FLEE
            return

        if self.target_player:
            dist_to_player = self._distance_to_target()
            if dist_to_player <= self.attack_range:
                self.state = EnemyState.ATTACK
            elif dist_to_player <= self.chase_range:
                self.state = EnemyState.CHASE
            else:
                self.state = EnemyState.PATROL
                self.target_player = None # Stop targeting if player is too far
        else:
            self.state = EnemyState.PATROL

    def _update_patrol(self):
        """Default behavior: Move horizontally or towards a random point."""
        # Simple horizontal patrol for now
        self.x += self.speed * 0.5 * self.direction # Slower patrol
        if self.x <= 0 or self.x >= self.screen_width - self.width:
            self.direction *= -1
            # Optional: Move down slightly when hitting edge
            # self.y += 20 

    def _update_chase(self):
        """Move towards the target player."""
        if not self.target_player: return

        dx = self.target_player.x - self.x
        dy = self.target_player.y - self.y
        dist = math.hypot(dx, dy)
        
        if dist > self.attack_range: # Move closer only if outside attack range
            if dist > 0:
                self.x += (dx / dist) * self.speed
                self.y += (dy / dist) * self.speed
        # If inside attack range but state is CHASE, maybe move slightly to reposition?
        # Or just let the state transition to ATTACK handle it.

    def _update_attack(self):
        """Maintain optimal distance and attempt to shoot."""
        if not self.target_player: return False

        dist_to_player = self._distance_to_target()
        ideal_distance = self.attack_range * 0.8 # Try to stay slightly inside range

        # Optional: Add slight repositioning to avoid being static
        if abs(dist_to_player - ideal_distance) > 20: # If too far or too close
             dx = self.target_player.x - self.x
             dy = self.target_player.y - self.y
             if dist_to_player > 0:
                  # Move closer if too far, move away if too close
                  move_direction = 1 if dist_to_player > ideal_distance else -1
                  self.x += (dx / dist_to_player) * self.speed * 0.3 * move_direction
                  self.y += (dy / dist_to_player) * self.speed * 0.3 * move_direction
        
        # Indicate intention to shoot
        return True 

    def _update_flee(self):
        """Move away from the target player."""
        if not self.target_player: 
            # If no target while fleeing, switch back to patrol
            self.state = EnemyState.PATROL
            return

        dx = self.x - self.target_player.x # Reverse direction
        dy = self.y - self.target_player.y
        dist = math.hypot(dx, dy)
        
        if dist > 0:
            # Move away at slightly increased speed
            flee_speed = self.speed * 1.2
            self.x += (dx / dist) * flee_speed
            self.y += (dy / dist) * flee_speed
            
            # Boundary checks (simple clamp)
            self.x = max(0, min(self.screen_width - self.width, self.x))
            self.y = max(0, min(self.screen_width - self.height, self.y)) # Assume square screen for now, fix later
            
    def _can_shoot(self) -> bool:
        """Check if the shot cooldown has passed."""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_shot_time >= self.shot_cooldown:
            self.last_shot_time = current_time # Reset timer IF shooting occurs (handled by caller)
            return True
        return False

    def _distance_to_target(self) -> float:
         """Calculate distance to the current target player."""
         if not self.target_player: return float('inf')
         return math.hypot(self.target_player.x - self.x, self.target_player.y - self.y)

    def draw(self, screen, color):
        """Draw the enemy rectangle."""
        if not self.is_alive: return
        pygame.draw.rect(screen, color, (self.x, self.y, self.width, self.height))
        # Optional: Draw state indicator or health bar
        # ...

    def find_nearest_living_player(self):
        """Find the closest living player from the environment's agent list."""
        # Ensure env and agents list exist
        if not self.env or not hasattr(self.env, 'agents') or not self.env.agents:
            self.target_player = None
            return
        
        nearest_player_obj = None
        min_dist_sq = float('inf')
        
        for agent_data in self.env.agents.values():
            # Get the Player object associated with the agent
            player_obj = agent_data.get('player')
            
            # Check if it's a valid, living Player object
            if player_obj and getattr(player_obj, 'is_alive', False):
                dx = player_obj.x - self.x
                dy = player_obj.y - self.y
                dist_sq = dx*dx + dy*dy
                
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    nearest_player_obj = player_obj
        
        self.target_player = nearest_player_obj

    def take_damage(self, amount: float):
         """Applies damage to the enemy, checks for death."""
         if not self.is_alive: return
         self.health -= amount
         if self.health <= 0:
              self.health = 0
              self.is_alive = False
              # TODO: Emit death event or handle death logic here or in Environment
              print(f"Enemy at ({self.x:.0f}, {self.y:.0f}) died!") 