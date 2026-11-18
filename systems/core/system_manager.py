from typing import Dict, List, Any, Optional, Type, Callable
import logging
import traceback
from enum import Enum, auto
from collections import defaultdict

# Get the main logger configured in logging.py
logger = logging.getLogger('battle_arena') # Use the main logger name

# Define system event types
class SystemEventType(Enum):
    ENTITY_CREATED = auto()
    ENTITY_DESTROYED = auto()
    COLLISION = auto()
    ENTITY_COLLISION = auto()
    AGENT_ACTION = auto()
    RESOURCE_COLLECTED = auto()
    DAMAGE_DEALT = auto()
    AGENT_DAMAGED = auto()
    AGENT_DAMAGE = auto() # Renamed from AGENT_DAMAGED for consistency, if needed
    ZONE_CHANGED = auto()
    FORMATION_CHANGED = auto()
    COMBAT_STARTED = auto()
    GAME_STATE_CHANGED = auto()
    PERFORMANCE_WARNING = auto()
    ATTACK_HIT = auto() # Added
    ATTACK_MISS = auto() # Added
    NEAR_MISS_DETECTED = auto() # Added for suppression system
    EXPLOSION_NEAR_AGENT = auto() # Added for suppression system
    BULLET_FIRED = auto() # Added
    HAZARD_ACTIVATED = auto() # Added missing hazard activated event
    PICKUP_ACQUIRED = auto() # Added missing pickup acquired event
    TEAM_ACTION_SUCCESS = auto() # Added for team morale handling
    TEAM_ACTION_FAILURE = auto() # Added for team morale handling
    

class SystemManager:
    """
    Central manager for all game subsystems.
    
    Coordinates communication and data sharing between subsystems,
    ensuring proper initialization, update order, and shutdown.
    """
    
    def __init__(self):
        # Dictionary to store all registered systems
        self.systems: Dict[str, Any] = {}
        
        # System execution order
        self.update_order: List[str] = []
        
        # Event listeners
        self.event_listeners: Dict[SystemEventType, List[Callable]] = defaultdict(list)
        
        # Shared state that can be accessed by all systems
        self.shared_state: Dict[str, Any] = {}
        
        # Logger - Use the main logger instance obtained above
        self.logger = logger
    
    def register_system(self, name: str, system: Any, priority: int = 0) -> None:
        """
        Register a system with the manager.
        
        Args:
            name: Unique name for the system
            system: The system instance
            priority: Update priority (lower values update first)
        """
        # --- DEBUG LOGGING ---
        system_type = type(system).__name__
        self.logger.debug(f"Attempting to register system: Name='{name}', Type={system_type}, Priority={priority}, Object={system}")
        # --- END DEBUG LOGGING ---
        
        if name in self.systems:
            self.logger.warning(f"System '{name}' already registered, replacing")
        
        self.systems[name] = system
        
        # Store system in update order list based on priority
        # Find the position to insert based on priority
        position = 0
        for i, existing_name in enumerate(self.update_order):
            # Fetch priority using getattr safely
            existing_priority = 0
            existing_system = self.systems.get(existing_name)
            if existing_system and hasattr(existing_system, 'priority'):
                 try:
                      # Ensure priority is treated as a number
                      existing_priority = int(getattr(existing_system, 'priority', 0))
                 except ValueError:
                      self.logger.warning(f"System '{existing_name}' has non-numeric priority: {getattr(existing_system, 'priority', 'N/A')}")
                      existing_priority = 0 # Default to 0 on error
            else:
                 # If priority attribute doesn't exist, use default 0
                 existing_priority = 0

            # Ensure current priority is also treated as a number
            current_priority = 0
            try:
                current_priority = int(priority) # Convert priority to int
            except ValueError:
                self.logger.warning(f"Registering system '{name}' with non-numeric priority: {priority}")
                current_priority = 0 # Default to 0 on error

            if current_priority < existing_priority:
                position = i
                break
            position = i + 1
        
        # Insert system name at the calculated position
        self.update_order.insert(position, name)
        self.logger.info(f"Registered system: {name} with priority {priority}")
    
    def unregister_system(self, name: str) -> bool:
        """
        Unregister a system from the manager.
        
        Args:
            name: Name of the system to unregister
            
        Returns:
            True if successful, False otherwise
        """
        if name not in self.systems:
            self.logger.warning(f"System '{name}' not found")
            return False
            
        del self.systems[name]
        self.update_order.remove(name)
        self.logger.info(f"Unregistered system: {name}")
        return True
    
    def get_system(self, name: str) -> Optional[Any]:
        """
        Get a registered system by name.
        
        Args:
            name: Name of the system to retrieve
            
        Returns:
            The system instance or None if not found
        """
        return self.systems.get(name)
    
    def update(self, delta_time: float) -> None:
        """
        Update all systems in priority order.
        
        Args:
            delta_time: Time in seconds since the last update
        """
        for system_name in self.update_order:
            # --- ADDED: Log before attempting update --- 
            # self.logger.debug(f"SystemManager: Attempting to update system: {system_name}")
            # --- END ADDED --- 
            system = self.systems[system_name]
            if hasattr(system, 'update') and callable(system.update):
                try:
                    # --- ADDED: Log just before calling update --- 
                    # self.logger.debug(f"SystemManager: Calling update() for {system_name}...")
                    # --- END ADDED ---
                    system.update(delta_time)
                    # --- ADDED: Log after calling update --- 
                    # self.logger.debug(f"SystemManager: ...Finished update() for {system_name}.")
                    # --- END ADDED ---
                except Exception as e:
                    self.logger.error(f"Error updating system '{system_name}': {str(e)}")
                    # Ensure traceback is imported at the top of system_manager.py
                    import traceback 
                    self.logger.error(traceback.format_exc())
            else:
                # --- ADDED: Log if update method is missing/not callable --- 
                # self.logger.debug(f"SystemManager: System {system_name} has no callable update method, skipping.")
                # --- END ADDED ---
                pass # ADDED: To prevent indentation error
    
    def initialize_all(self) -> None:
        """Initialize all registered systems."""
        for system_name in self.update_order:
            system = self.systems[system_name]
            if hasattr(system, 'initialize') and callable(system.initialize):
                try:
                    system.initialize()
                except Exception as e:
                    self.logger.error(f"Error initializing system '{system_name}': {str(e)}")
    
    def shutdown_all(self) -> None:
        """Shutdown all registered systems."""
        # Shutdown in reverse order of initialization
        for system_name in reversed(self.update_order):
            system = self.systems[system_name]
            if hasattr(system, 'shutdown') and callable(system.shutdown):
                try:
                    system.shutdown()
                except Exception as e:
                    self.logger.error(f"Error shutting down system '{system_name}': {str(e)}")
    
    def set_shared_state(self, key: str, value: Any) -> None:
        """
        Set a value in the shared state.
        
        Args:
            key: State key
            value: State value
        """
        self.shared_state[key] = value
    
    def get_shared_state(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the shared state.
        
        Args:
            key: State key
            default: Default value if key doesn't exist
            
        Returns:
            The state value or default
        """
        return self.shared_state.get(key, default)
    
    def subscribe(self, event_type: SystemEventType, callback: Callable) -> None:
        """
        Subscribe to a system event.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
        """
        self.event_listeners[event_type].append(callback)
    
    def unsubscribe(self, event_type: SystemEventType, callback: Callable) -> bool:
        """
        Unsubscribe from a system event.
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to remove from listeners
            
        Returns:
            True if successful, False otherwise
        """
        if event_type in self.event_listeners and callback in self.event_listeners[event_type]:
            self.event_listeners[event_type].remove(callback)
            return True
        return False
    
    def emit_event(self, event_type: SystemEventType, data: Dict[str, Any]) -> None:
        """
        Emit an event to all subscribers.
        
        Args:
            event_type: Type of event to emit
            data: Event data
        """
        if event_type in self.event_listeners:
            for callback in self.event_listeners[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.error(f"Error in event listener for {event_type}: {str(e)}")

# Singleton instance
system_manager = SystemManager() 