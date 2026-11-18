from typing import Dict, Any
import pygame
from systems.combat_zones import CombatZone
from systems.environment.resource_system import ResourceManager

class GameManager:
    """
    Central manager for game state and systems coordination.
    
    Attributes:
        width (int): Screen width
        height (int): Screen height
        combat_zone (CombatZone): Manages combat areas
        resource_manager (ResourceManager): Handles resource spawning and collection
    """
    
    def __init__(self, width: int, height: int):
        """
        Initialize the game manager.
        
        Args:
            width (int): Screen width in pixels
            height (int): Screen height in pixels
        """
        self.width = width
        self.height = height
        self.combat_zone = CombatZone(width, height)
        self.resource_manager = ResourceManager(width, height)
        
        # Game state
        self.round_number = 1
        self.round_time = 0
        self.max_round_time = 3600  # 1 minute at 60 FPS
        self.between_rounds = False
        self.round_end_delay = 180  # 3 seconds
        
        # Performance monitoring
        self.frame_times = []
        self.last_update = pygame.time.get_ticks()
        
    def update(self, players: Dict[str, Any], delta_time: float) -> Dict[str, Any]:
        """
        Update game state.
        
        Args:
            players: Dictionary of active players
            delta_time: Time since last update
            
        Returns:
            Dictionary of effects to apply to players
        """
        # Update game systems
        self.combat_zone.update()
        self.resource_manager.update()
        
        # Update round time
        if not self.between_rounds:
            self.round_time += 1
            if self.round_time >= self.max_round_time:
                self.between_rounds = True
                self.round_time = 0
                self.round_number += 1
        
        # Check zone effects
        effects = {}
        for name, player_data in players.items():
            player = player_data['player']
            pos_effects = self.combat_zone.check_player_in_zone(player.x, player.y)
            effects[name] = pos_effects
        
        return effects
    
    def draw(self, screen: pygame.Surface) -> None:
        """
        Draw game elements to screen.
        
        Args:
            screen: Pygame surface to draw on
        """
        # Draw combat zones
        self.combat_zone.draw(screen)
        # Draw resource nodes
        self.resource_manager.draw(screen)
        
        # Draw round info
        font = pygame.font.Font(None, 36)
        round_text = font.render(f"Round {self.round_number}", True, (255, 255, 255))
        time_left = (self.max_round_time - self.round_time) // 60
        time_text = font.render(f"Time: {time_left}", True, (255, 255, 255))
        screen.blit(round_text, (10, 10))
        screen.blit(time_text, (10, 50))
