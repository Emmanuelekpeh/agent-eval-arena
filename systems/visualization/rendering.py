"""
Rendering utilities for the visualization system.

This module provides rendering functions and utilities for the visualization system,
abstracting away platform-specific rendering details and providing a common interface.
"""

import math
from typing import Dict, List, Tuple, Optional, Any, Callable
import time

# Import base visualization components
from systems.visualization.visualization_system import Color

class RenderingBackend:
    """
    Abstract base class for rendering backends.
    
    Implementations should provide concrete methods for rendering
    primitives like circles, lines, rectangles, and text.
    """
    
    def __init__(self):
        """Initialize the rendering backend."""
        self.initialized = False
        
    def initialize(self, width: int, height: int, title: str = "AI Battle Arena") -> bool:
        """Initialize the rendering backend with the given dimensions."""
        self.width = width
        self.height = height
        self.title = title
        self.initialized = True
        return True
        
    def begin_frame(self) -> None:
        """Begin a new frame for rendering."""
        raise NotImplementedError("Subclasses must implement begin_frame()")
        
    def end_frame(self) -> None:
        """End the current frame and present it to the screen."""
        raise NotImplementedError("Subclasses must implement end_frame()")
        
    def clear(self, color: Color) -> None:
        """Clear the screen to the specified color."""
        raise NotImplementedError("Subclasses must implement clear()")
        
    def draw_circle(self, x: float, y: float, radius: float, color: Color, filled: bool = True) -> None:
        """Draw a circle at the specified position with the given radius and color."""
        raise NotImplementedError("Subclasses must implement draw_circle()")
        
    def draw_line(self, x1: float, y1: float, x2: float, y2: float, 
                  color: Color, thickness: float = 1.0) -> None:
        """Draw a line between the specified points with the given color and thickness."""
        raise NotImplementedError("Subclasses must implement draw_line()")
        
    def draw_rect(self, x: float, y: float, width: float, height: float, 
                 color: Color, filled: bool = True) -> None:
        """Draw a rectangle at the specified position with the given dimensions and color."""
        raise NotImplementedError("Subclasses must implement draw_rect()")
        
    def draw_text(self, x: float, y: float, text: str, color: Color, 
                 size: float = 12.0, centered: bool = False) -> None:
        """Draw text at the specified position with the given color and size."""
        raise NotImplementedError("Subclasses must implement draw_text()")
        
    def draw_polygon(self, points: List[Tuple[float, float]], color: Color, 
                    filled: bool = True) -> None:
        """Draw a polygon with the specified points and color."""
        raise NotImplementedError("Subclasses must implement draw_polygon()")
        
    def shutdown(self) -> None:
        """Clean up the rendering backend."""
        self.initialized = False


class Renderer:
    """
    High-level renderer that uses a backend for actual rendering.
    
    This class provides additional features like:
    - Camera transforms
    - Visual effects
    - Animations
    - Debug rendering
    """
    
    def __init__(self, backend: RenderingBackend = None):
        """Initialize the renderer with an optional backend."""
        self.backend = backend
        self.camera = {
            "x": 0,
            "y": 0,
            "zoom": 1.0,
        }
        self.debug_draw_enabled = False
        self.debug_shapes = []
        
    def set_backend(self, backend: RenderingBackend) -> None:
        """Set the rendering backend."""
        self.backend = backend
        
    def is_initialized(self) -> bool:
        """Check if the renderer is initialized with a backend."""
        return self.backend is not None and self.backend.initialized
        
    def initialize(self, width: int, height: int, title: str = "AI Battle Arena") -> bool:
        """Initialize the renderer with the given dimensions."""
        if self.backend is None:
            return False
        return self.backend.initialize(width, height, title)
        
    def set_camera(self, x: float, y: float, zoom: float = 1.0) -> None:
        """Set the camera position and zoom."""
        self.camera["x"] = x
        self.camera["y"] = y
        self.camera["zoom"] = zoom
        
    def set_zoom(self, zoom: float) -> None:
        """Sets the camera zoom level directly, clamping it within bounds."""
        # Clamp zoom level (e.g., 0.2x to 8x)
        self.camera["zoom"] = max(0.2, min(zoom, 8.0))
        # logger.debug(f"Renderer zoom set to: {self.camera['zoom']:.2f}")
        # We don't use target_zoom here for direct setting via mouse wheel
        
    def world_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        """Convert world coordinates to screen coordinates considering camera position and zoom."""
        if not self.is_initialized():
            return (0, 0)

        zoom = self.camera.get("zoom", 1.0)
        cam_x = self.camera.get("x", 0.0)
        cam_y = self.camera.get("y", 0.0)

        # Calculate the center of the screen
        screen_center_x = self.backend.width / 2
        screen_center_y = self.backend.height / 2

        # Apply zoom first, relative to the camera center
        zoomed_x = (x - cam_x) * zoom
        zoomed_y = (y - cam_y) * zoom

        # Translate to screen coordinates based on screen center
        screen_x = screen_center_x + zoomed_x
        screen_y = screen_center_y + zoomed_y

        return screen_x, screen_y
        
    def screen_to_world(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """Convert screen coordinates back to world coordinates."""
        if not self.is_initialized():
            return (0, 0)
            
        zoom = self.camera.get("zoom", 1.0)
        if abs(zoom) < 1e-6: # Avoid division by zero
             return (self.camera.get("x", 0.0), self.camera.get("y", 0.0)) # Return camera center

        cam_x = self.camera.get("x", 0.0)
        cam_y = self.camera.get("y", 0.0)

        screen_center_x = self.backend.width / 2
        screen_center_y = self.backend.height / 2

        # Reverse the translation from screen center
        relative_screen_x = screen_x - screen_center_x
        relative_screen_y = screen_y - screen_center_y

        # Reverse the zoom relative to the camera center
        world_relative_x = relative_screen_x / zoom
        world_relative_y = relative_screen_y / zoom

        # Add camera position back
        world_x = world_relative_x + cam_x
        world_y = world_relative_y + cam_y

        return world_x, world_y
        
    def begin_frame(self) -> None:
        """Begin a new frame for rendering."""
        if self.is_initialized():
            self.backend.begin_frame()
            self.debug_shapes = []
        
    def end_frame(self) -> None:
        """End the current frame and present it to the screen."""
        if self.is_initialized():
            # Draw any debug shapes
            if self.debug_draw_enabled:
                for shape in self.debug_shapes:
                    shape_type = shape.get("type")
                    if shape_type == "circle":
                        self.backend.draw_circle(
                            shape["x"], shape["y"], shape["radius"],
                            shape["color"], shape.get("filled", True)
                        )
                    elif shape_type == "line":
                        self.backend.draw_line(
                            shape["x1"], shape["y1"], shape["x2"], shape["y2"],
                            shape["color"], shape.get("thickness", 1.0)
                        )
                    elif shape_type == "rect":
                        self.backend.draw_rect(
                            shape["x"], shape["y"], shape["width"], shape["height"],
                            shape["color"], shape.get("filled", True)
                        )
                    elif shape_type == "text":
                        self.backend.draw_text(
                            shape["x"], shape["y"], shape["text"],
                            shape["color"], shape.get("size", 12.0),
                            shape.get("centered", False)
                        )
                    elif shape_type == "polygon":
                        self.backend.draw_polygon(
                            shape["points"], shape["color"],
                            shape.get("filled", True)
                        )
            
            self.backend.end_frame()
        
    def clear(self, color: Color) -> None:
        """Clear the screen to the specified color."""
        if self.is_initialized():
            self.backend.clear(color)
        
    def draw_circle(self, x: float, y: float, radius: float, color: Color, 
                   filled: bool = True, is_world_space: bool = True) -> None:
        if not self.backend or not self.is_initialized(): return
        zoom = self.camera.get("zoom", 1.0)
        if is_world_space:
            screen_x, screen_y = self.world_to_screen(x, y)
            # Scale radius by zoom, ensure minimum visible size (e.g., 1 pixel)
            screen_radius = max(1, radius * zoom)
        else:
            screen_x, screen_y = x, y
            screen_radius = radius

        self.backend.draw_circle(screen_x, screen_y, screen_radius, color, filled)
        
    def draw_line(self, x1: float, y1: float, x2: float, y2: float, color: Color, 
                 thickness: float = 1.0, is_world_space: bool = True) -> None:
        if not self.backend or not self.is_initialized(): return
        zoom = self.camera.get("zoom", 1.0)
        if is_world_space:
            sx1, sy1 = self.world_to_screen(x1, y1)
            sx2, sy2 = self.world_to_screen(x2, y2)
            # Scale thickness by zoom, ensure minimum visible size (e.g., 1 pixel)
            scaled_thickness = max(1, thickness * zoom)
        else:
            sx1, sy1, sx2, sy2 = x1, y1, x2, y2
            scaled_thickness = thickness
        self.backend.draw_line(sx1, sy1, sx2, sy2, color, scaled_thickness)
        
    def draw_rect(self, x: float, y: float, width: float, height: float, color: Color, 
                 filled: bool = True, is_world_space: bool = True) -> None:
        if not self.backend or not self.is_initialized(): return
        zoom = self.camera.get("zoom", 1.0)
        if is_world_space:
            # Convert top-left corner and dimensions
            screen_x, screen_y = self.world_to_screen(x, y)
            # Scale width and height by zoom
            screen_width = width * zoom
            screen_height = height * zoom
            # Avoid drawing rects that become too small/negative
            if screen_width < 1 or screen_height < 1:
                 # Optionally draw a single pixel or skip
                 # self.backend.draw_rect(screen_x, screen_y, 1, 1, color, filled)
                 return 
        else:
            screen_x, screen_y, screen_width, screen_height = x, y, width, height
        self.backend.draw_rect(screen_x, screen_y, screen_width, screen_height, color, filled)
        
    def draw_text(self, x: float, y: float, text: str, color: Color, size: float = 12.0, 
                 centered: bool = False, is_world_space: bool = True) -> None:
        if not self.backend or not self.is_initialized(): return
        zoom = self.camera.get("zoom", 1.0)
        if is_world_space:
            screen_x, screen_y = self.world_to_screen(x, y)
            # Scale font size by zoom, ensure minimum readable size (e.g., 6)
            scaled_size = max(6, int(size * zoom))
        else:
            screen_x, screen_y, scaled_size = x, y, int(size)
        # Don't draw if size is too small after scaling
        if scaled_size < 6 and is_world_space: return
        self.backend.draw_text(screen_x, screen_y, text, color, scaled_size, centered)
        
    def draw_polygon(self, points: List[Tuple[float, float]], color: Color, 
                    filled: bool = True, is_world_space: bool = True) -> None:
        if not self.backend or not self.is_initialized() or not points:
             return
        if is_world_space:
            screen_points = [self.world_to_screen(px, py) for px, py in points]
        else:
            screen_points = points
        # Check if points form a valid polygon (e.g., not collapsed to a point/line after transform)
        # Basic check: area or bounding box size could be used
        if len(screen_points) >= 3:
            min_x = min(p[0] for p in screen_points)
            max_x = max(p[0] for p in screen_points)
            min_y = min(p[1] for p in screen_points)
            max_y = max(p[1] for p in screen_points)
            if max_x - min_x < 1 and max_y - min_y < 1: # Too small to draw
                return
            self.backend.draw_polygon(screen_points, color, filled)
    
    def draw_agent(self, x: float, y: float, radius: float, color: Color,
                   direction: float = 0.0, is_selected: bool = False,
                   health_pct: float = 1.0, energy_pct: float = 1.0,
                   agent_id: Optional[str] = None,
                   last_action_time: Optional[float] = None,
                   current_time: Optional[float] = None) -> None:
        """Draw an agent with an avant-garde style, ID, and action effects.

        Args:
            x, y: Position in world space
            radius: Base size parameter
            color: Base color for the agent
            direction: Facing direction in radians
            is_selected: Whether the agent is currently selected
            health_pct: Health percentage (0.0 to 1.0)
            energy_pct: Energy percentage (0.0 to 1.0)
            agent_id: The unique ID of the agent (for labeling).
            last_action_time: Timestamp of the agent's last significant action (e.g., shooting).
            current_time: Current simulation time, used for effect timing.
        """
        if not self.backend or not self.is_initialized():
            return

        screen_x, screen_y = self.world_to_screen(x, y)
        screen_radius = max(3, radius * self.camera["zoom"]) # Ensure minimum size

        # Define base colors
        outline_color = Color(255, 255, 255) # White outline
        fill_color = color
        secondary_color = Color(0, 0, 0) # Black accent

        # --- Draw Agent Shape (Existing Avant-Garde Style) ---
        num_triangles = 3
        angle_offset = math.pi / 4
        for i in range(num_triangles):
            angle = direction + (i * 2 * math.pi / num_triangles)
            p1 = (screen_x + math.cos(angle) * screen_radius * 1.2,
                  screen_y + math.sin(angle) * screen_radius * 1.2)
            p2 = (screen_x + math.cos(angle + angle_offset) * screen_radius * 0.6,
                  screen_y + math.sin(angle + angle_offset) * screen_radius * 0.6)
            p3 = (screen_x + math.cos(angle - angle_offset) * screen_radius * 0.6,
                  screen_y + math.sin(angle - angle_offset) * screen_radius * 0.6)
            current_fill = fill_color if i % 2 == 0 else secondary_color
            self.backend.draw_polygon([p1, p2, p3], current_fill, filled=True)
            self.backend.draw_polygon([p1, p2, p3], outline_color, filled=False)

        # --- ADDED: Draw Orientation Line ---
        line_length = screen_radius * 1.5 # Make line extend beyond radius
        end_x = screen_x + math.cos(direction) * line_length
        end_y = screen_y + math.sin(direction) * line_length
        # Use a distinct color, perhaps white or the agent's base color
        orientation_color = Color(255, 255, 255, 200) # Semi-transparent white
        self.backend.draw_line(screen_x, screen_y, end_x, end_y, orientation_color, thickness=max(1, 2 * self.camera["zoom"]))
        # --- END ADDED ---

        # --- Shooting Indicator --- 
        shoot_effect_duration = 0.2 # seconds
        if last_action_time is not None and current_time is not None and \
           (current_time - last_action_time) < shoot_effect_duration:
            # Draw a bright yellow star/burst at the front
            flash_color = Color(255, 255, 0, 200)
            flash_radius = screen_radius * 0.5
            num_points = 5
            points = []
            for i in range(num_points * 2):
                r = flash_radius if i % 2 == 0 else flash_radius * 0.5
                angle = direction + i * math.pi / num_points
                px = screen_x + math.cos(direction) * screen_radius + math.cos(angle) * r
                py = screen_y + math.sin(direction) * screen_radius + math.sin(angle) * r
                points.append((px, py))
            self.backend.draw_polygon(points, flash_color, filled=True)

        # --- Selection Indicator (Existing) ---
        if is_selected:
            num_fragments = 8
            pulse = abs(math.sin(time.time() * 5))
            select_radius = screen_radius * (1.3 + pulse * 0.2)
            fragment_angle = 2 * math.pi / num_fragments
            for i in range(num_fragments):
                start_angle = i * fragment_angle
                end_angle = start_angle + fragment_angle * 0.6
                if hasattr(self.backend, 'draw_arc'):
                    self.backend.draw_arc(screen_x, screen_y, select_radius, start_angle, end_angle, outline_color, thickness=2)
                else:
                    p_start = (screen_x + math.cos(start_angle) * select_radius, screen_y + math.sin(start_angle) * select_radius)
                    p_end = (screen_x + math.cos(end_angle) * select_radius, screen_y + math.sin(end_angle) * select_radius)
                    self.backend.draw_line(p_start[0], p_start[1], p_end[0], p_end[1], outline_color, thickness=2)

        # --- Health/Energy Indicators (Existing) ---
        health_bar_width = screen_radius * 1.5
        health_bar_height = max(2, 4 * self.camera["zoom"])
        health_y_offset = screen_radius * 1.5
        self.backend.draw_rect(screen_x - health_bar_width / 2, screen_y + health_y_offset,
                               health_bar_width, health_bar_height, Color(100, 0, 0), filled=True)
        health_fill_width = health_bar_width * health_pct
        self.backend.draw_rect(screen_x - health_bar_width / 2, screen_y + health_y_offset,
                               health_fill_width, health_bar_height, Color(0, 255, 0), filled=True)
        energy_y_offset = health_y_offset + health_bar_height + max(1, 2 * self.camera["zoom"])
        self.backend.draw_rect(screen_x - health_bar_width / 2, screen_y + energy_y_offset,
                               health_bar_width, health_bar_height, Color(0, 0, 100), filled=True)
        energy_fill_width = health_bar_width * energy_pct
        self.backend.draw_rect(screen_x - health_bar_width / 2, screen_y + energy_y_offset,
                               energy_fill_width, health_bar_height, Color(0, 150, 255), filled=True)

        # --- Agent ID Label ---
        if agent_id and self.camera["zoom"] > 0.8: # Only draw if zoomed in enough
            label_y_offset = energy_y_offset + health_bar_height + max(2, 4 * self.camera["zoom"])
            label_size = max(8, int(10 * self.camera["zoom"])) # Scale size with zoom
            # Extract short ID (e.g., last part after '-')
            short_id = agent_id.split('-')[-1]
            self.backend.draw_text(screen_x, screen_y + label_y_offset,
                                   short_id, Color(200, 200, 200),
                                   size=label_size, centered=True)
    
    def draw_resource(self, x: float, y: float, resource_type: str, size: float,
                     color: Color) -> None:
        """
        Draw a resource at the specified position.
        
        Args:
            x, y: Position of the resource in world space
            resource_type: Type of resource, used to determine shape
            size: Size of the resource
            color: Color of the resource
        """
        if not self.is_initialized():
            return
            
        # Different shapes for different resource types
        if resource_type == "energy":
            # Draw a diamond shape
            points = [
                (x, y - size),  # top
                (x + size, y),  # right
                (x, y + size),  # bottom
                (x - size, y),  # left
            ]
            self.draw_polygon(points, color)
            
        elif resource_type == "health":
            # Draw a cross shape (using lines)
            thickness = size * 0.4
            line_length = size * 0.8
            
            # Vertical line
            self.draw_line(x, y - line_length, x, y + line_length, color, thickness)
            
            # Horizontal line
            self.draw_line(x - line_length, y, x + line_length, y, color, thickness)
            
        elif resource_type == "shield":
            # Draw a shield shape (circle with a gap at the bottom)
            self.draw_circle(x, y, size, color)
            
            # Draw a black circle to create the gap
            gap_size = size * 0.6
            offset = size * 0.3
            self.draw_circle(x, y + offset, gap_size, Color(0, 0, 0))
            
        else:
            # Default shape is a circle
            self.draw_circle(x, y, size, color)
    
    def draw_team_formation(self, positions: List[Tuple[float, float]], 
                           team_color: Color, formation_type: str) -> None:
        """
        Draw team formation lines connecting agent positions.
        
        Args:
            positions: List of (x, y) positions for agents in the formation
            team_color: Color of the team/formation lines
            formation_type: Type of formation, affects how lines are drawn
        """
        if not self.is_initialized() or len(positions) < 2:
            return
            
        # Draw lines with reduced alpha
        line_color = Color(team_color.r, team_color.g, team_color.b, 120)
        line_thickness = 1.5
        
        if formation_type == "line":
            # Draw a line connecting all agents in sequence
            for i in range(len(positions) - 1):
                x1, y1 = positions[i]
                x2, y2 = positions[i + 1]
                self.draw_line(x1, y1, x2, y2, line_color, line_thickness)
                
        elif formation_type == "triangle":
            # Draw a triangle connecting all agents
            if len(positions) >= 3:
                # Draw the perimeter
                for i in range(len(positions)):
                    x1, y1 = positions[i]
                    x2, y2 = positions[(i + 1) % len(positions)]
                    self.draw_line(x1, y1, x2, y2, line_color, line_thickness)
                    
        elif formation_type == "square" or formation_type == "rectangle":
            # Draw a square/rectangle connecting all agents
            if len(positions) >= 4:
                # Draw the perimeter
                for i in range(len(positions)):
                    x1, y1 = positions[i]
                    x2, y2 = positions[(i + 1) % len(positions)]
                    self.draw_line(x1, y1, x2, y2, line_color, line_thickness)
                    
        elif formation_type == "circle":
            # Draw a circle with agents positioned around it
            if len(positions) >= 3:
                # Find the center
                center_x = sum(x for x, _ in positions) / len(positions)
                center_y = sum(y for _, y in positions) / len(positions)
                
                # Draw lines to each position
                for x, y in positions:
                    self.draw_line(center_x, center_y, x, y, line_color, line_thickness)
                    
        elif formation_type == "arrow":
            # Draw an arrow formation
            if len(positions) >= 3:
                # The first position is the tip of the arrow
                tip_x, tip_y = positions[0]
                
                # Draw lines from the tip to each other position
                for i in range(1, len(positions)):
                    x, y = positions[i]
                    self.draw_line(tip_x, tip_y, x, y, line_color, line_thickness)
                    
                # Connect the back positions
                for i in range(1, len(positions) - 1):
                    x1, y1 = positions[i]
                    x2, y2 = positions[i + 1]
                    self.draw_line(x1, y1, x2, y2, line_color, line_thickness)
        else:
            # Default: just connect each agent to each other agent
            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    x1, y1 = positions[i]
                    x2, y2 = positions[j]
                    self.draw_line(x1, y1, x2, y2, line_color, line_thickness)
    
    def enable_debug_draw(self, enabled: bool = True) -> None:
        """Enable or disable debug drawing."""
        self.debug_draw_enabled = enabled
        
    def debug_draw_circle(self, x: float, y: float, radius: float, color: Color, 
                          filled: bool = True, is_world_space: bool = True) -> None:
        """
        Add a circle to the debug drawing list.
        Only drawn if debug drawing is enabled.
        """
        if is_world_space:
            screen_x, screen_y = self.world_to_screen(x, y)
            screen_radius = radius * self.camera["zoom"]
            self.debug_shapes.append({
                "type": "circle",
                "x": screen_x,
                "y": screen_y,
                "radius": screen_radius,
                "color": color,
                "filled": filled
            })
        else:
            self.debug_shapes.append({
                "type": "circle",
                "x": x,
                "y": y,
                "radius": radius,
                "color": color,
                "filled": filled
            })
            
    def debug_draw_line(self, x1: float, y1: float, x2: float, y2: float, 
                       color: Color, thickness: float = 1.0, 
                       is_world_space: bool = True) -> None:
        """
        Add a line to the debug drawing list.
        Only drawn if debug drawing is enabled.
        """
        if is_world_space:
            screen_x1, screen_y1 = self.world_to_screen(x1, y1)
            screen_x2, screen_y2 = self.world_to_screen(x2, y2)
            screen_thickness = thickness * self.camera["zoom"]
            self.debug_shapes.append({
                "type": "line",
                "x1": screen_x1,
                "y1": screen_y1,
                "x2": screen_x2,
                "y2": screen_y2,
                "color": color,
                "thickness": screen_thickness
            })
        else:
            self.debug_shapes.append({
                "type": "line",
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "color": color,
                "thickness": thickness
            })
            
    def debug_draw_text(self, x: float, y: float, text: str, color: Color, 
                       size: float = 12.0, is_world_space: bool = True) -> None:
        """
        Add text to the debug drawing list.
        Only drawn if debug drawing is enabled.
        """
        if is_world_space:
            screen_x, screen_y = self.world_to_screen(x, y)
            screen_size = size * self.camera["zoom"]
            self.debug_shapes.append({
                "type": "text",
                "x": screen_x,
                "y": screen_y,
                "text": text,
                "color": color,
                "size": screen_size
            })
        else:
            self.debug_shapes.append({
                "type": "text",
                "x": x,
                "y": y,
                "text": text,
                "color": color,
                "size": size
            })
    
    def shutdown(self) -> None:
        """Clean up the renderer and its backend."""
        if self.backend is not None:
            self.backend.shutdown() 