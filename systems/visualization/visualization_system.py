"""
Visualization System for the AI Battle Arena.

This system is responsible for rendering the simulation state to a visual display,
including agents, teams, resources, terrain, and combat interactions.
"""

import math
import random
from typing import Dict, List, Tuple, Optional, Any

from systems.core.base_system import BaseSystem

class Color:
    """Represents an RGB color with optional alpha."""
    
    def __init__(self, r: int, g: int, b: int, a: int = 255):
        """Initialize a color with RGB values (0-255)."""
        self.r = max(0, min(r, 255))
        self.g = max(0, min(g, 255))
        self.b = max(0, min(b, 255))
        self.a = max(0, min(a, 255))
    
    @staticmethod
    def from_hex(hex_str: str) -> 'Color':
        """Create a Color from a hex string (#RRGGBB or #RRGGBBAA)."""
        hex_str = hex_str.lstrip('#')
        if len(hex_str) == 6:
            r, g, b = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
            return Color(r, g, b)
        elif len(hex_str) == 8:
            r, g, b, a = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4, 6))
            return Color(r, g, b, a)
        raise ValueError(f"Invalid hex color: {hex_str}")
    
    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Return color as a tuple (r, g, b, a)."""
        return (self.r, self.g, self.b, self.a)
    
    def to_hex(self) -> str:
        """Return color as a hex string (#RRGGBBAA)."""
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}{self.a:02x}"
    
    def with_alpha(self, alpha: int) -> 'Color':
        """Return a copy of this color with the specified alpha value."""
        return Color(self.r, self.g, self.b, alpha)


class VisualizationSystem(BaseSystem):
    """
    System responsible for visualizing the simulation state.
    
    This system renders the current state of all entities, including agents,
    teams, resources, terrain, and combat interactions, into a visual form
    for display and monitoring.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the visualization system with the provided configuration."""
        super().__init__("VisualizationSystem")
        self.config = config or {}
        
        # Default colors for different entity types
        self.color_scheme = {
            "agent": Color(100, 100, 255),
            "team": {
                "team_1": Color(255, 100, 100),
                "team_2": Color(100, 255, 100),
                "team_3": Color(255, 255, 100),
                "team_4": Color(255, 100, 255),
                "team_5": Color(100, 255, 255),
            },
            "resource": {
                "energy": Color(255, 255, 0),
                "health": Color(0, 255, 0),
                "shield": Color(0, 200, 255),
            },
            "terrain": {
                "grass": Color(100, 200, 100),
                "water": Color(100, 100, 200),
                "rock": Color(150, 150, 150),
                "sand": Color(200, 200, 150),
            },
            "combat": {
                "attack": Color(255, 0, 0),
                "defend": Color(0, 0, 255),
            },
            "communication": Color(255, 255, 255),
            "background": Color(40, 40, 40),
        }
        
        # Visual settings
        self.settings = {
            "agent_size": 10,
            "resource_size": 8,
            "line_thickness": 2,
            "animation_speed": 1.0,
            "show_team_formations": True,
            "show_agent_health": True,
            "show_agent_energy": True,
            "show_resource_transfers": True,
            "show_communications": True,
            "show_combat": True,
            "show_terrain": True,
            "show_grid": False,
            "grid_size": 20,
        }
        
        # Update settings from config
        if config:
            self.settings.update(config.get("visualization_settings", {}))
            
            # Update color scheme if provided in config
            config_colors = config.get("color_scheme", {})
            for category, colors in config_colors.items():
                if isinstance(self.color_scheme.get(category), dict):
                    self.color_scheme[category].update(colors)
                else:
                    self.color_scheme[category] = colors
        
        # Visual effects currently active
        self.active_effects = []
        
        # Display surface (to be set by the rendering system)
        self.display_surface = None
        
        # Camera properties
        self.camera = {
            "x": 0,
            "y": 0,
            "zoom": 1.0,
            "target_zoom": 1.0,
            "target_x": 0,
            "target_y": 0,
            "smooth_factor": 0.1,
        }
        
        # Performance metrics for visual optimization
        self.performance_metrics = {
            "frame_time": 0,
            "render_count": 0,
            "entities_rendered": 0,
        }
    
    def initialize(self) -> None:
        """Initialize the visualization system."""
        self.logger.info("Initializing visualization system")
        
        # Subscribe to relevant events
        self.subscribe_to_event("agent_moved", self._on_agent_moved)
        self.subscribe_to_event("resource_collected", self._on_resource_collected)
        self.subscribe_to_event("resource_transferred", self._on_resource_transferred)
        self.subscribe_to_event("combat_started", self._on_combat_started)
        self.subscribe_to_event("combat_ended", self._on_combat_ended)
        self.subscribe_to_event("agent_damaged", self._on_agent_damaged)
        self.subscribe_to_event("team_formed", self._on_team_formed)
        self.subscribe_to_event("message_sent", self._on_message_sent)
    
    def update(self, delta_time: float) -> None:
        """Update the visualization system."""
        # Update camera smoothing
        self._update_camera(delta_time)
        
        # Update active visual effects
        self._update_effects(delta_time)
    
    def shutdown(self) -> None:
        """Clean up the visualization system."""
        self.logger.info("Shutting down visualization system")
    
    def set_display_surface(self, surface: Any) -> None:
        """Set the display surface for rendering."""
        self.display_surface = surface
    
    def move_camera(self, x: float, y: float) -> None:
        """Move the camera to the specified coordinates."""
        self.camera["target_x"] = x
        self.camera["target_y"] = y
    
    def set_zoom(self, zoom: float) -> None:
        """Set the camera zoom level."""
        self.camera["target_zoom"] = max(0.5, min(zoom, 3.0))
    
    def add_visual_effect(self, effect_type: str, position: Tuple[float, float], 
                          color: Color, duration: float, data: Any = None) -> None:
        """
        Add a visual effect to the scene.
        
        Args:
            effect_type: Type of effect (e.g., 'explosion', 'highlight', 'trail')
            position: (x, y) coordinates for the effect
            color: Color of the effect
            duration: How long the effect should last in seconds
            data: Additional data needed for the effect
        """
        self.active_effects.append({
            "type": effect_type,
            "position": position,
            "color": color,
            "duration": duration,
            "elapsed": 0.0,
            "data": data
        })
    
    def get_team_color(self, team_id: str) -> Color:
        """Get the color for a team based on its ID."""
        team_colors = self.color_scheme.get("team", {})
        if team_id in team_colors:
            color_val = team_colors[team_id]
            if isinstance(color_val, str) and color_val.startswith("#"):
                 try:
                      return Color.from_hex(color_val)
                 except ValueError:
                      pass # Fall through to default/random
            elif isinstance(color_val, (list, tuple)) and len(color_val) >= 3:
                 return Color(*color_val[:3], a=color_val[3] if len(color_val) > 3 else 255)
            elif isinstance(color_val, Color):
                 return color_val
            # Fall through if format is unexpected
        
        # If team ID not found or format invalid, generate a random but consistent color
        # Ensure seed resets if we call random elsewhere, or use a dedicated Random instance
        try:
            # Use hash for potentially better distribution and consistency across runs/platforms
            seed_val = hash(team_id)
            random.seed(seed_val)
            r = random.randint(100, 255)
            g = random.randint(100, 255)
            b = random.randint(100, 255)
            # Store generated color to avoid re-generation and ensure consistency within session
            # Ensure the 'team' key exists
            if "team" not in self.color_scheme: self.color_scheme["team"] = {}
            self.color_scheme["team"][team_id] = Color(r, g, b) 
            return self.color_scheme["team"][team_id]
        except Exception as e:
             # Fallback to a default color in case of hashing/seeding issues
             print(f"Error generating color for team {team_id}: {e}")
             return self.color_scheme.get("agent", Color(150, 150, 150))

    def get_agent_color(self, agent_id: str, team_id: Optional[str] = None) -> Color:
        """Gets the color for an agent, using team color if available, otherwise generating a unique color."""
        if team_id:
            return self.get_team_color(team_id)
        
        # If no team, check if a color was already generated for this specific agent
        agent_colors = self.color_scheme.setdefault("individual_agents", {})
        if agent_id in agent_colors:
             # Ensure it's a Color object
             color_val = agent_colors[agent_id]
             if isinstance(color_val, Color):
                  return color_val
             # Attempt conversion if needed (e.g., loaded from config as list/hex)
             elif isinstance(color_val, str) and color_val.startswith("#"): return Color.from_hex(color_val)
             elif isinstance(color_val, (list, tuple)) and len(color_val) >= 3: return Color(*color_val[:3], a=color_val[3] if len(color_val) > 3 else 255)
             # else fall through to generate new

        # Generate a unique color for the individual agent
        try:
            seed_val = hash(agent_id) # Use agent_id for unique seed
            random.seed(seed_val)
            r = random.randint(50, 200) # Use a slightly different range to distinguish individuals?
            g = random.randint(50, 200)
            b = random.randint(50, 200)
            agent_color = Color(r, g, b)
            agent_colors[agent_id] = agent_color # Store the generated color
            return agent_color
        except Exception as e:
             print(f"Error generating color for agent {agent_id}: {e}")
             return self.color_scheme.get("agent", Color(150, 150, 150)) # Default fallback
    
    def _update_camera(self, delta_time: float) -> None:
        """Update camera position with smooth transitions."""
        smooth = self.camera["smooth_factor"]
        
        # Smooth camera movement
        self.camera["x"] += (self.camera["target_x"] - self.camera["x"]) * smooth
        self.camera["y"] += (self.camera["target_y"] - self.camera["y"]) * smooth
        
        # Smooth zoom
        self.camera["zoom"] += (self.camera["target_zoom"] - self.camera["zoom"]) * smooth
    
    def _update_effects(self, delta_time: float) -> None:
        """Update all active visual effects."""
        # Update elapsed time and remove expired effects
        i = 0
        while i < len(self.active_effects):
            effect = self.active_effects[i]
            effect["elapsed"] += delta_time
            
            if effect["elapsed"] >= effect["duration"]:
                self.active_effects.pop(i)
            else:
                i += 1
    
    def _on_agent_moved(self, agent_id: str, position: Tuple[float, float], 
                       velocity: Tuple[float, float], **kwargs) -> None:
        """Handle agent movement events for visualization."""
        # We could add movement trail effects here
        if abs(velocity[0]) > 1.0 or abs(velocity[1]) > 1.0:
            speed = math.sqrt(velocity[0]**2 + velocity[1]**2)
            if speed > 5.0:  # Only show trails for fast-moving agents
                trail_color = self.color_scheme["agent"].with_alpha(100)
                self.add_visual_effect("trail", position, trail_color, 0.5, {
                    "velocity": velocity,
                    "length": min(speed * 0.5, 10)
                })
    
    def _on_resource_collected(self, agent_id: str, resource_type: str, 
                              position: Tuple[float, float], amount: float, **kwargs) -> None:
        """Handle resource collection events for visualization."""
        resource_color = self.color_scheme["resource"].get(
            resource_type, Color(255, 255, 255))
        
        self.add_visual_effect("collect", position, resource_color, 0.8, {
            "resource_type": resource_type,
            "amount": amount
        })
    
    def _on_resource_transferred(self, sender_id: str, receiver_id: str, 
                               resource_type: str, amount: float, 
                               position: Tuple[float, float], **kwargs) -> None:
        """Handle resource transfer events for visualization."""
        resource_color = self.color_scheme["resource"].get(
            resource_type, Color(255, 255, 255))
        
        self.add_visual_effect("transfer", position, resource_color, 1.2, {
            "resource_type": resource_type,
            "amount": amount,
            "sender_id": sender_id,
            "receiver_id": receiver_id
        })
    
    def _on_combat_started(self, combat_id: str, attacker_id: str, 
                          defender_id: str, position: Tuple[float, float], **kwargs) -> None:
        """Handle combat start events for visualization."""
        combat_color = self.color_scheme["combat"]["attack"]
        
        self.add_visual_effect("combat_start", position, combat_color, 1.0, {
            "combat_id": combat_id,
            "attacker_id": attacker_id,
            "defender_id": defender_id
        })
    
    def _on_combat_ended(self, combat_id: str, winner_id: str, 
                        position: Tuple[float, float], **kwargs) -> None:
        """Handle combat end events for visualization."""
        # Different color based on whether there was a winner
        if winner_id:
            color = self.color_scheme["combat"]["attack"]
        else:
            color = self.color_scheme["combat"]["defend"]
        
        self.add_visual_effect("combat_end", position, color, 1.5, {
            "combat_id": combat_id,
            "winner_id": winner_id
        })
    
    def _on_agent_damaged(self, agent_id: str, damage: float, 
                         position: Tuple[float, float], **kwargs) -> None:
        """Handle agent damage events for visualization."""
        damage_color = Color(255, 0, 0, 200)
        
        # Scale effect by damage amount
        effect_size = min(damage / 10.0, 2.0)
        
        self.add_visual_effect("damage", position, damage_color, 0.7, {
            "agent_id": agent_id,
            "damage": damage,
            "size": effect_size
        })
    
    def _on_team_formed(self, team_id: str, member_ids: List[str], 
                       formation: str, **kwargs) -> None:
        """Handle team formation events for visualization."""
        team_color = self.get_team_color(team_id)
        
        # We don't have a position for this event, so we can't add a visual effect
        # This would normally be handled during rendering when we know positions
        pass
    
    def _on_message_sent(self, sender_id: str, receiver_id: str, 
                        message_type: str, **kwargs) -> None:
        """Handle message sent events for visualization."""
        # This would normally look up positions from the system state
        # and then create a visual effect
        pass 