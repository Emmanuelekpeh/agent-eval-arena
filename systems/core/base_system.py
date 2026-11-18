"""
Base class for all systems in the AI Battle Arena.
"""
from typing import Dict, Any, Optional
from systems.core.system_manager import SystemEventType, system_manager

class BaseSystem:
    """
    Base class for all systems in the game.
    
    Provides common functionality for initialization, updates,
    event handling, and system communication.
    """
    
    def __init__(self, name: str = None, priority: int = 0):
        """
        Initialize the base system.
        
        Args:
            name: System name (defaults to class name if None)
            priority: Update priority (lower values update first)
        """
        self.name = name or self.__class__.__name__
        self.priority = priority
        self.enabled = True
        
    def initialize(self) -> None:
        """
        Initialize the system. Called once when the game starts.
        
        Override this method to implement system-specific initialization.
        """
        pass
        
    def update(self, delta_time: float) -> None:
        """
        Update the system. Called every frame.
        
        Args:
            delta_time: Time since last update in seconds
            
        Override this method to implement system-specific updates.
        """
        pass
        
    def shutdown(self) -> None:
        """
        Shutdown the system. Called when the game exits.
        
        Override this method to implement system-specific cleanup.
        """
        pass
        
    def emit_event(self, event_type: SystemEventType, data: Dict[str, Any]) -> None:
        """
        Emit an event to all registered listeners.
        
        Args:
            event_type: Type of event to emit
            data: Event data to pass to listeners
        """
        system_manager.emit_event(event_type, data)
        
    def subscribe_to_event(self, event_type: SystemEventType, callback: callable) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to listen for
            callback: Function to call when event occurs
        """
        system_manager.subscribe(event_type, callback)
        
    def unsubscribe_from_event(self, event_type: SystemEventType, callback: callable) -> bool:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to stop listening for
            callback: Function to remove from listeners
            
        Returns:
            True if successfully unsubscribed, False otherwise
        """
        return system_manager.unsubscribe(event_type, callback)
        
    def get_shared_state(self, key: str, default: Any = None) -> Any:
        """
        Get a value from shared state.
        
        Args:
            key: State key
            default: Default value if key doesn't exist
            
        Returns:
            The state value or default
        """
        return system_manager.get_shared_state(key, default)
        
    def set_shared_state(self, key: str, value: Any) -> None:
        """
        Set a value in shared state.
        
        Args:
            key: State key
            value: State value
        """
        system_manager.set_shared_state(key, value)
        
    def get_system(self, name: str) -> Optional[Any]:
        """
        Get another system by name.
        
        Args:
            name: Name of the system to retrieve
            
        Returns:
            The system instance or None if not found
        """
        return system_manager.get_system(name)
        
    def enable(self) -> None:
        """Enable this system."""
        self.enabled = True
        
    def disable(self) -> None:
        """Disable this system."""
        self.enabled = False 