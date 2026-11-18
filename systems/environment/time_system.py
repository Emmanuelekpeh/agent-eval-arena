import pygame

class TimeSystem:
    """
    Time system for managing day-night cycles in the environment.
    """
    
    def __init__(self):
        """Initialize the time system."""
        self.current_time = 0.0  # 0.0 to 1.0 representing the day cycle (0.0 = dawn, 0.5 = noon, 1.0 = dusk)
        self.day_length = 10 * 60 * 60  # 10 minutes in frames at 60 FPS
        self.time_progression_rate = 1.0 / self.day_length
        self.day_night_cycle_enabled = True
        
        # Day-night cycle settings
        self.dawn_time = 0.0
        self.noon_time = 0.25
        self.dusk_time = 0.5
        self.midnight_time = 0.75
        
        # Lighting settings
        self.ambient_light = {
            "dawn": (150, 120, 100),    # Warm orange glow
            "noon": (255, 255, 255),    # Bright white
            "dusk": (150, 100, 120),    # Purple-ish sunset
            "night": (50, 50, 100)      # Dark blue
        }
        
        # Transition points
        self.day_transitions = [
            {"time": self.dawn_time, "name": "dawn"},
            {"time": self.noon_time, "name": "noon"},
            {"time": self.dusk_time, "name": "dusk"},
            {"time": self.midnight_time, "name": "night"}
        ]
    
    def update(self, delta_time: float = 0.0):
        """Update the time system."""
        if self.day_night_cycle_enabled:
            # Use delta_time for progression
            time_increment = delta_time * self.time_progression_rate * 60 # Scale delta_time (seconds) appropriately
            self.current_time += time_increment
            
            # Loop back after a full day
            if self.current_time >= 1.0:
                self.current_time = 0.0
    
    def get_current_time_of_day(self) -> float:
        """
        Get the current time of day.
        
        Returns:
            float: Time of day (0.0 to 1.0)
        """
        return self.current_time
    
    def get_time_name(self) -> str:
        """
        Get the current time of day as a string.
        
        Returns:
            str: Time of day name (dawn, day, dusk, night)
        """
        if self.current_time < self.noon_time:
            return "dawn"
        elif self.current_time < self.dusk_time:
            return "noon"
        elif self.current_time < self.midnight_time:
            return "dusk"
        else:
            return "night"
    
    def get_ambient_light(self) -> tuple:
        """
        Get the current ambient light color.
        
        Returns:
            tuple: RGB color for ambient light
        """
        time_name = self.get_time_name()
        return self.ambient_light[time_name]
    
    def get_lighting_factor(self) -> float:
        """
        Get the current lighting factor.
        
        Returns:
            float: Lighting factor (0.0 to 1.0)
        """
        if self.current_time < self.noon_time:
            # Dawn to noon: getting brighter
            factor = (self.current_time - self.dawn_time) / (self.noon_time - self.dawn_time)
            return 0.7 + 0.3 * factor
        elif self.current_time < self.dusk_time:
            # Noon to dusk: full brightness
            return 1.0
        elif self.current_time < self.midnight_time:
            # Dusk to midnight: getting darker
            factor = (self.current_time - self.dusk_time) / (self.midnight_time - self.dusk_time)
            return 0.7 * (1.0 - factor)
        else:
            # Midnight to dawn: darkest
            factor = (self.current_time - self.midnight_time) / (1.0 - self.midnight_time)
            return 0.3 + 0.4 * factor
    
    def set_time(self, time_value: float):
        """
        Set the current time of day.
        
        Args:
            time_value (float): Time of day (0.0 to 1.0)
        """
        self.current_time = max(0.0, min(0.999, time_value))
    
    def toggle_day_night_cycle(self, enabled: bool = None):
        """
        Toggle the day-night cycle.
        
        Args:
            enabled (bool, optional): Whether to enable the cycle. If None, toggles the current state.
        """
        if enabled is None:
            self.day_night_cycle_enabled = not self.day_night_cycle_enabled
        else:
            self.day_night_cycle_enabled = enabled
    
    def set_cycle_speed(self, minutes_per_day: float):
        """
        Set the speed of the day-night cycle.
        
        Args:
            minutes_per_day (float): Real-world minutes for a full day cycle
        """
        self.day_length = minutes_per_day * 60 * 60  # Convert to frames
        self.time_progression_rate = 1.0 / self.day_length 

    def draw(self, screen: pygame.Surface):
        """
        Draw the day/night overlay effect on the screen.

        Args:
            screen (pygame.Surface): The Pygame surface to draw onto.
        """
        if not self.day_night_cycle_enabled:
            return

        lighting_factor = self.get_lighting_factor()
        # Calculate alpha based on how dark it is (1.0 = full light, 0.0 = darkest)
        # We want overlay alpha to be higher when lighting_factor is lower.
        max_overlay_alpha = 150 # Max darkness/opacity
        overlay_alpha = int(max_overlay_alpha * (1.0 - lighting_factor))

        if overlay_alpha > 0:
            # Use a dark blue/black color for the overlay
            overlay_color = (*self.ambient_light["night"][:3], overlay_alpha)
            
            overlay_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay_surface.fill(overlay_color)
            screen.blit(overlay_surface, (0, 0)) 