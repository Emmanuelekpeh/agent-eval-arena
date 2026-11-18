from systems.core.system_manager import SystemEventType, system_manager
import logging
import inspect
from types import FunctionType
from typing import Dict, List, Callable, Any, Set, Optional, Tuple
import time
import traceback
from collections import defaultdict
from functools import wraps

logger = logging.getLogger('battle_arena')

class EventDiagnostics:
    """
    A utility class for diagnosing and monitoring event handlers in the application.
    Provides tools for tracking event execution, measuring performance, and detecting issues.
    """
    
    def __init__(self, system_manager=None):
        """Initialize the event diagnostics tracker."""
        self.system_manager = system_manager
        self.events_tracked = defaultdict(list)  # Maps event types to handlers called
        self.event_timings = defaultdict(list)   # Maps event types to timing information
        self.exceptions = defaultdict(list)      # Maps event types to exceptions encountered
        self.handler_stats = defaultdict(lambda: {"calls": 0, "errors": 0, "avg_time": 0, "total_time": 0})
        
    def set_system_manager(self, system_manager):
        """Set the system manager to diagnose"""
        self.system_manager = system_manager
        
    def get_all_event_handlers(self) -> Dict[str, List[Callable]]:
        """
        Extract all event handlers from the system manager
        
        Returns:
            Dict[str, List[Callable]]: Mapping of event names to handlers
        """
        if not self.system_manager:
            logger.error("System manager not set")
            return {}
            
        try:
            # Extract the event_handlers dictionary from system_manager
            if hasattr(self.system_manager, 'event_handlers'):
                return self.system_manager.event_handlers
            else:
                logger.error("System manager doesn't have event_handlers attribute")
                return {}
        except Exception as e:
            logger.error(f"Error getting event handlers: {e}")
            return {}
            
    def analyze_event_handlers(self) -> Dict[str, Any]:
        """
        Analyze event handlers for potential issues
        
        Returns:
            Dict with analysis results
        """
        handlers = self.get_all_event_handlers()
        
        if not handlers:
            return {"error": "No event handlers found"}
            
        results = {
            "event_count": len(handlers),
            "total_handlers": sum(len(h) for h in handlers.values()),
            "empty_events": [],
            "overloaded_events": [],
            "handler_signature_issues": [],
            "handler_parameter_types": {},
            "events_by_module": {},
            "handler_to_events": {},
        }
        
        # Find empty and overloaded events
        for event, event_handlers in handlers.items():
            if not event_handlers:
                results["empty_events"].append(event)
            elif len(event_handlers) > 5:  # Arbitrary threshold for "overloaded"
                results["overloaded_events"].append({
                    "event": event, 
                    "handler_count": len(event_handlers)
                })
                
            # Check handler signatures
            for handler in event_handlers:
                self._analyze_handler(handler, event, results)
                
        # Group by module
        for event, event_handlers in handlers.items():
            for handler in event_handlers:
                module = self._get_handler_module(handler)
                
                if module not in results["events_by_module"]:
                    results["events_by_module"][module] = {}
                    
                if event not in results["events_by_module"][module]:
                    results["events_by_module"][module][event] = 0
                    
                results["events_by_module"][module][event] += 1
                
                # Map handlers to events
                handler_id = self._get_handler_id(handler)
                
                if handler_id not in results["handler_to_events"]:
                    results["handler_to_events"][handler_id] = []
                    
                if event not in results["handler_to_events"][handler_id]:
                    results["handler_to_events"][handler_id].append(event)
        
        return results
    
    def _analyze_handler(self, handler: Callable, event: str, results: Dict) -> None:
        """Analyze a single handler for issues"""
        try:
            # Get the original function if it's a decorated function
            orig_handler = self._get_original_handler(handler)
            
            # Check signature
            sig = inspect.signature(orig_handler)
            
            # Track parameter types
            for param_name, param in sig.parameters.items():
                if param_name not in results["handler_parameter_types"]:
                    results["handler_parameter_types"][param_name] = set()
                
                if param.annotation != inspect.Parameter.empty:
                    annotation = str(param.annotation)
                    results["handler_parameter_types"][param_name].add(annotation)
                else:
                    results["handler_parameter_types"][param_name].add("untyped")
            
            # Check for common issues
            if len(sig.parameters) == 0:
                results["handler_signature_issues"].append({
                    "handler": self._get_handler_id(handler),
                    "event": event,
                    "issue": "No parameters, can't receive event data"
                })
            
            # If first parameter is not 'data' or 'event_data', might be an issue
            param_names = list(sig.parameters.keys())
            if param_names and param_names[0] not in ['data', 'event_data', 'self']:
                results["handler_signature_issues"].append({
                    "handler": self._get_handler_id(handler),
                    "event": event,
                    "issue": f"First parameter is '{param_names[0]}' instead of 'data' or 'event_data'"
                })
        
        except Exception as e:
            logger.error(f"Error analyzing handler {handler.__name__}: {e}")
            results["handler_signature_issues"].append({
                "handler": self._get_handler_id(handler),
                "event": event,
                "issue": f"Analysis error: {str(e)}"
            })
    
    def _get_original_handler(self, handler: Callable) -> Callable:
        """Get the original function from a potentially decorated handler"""
        if hasattr(handler, "__wrapped__"):
            return self._get_original_handler(handler.__wrapped__)
        
        # Check for closures that might be decorators
        if hasattr(handler, "__closure__") and handler.__closure__:
            for cell in handler.__closure__:
                if isinstance(cell.cell_contents, FunctionType):
                    return self._get_original_handler(cell.cell_contents)
        
        return handler
    
    def _get_handler_module(self, handler: Callable) -> str:
        """Get the module name for a handler"""
        try:
            return handler.__module__
        except AttributeError:
            return "unknown_module"
    
    def _get_handler_id(self, handler: Callable) -> str:
        """Get a unique identifier for a handler"""
        try:
            module = handler.__module__
            name = handler.__name__
            return f"{module}.{name}"
        except AttributeError:
            return str(handler)
    
    def find_conflicting_handlers(self) -> List[Dict[str, Any]]:
        """
        Find handlers that might conflict with each other
        
        Returns:
            List of potential conflicts
        """
        handlers = self.get_all_event_handlers()
        conflicts = []
        
        # Build a map of handler names to their events
        handler_map = {}
        
        for event, event_handlers in handlers.items():
            for handler in event_handlers:
                handler_id = self._get_handler_id(handler)
                
                if handler_id not in handler_map:
                    handler_map[handler_id] = []
                
                handler_map[handler_id].append(event)
        
        # Find handlers subscribed to multiple events
        for handler_id, events in handler_map.items():
            if len(events) > 1:
                conflicts.append({
                    "handler": handler_id,
                    "events": events,
                    "issue": "Handler subscribed to multiple events"
                })
        
        return conflicts
    
    def simulate_event(self, event_name: str, event_data: Optional[Dict] = None) -> List[Tuple[Callable, Any]]:
        """
        Simulate firing an event without actually calling handlers
        
        Args:
            event_name: The name of the event to simulate
            event_data: Optional data to pass to handlers
            
        Returns:
            List of (handler, expected_args) tuples
        """
        handlers = self.get_all_event_handlers()
        if event_name not in handlers:
            return []
            
        if event_data is None:
            event_data = {}
            
        results = []
        
        for handler in handlers[event_name]:
            # Get the original function
            orig_handler = self._get_original_handler(handler)
            
            # Check signature
            sig = inspect.signature(orig_handler)
            
            # Determine what args will be passed
            expected_args = {}
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    expected_args[param_name] = "instance_of_class"
                elif param_name in ['data', 'event_data']:
                    expected_args[param_name] = event_data
                elif param_name in event_data:
                    expected_args[param_name] = event_data[param_name]
                elif param.default != inspect.Parameter.empty:
                    expected_args[param_name] = param.default
                else:
                    expected_args[param_name] = None  # Missing required parameter
            
            results.append((handler, expected_args))
            
        return results
    
    def generate_event_graph(self) -> Dict[str, Any]:
        """
        Generate a graph representation of event handlers
        
        Returns:
            Dict with nodes and edges for visualization
        """
        handlers = self.get_all_event_handlers()
        
        nodes = []
        edges = []
        
        # Add event nodes
        for event in handlers:
            nodes.append({
                "id": f"event:{event}",
                "label": event,
                "type": "event"
            })
        
        # Add handler nodes and edges
        for event, event_handlers in handlers.items():
            for handler in event_handlers:
                handler_id = f"handler:{self._get_handler_id(handler)}"
                
                # Check if we've already added this handler
                if not any(n["id"] == handler_id for n in nodes):
                    nodes.append({
                        "id": handler_id,
                        "label": handler.__name__,
                        "module": self._get_handler_module(handler),
                        "type": "handler"
                    })
                
                # Add the edge
                edges.append({
                    "source": f"event:{event}",
                    "target": handler_id
                })
        
        return {
            "nodes": nodes,
            "edges": edges
        }

    def track_event(self, event_type: str, handler_name: str, duration: float, success: bool, error: Optional[Exception] = None):
        """
        Track an event execution.
        
        Args:
            event_type: The type of event that was handled
            handler_name: The name of the handler function
            duration: The execution time in seconds
            success: Whether the execution was successful
            error: The exception that occurred (if any)
        """
        # Record execution
        self.events_tracked[event_type].append({
            "handler": handler_name,
            "timestamp": time.time(),
            "duration": duration,
            "success": success
        })
        
        # Record timing information
        self.event_timings[event_type].append(duration)
        
        # Update handler statistics
        stats = self.handler_stats[handler_name]
        stats["calls"] += 1
        stats["total_time"] += duration
        stats["avg_time"] = stats["total_time"] / stats["calls"]
        
        if not success and error:
            stats["errors"] += 1
            self.exceptions[event_type].append({
                "handler": handler_name,
                "timestamp": time.time(),
                "error": error,
                "traceback": traceback.format_exc()
            })
    
    def get_event_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get a summary of all tracked events.
        
        Returns:
            Dictionary containing event statistics
        """
        summary = {}
        
        for event_type, executions in self.events_tracked.items():
            handlers = set(e["handler"] for e in executions)
            success_count = sum(1 for e in executions if e["success"])
            failure_count = len(executions) - success_count
            timings = self.event_timings[event_type]
            
            summary[event_type] = {
                "total_calls": len(executions),
                "unique_handlers": len(handlers),
                "handler_names": list(handlers),
                "success_rate": success_count / len(executions) if executions else 0,
                "failures": failure_count,
                "avg_duration": sum(timings) / len(timings) if timings else 0,
                "min_duration": min(timings) if timings else 0,
                "max_duration": max(timings) if timings else 0
            }
            
        return summary
    
    def get_handler_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all handlers.
        
        Returns:
            Dictionary mapping handler names to their statistics
        """
        return dict(self.handler_stats)
    
    def get_slowest_handlers(self, limit: int = 5) -> List[Tuple[str, float]]:
        """
        Get the slowest handlers by average execution time.
        
        Args:
            limit: Maximum number of handlers to return
            
        Returns:
            List of (handler_name, avg_time) tuples
        """
        handlers = [(name, stats["avg_time"]) for name, stats in self.handler_stats.items()]
        return sorted(handlers, key=lambda x: x[1], reverse=True)[:limit]
    
    def get_most_frequent_errors(self, limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get the most frequently occurring errors across all events.
        
        Args:
            limit: Maximum number of error types to return
            
        Returns:
            Dictionary mapping error types to error information
        """
        error_counts = defaultdict(list)
        
        for event_type, errors in self.exceptions.items():
            for error_info in errors:
                error_type = error_info["error"].__class__.__name__
                error_counts[error_type].append({
                    "event_type": event_type,
                    "handler": error_info["handler"],
                    "timestamp": error_info["timestamp"],
                    "traceback": error_info["traceback"]
                })
                
        # Sort by frequency
        sorted_errors = sorted(error_counts.items(), key=lambda x: len(x[1]), reverse=True)
        return {k: v for k, v in sorted_errors[:limit]}
    
    def reset_stats(self):
        """Reset all statistics."""
        self.events_tracked.clear()
        self.event_timings.clear()
        self.exceptions.clear()
        self.handler_stats.clear()
    
    def generate_report(self) -> str:
        """
        Generate a human-readable report of event handler diagnostics.
        
        Returns:
            String containing the formatted report
        """
        report = []
        report.append("# Event Handler Diagnostics Report")
        report.append(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Events summary
        event_summary = self.get_event_summary()
        report.append("## Event Summary")
        report.append(f"Total event types tracked: {len(event_summary)}")
        report.append("")
        
        if event_summary:
            report.append("| Event Type | Calls | Handlers | Success Rate | Avg Duration (ms) |")
            report.append("|------------|-------|----------|-------------|------------------|")
            
            for event_type, stats in event_summary.items():
                report.append(f"| {event_type} | {stats['total_calls']} | {stats['unique_handlers']} | " +
                             f"{stats['success_rate']:.2%} | {stats['avg_duration'] * 1000:.2f} |")
            
            report.append("")
        
        # Slowest handlers
        slowest = self.get_slowest_handlers()
        report.append("## Slowest Handlers")
        if slowest:
            report.append("| Handler | Avg Duration (ms) |")
            report.append("|---------|------------------|")
            
            for handler, avg_time in slowest:
                report.append(f"| {handler} | {avg_time * 1000:.2f} |")
            
            report.append("")
        else:
            report.append("No handler timing data available.")
            report.append("")
        
        # Most frequent errors
        error_stats = self.get_most_frequent_errors()
        report.append("## Most Frequent Errors")
        if error_stats:
            for error_type, occurrences in error_stats.items():
                report.append(f"### {error_type}: {len(occurrences)} occurrences")
                report.append("")
                report.append("| Event Type | Handler | Timestamp |")
                report.append("|------------|---------|-----------|")
                
                for error in occurrences[:5]:  # Show at most 5 examples
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(error["timestamp"]))
                    report.append(f"| {error['event_type']} | {error['handler']} | {timestamp} |")
                
                report.append("")
                
                # Include a sample traceback
                if occurrences:
                    report.append("#### Sample Traceback")
                    report.append("```")
                    report.append(occurrences[0]["traceback"])
                    report.append("```")
                    report.append("")
        else:
            report.append("No errors recorded.")
            report.append("")
        
        # Handler stats
        handler_stats = self.get_handler_stats()
        report.append("## Handler Statistics")
        if handler_stats:
            report.append("| Handler | Calls | Errors | Error Rate | Avg Duration (ms) |")
            report.append("|---------|-------|--------|------------|------------------|")
            
            for handler, stats in handler_stats.items():
                error_rate = stats["errors"] / stats["calls"] if stats["calls"] > 0 else 0
                report.append(f"| {handler} | {stats['calls']} | {stats['errors']} | " +
                             f"{error_rate:.2%} | {stats['avg_time'] * 1000:.2f} |")
        else:
            report.append("No handler statistics available.")
        
        return "\n".join(report)

# Global diagnostics instance
_diagnostics = EventDiagnostics()

def get_diagnostics() -> EventDiagnostics:
    """
    Get the global event diagnostics instance.
    
    Returns:
        The global EventDiagnostics instance
    """
    return _diagnostics

def diagnose_event_handler(func):
    """
    Decorator to add diagnostic tracking to an event handler.
    
    Args:
        func: The event handler function to decorate
        
    Returns:
        Decorated function with diagnostics
    """
    handler_name = f"{func.__module__}.{func.__name__}"
    
    @wraps(func)
    def wrapper(event, *args, **kwargs):
        event_type = getattr(event, 'type', 'unknown')
        start_time = time.time()
        success = True
        error = None
        
        try:
            result = func(event, *args, **kwargs)
            return result
        except Exception as e:
            success = False
            error = e
            raise
        finally:
            duration = time.time() - start_time
            _diagnostics.track_event(
                event_type=event_type,
                handler_name=handler_name,
                duration=duration,
                success=success,
                error=error
            )
    
    return wrapper

def analyze_event_consistency(handlers_dict: Dict[str, List[Callable]]) -> Dict[str, Any]:
    """
    Analyze the consistency of event handlers in the application.
    
    Args:
        handlers_dict: Dictionary mapping event types to lists of handler functions
        
    Returns:
        Dictionary containing analysis results
    """
    results = {
        "event_types": len(handlers_dict),
        "total_handlers": sum(len(handlers) for handlers in handlers_dict.values()),
        "issues": []
    }
    
    # Parameter consistency check
    for event_type, handlers in handlers_dict.items():
        event_params = defaultdict(list)
        
        for handler in handlers:
            sig = inspect.signature(handler)
            param_names = list(sig.parameters.keys())
            
            # Skip 'self' for method handlers
            if param_names and param_names[0] == 'self':
                param_names = param_names[1:]
                
            # Examine first parameter (event parameter)
            if not param_names:
                results["issues"].append({
                    "type": "missing_event_parameter",
                    "event_type": event_type,
                    "handler": f"{handler.__module__}.{handler.__name__}",
                    "description": "Handler has no parameters to receive event object"
                })
            else:
                event_param = param_names[0]
                event_params[tuple(param_names)].append(handler)
        
        # Check for inconsistent parameter signatures
        if len(event_params) > 1:
            results["issues"].append({
                "type": "inconsistent_parameters",
                "event_type": event_type,
                "parameter_sets": [
                    {
                        "parameters": list(params),
                        "handlers": [f"{h.__module__}.{h.__name__}" for h in handlers]
                    }
                    for params, handlers in event_params.items()
                ],
                "description": f"Handlers for event '{event_type}' have inconsistent parameters"
            })
    
    # Analyze error patterns
    error_patterns = _diagnostics.get_most_frequent_errors()
    for error_type, occurrences in error_patterns.items():
        results["issues"].append({
            "type": "error_pattern",
            "error_type": error_type,
            "occurrences": len(occurrences),
            "examples": [
                {
                    "event_type": err["event_type"],
                    "handler": err["handler"]
                }
                for err in occurrences[:3]  # Top 3 examples
            ],
            "description": f"Frequent {error_type} errors in event handlers"
        })
    
    # Performance outliers
    slow_handlers = _diagnostics.get_slowest_handlers(10)
    avg_times = [time for _, time in slow_handlers]
    if avg_times:
        overall_avg = sum(avg_times) / len(avg_times)
        outliers = [(handler, time) for handler, time in slow_handlers if time > overall_avg * 2]
        
        if outliers:
            results["issues"].append({
                "type": "performance_outliers",
                "outliers": [
                    {
                        "handler": handler,
                        "avg_time_ms": time * 1000,
                        "times_slower": time / overall_avg
                    }
                    for handler, time in outliers
                ],
                "description": "Handlers with significantly slower performance"
            })
    
    return results

class EventProfiler:
    """
    Utility for profiling event handler performance.
    Provides a context manager for focused profiling.
    """
    
    def __init__(self):
        """Initialize the event profiler."""
        self.active = False
        self.start_time = None
        self.event_stats = defaultdict(lambda: {
            "calls": 0,
            "total_time": 0,
            "min_time": float('inf'),
            "max_time": 0,
            "handlers": defaultdict(lambda: {
                "calls": 0,
                "total_time": 0,
                "errors": 0
            })
        })
    
    def __enter__(self):
        """Start profiling."""
        self.active = True
        self.start_time = time.time()
        self.event_stats.clear()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop profiling."""
        self.active = False
        self.total_time = time.time() - self.start_time
    
    def track_event(self, event_type: str, handler: str, duration: float, success: bool):
        """
        Track an event execution.
        
        Args:
            event_type: The type of event
            handler: The handler function name
            duration: Execution time in seconds
            success: Whether execution was successful
        """
        if not self.active:
            return
            
        stats = self.event_stats[event_type]
        stats["calls"] += 1
        stats["total_time"] += duration
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)
        
        handler_stats = stats["handlers"][handler]
        handler_stats["calls"] += 1
        handler_stats["total_time"] += duration
        if not success:
            handler_stats["errors"] += 1
    
    def get_report(self) -> str:
        """
        Generate a profiling report.
        
        Returns:
            String containing the formatted report
        """
        if not self.event_stats:
            return "No events were profiled."
            
        report = []
        report.append("# Event Profiling Report")
        report.append(f"Duration: {self.total_time:.2f} seconds")
        report.append(f"Events Tracked: {len(self.event_stats)}")
        report.append("")
        
        # Overall event statistics
        report.append("## Event Statistics")
        report.append("| Event Type | Calls | Avg Time (ms) | Min Time (ms) | Max Time (ms) | Handlers |")
        report.append("|------------|-------|---------------|---------------|---------------|----------|")
        
        for event_type, stats in self.event_stats.items():
            avg_time = stats["total_time"] / stats["calls"] if stats["calls"] > 0 else 0
            min_time = stats["min_time"] if stats["min_time"] != float('inf') else 0
            
            report.append(
                f"| {event_type} | {stats['calls']} | {avg_time * 1000:.2f} | " +
                f"{min_time * 1000:.2f} | {stats['max_time'] * 1000:.2f} | {len(stats['handlers'])} |"
            )
        
        report.append("")
        
        # Detailed handler statistics
        report.append("## Handler Statistics")
        
        for event_type, stats in self.event_stats.items():
            report.append(f"### {event_type}")
            report.append("| Handler | Calls | Avg Time (ms) | Total Time (ms) | Errors |")
            report.append("|---------|-------|---------------|-----------------|--------|")
            
            for handler, handler_stats in stats["handlers"].items():
                avg_time = handler_stats["total_time"] / handler_stats["calls"] if handler_stats["calls"] > 0 else 0
                
                report.append(
                    f"| {handler} | {handler_stats['calls']} | {avg_time * 1000:.2f} | " +
                    f"{handler_stats['total_time'] * 1000:.2f} | {handler_stats['errors']} |"
                )
            
            report.append("")
        
        return "\n".join(report)

def profile_events(func):
    """
    Function decorator that enables event profiling.
    
    Args:
        func: The function to wrap with profiling
        
    Returns:
        Decorated function that includes profiling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = EventProfiler()
        with profiler:
            result = func(*args, **kwargs)
            
        print(profiler.get_report())
        return result
    
    return wrapper

# Helper functions that can be used directly
def diagnose_events(system_manager):
    """Quick diagnostic of event handlers in a system manager"""
    diagnostics = EventDiagnostics(system_manager)
    return diagnostics.analyze_event_handlers()

def find_handler_conflicts(system_manager):
    """Find conflicting event handlers in a system manager"""
    diagnostics = EventDiagnostics(system_manager)
    return diagnostics.find_conflicting_handlers()

def simulate_event_dispatch(system_manager, event_name, event_data=None):
    """Simulate dispatching an event to see what would happen"""
    diagnostics = EventDiagnostics(system_manager)
    return diagnostics.simulate_event(event_name, event_data)

def analyze_event_handlers():
    """
    Analyze event handlers for all event types to find gaps
    
    Returns:
        dict: Dictionary with event analysis data
    """
    results = {}
    
    # Analyze each event type
    for event_type in SystemEventType:
        handlers = system_manager.event_listeners.get(event_type, [])
        count = len(handlers)
        
        # Get handler names when possible
        handler_names = []
        for h in handlers:
            if hasattr(h, '__qualname__'):
                handler_names.append(h.__qualname__)
            elif hasattr(h, '__name__'):
                handler_names.append(h.__name__)
            else:
                handler_names.append(str(h))
        
        results[event_type.name] = {
            'count': count,
            'handlers': handler_names
        }
    
    # Print report
    print("=== EVENT HANDLER ANALYSIS ===")
    for event, data in results.items():
        status = "✓" if data['count'] > 0 else "✗"
        print(f"{status} {event}: {data['count']} handlers")
        if data['count'] > 0:
            for handler in data['handlers']:
                print(f"    - {handler}")
    
    # Identify events with no handlers
    missing_handlers = [event for event, data in results.items() if data['count'] == 0]
    if missing_handlers:
        print("\nWARNING: Events with no handlers:")
        for event in missing_handlers:
            print(f"  - {event}")
    
    return results

def check_event_data_integrity(event_type, required_keys):
    """
    Verify that all events of the specified type have the required data keys
    
    Args:
        event_type: The SystemEventType to check
        required_keys: List of keys that should be present in event data
        
    Returns:
        bool: True if all events have required keys, False otherwise
    """
    # Create a test handler to analyze event data
    event_data_samples = []
    
    def data_collector(data):
        event_data_samples.append(data)
    
    # Register temporary handler
    system_manager.subscribe(event_type, data_collector)
    
    # Wait for some events to be collected
    # (This function would typically be called during testing/debugging)
    
    # Unregister temporary handler
    system_manager.unsubscribe(event_type, data_collector)
    
    # Analyze collected data
    if not event_data_samples:
        logger.warning(f"No events of type {event_type.name} were collected")
        return False
    
    # Check for required keys in each sample
    all_valid = True
    for i, data in enumerate(event_data_samples):
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            logger.warning(f"Event {event_type.name} sample {i} missing keys: {missing_keys}")
            all_valid = False
    
    return all_valid

def suggest_missing_handlers():
    """
    Suggest standard handler implementations for events with no handlers
    
    Returns:
        dict: Dictionary with suggested handler templates
    """
    results = analyze_event_handlers()
    suggestions = {}
    
    for event_name, data in results.items():
        if data['count'] == 0:
            event_type = getattr(SystemEventType, event_name)
            handler_name = f"_handle_{event_name.lower()}"
            
            # Create template implementation
            template = f"""def {handler_name}(self, event_data):
    \"\"\"
    Handle {event_name} events
    
    Args:
        event_data (dict): Event data including...
    \"\"\"
    # Implementation needed
    pass
"""
            suggestions[event_name] = template
    
    return suggestions 