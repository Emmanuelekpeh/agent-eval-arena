"""
Concrete Pygame rendering backend implementation.
"""
import pygame
from typing import Dict, List, Tuple, Optional, Any
import logging

from .rendering import RenderingBackend
from .visualization_system import Color

logger = logging.getLogger(__name__)

class PygameBackend(RenderingBackend):
    """
    RenderingBackend implementation using Pygame.
    """
    def __init__(self, screen: pygame.Surface):
        """
        Initialize the Pygame backend.

        Args:
            screen (pygame.Surface): The main Pygame display surface.
        """
        super().__init__()
        self.screen = screen
        self.fonts: Dict[float, pygame.font.Font] = {}

    def initialize(self, width: int, height: int, title: str = "AI Battle Arena") -> bool:
        """
        Initialize the Pygame backend (largely relies on external Pygame init).

        Returns:
            bool: True if initialization is considered successful.
        """
        if not pygame.get_init():
            logger.error("PygameBackend Error: Pygame is not initialized.")
            return False
        if self.screen is None:
             logger.error("PygameBackend Error: Screen surface is None.")
             return False

        # Store dimensions from the provided screen
        self.width = self.screen.get_width()
        self.height = self.screen.get_height()
        # Optionally set caption if needed, though usually done externally
        pygame.display.set_caption(title)

        self.initialized = True
        logger.info(f"PygameBackend initialized with screen size {self.width}x{self.height}.")
        return True

    def begin_frame(self) -> None:
        """Begin a new frame (no specific action needed for Pygame usually)."""
        pass # Pygame drawing happens directly on the surface

    def end_frame(self) -> None:
        """End the current frame (handled by pygame.display.flip() externally)."""
        pass # Flip is typically called outside the backend

    def clear(self, color: Color) -> None:
        """Clear the screen to the specified color."""
        if self.initialized and self.screen:
            self.screen.fill(color.to_tuple()[:3]) # Use RGB for fill

    def draw_circle(self, x: float, y: float, radius: float, color: Color, filled: bool = True) -> None:
        """Draw a circle using Pygame."""
        if self.initialized and self.screen:
            width = 0 if filled else max(1, int(1 * self.screen.get_width()/800)) # Basic thickness scaling
            try:
                pygame.draw.circle(self.screen, color.to_tuple(), (int(x), int(y)), int(radius), width)
            except Exception as e:
                 # Avoid crashing if radius is invalid, etc.
                 logger.warning(f"Pygame draw_circle failed: {e} (pos=({x},{y}), rad={radius}, color={color})")


    def draw_line(self, x1: float, y1: float, x2: float, y2: float,
                  color: Color, thickness: float = 1.0) -> None:
        """Draw a line using Pygame."""
        if self.initialized and self.screen:
            pygame.draw.line(self.screen, color.to_tuple(), (int(x1), int(y1)), (int(x2), int(y2)), max(1, int(thickness)))

    def draw_rect(self, x: float, y: float, width: float, height: float,
                 color: Color, filled: bool = True) -> None:
        """Draw a rectangle using Pygame."""
        if self.initialized and self.screen:
            line_width = 0 if filled else max(1, int(1 * self.screen.get_width()/800)) # Basic thickness scaling
            try:
                pygame.draw.rect(self.screen, color.to_tuple(), pygame.Rect(int(x), int(y), int(width), int(height)), line_width)
            except Exception as e:
                logger.warning(f"Pygame draw_rect failed: {e} (pos=({x},{y}), size=({width},{height}), color={color})")


    def draw_text(self, x: float, y: float, text: str, color: Color,
                 size: float = 12.0, centered: bool = False) -> None:
        """Draw text using Pygame."""
        if self.initialized and self.screen:
            try:
                int_size = max(1, int(size))
                if int_size not in self.fonts:
                    self.fonts[int_size] = pygame.font.Font(None, int_size) # Use default font
                font = self.fonts[int_size]
                text_surface = font.render(text, True, color.to_tuple())
                text_rect = text_surface.get_rect()
                if centered:
                    text_rect.center = (int(x), int(y))
                else:
                    text_rect.topleft = (int(x), int(y))
                self.screen.blit(text_surface, text_rect)
            except Exception as e:
                logger.error(f"Pygame draw_text failed: {e} (text='{text}')")


    def draw_polygon(self, points: List[Tuple[float, float]], color: Color,
                    filled: bool = True) -> None:
        """Draw a polygon using Pygame."""
        if self.initialized and self.screen and len(points) >= 3:
            int_points = [(int(px), int(py)) for px, py in points]
            line_width = 0 if filled else max(1, int(1 * self.screen.get_width()/800)) # Basic thickness scaling
            try:
                pygame.draw.polygon(self.screen, color.to_tuple(), int_points, line_width)
            except Exception as e:
                 logger.warning(f"Pygame draw_polygon failed: {e} (points={int_points}, color={color})")


    def shutdown(self) -> None:
        """Clean up Pygame resources (usually handled externally)."""
        super().shutdown()
        self.fonts.clear()
        logger.info("PygameBackend shutdown.") 