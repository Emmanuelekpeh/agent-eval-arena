import inspect
import logging
import time
import traceback
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

logger = logging.getLogger('battle_arena')

class EventHandlingError(Exception):
    """Base exception for event handling errors."""
    pass

class EventTypeError(EventHandlingError):
    """Raised when an event has an unexpected type."""
    pass

class EventAttributeError(EventHandlingError):
    """Raised when an event is missing required attributes."""
    pass

class CircularEventError(EventHandlingError):
    """Raised when circular event dependencies are detected."""
    pass

class EventHandlerTimeoutError(EventHandlingError):
    """Raised when an event handler exceeds its timeout."""
    pass

def safe_event_handler(
    expected_event_type: Optional[Union[str, List[str]]] = None,
    required_attributes: Optional[List[str]] = None,
    timeout: Optional[float] = None,
    retry_count: int = 0,
    retry_delay: float = 0.1,
    fallback_handler: Optional[Callable] = None
):
    """
    Decorator to make event handlers safer by adding validation and error handling.
    
    Args:
        expected_event_type: Expected event type(s). Can be a string or list of strings.
        required_attributes: List of attributes that must be present on the event.
        timeout: Maximum execution time in seconds before aborting.
        retry_count: Number of times to retry on failure.
        retry_delay: Delay between retries in seconds.
        fallback_handler: Function to call if handler fails after all retries.
    
    Returns:
        Decorated event handler function.
    """
    def decorator(func):
        handler_name = f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def wrapper(event, *args, **kwargs):
            # Type checking
            if expected_event_type is not None:
                event_type = getattr(event, 'type', None)
                if event_type is None:
                    logger.error(f"Event passed to {handler_name} has no 'type' attribute")
                    raise EventTypeError(f"Event has no 'type' attribute: {event}")
                
                if isinstance(expected_event_type, list):
                    if event_type not in expected_event_type:
                        logger.error(f"Unexpected event type '{event_type}' in {handler_name}. Expected one of {expected_event_type}")
                        raise EventTypeError(f"Unexpected event type: {event_type}")
                elif event_type != expected_event_type:
                    logger.error(f"Unexpected event type '{event_type}' in {handler_name}. Expected {expected_event_type}")
                    raise EventTypeError(f"Unexpected event type: {event_type}")
            
            # Attribute checking
            if required_attributes:
                missing_attrs = []
                for attr in required_attributes:
                    if not hasattr(event, attr):
                        missing_attrs.append(attr)
                
                if missing_attrs:
                    logger.error(f"Event missing required attributes in {handler_name}: {missing_attrs}")
                    raise EventAttributeError(f"Event missing required attributes: {missing_attrs}")
            
            # Execution with timeout
            if timeout is not None:
                start_time = time.time()
                
                def check_timeout():
                    if time.time() - start_time > timeout:
                        logger.error(f"Event handler {handler_name} timed out after {timeout} seconds")
                        raise EventHandlerTimeoutError(f"Handler timed out after {timeout} seconds")
                
                # We can't easily implement preemptive timeouts in Python without threads,
                # but we can check after potentially long operations
            
            # Main execution with retries
            last_exception = None
            for attempt in range(retry_count + 1):
                try:
                    # Execute the handler
                    result = func(event, *args, **kwargs)
                    return result
                except Exception as e:
                    last_exception = e
                    if attempt < retry_count:
                        logger.warning(f"Event handler {handler_name} failed, retrying ({attempt+1}/{retry_count}): {str(e)}")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"Event handler {handler_name} failed after {retry_count} retries: {str(e)}")
                        if fallback_handler is not None:
                            logger.info(f"Using fallback handler for {handler_name}")
                            return fallback_handler(event, *args, **kwargs)
                        else:
                            raise
            
            # This code should be unreachable
            raise last_exception
        
        return wrapper
    
    return decorator

def validate_event_schema(event_type: str, schema: Dict[str, Dict[str, Any]]):
    """
    Decorator factory that validates event attributes against a schema.
    
    Args:
        event_type: Expected event type
        schema: Schema dictionary mapping attribute names to type information
               e.g. {'player_id': {'type': int, 'required': True}}
    
    Returns:
        Decorator function for validating events
    """
    def decorator(func):
        @wraps(func)
        def wrapper(event, *args, **kwargs):
            # Check event type
            actual_type = getattr(event, 'type', None)
            if actual_type != event_type:
                raise EventTypeError(f"Expected event type '{event_type}', got '{actual_type}'")
            
            # Validate schema
            for attr_name, attr_schema in schema.items():
                # Check if attribute exists
                if not hasattr(event, attr_name):
                    if attr_schema.get('required', False):
                        raise EventAttributeError(f"Required attribute '{attr_name}' missing from event")
                    continue
                
                # Check type if specified
                if 'type' in attr_schema:
                    attr_value = getattr(event, attr_name)
                    expected_type = attr_schema['type']
                    
                    if not isinstance(attr_value, expected_type):
                        raise EventAttributeError(
                            f"Attribute '{attr_name}' has wrong type: expected {expected_type.__name__}, "
                            f"got {type(attr_value).__name__}"
                        )
                
                # Check allowed values if specified
                if 'allowed_values' in attr_schema:
                    attr_value = getattr(event, attr_name)
                    allowed = attr_schema['allowed_values']
                    
                    if attr_value not in allowed:
                        raise EventAttributeError(
                            f"Invalid value for attribute '{attr_name}': '{attr_value}'. "
                            f"Allowed values: {allowed}"
                        )
            
            # All validation passed, call the handler
            return func(event, *args, **kwargs)
        
        return wrapper
    
    return decorator

class EventTracker:
    """
    Utility for tracking events and detecting circular dependencies.
    """
    
    def __init__(self):
        """Initialize the event tracker."""
        self.event_stack = []
        self.dependency_graph = {}
    
    def track_event(self, event_type: str):
        """
        Track a new event and check for circular dependencies.
        
        Args:
            event_type: The type of event being processed
            
        Returns:
            A context manager for tracking the event
            
        Raises:
            CircularEventError: If a circular dependency is detected
        """
        # Check for circular dependencies
        if event_type in self.event_stack:
            cycle = self.event_stack[self.event_stack.index(event_type):] + [event_type]
            raise CircularEventError(f"Circular event dependency detected: {' -> '.join(cycle)}")
        
        # Update dependency graph
        if self.event_stack:
            parent = self.event_stack[-1]
            if parent not in self.dependency_graph:
                self.dependency_graph[parent] = set()
            self.dependency_graph[parent].add(event_type)
        
        # Track the event
        self.event_stack.append(event_type)
    
    def end_tracking(self, event_type: str):
        """
        End tracking for an event.
        
        Args:
            event_type: The type of event that has finished processing
        """
        if self.event_stack and self.event_stack[-1] == event_type:
            self.event_stack.pop()
    
    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """
        Get the current event dependency graph.
        
        Returns:
            Dictionary mapping event types to sets of their dependencies
        """
        return {k: v.copy() for k, v in self.dependency_graph.items()}
    
    def check_for_cycles(self) -> List[List[str]]:
        """
        Check for cycles in the dependency graph.
        
        Returns:
            List of cycles found, where each cycle is a list of event types
        """
        cycles = []
        visited = set()
        path = []
        
        def dfs(node):
            if node in path:
                cycle = path[path.index(node):] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for neighbor in self.dependency_graph.get(node, set()):
                dfs(neighbor)
            
            path.pop()
        
        for node in self.dependency_graph:
            if node not in visited:
                dfs(node)
        
        return cycles

# Global event tracker
_event_tracker = EventTracker()

def track_event_dependencies(func):
    """
    Decorator to track event dependencies and detect circular references.
    
    Args:
        func: The event handler function to decorate
        
    Returns:
        Decorated function with event tracking
    """
    @wraps(func)
    def wrapper(event, *args, **kwargs):
        event_type = getattr(event, 'type', 'unknown')
        
        try:
            _event_tracker.track_event(event_type)
            result = func(event, *args, **kwargs)
            return result
        finally:
            _event_tracker.end_tracking(event_type)
    
    return wrapper

def rate_limit_events(max_calls: int, time_window: float):
    """
    Decorator to rate limit event handler execution.
    
    Args:
        max_calls: Maximum number of calls allowed in the time window
        time_window: Time window in seconds
        
    Returns:
        Decorated function with rate limiting
    """
    def decorator(func):
        # Use lists instead of deque for better thread safety
        call_timestamps = []
        
        @wraps(func)
        def wrapper(event, *args, **kwargs):
            current_time = time.time()
            
            # Remove old timestamps
            while call_timestamps and call_timestamps[0] < current_time - time_window:
                call_timestamps.pop(0)
            
            # Check rate limit
            if len(call_timestamps) >= max_calls:
                logger.warning(f"Rate limit exceeded for {func.__name__}: {max_calls} calls per {time_window} seconds")
                return None  # Skip execution
            
            # Add timestamp and execute
            call_timestamps.append(current_time)
            return func(event, *args, **kwargs)
        
        return wrapper
    
    return decorator

def conditional_event_handler(condition_func: Callable[[Any], bool]):
    """
    Decorator to conditionally execute an event handler based on a condition.
    
    Args:
        condition_func: Function that takes the event and returns True if the handler should run
        
    Returns:
        Decorated function with conditional execution
    """
    def decorator(func):
        @wraps(func)
        def wrapper(event, *args, **kwargs):
            if condition_func(event):
                return func(event, *args, **kwargs)
            return None
        
        return wrapper
    
    return decorator

def apply_all_safeguards(event_type: Optional[str] = None, 
                         required_attrs: Optional[List[str]] = None,
                         timeout: Optional[float] = 1.0,
                         track_dependencies: bool = True,
                         rate_limit: Optional[Tuple[int, float]] = None):
    """
    Apply all safeguards to an event handler.
    
    Args:
        event_type: Expected event type
        required_attrs: Required event attributes
        timeout: Maximum execution time
        track_dependencies: Whether to track event dependencies
        rate_limit: Rate limit as (max_calls, time_window) tuple
        
    Returns:
        Decorated function with all safeguards
    """
    def decorator(func):
        # Start with the base function
        result = func
        
        # Apply decorators in reverse order (innermost first)
        if rate_limit is not None:
            result = rate_limit_events(rate_limit[0], rate_limit[1])(result)
        
        if track_dependencies:
            result = track_event_dependencies(result)
        
        # Always apply the safe event handler
        result = safe_event_handler(
            expected_event_type=event_type,
            required_attributes=required_attrs,
            timeout=timeout
        )(result)
        
        return result
    
    return decorator

# Example usage:
"""
# Apply safe event handler
@safe_event_handler(expected_event_type="player_move", required_attributes=["player_id", "position"])
def handle_player_move(event):
    # Handle the event safely
    pass

# Apply schema validation
player_move_schema = {
    'player_id': {'type': int, 'required': True},
    'position': {'type': dict, 'required': True},
    'speed': {'type': float, 'required': False},
    'direction': {'type': str, 'required': True, 'allowed_values': ['north', 'south', 'east', 'west']}
}

@validate_event_schema("player_move", player_move_schema)
def handle_validated_move(event):
    # Handle with validated schema
    pass

# Apply rate limiting
@rate_limit_events(max_calls=5, time_window=1.0)
def handle_chat_message(event):
    # Handle chat with rate limiting
    pass

# Apply conditional handling
def is_admin_user(event):
    return hasattr(event, 'user_id') and event.user_id in ADMIN_IDS

@conditional_event_handler(is_admin_user)
def handle_admin_command(event):
    # Handle admin commands
    pass

# Apply all safeguards
@apply_all_safeguards(
    event_type="player_attack",
    required_attrs=["player_id", "target_id", "damage"],
    timeout=0.5,
    track_dependencies=True,
    rate_limit=(10, 1.0)
)
def handle_player_attack(event):
    # Handle with all safeguards
    pass
""" 