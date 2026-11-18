import pygame
import sys
import time
import os

# Adjust path to import from parent directory (if necessary)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from systems.core.system_manager import system_manager
from systems.environment.environment import BattleRoyaleEnv
from systems.agents.agent_system import AgentSystem
from systems.visualization.visualization_integration import VisualizationIntegration
from systems.utils.config import config
from systems.utils.logging import logger

def run_demo():
    """Runs a basic demo of the AI Battle Arena."""
    try:
        logger.info("Starting Basic Arena Demo")

        # --- Pygame Setup ---
        pygame.init()
        screen_width = config.display['SCREEN_WIDTH']
        screen_height = config.display['SCREEN_HEIGHT']
        screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("AI Battle Arena - Basic Demo")
        clock = pygame.time.Clock()
        font = pygame.font.Font(None, 24) # Font for FPS display

        # --- System Setup ---
        system_manager.set_shared_state('screen', screen)
        system_manager.set_shared_state('config', config)

        # Initialize Environment
        env = BattleRoyaleEnv(
            width=screen_width,
            height=screen_height,
            target_fps=config.display['TARGET_FPS']
        )
        # Add env to shared state so other systems can access it
        system_manager.set_shared_state('environment', env)

        # Create Agents (using a smaller number for the demo)
        num_demo_agents = 4
        agents = env.create_agents(max_agents=num_demo_agents)
        logger.info(f"Demo: Created {len(agents)} agents.")

        # Register Core Systems
        agent_system = AgentSystem() # Automatically registers
        viz_integration = VisualizationIntegration() # Automatically registers

        # Initialize all registered systems
        system_manager.initialize_all()
        logger.info("Systems initialized.")

        # --- Main Loop ---
        running = True
        last_time = time.time()

        while running:
            current_time = time.time()
            delta_time = current_time - last_time
            last_time = current_time

            # Handle Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                # Pass events to visualization system (for potential camera controls etc.)
                viz_integration.handle_event(event)

            # Update Systems
            system_manager.update(delta_time)

            # Render using VisualizationIntegration
            screen.fill((30, 30, 30)) # Clear screen with dark grey
            viz_integration.render(screen) # Should render env, agents, bullets etc.

            # Display FPS
            fps = clock.get_fps()
            fps_text = font.render(f"FPS: {fps:.2f}", True, (255, 255, 255))
            screen.blit(fps_text, (10, 10))

            # Update Display
            pygame.display.flip()

            # Cap Frame Rate
            clock.tick(config.display['TARGET_FPS'])

    except Exception as e:
        logger.error(f"Demo Error: {str(e)}", exc_info=True)
    finally:
        # --- Shutdown ---
        logger.info("Shutting down demo...")
        system_manager.shutdown_all()
        pygame.quit()
        logger.info("Demo finished.")

if __name__ == "__main__":
    # Ensure the examples directory exists
    if not os.path.exists("examples"):
        os.makedirs("examples")
    run_demo() 