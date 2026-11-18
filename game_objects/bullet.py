import pygame
import math
from typing import Optional, Tuple # Added for type hinting

class Bullet:
    def __init__(self, x=0, y=0, angle=0, color=(255, 255, 255), owner=None,
                 damage: float = 10.0, # Added
                 max_range: float = 500.0, # Added
                 speed: float = 7.0, # Added speed param
                 radius: float = 5.0, # Added radius param
                 attacker_start_pos: Optional[Tuple[float, float]] = None, # Added
                 weapon_type: str = "standard", # Added
                 accuracy_mod: float = 1.0,
                 spread_override: Optional[float] = None):
        self.active = False # Start inactive, activated by reset
        # Call reset to initialize all attributes consistently
        self.reset(x=x, y=y, angle=angle, color=color, owner=owner,
                   speed=speed, damage=damage, max_range=max_range, radius=radius,
                   lifetime=180, # Default lifetime
                   attacker_start_pos=attacker_start_pos, weapon_type=weapon_type,
                   accuracy_mod=accuracy_mod, spread_override=spread_override)

    def reset(self, x, y, angle, color, owner=None, speed=7.0, damage=10.0, # Added damage
              max_range=500.0, radius=5.0, # Added max_range, radius
              lifetime=180, # Added lifetime param
              attacker_start_pos: Optional[Tuple[float, float]] = None, # Added
              weapon_type: str = "standard", # Added
              accuracy_mod: float = 1.0,
              spread_override: Optional[float] = None):
        """Reset the bullet's state for reuse from the pool."""
        self.x = x
        self.y = y
        self.start_x = x # Record start position for range check
        self.start_y = y
        self.angle = angle
        self.angle_rad = math.radians(angle) # Store radians for efficiency
        self.color = color
        self.owner = owner
        self.speed = speed
        self.damage = damage # Store damage
        self.max_range_sq = max_range * max_range # Store squared range
        self.radius = radius # Store radius
        self.lifetime = lifetime
        self.active = True
        self.attacker_start_pos = attacker_start_pos # Added assignment
        self.weapon_type = weapon_type # Added assignment
        # Optionally reset damage based on weapon_type from config here
        # self.damage = get_weapon_damage(weapon_type)
        # Reset any other state variables if necessary
        self.accuracy_mod = accuracy_mod
        self.spread_override = spread_override
        return self # Return self for potential chaining

    def move(self):
        # Move bullet based on angle
        # Corrected movement calculation using angle_rad
        self.x += math.cos(self.angle_rad) * self.speed 
        self.y += math.sin(self.angle_rad) * self.speed # Corrected y-direction (assuming y-up or consistent system)
        # Original had: self.y -= math.cos(math.radians(self.angle)) * self.speed
        # And          : self.x += math.sin(math.radians(self.angle)) * self.speed
        # This seems incorrect based on typical angle conventions.
        # Assuming angle=0 points right (positive x), angle=90 points up (positive y)
        
    def draw(self, screen):
        if self.active:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(self.radius))
    
    def update(self):
        """Update bullet position, lifetime, range check, and screen bounds."""
        if not self.active:
            return False
            
        self.move()
        
        # --- ADDED: Screen Bounds Check --- 
        # Fetch screen dimensions (ideally passed in or from a reliable source)
        # Using config as a fallback
        try:
            from config.unified_config import config # Local import
            screen_width = config.display.get('SCREEN_WIDTH', 1280)
            screen_height = config.display.get('SCREEN_HEIGHT', 720)
        except ImportError:
            screen_width = 1280 # Hardcoded fallback
            screen_height = 720

        if self.x < 0 or self.x > screen_width or self.y < 0 or self.y > screen_height:
            self.active = False
            # logger.debug(f"Bullet {id(self)} deactivated due to leaving screen bounds.") # Optional log
            return False
        # --- END ADDED ---

        # Check range
        dist_sq = (self.x - self.start_x)**2 + (self.y - self.start_y)**2
        if dist_sq > self.max_range_sq:
            self.active = False
            return False
            
        # Check lifetime
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.active = False
            return False
            
        # Return True if still active
        return True 

    def check_collision(self, target):
        """Checks collision with a target object (like agent or enemy) using distance."""
        if not self.active or not getattr(target, 'is_alive', True): # Also check if target is alive
            return False
            
        target_x = getattr(target, 'x', None)
        target_y = getattr(target, 'y', None)
        target_radius = getattr(target, 'radius', 0)
        
        if target_x is None or target_y is None:
             return False # Target doesn't have position attributes

        # Distance-based collision check
        dx = self.x - target_x
        dy = self.y - target_y
        distance_sq = dx*dx + dy*dy
        collision_distance = self.radius + target_radius
        
        return distance_sq <= (collision_distance * collision_distance)

    # --- Removed old rect-based collision --- 
    # def check_collision_rect(self, enemy):
    #     # Simple rectangular collision check
    #     if not self.active:
    #         return False
    #     bullet_rect = pygame.Rect(self.x - self.radius, self.y - self.radius, 
    #                             self.radius * 2, self.radius * 2)
    #     enemy_rect = pygame.Rect(enemy.x, enemy.y, enemy.width, enemy.height)
    #     return bullet_rect.colliderect(enemy_rect) 