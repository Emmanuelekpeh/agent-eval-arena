import logging
import functools
import traceback
import time
from typing import Callable, Any, Dict, Optional, Type, List, Union

logger = logging.getLogger('battle_arena')

def safe_event_handler(
    error_policy: str = 'log', 
    fallback_value: Any = None,
    max_retries: int = 0,
    retry_delay: float = 0.1,
    allowed_exceptions: List[Type[Exception]] = None
):
    """
    Decorator for making event handlers safer by handling exceptions gracefully.
    
    Args:
        error_policy: Strategy for handling errors:
            - 'log': Log the error and continue (default)
            - 'reraise': Re-raise the exception
            - 'fallback': Return the fallback value
        fallback_value: Value to return if error_policy is 'fallback'
        max_retries: Maximum number of retries if an exception occurs
        retry_delay: Delay between retries in seconds
        allowed_exceptions: List of exception types to handle (handles all if None)
    
    Returns:
        Decorated function that handles exceptions according to policy
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if allowed_exceptions is None:
                catch_exceptions = (Exception,)
            else:
                catch_exceptions = tuple(allowed_exceptions)
                
            retries = 0
            
            while True:
                try:
                    return func(*args, **kwargs)
                except catch_exceptions as e:
                    retries += 1
                    
                    # Log the exception
                    handler_name = getattr(func, '__name__', str(func))
                    logger.error(
                        f"Exception in event handler '{handler_name}': {str(e)}\n"
                        f"Args: {args}, Kwargs: {kwargs}\n"
                        f"Traceback: {traceback.format_exc()}"
                    )
                    
                    # Check if we should retry
                    if retries <= max_retries:
                        logger.info(f"Retrying {handler_name} ({retries}/{max_retries})...")
                        time.sleep(retry_delay)
                        continue
                    
                    # Apply error policy
                    if error_policy == 'reraise':
                        raise
                    elif error_policy == 'fallback':
                        return fallback_value
                    else:  # 'log' is the default
                        return None
                        
        # Store metadata on the function for analysis
        wrapper._safe_handler_metadata = {
            'error_policy': error_policy,
            'max_retries': max_retries,
            'retry_delay': retry_delay,
            'allowed_exceptions': allowed_exceptions,
        }
        
        return wrapper
    return decorator

def event_timer(func):
    """
    Decorator to time the execution of event handlers
    
    Args:
        func: The event handler function to time
        
    Returns:
        Decorated function that logs timing information
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        
        handler_name = getattr(func, '__name__', str(func))
        logger.debug(f"Event handler '{handler_name}' executed in {elapsed:.6f} seconds")
        
        # If too slow, log a warning
        if elapsed > 0.1:  # Arbitrary threshold for "slow" handlers
            logger.warning(
                f"Slow event handler '{handler_name}' took {elapsed:.6f} seconds to execute"
            )
            
        return result
    return wrapper

def event_validator(required_fields: Optional[List[str]] = None, validator_func: Optional[Callable] = None):
    """
    Decorator to validate event data before passing it to a handler
    
    Args:
        required_fields: List of field names that must be present in the event data
        validator_func: Custom validation function that takes event data and returns bool
        
    Returns:
        Decorated function that validates event data
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract event data from args or kwargs
            event_data = None
            
            # Try to find event data in args
            for arg in args:
                if isinstance(arg, dict):
                    event_data = arg
                    break
            
            # If not found in args, check kwargs
            if event_data is None:
                for param_name in ['data', 'event_data']:
                    if param_name in kwargs and isinstance(kwargs[param_name], dict):
                        event_data = kwargs[param_name]
                        break
            
            # Validate if we found event data
            if event_data is not None:
                # Check required fields
                if required_fields:
                    missing_fields = [f for f in required_fields if f not in event_data]
                    if missing_fields:
                        handler_name = getattr(func, '__name__', str(func))
                        logger.error(
                            f"Event handler '{handler_name}' missing required fields: {missing_fields}"
                        )
                        return None
                
                # Run custom validator
                if validator_func and not validator_func(event_data):
                    handler_name = getattr(func, '__name__', str(func))
                    logger.error(
                        f"Event handler '{handler_name}' failed custom validation for data: {event_data}"
                    )
                    return None
            
            # Validation passed or no event data found, call the function
            return func(*args, **kwargs)
        
        # Store metadata for analysis
        wrapper._validator_metadata = {
            'required_fields': required_fields,
            'has_custom_validator': validator_func is not None
        }
        
        return wrapper
    return decorator

def lazy_import_handler(module_path: str, function_name: str):
    """
    Create a lazy-loading event handler to avoid circular imports
    
    Args:
        module_path: Import path to the module containing the handler
        function_name: Name of the handler function within the module
        
    Returns:
        Function that imports and calls the handler on demand
    """
    # Store the real handler once it's imported
    real_handler = [None]
    
    def lazy_handler(*args, **kwargs):
        # Import the real handler on first use
        if real_handler[0] is None:
            try:
                module = __import__(module_path, fromlist=[function_name])
                real_handler[0] = getattr(module, function_name)
            except (ImportError, AttributeError) as e:
                logger.error(f"Error importing lazy handler {module_path}.{function_name}: {e}")
                return None
        
        # Call the real handler
        return real_handler[0](*args, **kwargs)
    
    # Set metadata for better debugging
    lazy_handler.__name__ = f"lazy_{function_name}"
    lazy_handler.__module__ = f"lazy_import({module_path})"
    lazy_handler._lazy_import_target = f"{module_path}.{function_name}"
    
    return lazy_handler

def timed_safe_event(
    error_policy: str = 'log',
    fallback_value: Any = None,
    max_retries: int = 0
):
    """
    Combines timer and safe_event_handler decorators for common use case
    
    Args:
        error_policy: Strategy for handling errors
        fallback_value: Value to return on error if using fallback
        max_retries: Maximum number of retries on exception
        
    Returns:
        Function decorated with both timing and safe handling
    """
    def decorator(func):
        # Apply both decorators (timer first, then safe handler)
        return safe_event_handler(
            error_policy=error_policy,
            fallback_value=fallback_value,
            max_retries=max_retries
        )(event_timer(func))
    return decorator

# Example usage:
"""
@safe_event_handler(error_policy='log', max_retries=3)
def handle_player_move(data):
    # Handler implementation
    pass

@event_timer
@safe_event_handler()
def handle_combat_result(data):
    # Handler implementation
    pass

@event_validator(required_fields=['player_id', 'position'])
def handle_player_spawn(data):
    # Will only execute if data contains required fields
    pass

# Lazy import to avoid circular dependencies
handle_end_turn = lazy_import_handler('systems.turn_system', 'handle_end_turn')

# Combined decorators
@timed_safe_event(max_retries=1)
def handle_ai_decision(data):
    # Handler with both timing and safety
    pass
""" 