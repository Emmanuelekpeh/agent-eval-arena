"""
Patched version of event diagnostics that works with the event_listeners attribute instead of event_handlers
"""

import logging
import inspect
from types import FunctionType
from typing import Dict, List, Callable, Any, Set, Optional, Tuple
import time
import traceback
from collections import defaultdict
from functools import wraps

from systems.core.system_manager import system_manager, SystemEventType

logger = logging.getLogger('battle_arena')

class EventDiagnosticsPatch:
    """
    A patched version of the EventDiagnostics class that works with the current system_manager
    by using the event_listeners attribute instead of event_handlers.
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
            # Convert event_listeners to the expected format
            handlers = {}
            for event_type, callbacks in self.system_manager.event_listeners.items():
                handlers[event_type.name] = callbacks
            return handlers
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
        
        # List all registered handlers
        handlers = self.get_all_event_handlers()
        if handlers:
            report.append("## Registered Event Handlers")
            report.append("| Event Type | Handlers |")
            report.append("|------------|----------|")
            
            for event_type, handlers_list in handlers.items():
                handler_names = [self._get_handler_id(h) for h in handlers_list]
                report.append(f"| {event_type} | {', '.join(handler_names) if handler_names else 'None'} |")
            
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
_diagnostics_patch = EventDiagnosticsPatch(system_manager)

def get_diagnostics_patched() -> EventDiagnosticsPatch:
    """
    Get the patched global event diagnostics instance.
    
    Returns:
        The patched global EventDiagnosticsPatch instance
    """
    return _diagnostics_patch

def diagnose_event_handler_patched(func):
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
        # For enum event types, extract the name
        if hasattr(event, 'name'):
            event_type = event.name
        else:
            event_type = str(event)
            
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
            _diagnostics_patch.track_event(
                event_type=event_type,
                handler_name=handler_name,
                duration=duration,
                success=success,
                error=error
            )
    
    return wrapper 