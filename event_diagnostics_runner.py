import logging
import time
from utils.event_diagnostics import (
    get_diagnostics, 
    diagnose_event_handler, 
    profile_events, 
    EventProfiler
)
from systems.core.system_manager import system_manager, SystemEventType
from utils.event_decorators import safe_event_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('event_diagnostics')

def test_event_system():
    """
    Test the event system by registering handlers and emitting events
    """
    # Get the diagnostics instance
    diagnostics = get_diagnostics()
    diagnostics.set_system_manager(system_manager)
    
    # Register some test event handlers
    @diagnose_event_handler
    @safe_event_handler()
    def test_handler(data):
        logger.info(f"Test handler received: {data}")
        time.sleep(0.1)  # Simulate some work
    
    @diagnose_event_handler
    @safe_event_handler()
    def slow_handler(data):
        logger.info(f"Slow handler processing: {data}")
        time.sleep(0.5)  # Simulate slow processing
    
    @diagnose_event_handler
    @safe_event_handler()
    def error_handler(data):
        logger.info(f"Error handler received: {data}")
        # Simulate an error
        if data.get('cause_error', False):
            raise ValueError("Simulated error in handler")
    
    # Register handlers with the system manager
    logger.info("Registering event handlers...")
    system_manager.subscribe(SystemEventType.ENTITY_CREATED, test_handler)
    system_manager.subscribe(SystemEventType.ENTITY_COLLISION, slow_handler)
    system_manager.subscribe(SystemEventType.AGENT_DAMAGED, error_handler)
    
    # Analyze the current event handlers
    logger.info("Analyzing event handlers...")
    analysis = diagnostics.analyze_event_handlers()
    print("\n=== EVENT HANDLER ANALYSIS ===")
    print(f"Total events: {analysis.get('event_count', 0)}")
    print(f"Total handlers: {analysis.get('total_handlers', 0)}")
    if analysis.get('handler_signature_issues'):
        print("\nHandler signature issues:")
        for issue in analysis['handler_signature_issues']:
            print(f"  - {issue['handler']} on {issue['event']}: {issue['issue']}")
    
    # Test emitting events with profiling
    logger.info("Testing event emission with profiling...")
    profiler = EventProfiler()
    with profiler:
        # Emit test events
        system_manager.emit_event(SystemEventType.ENTITY_CREATED, {"entity_id": 1})
        system_manager.emit_event(SystemEventType.ENTITY_COLLISION, {"entity_id": 1, "other_id": 2})
        system_manager.emit_event(SystemEventType.AGENT_DAMAGED, {"agent_id": 1, "damage": 10})
        
        # Try to cause an error
        system_manager.emit_event(SystemEventType.AGENT_DAMAGED, {
            "agent_id": 2, 
            "damage": 20, 
            "cause_error": True
        })
    
    # Print profiler report
    print("\n=== EVENT PROFILER REPORT ===")
    print(profiler.get_report())
    
    # Check for conflicts
    conflicts = diagnostics.find_conflicting_handlers()
    if conflicts:
        print("\n=== HANDLER CONFLICTS ===")
        for conflict in conflicts:
            print(f"Handler {conflict['handler']} is subscribed to multiple events: {conflict['events']}")
    
    # Get slowest handlers
    slowest = diagnostics.get_slowest_handlers()
    print("\n=== SLOWEST HANDLERS ===")
    for handler, avg_time in slowest:
        print(f"{handler}: {avg_time*1000:.2f}ms")
    
    # Get error information
    errors = diagnostics.get_most_frequent_errors()
    if errors:
        print("\n=== ERROR REPORT ===")
        for error_type, instances in errors.items():
            print(f"{error_type}: {len(instances)} occurrences")
    
    # Generate a full report
    report = diagnostics.generate_report()
    with open("event_diagnostics_report.md", "w") as f:
        f.write(report)
    logger.info("Saved full report to event_diagnostics_report.md")
    
    # Unregister handlers
    logger.info("Unregistering event handlers...")
    system_manager.unsubscribe(SystemEventType.ENTITY_CREATED, test_handler)
    system_manager.unsubscribe(SystemEventType.ENTITY_COLLISION, slow_handler)
    system_manager.unsubscribe(SystemEventType.AGENT_DAMAGED, error_handler)

if __name__ == "__main__":
    test_event_system() 