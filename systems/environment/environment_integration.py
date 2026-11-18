"""
Environment Integration Module for Battle Royale

This module integrates the frustum culling system with the battle royale environment,
providing stage-based rendering with optimized performance.
"""

import time
import logging
import pygame
from typing import Dict, List, Any, Optional

from systems.core.base_system import BaseSystem
from systems.environment.frustum_culling import FrustumCullingSystem, Frustum, AABB

logger = logging.getLogger(__name__)

class StageBasedEnvironment(BaseSystem):
    """
    System that manages stage-based environment rendering with frustum culling
    optimization for the battle royale environment.
    """
    
    def __init__(self):
        """Initialize the stage-based environment system."""
        super().__init__(name="stage_based_environment", priority=60)
        self.environment = None
        self.frustum_culling = None
        self.visualization_integration = None
        
        # Stage management
        self.current_stage = 0
        self.total_stages = 3  # Default number of stages
        self.entities_per_stage = [100, 500, 1000]  # Different entity counts per stage
        
        # Performance tracking
        self.render_time = 0.0
        self.update_time = 0.0
        self.frame_times = []
        self.max_frame_times = 60  # Track last 60 frames
        self.current_fps = 60
        
        # Display options
        self.show_debug_info = True
        self.show_stage_info = True
        
        logger.info("StageBasedEnvironment initialized")
    
    def initialize(self):
        """Initialize the system and get references to dependencies."""
        # Get reference to main environment
        self.environment = self.get_system("battle_royale_env")
        if not self.environment:
            logger.error("Could not get battle_royale_env")
            return False
        
        # Get reference to visualization integration
        self.visualization_integration = self.get_system("visualization_integration")
        if not self.visualization_integration:
            logger.warning("Could not get visualization_integration, some features may be limited")
        
        # Create frustum culling system
        self.frustum_culling = FrustumCullingSystem(self.environment)
        
        # Generate initial stage
        self.load_stage(0)
        
        # Subscribe to events
        self.subscribe_to_event("key_press", self._on_key_press)
        self.subscribe_to_event("game_state_changed", self._on_game_state_changed)
        
        logger.info("StageBasedEnvironment successfully initialized")
        return True
    
    def load_stage(self, stage_index):
        """
        Load a specific stage with preset parameters
        
        Args:
            stage_index: Index of stage to load (0-based)
        """
        if stage_index < 0 or stage_index >= self.total_stages:
            logger.warning(f"Attempted to load invalid stage index: {stage_index}")
            return
        
        self.current_stage = stage_index
        
        # Clear existing entities if needed
        if hasattr(self.environment, 'clear_entities'):
            self.environment.clear_entities()
        
        # Different stage configurations
        num_entities = self.entities_per_stage[stage_index]
        hierarchical = True  # Use hierarchical culling for all stages
        
        logger.info(f"Loading stage {stage_index + 1}/{self.total_stages} with {num_entities} entities")
        
        # Generate the new stage
        start_time = time.time()
        self.frustum_culling.generate_stage(num_entities, hierarchical)
        end_time = time.time()
        
        logger.info(f"Stage {stage_index + 1} loaded in {(end_time - start_time) * 1000:.2f}ms")
        
        # Publish event that stage was loaded
        self.emit_event("stage_loaded", {
            "stage_index": stage_index,
            "num_entities": num_entities,
            "load_time": end_time - start_time
        })
    
    def load_next_stage(self):
        """Load the next stage, wrapping around if needed"""
        next_stage = (self.current_stage + 1) % self.total_stages
        self.load_stage(next_stage)
    
    def load_previous_stage(self):
        """Load the previous stage, wrapping around if needed"""
        prev_stage = (self.current_stage - 1) % self.total_stages
        self.load_stage(prev_stage)
    
    def update(self, delta_time):
        """
        Update the system for the current frame
        
        Args:
            delta_time: Time since last update
        """
        start_time = time.time()
        
        # Update frustum culling system with current camera parameters
        self.frustum_culling.update_camera()
        
        # Update FPS calculation
        self.frame_times.append(delta_time)
        if len(self.frame_times) > self.max_frame_times:
            self.frame_times.pop(0)
        
        if self.frame_times:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            if avg_frame_time > 0:
                self.current_fps = 1.0 / avg_frame_time
        
        end_time = time.time()
        self.update_time = end_time - start_time
    
    def pre_render(self, screen):
        """
        Prepare for rendering by updating culling and getting visible entities
        
        Args:
            screen: Pygame surface to render to
        """
        # Update frustum with current camera before rendering
        self.frustum_culling.update_camera()
        
        # Get visible entities (this will be used by environment.render)
        visible_entities = self.frustum_culling.get_visible_entities()
        
        # Make visible entities available to environment
        if hasattr(self.environment, 'set_visible_entities'):
            self.environment.set_visible_entities(visible_entities)
    
    def post_render(self, screen):
        """
        Render debug information after the main rendering
        
        Args:
            screen: Pygame surface to render to
        """
        if not self.show_debug_info:
            return
        
        # Render stage and debugging information
        font = pygame.font.SysFont(None, 24)
        
        # FPS counter
        fps_text = f"FPS: {self.current_fps:.1f}"
        fps_color = (0, 255, 0) if self.current_fps >= 55 else (255, 255, 0) if self.current_fps >= 30 else (255, 0, 0)
        fps_surface = font.render(fps_text, True, fps_color)
        screen.blit(fps_surface, (10, 10))
        
        # Stage info
        if self.show_stage_info:
            stage_text = f"Stage: {self.current_stage + 1}/{self.total_stages} - {self.entities_per_stage[self.current_stage]} entities"
            stage_surface = font.render(stage_text, True, (255, 255, 255))
            screen.blit(stage_surface, (10, 40))
            
            # Culling efficiency
            total = self.frustum_culling.stage_manager.total_entities
            rendered = self.frustum_culling.stage_manager.rendered_entities
            if total > 0:
                culling_text = f"Entities: {rendered}/{total} ({rendered/total*100:.1f}% rendered)"
                culling_surface = font.render(culling_text, True, (255, 255, 255))
                screen.blit(culling_surface, (10, 70))
        
        # Controls hint
        controls_text = "Controls: [N]ext stage, [P]revious stage, [F1] Toggle debug, [F2] Toggle culling"
        controls_surface = font.render(controls_text, True, (200, 200, 200))
        screen.blit(controls_surface, (10, screen.get_height() - 30))
    
    def _on_key_press(self, event_data):
        """
        Handle key press events
        
        Args:
            event_data: Event data containing key information
        """
        if 'key' not in event_data:
            return
        
        key = event_data['key']
        
        # Handle stage navigation
        if key == pygame.K_n:
            self.load_next_stage()
        elif key == pygame.K_p:
            self.load_previous_stage()
        
        # Toggle options
        elif key == pygame.K_F1:
            self.show_debug_info = not self.show_debug_info
            logger.info(f"Debug info display {'enabled' if self.show_debug_info else 'disabled'}")
        elif key == pygame.K_F2:
            self.frustum_culling.toggle_culling()
    
    def _on_game_state_changed(self, event_data):
        """
        Handle game state changed events
        
        Args:
            event_data: Event data containing state information
        """
        if 'state' not in event_data:
            return
        
        state = event_data['state']
        
        # Automatically adjust stage complexity based on game state
        if state == 'menu' or state == 'paused':
            # Load a more visually appealing but less complex stage for menus
            if self.current_stage != 0:
                self.load_stage(0)
        elif state == 'game_start':
            # Reset to first stage when game starts
            self.load_stage(0)
    
    def integrate_with_environment(self):
        """
        Integrate this system with the battle royale environment
        
        This method should be called after initialization to patch the necessary
        functions in the environment to use frustum culling
        """
        if not self.environment:
            logger.error("Cannot integrate with environment - reference is missing")
            return
        
        # Store the original render method
        original_render = self.environment.render
        
        # Create a replacement render method that uses frustum culling
        def render_with_culling(screen):
            start_time = time.time()
            
            # Pre-render: update culling and get visible entities
            self.pre_render(screen)
            
            # Call the original render method
            original_render(screen)
            
            # Post-render: draw debug information
            self.post_render(screen)
            
            end_time = time.time()
            self.render_time = end_time - start_time
            
            # Update performance metrics
            self.frustum_culling.update_performance_metrics(self.render_time)
        
        # Replace the environment's render method
        self.environment.render = render_with_culling
        
        # Add method to set visible entities if not present
        if not hasattr(self.environment, 'set_visible_entities'):
            def set_visible_entities(entities):
                self.environment._visible_entities = entities
            self.environment.set_visible_entities = set_visible_entities
            self.environment._visible_entities = []
        
        # Patch the environment's entity rendering to respect visibility
        original_render_entities = getattr(self.environment, '_render_entities', None)
        if original_render_entities:
            def render_entities_with_culling(screen):
                # If original method exists, call it with filtered entities
                if hasattr(self.environment, '_visible_entities'):
                    entities_to_render = self.environment._visible_entities
                else:
                    entities_to_render = self.environment.entities.values()
                
                # Render only visible entities
                for entity in entities_to_render:
                    if isinstance(entity, dict) and 'id' in entity:
                        entity_id = entity['id']
                        self.environment._render_entity(entity, screen)
            
            # Replace the entity rendering method
            self.environment._render_entities = render_entities_with_culling
        
        logger.info("Successfully integrated stage-based environment with frustum culling")
    
    def shutdown(self):
        """Shutdown the stage-based environment system."""
        logger.info("StageBasedEnvironment shutting down")
        
        # Restore original methods if we patched them
        if self.environment and hasattr(self.environment, '_original_render'):
            self.environment.render = self.environment._original_render
            
        # Clear references
        self.environment = None
        self.frustum_culling = None
        self.visualization_integration = None 