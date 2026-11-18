import pygame
import sys
import os
import random
import math
import logging
import time
from pygame import gfxdraw

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
BACKGROUND = (10, 10, 20)

class SimpleEntity:
    """A simple entity class for rendering tests"""
    def __init__(self, entity_id, position, radius, color):
        self.id = entity_id
        self.position = position  # (x, y) tuple
        self.radius = radius
        self.color = color
        self.visible = True
        self.pulse_factor = random.uniform(0, 2*math.pi)  # Random starting point for pulse
        self.pulse_speed = random.uniform(0.02, 0.05)     # How fast it pulses
        self.alpha = random.randint(180, 255)             # Base alpha for glow effect
        self.original_radius = radius                     # Store original radius for animations
        self.target_radius = radius                       # Target radius for animations
        self.x_vel = random.uniform(-0.1, 0.1)            # X velocity for subtle movement
        self.y_vel = random.uniform(-0.1, 0.1)            # Y velocity for subtle movement
    
    def update(self, time_delta):
        """Update entity animation"""
        # Update pulse animation
        self.pulse_factor += self.pulse_speed
        pulse = math.sin(self.pulse_factor) * 0.2 + 0.8  # Pulse between 0.6 and 1.0
        
        # Animate radius toward target
        self.radius += (self.target_radius - self.radius) * 0.1
        
        # Add subtle movement
        self.position = (
            self.position[0] + self.x_vel,
            self.position[1] + self.y_vel
        )
        
        # Bounce off screen edges
        if self.position[0] < self.radius or self.position[0] > 800 - self.radius:
            self.x_vel *= -1
        if self.position[1] < self.radius or self.position[1] > 600 - self.radius:
            self.y_vel *= -1
        
        return pulse
    
    def render(self, surface):
        """Render the entity as a circle with glow effect"""
        if not self.visible:
            return
            
        # Calculate pulsing effect
        pulse = self.update(None)
        current_radius = max(1, int(self.radius * pulse))
        
        # Create color with alpha for glow effect
        base_color = self.color
        r, g, b = base_color
        
        # Draw antialiased circle
        gfxdraw.aacircle(surface, int(self.position[0]), int(self.position[1]), current_radius, base_color)
        gfxdraw.filled_circle(surface, int(self.position[0]), int(self.position[1]), current_radius, base_color)
        
        # Draw inner glow
        inner_radius = max(1, current_radius - 2)
        inner_color = (min(255, r+50), min(255, g+50), min(255, b+50))
        gfxdraw.aacircle(surface, int(self.position[0]), int(self.position[1]), inner_radius, inner_color)
        gfxdraw.filled_circle(surface, int(self.position[0]), int(self.position[1]), inner_radius, inner_color)
            
class SimpleEntityRenderer:
    """A stripped-down renderer that only handles simple entities"""
    def __init__(self, screen):
        self.screen = screen
        self.entities = {}
        self.transition_progress = 1.0  # 0.0 to 1.0, 1.0 means no transition
        self.transition_speed = 0.05
        
    def add_entity(self, entity):
        """Add an entity to be rendered"""
        self.entities[entity.id] = entity
        
    def remove_entity(self, entity_id):
        """Remove an entity"""
        if entity_id in self.entities:
            del self.entities[entity_id]
            
    def clear_entities(self):
        """Remove all entities"""
        self.entities.clear()
    
    def start_transition(self):
        """Start a transition effect"""
        self.transition_progress = 0.0
        
    def update(self):
        """Update transition animations"""
        if self.transition_progress < 1.0:
            self.transition_progress += self.transition_speed
            if self.transition_progress > 1.0:
                self.transition_progress = 1.0
        
    def render(self):
        """Render all entities"""
        # Apply transition effect to all entities
        for entity in self.entities.values():
            if self.transition_progress < 1.0:
                # Scale radius based on transition progress
                entity.target_radius = entity.original_radius * self.transition_progress
            else:
                entity.target_radius = entity.original_radius
            
            # Render the entity
            entity.render(self.screen)
            
    def get_entity_count(self):
        """Get count of entities"""
        return len(self.entities)

class TestStageManager:
    """Manages different test stages for rendering performance testing"""
    def __init__(self, screen_width, screen_height, renderer):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.renderer = renderer
        self.current_stage = 0
        self.stages = [
            "Empty",
            "Basic (5 entities)",
            "Circle Pattern (50 entities)",
            "Grid Pattern (100 entities)",
            "Random Scatter (200 entities)",
            "Random Scatter (500 entities)",
            "Random Scatter (1000 entities)"
        ]
    
    def load_stage(self, stage_index):
        """Load a specific stage by index"""
        if 0 <= stage_index < len(self.stages):
            self.current_stage = stage_index
            self.renderer.clear_entities()
            self.renderer.start_transition()
            
            if stage_index == 0:  # Empty
                pass  # No entities to add
            elif stage_index == 1:  # Basic (5 entities)
                self._create_basic_entities(5)
            elif stage_index == 2:  # Circle Pattern
                self._create_circle_pattern_entities(50)
            elif stage_index == 3:  # Grid Pattern
                self._create_grid_pattern_entities(100)
            elif stage_index == 4:  # Random Scatter (200)
                self._create_random_scatter_entities(200)
            elif stage_index == 5:  # Random Scatter (500)
                self._create_random_scatter_entities(500)
            elif stage_index == 6:  # Random Scatter (1000)
                self._create_random_scatter_entities(1000)
            
            logger.info(f"Loaded stage {stage_index}: {self.stages[stage_index]} with {self.renderer.get_entity_count()} entities")
            return True
        return False
    
    def load_next_stage(self):
        """Load the next stage in sequence"""
        return self.load_stage((self.current_stage + 1) % len(self.stages))
    
    def load_previous_stage(self):
        """Load the previous stage in sequence"""
        return self.load_stage((self.current_stage - 1) % len(self.stages))
    
    def _create_basic_entities(self, count):
        """Create a few basic entities in the center of the screen"""
        colors = [RED, GREEN, BLUE, YELLOW, CYAN]
        for i in range(count):
            angle = (i / count) * 2 * math.pi
            x = self.screen_width // 2 + int(100 * math.cos(angle))
            y = self.screen_height // 2 + int(100 * math.sin(angle))
            color = colors[i % len(colors)]
            entity = SimpleEntity(f"entity_{i}", (x, y), 20, color)
            self.renderer.add_entity(entity)
    
    def _create_circle_pattern_entities(self, count):
        """Create entities arranged in a circle pattern"""
        for i in range(count):
            angle = (i / count) * 2 * math.pi
            radius = 200
            x = self.screen_width // 2 + int(radius * math.cos(angle))
            y = self.screen_height // 2 + int(radius * math.sin(angle))
            
            # Create gradient colors around the circle
            hue = int(i / count * 360)
            color = self._hsv_to_rgb(hue, 0.8, 1.0)
            
            entity = SimpleEntity(f"entity_{i}", (x, y), 10, color)
            self.renderer.add_entity(entity)
    
    def _create_grid_pattern_entities(self, count):
        """Create entities arranged in a grid pattern"""
        grid_size = int(math.sqrt(count))
        spacing_x = self.screen_width // (grid_size + 1)
        spacing_y = self.screen_height // (grid_size + 1)
        
        for i in range(grid_size):
            for j in range(grid_size):
                x = spacing_x * (i + 1)
                y = spacing_y * (j + 1)
                
                # Create gradient colors across the grid
                hue = int((i / grid_size + j / grid_size) * 180)
                color = self._hsv_to_rgb(hue, 0.8, 1.0)
                
                entity = SimpleEntity(f"entity_{i*grid_size+j}", (x, y), 8, color)
                self.renderer.add_entity(entity)
    
    def _create_random_scatter_entities(self, count):
        """Create randomly scattered entities"""
        for i in range(count):
            x = random.randint(20, self.screen_width - 20)
            y = random.randint(20, self.screen_height - 20)
            radius = random.randint(5, 15)
            
            # Use HSV color space for more vibrant colors
            hue = random.randint(0, 360)
            sat = random.uniform(0.7, 1.0)
            val = random.uniform(0.7, 1.0)
            color = self._hsv_to_rgb(hue, sat, val)
            
            entity = SimpleEntity(f"entity_{i}", (x, y), radius, color)
            self.renderer.add_entity(entity)
    
    def _hsv_to_rgb(self, h, s, v):
        """Convert HSV color values to RGB"""
        h = h % 360
        h_i = int(h / 60)
        f = h / 60 - h_i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        
        if h_i == 0:
            r, g, b = v, t, p
        elif h_i == 1:
            r, g, b = q, v, p
        elif h_i == 2:
            r, g, b = p, v, t
        elif h_i == 3:
            r, g, b = p, q, v
        elif h_i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q
        
        return (int(r * 255), int(g * 255), int(b * 255))

class UIManager:
    """Manages UI elements and visual effects"""
    def __init__(self, screen, width, height):
        self.screen = screen
        self.width = width
        self.height = height
        self.title_font = pygame.font.SysFont("Arial", 24, bold=True)
        self.info_font = pygame.font.SysFont("Arial", 18)
        self.controls_font = pygame.font.SysFont("Arial", 16)
        
        # Pre-render the icon
        self.icon = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(self.icon, YELLOW, (16, 16), 14)
        pygame.draw.circle(self.icon, BLACK, (16, 16), 14, 2)
        pygame.draw.circle(self.icon, BLACK, (10, 10), 3)
        pygame.draw.circle(self.icon, BLACK, (22, 10), 3)
        pygame.draw.arc(self.icon, BLACK, (8, 12, 16, 16), 0, math.pi, 2)
        
        # Set the window icon
        pygame.display.set_icon(self.icon)
    
    def render(self, fps, stage_name, entity_count):
        # Render the background gradient
        self._render_background()
        
        # Render FPS counter with color based on performance
        if fps > 55:
            fps_color = GREEN
        elif fps > 30:
            fps_color = YELLOW
        else:
            fps_color = RED
        fps_text = self.title_font.render(f"FPS: {fps:.1f}", True, fps_color)
        self.screen.blit(fps_text, (10, 10))
        
        # Render stage info
        stage_text = self.title_font.render(f"Stage: {stage_name}", True, WHITE)
        self.screen.blit(stage_text, (10, 40))
        
        # Render entity count
        entities_text = self.title_font.render(f"Entities: {entity_count}", True, WHITE)
        self.screen.blit(entities_text, (10, 70))
        
        # Render controls help at the bottom
        controls_shadow = self.controls_font.render("Controls: N (next stage), P (previous stage), ESC (quit)", True, (0, 0, 0))
        controls_text = self.controls_font.render("Controls: N (next stage), P (previous stage), ESC (quit)", True, WHITE)
        self.screen.blit(controls_shadow, (12, self.height - 28))
        self.screen.blit(controls_text, (10, self.height - 30))
    
    def _render_background(self):
        # Create a subtle gradient background
        for y in range(0, self.height, 2):
            pygame.draw.line(
                self.screen,
                (
                    max(0, BACKGROUND[0] - y//10),
                    max(0, BACKGROUND[1] - y//10),
                    min(50, BACKGROUND[2] + y//10)
                ),
                (0, y),
                (self.width, y)
            )

def main():
    """Main function to run the simple rendering test"""
    # Initialize Pygame
    pygame.init()
    
    # Set up display
    screen_width, screen_height = 800, 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Simple Entity Rendering Test")
    
    # Set up clock for controlling frame rate
    clock = pygame.time.Clock()
    target_fps = 60
    
    # Create renderer and managers
    renderer = SimpleEntityRenderer(screen)
    stage_manager = TestStageManager(screen_width, screen_height, renderer)
    ui_manager = UIManager(screen, screen_width, screen_height)
    
    # Load the first stage
    stage_manager.load_stage(1)  # Start with the basic stage
    
    # Variables for FPS tracking
    frame_count = 0
    start_time = time.time()
    fps_update_interval = 1.0  # Update FPS display every second
    current_fps = 0
    
    # Main loop
    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_n:
                    stage_manager.load_next_stage()
                elif event.key == pygame.K_p:
                    stage_manager.load_previous_stage()
        
        # Clear the screen
        screen.fill(BACKGROUND)
        
        # Update renderer animations
        renderer.update()
        
        # Render UI background
        ui_manager.render(current_fps, stage_manager.stages[stage_manager.current_stage], renderer.get_entity_count())
        
        # Render entities
        renderer.render()
        
        # Calculate and display FPS
        frame_count += 1
        if time.time() - start_time > fps_update_interval:
            current_fps = frame_count / (time.time() - start_time)
            frame_count = 0
            start_time = time.time()
        
        # Update display
        pygame.display.flip()
        
        # Cap the frame rate
        clock.tick(target_fps)
    
    # Clean up
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main() 