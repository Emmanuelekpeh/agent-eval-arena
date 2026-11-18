import pygame
import sys
import os
import random
import math
import logging
import time

# Add this to see debug logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("battle_arena_debug")

# Import core components
from systems.core.system_manager import system_manager
from systems.environment.environment import BattleRoyaleEnv
from systems.visualization.visualization_integration import VisualizationIntegration

# Force visualization flag
os.environ["FORCE_RENDER"] = "1"
os.environ["DEBUG_RENDER"] = "1" 
os.environ["DISPLAY_ENTITY_IDS"] = "1"  # Show entity IDs for debugging

class StageManager:
    """Manages stage-based entity creation to optimize performance"""
    
    def __init__(self, env, width, height):
        self.env = env
        self.width = width
        self.height = height
        self.current_stage = 0
        self.entities_by_stage = {}
        self.last_entity_count = 0
        
        # Define available stages
        self.stages = [
            {"name": "Empty Stage", "creator": self.create_empty_stage},
            {"name": "Basic Entities", "creator": self.create_basic_stage},
            {"name": "Circle Pattern", "creator": self.create_circle_pattern},
            {"name": "Random Scatter", "creator": self.create_random_scatter}
        ]
        
    def load_stage(self, stage_num):
        """Load a specific stage, clearing previous entities"""
        logger.info(f"Loading stage {stage_num}: {self.stages[stage_num]['name']}")
        
        start_time = time.time()
        
        # Clear existing entities if needed
        self.clear_entities()
            
        # Call the appropriate stage creation function
        if 0 <= stage_num < len(self.stages):
            self.current_stage = stage_num
            entities = self.stages[stage_num]["creator"]()
            self.last_entity_count = len(entities) if entities else 0
            
            end_time = time.time()
            logger.info(f"Stage loaded in {(end_time - start_time):.3f} seconds with {self.last_entity_count} entities")
            
            return entities
        return []
    
    def clear_entities(self):
        """Clear all existing entities"""
        # Check if env has entities attribute
        if hasattr(self.env, 'entities'):
            start_count = len(self.env.entities) if self.env.entities else 0
            logger.info(f"Clearing {start_count} existing entities")
            
            # Store reference to existing entities to remove
            to_remove = list(self.env.entities.keys()) if self.env.entities else []
            
            # Remove entities properly based on available methods
            for entity_id in to_remove:
                if entity_id in self.env.entities:
                    if hasattr(self.env, 'remove_entity'):
                        self.env.remove_entity(entity_id)
                    else:
                        # As fallback, just delete from the dictionary
                        del self.env.entities[entity_id]
    
    def create_empty_stage(self):
        """Create an empty stage with no entities"""
        logger.info("Creating empty stage")
        entities = []
        self.entities_by_stage[0] = entities
        return entities
        
    def create_basic_stage(self):
        """Create a basic stage with a few simple entities"""
        logger.info("Creating basic stage with simple entities")
        entities = []
        
        # Create some basic entities in a row
        if hasattr(self.env, 'create_entity'):
            for i in range(5):
                entity = self.env.create_entity(
                    entity_type="circle",
                    position=(100 + i*100, 300),
                    radius=30,
                    color=(255, 0, 0),  # Bright red
                    data={"id": f"basic_entity_{i}", "visible": True}
                )
                entities.append(entity)
                
        self.entities_by_stage[1] = entities
        return entities
    
    def create_circle_pattern(self):
        """Create a circle pattern of entities"""
        logger.info("Creating circle pattern stage")
        entities = []
        
        # Create a circle pattern of entities
        if hasattr(self.env, 'create_entity'):
            # Create a circle pattern
            center_x, center_y = self.width // 2, self.height // 2
            radius = 150
            num_points = 8
            
            for i in range(num_points):
                angle = 2 * math.pi * i / num_points
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                
                entity = self.env.create_entity(
                    entity_type="circle",
                    position=(x, y),
                    radius=20,
                    color=(0, 255, 0),  # Green
                    data={"id": f"circle_entity_{i}", "visible": True}
                )
                entities.append(entity)
                
            # Add center entity
            entity = self.env.create_entity(
                entity_type="circle",
                position=(center_x, center_y),
                radius=30,
                color=(255, 255, 0),  # Yellow
                data={"id": "circle_center", "visible": True}
            )
            entities.append(entity)
                
        self.entities_by_stage[2] = entities
        return entities
    
    def create_random_scatter(self):
        """Create a random scatter of entities"""
        logger.info("Creating random scatter stage")
        entities = []
        
        # Create randomly scattered entities
        if hasattr(self.env, 'create_entity'):
            for i in range(20):  # Limit to 20 for performance
                x = random.randint(50, self.width - 50)
                y = random.randint(50, self.height - 50)
                size = random.randint(10, 40)
                r = random.randint(100, 255)
                g = random.randint(100, 255)
                b = random.randint(100, 255)
                
                entity = self.env.create_entity(
                    entity_type="circle",
                    position=(x, y),
                    radius=size,
                    color=(r, g, b),
                    data={"id": f"random_entity_{i}", "visible": True}
                )
                entities.append(entity)
                
        self.entities_by_stage[3] = entities
        return entities

    def next_stage(self):
        """Load the next stage in sequence"""
        next_stage = (self.current_stage + 1) % len(self.stages)
        return self.load_stage(next_stage)
        
    def prev_stage(self):
        """Load the previous stage in sequence"""
        next_stage = (self.current_stage - 1) % len(self.stages)
        return self.load_stage(next_stage)


def main():
    try:
        logger.info("Starting Optimized Debug Battle Arena")
        
        # Initialize pygame
        pygame.init()
        
        # Create screen with explicit settings for better performance
        screen_width = 800
        screen_height = 600
        screen = pygame.display.set_mode(
            (screen_width, screen_height),
            pygame.HWSURFACE | pygame.DOUBLEBUF  # Hardware acceleration
        )
        pygame.display.set_caption("Optimized Debug Battle Arena")
        
        # Store screen in shared state
        system_manager.set_shared_state('screen', screen)
        
        # Initialize environment with minimal settings
        env = BattleRoyaleEnv(
            width=screen_width,
            height=screen_height,
            target_fps=30,
        )
        
        # Try to disable auto-generation if that attribute exists
        if hasattr(env, 'auto_generate'):
            env.auto_generate = False
        
        # Register the env instance
        system_manager.register_system("battle_royale_env", env, priority=15)
        system_manager.set_shared_state('environment', env)
        
        # Initialize visualization with debug mode
        vis_system = VisualizationIntegration()
        vis_system.visualization_enabled = True  # Force enable
        system_manager.register_system("visualization_integration", vis_system, priority=80)
        
        # Initialize systems first before creating entities
        system_manager.initialize_all()
        
        # Initialize the stage manager after systems are ready
        stage_manager = StageManager(env, screen_width, screen_height)
        
        # Load the empty stage first to start clean
        entities = stage_manager.load_stage(0)
        
        # Print debug info
        logger.info(f"Environment initialized: {screen_width}x{screen_height}")
        logger.info(f"Visualization enabled: {vis_system.visualization_enabled}")
        logger.info(f"Stage loaded with {len(entities)} entities")
        
        # Performance monitoring
        clock = pygame.time.Clock()
        frame_count = 0
        fps_samples = []
        last_sample_time = time.time()
        
        # Display help text
        help_text = [
            "OPTIMIZED RENDERER - STAGE-BASED APPROACH",
            "",
            "Controls:",
            "F - Force redraw",
            "R - Reset current stage",
            "N - Next stage",
            "P - Previous stage",
            "Q - Quit"
        ]
        
        # Main game loop
        running = True
        
        while running:
            frame_count += 1
            current_time = time.time()
            
            # Sample FPS periodically
            if current_time - last_sample_time >= 1.0:
                fps = clock.get_fps()
                fps_samples.append(fps)
                # Keep only the last 5 samples
                if len(fps_samples) > 5:
                    fps_samples.pop(0)
                last_sample_time = current_time
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                # Handle keypresses for debug
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_f:
                        # Force redraw everything
                        vis_system.visualization_enabled = True
                        logger.info("Forcing visualization refresh")
                    elif event.key == pygame.K_r:
                        # Reset/reload current stage
                        logger.info(f"Reloading stage {stage_manager.current_stage}")
                        entities = stage_manager.load_stage(stage_manager.current_stage)
                    elif event.key == pygame.K_n:
                        # Load next stage
                        entities = stage_manager.next_stage()
                    elif event.key == pygame.K_p:
                        # Load previous stage
                        entities = stage_manager.prev_stage()
                    elif event.key == pygame.K_q:
                        running = False
            
            # Fill background with dark gray for visibility
            screen.fill((30, 30, 30))
            
            # Update all systems (reduced frequency to improve performance)
            system_manager.update(1/30)
            
            # DEBUG: Force draw entities from environment if they exist
            if hasattr(env, 'entities') and env.entities:
                for entity_id, entity in env.entities.items():
                    if hasattr(entity, 'position') and hasattr(entity, 'radius'):
                        try:
                            pos = entity.position if hasattr(entity, 'position') else (0, 0)
                            radius = entity.radius if hasattr(entity, 'radius') else 10
                            color = entity.color if hasattr(entity, 'color') else (255, 255, 0)
                            
                            # Ensure position is a tuple of numbers
                            if not isinstance(pos, tuple) or len(pos) != 2:
                                pos = (0, 0)
                                
                            # Draw entity
                            pygame.draw.circle(screen, color, pos, radius)
                            
                            # Draw entity ID for debugging - only if close to player
                            if os.environ.get("DISPLAY_ENTITY_IDS", "0") == "1":
                                font = pygame.font.SysFont('Arial', 12)
                                short_id = entity_id.split('_')[-1] if '_' in entity_id else entity_id
                                text = font.render(short_id, True, (255, 255, 255))
                                screen.blit(text, (pos[0] - text.get_width() // 2, pos[1] - text.get_height() // 2))
                        except Exception as e:
                            # Skip this entity if it causes rendering issues
                            pass
            
            # Render visualization components
            if vis_system and vis_system.visualization_enabled:
                vis_system.render(screen)
            
            # Calculate average FPS
            avg_fps = sum(fps_samples) / len(fps_samples) if fps_samples else 0
            
            # Draw FPS counter
            fps = clock.get_fps()
            font = pygame.font.SysFont('Arial', 18)
            fps_text = font.render(f"FPS: {fps:.1f} (Avg: {avg_fps:.1f})", True, (255, 255, 255))
            screen.blit(fps_text, (10, 10))
            
            # Draw current stage info
            stage_name = stage_manager.stages[stage_manager.current_stage]["name"]
            stage_text = font.render(f"Stage: {stage_manager.current_stage + 1}/{len(stage_manager.stages)} - {stage_name}", True, (255, 255, 255))
            screen.blit(stage_text, (10, 30))
            
            # Draw entity count
            if hasattr(env, 'entities'):
                count_text = font.render(f"Entities: {len(env.entities)}", True, (255, 255, 255))
                screen.blit(count_text, (10, 50))
            
            # Draw help text
            y_offset = 80
            help_font = pygame.font.SysFont('Arial', 16)
            for line in help_text:
                if line:
                    help_line = help_font.render(line, True, (200, 200, 200))
                    screen.blit(help_line, (10, y_offset))
                y_offset += 20
            
            # Update display
            pygame.display.flip()
            
            # Control frame rate - cap at 30 FPS to reduce CPU usage
            clock.tick(30)
        
        # Shutdown all systems
        system_manager.shutdown_all()
        
    except Exception as e:
        import traceback
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main() 