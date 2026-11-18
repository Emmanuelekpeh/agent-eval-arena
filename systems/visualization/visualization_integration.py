"""
Visualization integration system for connecting learning visualization to the game UI.

This module provides the integration between the learning systems and 
the game UI, allowing visualization of learning progress directly in-game.
"""

import pygame
import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict
import math
import time

from systems.core.system_manager import system_manager, SystemEventType
from systems.visualization.learning_ui_component import LearningUIComponent
from systems.visualization.learning_visualizer import LearningVisualizer
from systems.core.base_system import BaseSystem
from systems.visualization.rendering import Renderer
from systems.visualization.visualization_system import Color
# from systems.visualization.optimized_agent_rendering import OptimizedAgentRenderingSystem

logger = logging.getLogger(__name__)

class VisualizationIntegration(BaseSystem):
    """
    Integrates visualization components with the game UI.
    
    This system manages UI components for visualizing learning and other processes,
    routing events to them and handling their lifecycle.
    """
    
    def __init__(self):
        """Initialize the visualization integration system."""
        super().__init__(name="visualization_integration", priority=80)
        
        self.logger = logging.getLogger(__name__)
        
        # UI components
        self.components = []
        
        # Learning visualization component (created during initialize)
        self.learning_ui = None
        
        # Track which agents to visualize
        self.active_agent_ids = []
        self.selected_agent_id = None
        
        # Configuration
        self.update_interval = 2.0  # Update visualizations every 2 seconds
        self.auto_hide = False  # Automatically hide visualization during intensive gameplay
        self.visualization_enabled = True
        
        # --- ADDED: Initialize the Renderer --- #
        self.renderer = Renderer() # Create the renderer instance
        # ------------------------------------- #
        
        # --- Optimized Agent Rendering --- #
        # self.optimized_agent_rendering = None  # Will be initialized later
        
        self.environment = None # Reference to the main environment
        
        self.logger.info("Visualization integration system initialized")
    
    def initialize(self):
        """Initialize the visualization system."""
        # Get screen from shared state
        screen = system_manager.get_shared_state('screen')
        if not screen:
            self.logger.warning("No screen available in shared state")
            return
        
        # Get screen dimensions
        screen_width, screen_height = screen.get_size()
        
        # Get learning integration system
        learning_integration = system_manager.get_system("learning_integration")
        
        if learning_integration:
            # Create learning visualization component
            self.learning_ui = LearningUIComponent(
                position=(20, 20),
                size=(int(screen_width * 0.5), int(screen_height * 0.4)),
                learning_integration=learning_integration,
                update_interval=self.update_interval
            )
            self.components.append(self.learning_ui)
            
            # Subscribe to agent-related events
            system_manager.subscribe(SystemEventType.ENTITY_CREATED, self._on_entity_created)
            system_manager.subscribe(SystemEventType.AGENT_ACTION, self._on_agent_action)
            
            self.logger.info("Learning visualization component initialized")
        else:
            self.logger.warning("Learning integration system not found")
        
        # Subscribe to game state changes to auto-hide during intensive gameplay
        system_manager.subscribe(SystemEventType.GAME_STATE_CHANGED, self._on_game_state_changed)
        
        # Subscribe to performance warnings to auto-hide when performance is low
        system_manager.subscribe(SystemEventType.PERFORMANCE_WARNING, self._on_performance_warning)
        
        # Get screen dimensions from config (via shared state)
        screen_width = self.get_shared_state('config').display.get('SCREEN_WIDTH', 1200)
        screen_height = self.get_shared_state('config').display.get('SCREEN_HEIGHT', 800)

        # Initialize the renderer (assuming Pygame backend for now)
        # TODO: Make backend selection configurable
        if not self.renderer.initialize(screen_width, screen_height, "AI Battle Arena"):
             logger.error("Failed to initialize Renderer!")
             self.environment = None # Disable visualization if renderer fails
             self.enabled = False # Disable visualization if renderer fails
             return
        
        # Get environment reference
        self.environment = self.get_shared_state('environment')
        if not self.environment:
            self.logger.warning("Environment reference is missing")
            
        # Initialize and register optimized agent rendering system
        # self.optimized_agent_rendering = OptimizedAgentRenderingSystem()
        # system_manager.register_system("optimized_agent_rendering", self.optimized_agent_rendering, priority=75)
    
    def update(self, delta_time):
        """
        Update the visualization integration system.
        
        Args:
            delta_time: Time since last update
        """
        if not self.visualization_enabled:
            return
        
        # Update all components
        for component in self.components:
            component.update(delta_time)
    
    def render(self, screen):
        """
        Render all visualization components.
        
        Args:
            screen: Pygame surface to render to
        """
        if not self.visualization_enabled:
            return
        
        logger.debug(f"VisualizationIntegration.render: Starting frame render on screen {id(screen)}.")
        
        # Begin frame rendering
        self.renderer.begin_frame()
        self.renderer.clear(Color(30, 30, 30)) # Clear with dark grey
        
        # Begin optimized agent rendering frame
        # if self.optimized_agent_rendering:
        #     self.optimized_agent_rendering.begin_render()
        
        # Render the main environment (delegates to BattleRoyaleEnv.render)
        if self.environment:
            logger.debug("VisualizationIntegration.render: Calling environment.render().")
            if hasattr(self.environment, 'render') and callable(self.environment.render):
                self.environment.render(screen) # Pass screen if env needs it, though ideally it uses the renderer
            else:
                logger.warning("Environment object lacks a callable render method.")
        else:
            if self.renderer.is_initialized():
                logger.warning("VisualizationIntegration: Environment reference is missing during render.")
        
        # --- ADDED: Render Agents --- #
        agent_system = system_manager.get_system("agent_system")
        if agent_system and hasattr(agent_system, 'env') and agent_system.env and self.renderer.is_initialized(): # Check env exists
            camera = self.renderer.camera
            # Access agents via agent_system.env.agents
            agent_dict = agent_system.env.agents
            logger.debug(f"VisualizationIntegration.render: Rendering {len(agent_dict)} agents.")
            # Iterate through env's agents dictionary
            for agent_id, agent_info_dict in agent_dict.items(): 
                try:
                    # Extract the actual agent instance from the dictionary
                    agent_instance = agent_info_dict.get('agent')
                    if not agent_instance:
                        logger.warning(f"Agent instance not found in dict for agent {agent_id}. Skipping render.")
                        continue
                    
                    # Position needs to be looked up from env.agent_positions
                    world_pos = agent_system.env.agent_positions.get(agent_id)
                    # Check attributes on the agent_instance now - USE 'angle'
                    if world_pos and hasattr(agent_instance, 'angle'): 
                        # Use team color or default
                        color = Color(0, 150, 255) # Default blue
                        team_id = agent_system.env.team_system.get_team_id_for_agent(agent_id) if agent_system.env.team_system else None
                        if team_id is not None:
                            # Use team system to get color or generate one
                            if agent_system.env.team_system:
                                 team_color_tuple = agent_system.env.team_system.get_team_color(team_id)
                                 color = Color(*team_color_tuple)
                            else: # Fallback if team_system isn't available on env?
                                 team_colors = {1: Color(255, 50, 50), 2: Color(50, 255, 50)} # Example
                                 color = team_colors.get(team_id, color)

                        # Use the dedicated draw_agent method from the renderer
                        health = agent_system.env.agent_health.get(agent_id, 100.0)
                        # Access max_health from the agent_instance
                        max_health = getattr(agent_instance, 'max_health', 100.0)
                        health_pct = health / max_health if max_health > 0 else 0.0
                        
                        energy = agent_system.env.agent_energy.get(agent_id, 100.0)
                        # Access max_energy from the agent_instance
                        max_energy = getattr(agent_instance, 'max_energy', 100.0)
                        energy_pct = energy / max_energy if max_energy > 0 else 0.0
                        
                        last_action_time = agent_system.agent_last_action_time.get(agent_id)
                        current_sim_time = time.time() # Or get from a TimeSystem if available

                        self.renderer.draw_agent(
                            x=world_pos[0],
                            y=world_pos[1],
                            # Access radius from the agent_instance
                            radius=getattr(agent_instance, 'radius', 8),
                            color=color,
                            # Access orientation from the agent_instance - USE 'angle'
                            direction=agent_instance.angle,
                            is_selected=(agent_id == self.selected_agent_id), # Check if this agent is selected
                            health_pct=health_pct,
                            energy_pct=energy_pct,
                            agent_id=agent_id,
                            last_action_time=last_action_time,
                            current_time=current_sim_time
                        )
                                
                    else:
                        # Check specific missing attribute
                        missing_attrs = []
                        if not world_pos:
                            missing_attrs.append("position")
                        # Check for 'angle' now
                        if not hasattr(agent_instance, 'angle'):
                            missing_attrs.append("angle")
                        logger.warning(f"Agent {agent_id} missing attributes for rendering: {', '.join(missing_attrs)}.")
                except Exception as e:
                    logger.error(f"Error rendering agent {agent_id}: {e}", exc_info=True)
                    # Continue rendering other agents
        elif not agent_system:
             logger.warning("VisualizationIntegration: AgentSystem not found during render.")
        elif not hasattr(agent_system, 'env') or not agent_system.env:
             logger.warning("VisualizationIntegration: AgentSystem found, but its 'env' attribute is missing or None.")
        # --- END ADDED --- #

        # --- ADDED: Render Bullets --- #
        if agent_system and hasattr(agent_system, 'env') and agent_system.env and self.renderer.is_initialized():
            environment = agent_system.env  # Reuse environment reference
            if hasattr(environment, 'active_bullets'):
                active_bullets = environment.active_bullets
                logger.debug(f"VisualizationIntegration.render: Rendering {len(active_bullets)} bullets.")
                for i, bullet_data in enumerate(active_bullets):
                    try:
                        # Assuming bullet_data is a dict or object with attributes
                        if isinstance(bullet_data, dict):
                            pos = bullet_data.get('position')
                            radius = bullet_data.get('radius', 2) # Default radius
                            color_tuple = bullet_data.get('color', (255, 255, 0)) # Default yellow
                        elif hasattr(bullet_data, 'position') and hasattr(bullet_data, 'radius') and hasattr(bullet_data, 'color'):
                            pos = bullet_data.position
                            radius = bullet_data.radius
                            color_tuple = bullet_data.color
                        else:
                            logger.warning(f"Bullet at index {i} has unexpected format: {type(bullet_data)}. Skipping.")
                            continue # Skip this bullet

                        color = Color(*color_tuple)

                        if pos is not None: # Check if position was successfully retrieved
                            self.renderer.draw_circle(
                                x=pos[0],
                                y=pos[1],
                                radius=radius,
                                color=color
                            )
                        else:
                            logger.warning(f"Bullet at index {i} missing position data. Skipping render.")
                    except Exception as e:
                        logger.error(f"Error rendering bullet at index {i}: {e}", exc_info=True)
            else:
                logger.debug("VisualizationIntegration: Environment has no 'active_bullets' attribute.")
        # --- END ADDED --- #

        # Render UI components on top
        for component in self.components:
            logger.debug(f"VisualizationIntegration.render: Rendering component {type(component).__name__}.")
            if hasattr(component, 'render') and callable(component.render):
                component.render(screen) # UI components might draw directly to screen
            else:
                logger.warning(f"Component {type(component).__name__} lacks a callable render method.")
        
        # End optimized agent rendering frame
        # if self.optimized_agent_rendering:
        #     self.optimized_agent_rendering.end_render()
        
        # End frame rendering
        logger.debug("VisualizationIntegration.render: Ending frame render.")
        self.renderer.end_frame()
    
    def handle_event(self, event):
        """
        Handle pygame events for visualization components and zoom.
        
        Args:
            event: Pygame event
            
        Returns:
            bool: True if the event was handled
        """
        if not self.visualization_enabled:
            return False
        
        # Try each component until one handles the event
        for component in self.components:
            if component.handle_event(event):
                return True
        
        # --- ADDED: Handle Mouse Wheel for Zoom --- #
        if event.type == pygame.MOUSEWHEEL:
            # Check if renderer exists and is initialized
            if hasattr(self, 'renderer') and self.renderer and self.renderer.is_initialized():
                zoom_speed = 0.1 # Adjust sensitivity as needed
                # event.y > 0 means scroll up (zoom in), < 0 means scroll down (zoom out)
                zoom_change = event.y * zoom_speed
                current_zoom = self.renderer.camera.get("zoom", 1.0)
                new_zoom = current_zoom + zoom_change
                # Clamp zoom level (using Renderer's internal clamping)
                # clamped_zoom = max(0.5, min(new_zoom, 5.0))
                self.renderer.set_zoom(new_zoom) # Let set_zoom handle clamping
                # logger.debug(f"Zoom changed to: {self.renderer.camera.get("zoom"):.2f}")
                return True # Event handled
            else:
                logger.warning("Renderer not available for zoom handling.")
                return False
        # --- END ADDED --- 

        # Special key bindings for controlling visualization
        if event.type == pygame.KEYDOWN:
            # --- ADDED: Camera Panning with WASD ---
            if hasattr(self, 'renderer') and self.renderer and self.renderer.is_initialized():
                camera_speed = 20 / self.renderer.camera.get("zoom", 1.0) # Move faster when zoomed out
                handled = True
                if event.key == pygame.K_w:
                    self.renderer.camera['y'] -= camera_speed
                elif event.key == pygame.K_s:
                    self.renderer.camera['y'] += camera_speed
                elif event.key == pygame.K_a:
                    self.renderer.camera['x'] -= camera_speed
                elif event.key == pygame.K_d:
                    self.renderer.camera['x'] += camera_speed
                else:
                    handled = False # Key was not WASD

                if handled:
                     # logger.debug(f"Camera moved to: ({self.renderer.camera['x']:.1f}, {self.renderer.camera['y']:.1f})")
                     return True # Event handled
            # --- END ADDED ---

            # Toggle visualization with F3
            if event.key == pygame.K_F3:
                self.toggle_visualization()
            
            # Toggle learning UI with F4
            if event.key == pygame.K_F4 and self.learning_ui:
                self.learning_ui._toggle_visibility()
                return True
        
        return False
    
    def toggle_visualization(self):
        """Toggle whether visualization is enabled."""
        self.visualization_enabled = not self.visualization_enabled
        self.logger.info(f"Visualization {'enabled' if self.visualization_enabled else 'disabled'}")
    
    def set_active_agents(self, agent_ids):
        """
        Set which agents should be visualized.
        
        Args:
            agent_ids: List of agent IDs to visualize
        """
        self.active_agent_ids = agent_ids
        
        # Update learning UI if available
        if self.learning_ui:
            self.learning_ui.set_active_agents(agent_ids)
    
    def set_selected_agent(self, agent_id):
        """
        Set the currently selected agent for detailed visualization.
        
        Args:
            agent_id: ID of the selected agent
        """
        self.selected_agent_id = agent_id
        
        # Update learning UI if available
        if self.learning_ui:
            self.learning_ui.set_agent_selection(agent_id)
    
    def add_component(self, component):
        """
        Add a visualization component.
        
        Args:
            component: UI component to add
        """
        self.components.append(component)
    
    def remove_component(self, component):
        """
        Remove a visualization component.
        
        Args:
            component: UI component to remove
        """
        if component in self.components:
            self.components.remove(component)
    
    def _on_entity_created(self, data):
        """
        Handle entity created events.
        
        Args:
            data: Event data
        """
        # Check if it's an agent
        if 'entity_type' in data and data['entity_type'] == 'agent':
            if 'agent_id' in data:
                # Add to active agents if we don't have too many
                if len(self.active_agent_ids) < 5:  # Limit number of agents we visualize
                    self.active_agent_ids.append(data['agent_id'])
                    
                    # Update learning UI
                    if self.learning_ui:
                        self.learning_ui.set_active_agents(self.active_agent_ids)
    
    def _on_agent_action(self, data):
        """
        Handle agent action events.
        
        Args:
            data: Event data
        """
        # If it's the selected agent, could update visualization immediately
        if 'agent_id' in data and data['agent_id'] == self.selected_agent_id:
            # Could force an immediate update here if desired
            pass
    
    def _on_game_state_changed(self, data):
        """
        Handle game state changed events.
        
        Args:
            data: Event data
        """
        # Auto-hide visualization during certain game states if enabled
        if self.auto_hide and 'state' in data:
            game_state = data['state']
            
            # Hide during combat or other intensive states
            if game_state in ['combat', 'boss_fight', 'high_activity']:
                self.visualization_enabled = False
            else:
                self.visualization_enabled = True
    
    def _on_performance_warning(self, data):
        """
        Handle performance warning events.
        
        Args:
            data: Event data
        """
        # Auto-hide visualization when performance is low
        if self.auto_hide and 'fps' in data:
            fps = data['fps']
            target_fps = data.get('target_fps', 60)
            
            # If FPS drops below 70% of target, disable visualization
            if fps < (target_fps * 0.7):
                self.visualization_enabled = False
    
    def shutdown(self):
        """Shutdown the visualization integration system."""
        # Unsubscribe from events
        system_manager.unsubscribe(SystemEventType.ENTITY_CREATED, self._on_entity_created)
        system_manager.unsubscribe(SystemEventType.AGENT_ACTION, self._on_agent_action)
        system_manager.unsubscribe(SystemEventType.GAME_STATE_CHANGED, self._on_game_state_changed)
        system_manager.unsubscribe(SystemEventType.PERFORMANCE_WARNING, self._on_performance_warning)
        
        # Clear components
        self.components = []
        self.learning_ui = None
        
        self.logger.info("Visualization integration system shutdown") 