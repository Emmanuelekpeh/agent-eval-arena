import pygame
import math
from typing import Tuple, List

# Assuming Bullet class exists in the same directory
from .bullet import Bullet 
# Assuming ObjectPool is available
from systems.utils.object_pool import ObjectPool 

class Player:
    """Represents the player entity in the game."""
    
    def __init__(self, 
                 x: float, 
                 y: float, 
                 color: Tuple[int, int, int],
                 screen_width: int, 
                 screen_height: int,
                 bullet_color: Tuple[int, int, int] = (255, 255, 255),
                 health_color: Tuple[int, int, int] = (0, 255, 0),
                 energy_color: Tuple[int, int, int] = (0, 200, 255),
                 indicator_color: Tuple[int, int, int] = (255, 255, 255),
                 hit_color: Tuple[int, int, int] = (255, 0, 0),
                 radius: int = 15,
                 speed: int = 5,
                 initial_health: int = 100,
                 initial_energy: int = 100,
                 shot_cooldown_ms: int = 500,
                 energy_cost_shoot: int = 10,
                 invulnerable_duration_ms: int = 1000,
                 name: str = "Player"):
        """
        Initialize the Player.

        Args:
            x, y: Initial position.
            color: Base color of the player.
            screen_width, screen_height: Dimensions for boundary checks.
            bullet_color: Color for bullets fired by this player.
            health_color: Color for the health bar fill.
            energy_color: Color for the energy bar fill.
            indicator_color: Color for the direction indicator.
            hit_color: Color to flash when hit.
            radius: Player radius.
            speed: Player movement speed.
            initial_health: Starting health.
            initial_energy: Starting energy.
            shot_cooldown_ms: Cooldown between shots in milliseconds.
            energy_cost_shoot: Energy consumed per shot.
            invulnerable_duration_ms: Invulnerability time after being hit.
            name: Player's name identifier.
        """
        self.name = name
        self.x = x
        self.y = y
        self.radius = radius
        self.speed = speed
        self.color = color
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        self.angle = 0  # Angle in degrees for orientation
        self.rotation = 0 # Explicit rotation property (synced with angle)
        
        self.health = initial_health
        self.max_health = initial_health
        self.energy = initial_energy
        self.max_energy = initial_energy
        
        self.last_shot_time = 0
        self.shot_cooldown = shot_cooldown_ms
        self.energy_cost_shoot = energy_cost_shoot
        
        self.invulnerable_until = 0 # Timestamp until invulnerable
        self.invulnerable_duration = invulnerable_duration_ms
        
        self.is_alive = True
        self.hit_flash_timer = 0 # Visual feedback timer (frames)
        
        # Store colors for drawing
        self.bullet_color = bullet_color
        self.health_color = health_color
        self.energy_color = energy_color
        self.indicator_color = indicator_color
        self.hit_color = hit_color
        
        # Bullet Management (using ObjectPool)
        # Assuming the pool is created externally and passed, or created here
        self.bullet_pool = ObjectPool(Bullet, initial_size=10, max_size=50)
        self.active_bullets: List[Bullet] = []

    def move(self, dx: float, dy: float):
        """
        Update player position based on direction vector (dx, dy).
        Enforces screen boundaries. Updates rotation based on movement.
        """
        if not self.is_alive: return

        # Normalize direction vector if needed (allows diagonal movement at same speed)
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 0:
            dx /= dist
            dy /= dist
            
        new_x = self.x + dx * self.speed
        new_y = self.y + dy * self.speed
        
        # Keep player within screen bounds using stored dimensions
        self.x = max(self.radius, min(self.screen_width - self.radius, new_x))
        self.y = max(self.radius, min(self.screen_height - self.radius, new_y))
        
        # Update angle based on movement direction if there was movement
        if dx != 0 or dy != 0:
            self.rotation = math.degrees(math.atan2(dx, -dy))
            self.angle = self.rotation # Sync angle with rotation

    def shoot(self):
        """Attempt to fire a bullet if cooldown allows and energy permits."""
        if not self.is_alive: return

        current_time = pygame.time.get_ticks()
        if (current_time - self.last_shot_time >= self.shot_cooldown and 
            self.energy >= self.energy_cost_shoot):
            
            # Get a bullet from the pool
            bullet = self.bullet_pool.get()
            
            if bullet:
                # Calculate spawn position slightly ahead of the player
                spawn_x = self.x + math.sin(math.radians(self.angle)) * (self.radius + bullet.radius)
                spawn_y = self.y - math.cos(math.radians(self.angle)) * (self.radius + bullet.radius)
                
                # Reset the bullet's state
                bullet.reset(
                    x=spawn_x, 
                    y=spawn_y, 
                    angle=self.angle, 
                    color=self.bullet_color, 
                    owner=self.name # Pass owner identifier
                )
                self.active_bullets.append(bullet)
                self.last_shot_time = current_time
                self.energy -= self.energy_cost_shoot
                # Return the newly activated bullet if needed by the caller
                return bullet 
            else:
                # Pool might be exhausted
                print(f"Warning: Bullet pool exhausted for {self.name}")
                pass 
        return None # No bullet fired

    def update(self):
        """Update player state, including bullets and timers."""
        if not self.is_alive: return

        # Update hit flash timer
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= 1
            
        # Update active bullets
        bullets_to_remove = []
        for bullet in self.active_bullets:
            if not bullet.update(): # Bullet.update returns False if lifetime ends
                bullets_to_remove.append(bullet)
            # Optional: Check screen boundaries here too, or rely on Bullet's update
            elif (bullet.x < 0 or bullet.x > self.screen_width or
                  bullet.y < 0 or bullet.y > self.screen_height):
                  bullets_to_remove.append(bullet)

        # Release inactive/off-screen bullets back to the pool
        for bullet in bullets_to_remove:
            if bullet in self.active_bullets: # Check if not already removed
                self.active_bullets.remove(bullet)
                self.bullet_pool.release(bullet)

        # Regenerate energy slowly
        self.energy = min(self.max_energy, self.energy + 0.05) # Very slow regen

    def take_damage(self, amount: float) -> bool:
        """
        Apply damage to the player if not invulnerable. Updates health and alive status.
        Triggers hit flash effect.
        
        Args:
            amount: The amount of damage to take.
            
        Returns:
            bool: True if damage was applied, False if invulnerable.
        """
        if not self.is_alive: return False

        current_time = pygame.time.get_ticks()
        if current_time > self.invulnerable_until:
            self.health = max(0, self.health - amount)
            self.invulnerable_until = current_time + self.invulnerable_duration
            self.hit_flash_timer = 10 # Flash for 10 frames
            
            if self.health <= 0:
                self.is_alive = False
                # Optional: Add logic here for death effects or scoring
            return True
        return False

    def rotate(self, direction: int):
        """
        Rotate the player left (-1) or right (1).
        
        Args:
            direction: -1 for left, 1 for right.
        """
        if not self.is_alive: return

        rotation_speed = 15 # Degrees per call
        self.angle = (self.angle + direction * rotation_speed) % 360
        self.rotation = self.angle # Keep rotation property synced

    def draw(self, screen: pygame.Surface):
        """Draw the player and associated UI elements on the screen."""
        if not self.is_alive: return

        # Determine color based on hit flash
        current_color = self.hit_color if self.hit_flash_timer > 0 else self.color
        
        # Draw player circle
        pygame.draw.circle(screen, current_color, (int(self.x), int(self.y)), self.radius)
        
        # Draw direction indicator
        end_x = self.x + math.sin(math.radians(self.angle)) * self.radius
        end_y = self.y - math.cos(math.radians(self.angle)) * self.radius
        pygame.draw.line(screen, self.indicator_color, 
                        (int(self.x), int(self.y)), 
                        (int(end_x), int(end_y)), 3)
        
        # --- Draw Health Bar ---
        bar_width = 40
        bar_height = 5
        bar_x = self.x - bar_width // 2
        health_bar_y = self.y - self.radius - 15 # Position above player
        
        # Background (e.g., grey)
        pygame.draw.rect(screen, (50, 50, 50), 
                        (bar_x, health_bar_y, bar_width, bar_height))
        # Health fill
        health_fill_width = max(0, bar_width * (self.health / self.max_health))
        pygame.draw.rect(screen, self.health_color,
                        (bar_x, health_bar_y, health_fill_width, bar_height))
        
        # --- Draw Energy Bar ---
        energy_bar_y = health_bar_y + bar_height + 2 # Position below health bar
        
        # Background
        pygame.draw.rect(screen, (50, 50, 50), 
                        (bar_x, energy_bar_y, bar_width, bar_height))
        # Energy fill
        energy_fill_width = max(0, bar_width * (self.energy / self.max_energy))
        pygame.draw.rect(screen, self.energy_color,
                        (bar_x, energy_bar_y, energy_fill_width, bar_height))

        # Draw active bullets associated with this player
        # Note: Usually, the main game loop/environment handles drawing all bullets
        # But if Player needs to draw its own bullets, do it here:
        # for bullet in self.active_bullets:
        #     bullet.draw(screen) 