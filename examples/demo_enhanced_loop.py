import sys
import pygame

from enhanced_game_loop import EnhancedGameLoop
from systems.utils.logging import logger

def main():
    """Main entry point for the enhanced game loop demo."""
    logger.info("Starting Enhanced Game Loop Demo")
    game = None
    try:
        # Instantiate the game loop
        # It will load configuration internally
        game = EnhancedGameLoop()
        
        # Run the game loop (this includes setup)
        game.run()
        
    except Exception as e:
        logger.error(f"An error occurred during the game loop: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    finally:
        # Ensure Pygame quits properly, even if errors occurred
        # The game loop's _shutdown method also calls pygame.quit(), 
        # but this provides an extra layer of safety.
        logger.info("Enhanced Game Loop Demo finished. Shutting down Pygame.")
        pygame.quit()
        # Optionally exit the script
        # sys.exit()

if __name__ == "__main__":
    main() 