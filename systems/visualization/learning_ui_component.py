import pygame
import numpy as np
from io import BytesIO
from typing import Dict, List, Any, Optional, Tuple
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from systems.visualization.learning_visualizer import LearningVisualizer
from systems.core.system_manager import system_manager
import matplotlib.pyplot as plt


class LearningUIComponent:
    """
    UI component for displaying learning visualizations in-game.
    
    This component renders learning visualizations from the LearningVisualizer
    directly into the game UI using Pygame.
    """
    
    def __init__(self, position: Tuple[int, int] = (10, 10), size: Tuple[int, int] = (400, 300),
                 learning_integration=None, update_interval: float = 2.0):
        """
        Initialize the learning UI component.
        
        Args:
            position: Position (x, y) in the UI
            size: Size (width, height) of the visualization panel
            learning_integration: LearningIntegration instance to use (auto-detected if None)
            update_interval: How often to update visualizations (seconds)
        """
        self.position = position
        self.size = size
        self.update_interval = update_interval
        self.last_update_time = 0
        
        # Get learning integration from system manager if not provided
        self.learning_integration = learning_integration
        if self.learning_integration is None:
            self.learning_integration = system_manager.get_system("learning_integration")
        
        # Get learning visualizer from integration or create a new one
        if self.learning_integration:
            self.visualizer = self.learning_integration.visualizer
        else:
            self.visualizer = LearningVisualizer()
        
        # Visualization state
        self.current_visualization = None
        self.current_surface = None
        self.current_visualization_type = "learning_curve"
        self.current_agent_selection = None
        self.visualization_types = [
            "learning_curve", "pattern_progress", "strategy_adaptation", 
            "pattern_clusters", "cross_agent"
        ]
        
        # UI state
        self.visible = True
        self.minimized = False
        self.dragging = False
        self.drag_offset = (0, 0)
        self.active_agent_ids = []
        
        # Create UI surfaces
        self.panel_surface = pygame.Surface(size, pygame.SRCALPHA)
        self.header_height = 30
        self.header_surface = pygame.Surface((size[0], self.header_height), pygame.SRCALPHA)
        
        # UI fonts
        self.font = pygame.font.SysFont("Arial", 14)
        self.title_font = pygame.font.SysFont("Arial", 16, bold=True)
        
        # Buttons
        self.buttons = []
        self._create_buttons()
        
        # Generate initial visualization
        self._update_visualization()
    
    def _create_buttons(self):
        """Create UI buttons for the component."""
        # Button definitions: (rect, text, action)
        button_width = 80
        button_height = 20
        button_y = 5
        
        # Close button
        self.buttons.append((
            pygame.Rect(self.size[0] - 25, 5, 20, 20),
            "X",
            self._toggle_visibility
        ))
        
        # Minimize button
        self.buttons.append((
            pygame.Rect(self.size[0] - 50, 5, 20, 20),
            "_",
            self._toggle_minimized
        ))
        
        # Visualization type buttons
        x_offset = 5
        for i, viz_type in enumerate(self.visualization_types):
            # Create wrapped action with viz_type captured
            def make_change_viz_action(vt):
                return lambda: self._change_visualization_type(vt)
            
            action = make_change_viz_action(viz_type)
            
            # Use more user-friendly text
            if viz_type == "learning_curve":
                text = "Learning"
            elif viz_type == "pattern_progress":
                text = "Patterns"
            elif viz_type == "strategy_adaptation":
                text = "Strategy"
            elif viz_type == "pattern_clusters":
                text = "Clusters"
            elif viz_type == "cross_agent":
                text = "Compare"
            else:
                text = viz_type
            
            self.buttons.append((
                pygame.Rect(x_offset, button_y, button_width, button_height),
                text,
                action
            ))
            x_offset += button_width + 5
    
    def _change_visualization_type(self, viz_type):
        """Change the current visualization type."""
        self.current_visualization_type = viz_type
        self._update_visualization()
    
    def _toggle_visibility(self):
        """Toggle component visibility."""
        self.visible = not self.visible
    
    def _toggle_minimized(self):
        """Toggle minimized state."""
        self.minimized = not self.minimized
    
    def _update_visualization(self):
        """Update the current visualization."""
        if not self.learning_integration or not self.visualizer:
            return
        
        # Get active agent IDs
        if not self.active_agent_ids and self.learning_integration:
            self.active_agent_ids = list(self.learning_integration.registered_agents)
        
        # Skip if no agents or minimized
        if not self.active_agent_ids:
            return
        
        try:
            # Generate visualization based on current type
            if self.current_visualization_type == "learning_curve":
                self.current_visualization = self.learning_integration.visualize_learning_curve(
                    agent_ids=self.active_agent_ids, metric='rewards'
                )
            elif self.current_visualization_type == "pattern_progress":
                self.current_visualization = self.learning_integration.visualize_pattern_progress(
                    agent_ids=self.active_agent_ids
                )
            elif self.current_visualization_type == "strategy_adaptation":
                self.current_visualization = self.learning_integration.visualize_strategy_adaptation(
                    agent_ids=self.active_agent_ids
                )
            elif self.current_visualization_type == "pattern_clusters" and self.current_agent_selection:
                # Need a specific agent for this one
                self.current_visualization = self.learning_integration.visualize_pattern_clusters(
                    agent_id=self.current_agent_selection
                )
            elif self.current_visualization_type == "cross_agent":
                self.current_visualization = self.learning_integration.visualize_cross_agent_comparison(
                    metric='rewards'
                )
            
            # Convert the matplotlib figure to a pygame surface
            if self.current_visualization:
                self.current_surface = self._figure_to_surface(
                    self.current_visualization, 
                    (self.size[0], self.size[1] - self.header_height)
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error updating visualization: {e}")
    
    def _figure_to_surface(self, fig: Figure, size: Tuple[int, int]) -> pygame.Surface:
        """
        Convert a matplotlib figure to a pygame surface.
        
        Args:
            fig: Matplotlib figure
            size: Target size (width, height)
            
        Returns:
            pygame.Surface: Surface with the rendered figure
        """
        try:
            # Render figure to a canvas
            canvas = FigureCanvasAgg(fig)
            canvas.draw()
            
            # Get the RGBA buffer (Agg rendering uses RGBA)
            buf = np.asarray(canvas.buffer_rgba())
            
            # Create a pygame surface from the buffer
            surf = pygame.surfarray.make_surface(buf[:, :, :3])  # Exclude alpha channel
            surf = pygame.transform.flip(surf, False, True)   # Matplotlib origin is bottom-left
            
            # Ensure surface size matches target size
            if surf.get_size() != size:
                surf = pygame.transform.scale(surf, size)
            
            plt.close(fig) # Explicitly close the figure to free memory
            return surf
        except Exception as e:
            logger.error(f"Error converting Matplotlib figure to surface: {e}", exc_info=True)
            # Return a placeholder surface on error
            error_surf = pygame.Surface(size)
            error_surf.fill((50, 50, 50)) # Dark grey placeholder
            font = pygame.font.Font(None, 18)
            text = font.render("Error", True, (255, 0, 0))
            error_surf.blit(text, (5, 5))
            plt.close(fig) # Also close the figure in case of error
            return error_surf
    
    def update(self, delta_time: float):
        """
        Update the UI component.
        
        Args:
            delta_time: Time since last update
        """
        if not self.visible:
            return
        
        # Update visualization at the specified interval
        self.last_update_time += delta_time
        if self.last_update_time >= self.update_interval:
            self.last_update_time = 0
            if not self.minimized:
                self._update_visualization()
    
    def handle_event(self, event):
        """
        Handle input events for the UI component.
        
        Args:
            event: Pygame event
            
        Returns:
            bool: True if the event was handled
        """
        if not self.visible:
            return False
        
        handled = False
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Adjust mouse position to component-relative coordinates
            rel_pos = (mouse_pos[0] - self.position[0], mouse_pos[1] - self.position[1])
            
            # Check for button clicks
            for button_rect, _, action in self.buttons:
                if button_rect.collidepoint(rel_pos):
                    action()
                    handled = True
                    break
            
            # Check for dragging the panel (header only)
            header_rect = pygame.Rect(0, 0, self.size[0], self.header_height)
            if header_rect.collidepoint(rel_pos):
                self.dragging = True
                self.drag_offset = rel_pos
                handled = True
        
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                mouse_pos = pygame.mouse.get_pos()
                self.position = (
                    mouse_pos[0] - self.drag_offset[0],
                    mouse_pos[1] - self.drag_offset[1]
                )
                handled = True
        
        return handled
    
    def set_agent_selection(self, agent_id: str):
        """
        Set the currently selected agent.
        
        Args:
            agent_id: ID of the selected agent
        """
        self.current_agent_selection = agent_id
        if self.current_visualization_type == "pattern_clusters":
            self._update_visualization()
    
    def set_active_agents(self, agent_ids: List[str]):
        """
        Set the active agents for visualization.
        
        Args:
            agent_ids: List of agent IDs to include in visualizations
        """
        self.active_agent_ids = agent_ids
        self._update_visualization()
    
    def render(self, screen):
        """
        Render the UI component to the screen.
        
        Args:
            screen: Pygame surface to render to
        """
        if not self.visible:
            return
        
        # Determine component size based on minimized state
        if self.minimized:
            component_height = self.header_height
        else:
            component_height = self.size[1]
        
        # Clear the panel
        self.panel_surface.fill((0, 0, 0, 200))  # Semi-transparent black
        
        # Clear the header
        self.header_surface.fill((50, 50, 50, 230))  # Dark gray, more opaque
        
        # Draw buttons
        for button_rect, button_text, _ in self.buttons:
            # Draw button
            pygame.draw.rect(
                self.header_surface,
                (100, 100, 100),
                button_rect,
                0,
                3  # Rounded corners
            )
            
            # Highlight the current visualization type button
            if button_text in ["Learning", "Patterns", "Strategy", "Clusters", "Compare"]:
                viz_name = "learning_curve" if button_text == "Learning" else \
                           "pattern_progress" if button_text == "Patterns" else \
                           "strategy_adaptation" if button_text == "Strategy" else \
                           "pattern_clusters" if button_text == "Clusters" else \
                           "cross_agent"
                
                if viz_name == self.current_visualization_type:
                    pygame.draw.rect(
                        self.header_surface,
                        (150, 150, 220),
                        button_rect,
                        0,
                        3
                    )
            
            # Draw text
            text_surf = self.font.render(button_text, True, (255, 255, 255))
            text_pos = (
                button_rect.x + (button_rect.width - text_surf.get_width()) // 2,
                button_rect.y + (button_rect.height - text_surf.get_height()) // 2
            )
            self.header_surface.blit(text_surf, text_pos)
        
        # Draw title
        title_text = f"Learning Visualization: {self.current_visualization_type.replace('_', ' ').title()}"
        title_surf = self.title_font.render(title_text, True, (255, 255, 255))
        title_x = (self.size[0] // 2) - (title_surf.get_width() // 2)
        self.header_surface.blit(title_surf, (title_x, 5))
        
        # Blit header to panel
        self.panel_surface.blit(self.header_surface, (0, 0))
        
        # Draw visualization if not minimized
        if not self.minimized and self.current_surface:
            self.panel_surface.blit(self.current_surface, (0, self.header_height))
        
        # Blit panel to screen
        screen.blit(self.panel_surface, self.position) 