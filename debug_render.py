import pygame
import sys
import os
import random
import math

# Add this to see debug logs
import logging
logging.basicConfig(level=logging.DEBUG)

from systems.core.system_manager import system_manager
from systems.environment.environment import BattleRoyaleEnv
from systems.visualization.visualization_integration import VisualizationIntegration

# Force visualization flag
os.environ["FORCE_RENDER"] = "1"
os.environ["DEBUG_RENDER"] = "1"
os.environ["DISPLAY_ENTITY_IDS"] = "1"  # Show entity IDs for debugging

# Stage/level management
class StageManager:
    def __init__(self, env, width, height):
        self.env = env
        self.width = width
        self.height = height
        self.current_stage = 0
        self.stages = [
            self.create_stage_1,
            self.create_stage_2,
            self.create_stage_3
        ]
        self.entities_by_stage = {}
        
    def load_stage(self, stage_num):
        print(f"Loading stage {stage_num}")
        # Clear existing entities if needed
        if hasattr(self.env, 'entities'):
            # Store reference to existing entities to remove later
            to_remove = list(self.env.entities.keys())
            
            # Remove entities from previous stage
            for entity_id in to_remove:
                if entity_id in self.env.entities:
                    print(f"Removing entity {entity_id}")
                    # Use proper method if available, otherwise direct removal
                    if hasattr(self.env, 'remove_entity'):
                        self.env.remove_entity(entity_id)
                    else:
                        del self.env.entities[entity_id]
        
        # Call the appropriate stage creation function
        if 0 <= stage_num < len(self.stages):
            self.current_stage = stage_num
            return self.stages[stage_num]()
        return []
        
    def create_stage_1(self):
        print("Creating stage 1 - Basic entities")
        entities = []
        
        # Create some basic entities
        if hasattr(self.env, 'create_entity'):
            for i in range(5):
                entity = self.env.create_entity(
                    entity_type="circle",
                    position=(100 + i*100, 300),
                    radius=30,
                    color=(255, 0, 0),  # Bright red
                    data={"id": f"stage1_entity_{i}", "visible": True}
                )
                entities.append(entity)
                
        self.entities_by_stage[0] = entities
        return entities
    
    def create_stage_2(self):
        print("Creating stage 2 - Advanced pattern")
        entities = []
        
        # Create a more complex pattern of entities
        if hasattr(self.env, 'create_entity'):
            # Create a circle pattern
            center_x, center_y = self.width // 2, self.height // 2
            radius = 150
            num_points = 8
            
            for i in range(num_points):
                angle = 2 * 3.14159 * i / num_points
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                
                entity = self.env.create_entity(
                    entity_type="circle",
                    position=(x, y),
                    radius=20,
                    color=(0, 255, 0),  # Green
                    data={"id": f"stage2_entity_{i}", "visible": True}
                )
                entities.append(entity)
                
        self.entities_by_stage[1] = entities
        return entities
    
    def create_stage_3(self):
        print("Creating stage 3 - Complex scene")
        entities = []
        
        # Create a more complex scene with different entity types
        if hasattr(self.env, 'create_entity'):
            # Add some scattered entities
            for i in range(10):
                x = random.randint(50, self.width - 50)
                y = random.randint(50, self.height - 50)
                size = random.randint(10, 40)
                
                entity = self.env.create_entity(
                    entity_type="circle",
                    position=(x, y),
                    radius=size,
                    color=(0, 0, 255),  # Blue
                    data={"id": f"stage3_entity_{i}", "visible": True}
                )
                entities.append(entity)
                
        self.entities_by_stage[2] = entities
        return entities

    def next_stage(self):
        next_stage = (self.current_stage + 1) % len(self.stages)
        return self.load_stage(next_stage)
        
    def prev_stage(self):
        next_stage = (self.current_stage - 1) % len(self.stages)
        return self.load_stage(next_stage)


def main():
    try:
        print("Starting Debug Battle Arena")
        
        # Initialize pygame
        pygame.init()
        
        # Create screen with explicit settings
        screen_width = 800
        screen_height = 600
        screen = pygame.display.set_mode(
            (screen_width, screen_height),
            pygame.HWSURFACE | pygame.DOUBLEBUF  # Hardware acceleration
        )
        pygame.display.set_caption("Debug Battle Arena")
        
        # Store screen in shared state
        system_manager.set_shared_state('screen', screen)
        
        # Initialize environment with minimal components and disable auto generation
        env = BattleRoyaleEnv(
            width=screen_width,
            height=screen_height,
            target_fps=30,
        )
        
        # Disable auto-generation if applicable
        if hasattr(env, 'auto_generate'):
            env.auto_generate = False
        
        # Register the env instance
        system_manager.register_system("battle_royale_env", env, priority=15)
        system_manager.set_shared_state('environment', env)
        
        # Initialize visualization with debug mode
        vis_system = VisualizationIntegration()
        vis_system.visualization_enabled = True  # Force enable
        system_manager.register_system("visualization_integration", vis_system, priority=80)
        
        # Initialize the stage manager
        stage_manager = StageManager(env, screen_width, screen_height)
        
        # Initialize all systems
        system_manager.initialize_all()
        
        # Load the first stage
        entities = stage_manager.load_stage(0)
        
        # Print debug info
        print(f"Environment initialized: {screen_width}x{screen_height}")
        print(f"Visualization enabled: {vis_system.visualization_enabled}")
        print(f"Stage 1 entities created: {len(entities)}")
        
        # Main game loop
        running = True
        clock = pygame.time.Clock()
        frame_count = 0
        
        # Display help text
        help_text = [
            "Controls:",
            "F - Force redraw",
            "R - Create new entity",
            "N - Next stage",
            "P - Previous stage",
            "Q - Quit"
        ]
        
        while running:
            frame_count += 1
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                # Handle keypresses for debug
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_f:
                        # Force redraw everything
                        vis_system.visualization_enabled = True
                        print("Forcing visualization")
                    elif event.key == pygame.K_r:
                        # Reset/recreate entities
                        print("Creating a new entity")
                        if hasattr(env, 'create_entity'):
                            entity = env.create_entity(
                                entity_type="circle",
                                position=(400, 300),
                                radius=30,
                                color=(255, 255, 0),  # Yellow
                                data={"id": f"manual_entity_{frame_count}", "visible": True}
                            )
                    elif event.key == pygame.K_n:
                        # Load next stage
                        entities = stage_manager.next_stage()
                        print(f"Loaded next stage: {stage_manager.current_stage+1}/{len(stage_manager.stages)}")
                    elif event.key == pygame.K_p:
                        # Load previous stage
                        entities = stage_manager.prev_stage()
                        print(f"Loaded previous stage: {stage_manager.current_stage+1}/{len(stage_manager.stages)}")
                    elif event.key == pygame.K_q:
                        running = False
            
            # Fill background with dark gray for visibility
            screen.fill((30, 30, 30))
            
            # Update all systems (reduced frequency to improve performance)
            if frame_count % 1 == 0:  # Every frame
                system_manager.update(1/30)
            
            # DEBUG: Force draw entities from environment if they exist
            if hasattr(env, 'entities'):
                for entity_id, entity in env.entities.items():
                    if hasattr(entity, 'position') and hasattr(entity, 'radius'):
                        pos = entity.position if hasattr(entity, 'position') else (0, 0)
                        radius = entity.radius if hasattr(entity, 'radius') else 10
                        color = entity.color if hasattr(entity, 'color') else (255, 255, 0)
                        
                        # Ensure position is a tuple of numbers
                        if not isinstance(pos, tuple) or len(pos) != 2:
                            pos = (0, 0)
                            
                        # Draw entity
                        pygame.draw.circle(screen, color, pos, radius)
                        
                        # Draw entity ID for debugging
                        font = pygame.font.SysFont('Arial', 12)
                        text = font.render(str(entity_id), True, (255, 255, 255))
                        screen.blit(text, (pos[0] - text.get_width() // 2, pos[1] - text.get_height() // 2))
            
            # Render visualization components
            if vis_system and vis_system.visualization_enabled:
                vis_system.render(screen)
            
            # Draw FPS counter
            fps = clock.get_fps()
            font = pygame.font.SysFont('Arial', 18)
            fps_text = font.render(f"FPS: {fps:.2f}", True, (255, 255, 255))
            screen.blit(fps_text, (10, 10))
            
            # Draw current stage info
            stage_text = font.render(f"Stage: {stage_manager.current_stage + 1}/{len(stage_manager.stages)}", True, (255, 255, 255))
            screen.blit(stage_text, (10, 30))
            
            # Draw entity count
            if hasattr(env, 'entities'):
                count_text = font.render(f"Entities: {len(env.entities)}", True, (255, 255, 255))
                screen.blit(count_text, (10, 50))
            
            # Draw help text
            y_offset = 70
            for line in help_text:
                help_line = font.render(line, True, (200, 200, 200))
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
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
    finally:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main() 