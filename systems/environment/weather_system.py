import random
import pygame
from typing import Tuple, List, Dict, Any
from systems.visualization.visualization_system import Color

class WeatherSystem:
    """
    Weather system for the environment.
    
    Manages different weather types and their effects on gameplay.
    """
    
    def __init__(self):
        """Initialize the weather system."""
        self.current_weather = "clear"
        self.weather_duration = random.randint(600, 1800) # 10-30 seconds
        self.current_duration = 0
        self.transition_duration = 120  # 2 seconds at 60 FPS
        self.transition_progress = 0
        self.transitioning = False
        self.previous_weather = None
        
        # Weather types and their properties
        self.weather_types = {
            "clear": {
                "visibility": 1.0,
                "movement_modifier": 1.0,
                "particles": None,
                "overlay_color": None,
                "sound": None,
                "probability": 0.4
            },
            "rain": {
                "visibility": 0.8,
                "movement_modifier": 0.9,
                "particles": {"color": (120, 120, 255), "size": 2, "speed": 5, "density": 100},
                "overlay_color": (100, 100, 150, 30),
                "sound": "rain",
                "probability": 0.3
            },
            "fog": {
                "visibility": 0.5,
                "movement_modifier": 0.95,
                "particles": None,
                "overlay_color": (200, 200, 200, 100),
                "sound": None,
                "probability": 0.2
            },
            "storm": {
                "visibility": 0.6,
                "movement_modifier": 0.8,
                "particles": {"color": (90, 90, 200), "size": 3, "speed": 8, "density": 150},
                "overlay_color": (80, 80, 100, 50),
                "sound": "storm",
                "probability": 0.1
            }
        }
        
        # Particle systems for weather effects
        self.particles = []
    
    def update(self, delta_time: float = 0.0):
        """Update the weather system."""
        # Use delta_time if logic becomes time-dependent
        frame_increment = 1 # Assume updates happen per frame for now
        self.current_duration += frame_increment
        
        # Handle weather transition
        if self.transitioning:
            self.transition_progress += 1
            if self.transition_progress >= self.transition_duration:
                self.transitioning = False
                self.transition_progress = 0
                self.previous_weather = None
        
        # Change weather if duration exceeded
        if self.current_duration >= self.weather_duration:
            self._change_weather()
            self.current_duration = 0
        
        # Update particles
        self._update_particles()
    
    def _change_weather(self):
        """Change to a new weather type based on probabilities."""
        self.previous_weather = self.current_weather
        self.transitioning = True
        
        # Select new weather based on probabilities
        weather_options = []
        for weather, props in self.weather_types.items():
            if weather != self.current_weather:  # Avoid same weather twice
                weather_options.extend([weather] * int(props["probability"] * 100))
        
        self.current_weather = random.choice(weather_options) if weather_options else "clear"
    
    def _update_particles(self):
        """Update weather particle effects."""
        # Clear old particles
        self.particles = [p for p in self.particles if p["y"] < 800]
        
        # Add new particles based on current weather
        weather_props = self.weather_types[self.current_weather]
        if weather_props["particles"]:
            particles_config = weather_props["particles"]
            
            # Determine number of particles to add based on density
            to_add = particles_config["density"] // 60  # Add density/60 particles per frame
            
            for _ in range(to_add):
                self.particles.append({
                    "x": random.randint(0, 1280),
                    "y": -10,
                    "speed": particles_config["speed"] + random.uniform(-1, 1),
                    "size": particles_config["size"],
                    "color": particles_config["color"]
                })
        
        # Move particles
        for particle in self.particles:
            particle["y"] += particle["speed"]
            
            # Add wind effect for certain weather types
            if self.current_weather in ["rain", "storm"]:
                particle["x"] += random.uniform(-1, 1)
    
    def get_visibility(self) -> float:
        """
        Get the current visibility factor.
        
        Returns:
            float: Visibility factor (0.0-1.0)
        """
        weather_props = self.weather_types[self.current_weather]
        
        if self.transitioning and self.previous_weather:
            # Blend visibility during transition
            prev_visibility = self.weather_types[self.previous_weather]["visibility"]
            current_visibility = weather_props["visibility"]
            
            blend_factor = self.transition_progress / self.transition_duration
            return prev_visibility * (1 - blend_factor) + current_visibility * blend_factor
        
        return weather_props["visibility"]
    
    def get_movement_modifier(self) -> float:
        """
        Get the current movement modifier.
        
        Returns:
            float: Movement speed modifier (0.0-1.0)
        """
        weather_props = self.weather_types[self.current_weather]
        
        if self.transitioning and self.previous_weather:
            # Blend movement modifier during transition
            prev_modifier = self.weather_types[self.previous_weather]["movement_modifier"]
            current_modifier = weather_props["movement_modifier"]
            
            blend_factor = self.transition_progress / self.transition_duration
            return prev_modifier * (1 - blend_factor) + current_modifier * blend_factor
        
        return weather_props["movement_modifier"]
    
    def draw(self, renderer):
        """Draw weather effects using the provided Renderer."""
        if not renderer or not renderer.is_initialized():
            # logger.warning("WeatherSystem.draw: Renderer not available.")
            return
            
        # Draw particles (assuming renderer can handle simple primitives)
        particle_color = Color(200, 200, 255, 150) # Default rain/snow color
        if self.current_weather == 'fog':
            # Draw a semi-transparent overlay
            # Get fog color properties from the dictionary
            fog_props = self.weather_types['fog']
            overlay_color_tuple = fog_props.get('overlay_color')
            if overlay_color_tuple:
                fog_color = Color(*overlay_color_tuple) # Use the defined color and alpha
                if renderer.backend:
                    screen_w, screen_h = renderer.backend.width, renderer.backend.height
                else:
                    screen_w, screen_h = 1280, 720 # Fallback
                if screen_w and screen_h:
                    renderer.draw_rect(0, 0, screen_w, screen_h, fog_color, filled=True, is_world_space=False)
            else:
                # Fallback or log warning if color not defined
                pass # Or log a warning
        elif self.current_weather == 'storm':
             particle_color = Color(230, 230, 255, 180)
             # Maybe add occasional lightning flash (using renderer.clear or overlay?)
             if random.random() < 0.005:
                 flash_color = Color(255, 255, 255, 150)
                 if renderer.backend:
                    screen_w, screen_h = renderer.backend.width, renderer.backend.height
                 else:
                    screen_w, screen_h = 1280, 720 # Fallback
                 if screen_w and screen_h:
                      renderer.draw_rect(0, 0, screen_w, screen_h, flash_color, filled=True, is_world_space=False)
        
        # Draw particles like rain/snow
        if self.current_weather in ['rain', 'storm']:
            for p in self.particles:
                # Use renderer.draw_line or renderer.draw_circle for particles
                # Ensure coordinates are screen space if particles aren't world objects
                renderer.draw_circle(p['x'], p['y'], p['size'], particle_color, filled=True, is_world_space=False) # Draw as circle for simplicity
                # Or as lines:
                # end_y = p['y'] + p['speed']
                # renderer.draw_line(p['x'], p['y'], p['x'], end_y, particle_color, thickness=p['size'], is_world_space=False)
    
    def get_current_weather(self) -> str:
        """
        Get the current weather type.
        
        Returns:
            str: Current weather type
        """
        return self.current_weather 