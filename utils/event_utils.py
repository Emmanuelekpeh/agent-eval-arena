import functools
import logging
from typing import Dict, List, Any, Callable, Union

logger = logging.getLogger('battle_arena')

def safe_event_handler(expected_keys: Union[List[str], Dict[str, Any]] = None):
    """
    Decorator to ensure event handlers safely handle missing data
    
    Args:
        expected_keys: List of required keys or dict mapping keys to default values
        
    Returns:
        Callable: Decorated function
    """
    def decorator(handler_func):
        @functools.wraps(handler_func)
        def wrapper(data):
            # Check if data is a dictionary
            if not isinstance(data, dict):
                logger.warning(f"Event handler {handler_func.__name__} received non-dict data: {data}")
                # Try to convert simple types to dict if possible
                if hasattr(data, '__dict__'):
                    data = data.__dict__
                else:
                    # Create empty dict as fallback
                    data = {'raw_data': data}
            
            # Handle expected keys
            if expected_keys:
                if isinstance(expected_keys, list):
                    # Check for missing keys
                    missing_keys = [key for key in expected_keys if key not in data]
                    if missing_keys:
                        logger.warning(f"Event handler {handler_func.__name__} missing expected keys: {missing_keys}")
                        # Continue with what we have
                        
                elif isinstance(expected_keys, dict):
                    # Apply defaults for missing keys
                    for key, default in expected_keys.items():
                        if key not in data:
                            logger.debug(f"Applying default value for missing key '{key}'")
                            data[key] = default
            
            # Call the original handler with validated data
            return handler_func(data)
        
        # Store the expected keys for introspection
        wrapper._expected_keys = expected_keys
        
        return wrapper
    
    return decorator

def register_event_handler(event_type, handler, expected_keys=None):
    """
    Register an event handler with automatic data validation
    
    Args:
        event_type: The SystemEventType to subscribe to
        handler: Function to call when event occurs
        expected_keys: List of required keys or dict mapping keys to default values
        
    Returns:
        Callable: The decorated handler function
    """
    from systems.core.system_manager import system_manager
    
    # Apply the decorator if expected_keys is provided
    if expected_keys:
        decorated_handler = safe_event_handler(expected_keys)(handler)
    else:
        decorated_handler = handler
    
    # Register with system manager
    system_manager.subscribe(event_type, decorated_handler)
    
    return decorated_handler

def unregister_event_handler(event_type, handler):
    """
    Unregister an event handler
    
    Args:
        event_type: The SystemEventType to unsubscribe from
        handler: Function to unregister
    """
    from systems.core.system_manager import system_manager
    
    # Handle both raw and decorated handlers
    if hasattr(handler, '__closure__') and handler.__closure__:
        # Try to extract original function from decorator
        for cell in handler.__closure__:
            if callable(cell.cell_contents):
                # If we find a callable in closure, that might be our original function
                original_handler = cell.cell_contents
                system_manager.unsubscribe(event_type, original_handler)
                break
    
    # Always try with the handler as provided
    system_manager.unsubscribe(event_type, handler) 