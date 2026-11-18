"""
Event System Test

This script provides a focused test of the event system,
registering handlers for various events and testing the 
diagnostic capabilities.
"""

import logging
import time
from utils.event_diagnostics_patched import (
    get_diagnostics_patched,
    diagnose_event_handler_patched,
    EventDiagnosticsPatch
)
from systems.core.system_manager import system_manager, SystemEventType
from utils.event_decorators import safe_event_handler, event_timer
from utils.safe_events import safe_event_handler as safe_event_handler_alt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('event_system_test')

def test_basic_event_handling():
    """Test basic event handling with the system manager."""
    print("\n=== TESTING BASIC EVENT HANDLING ===")
    
    # Create a simple handler
    def basic_handler(data):
        print(f"Basic handler received: {data}")
    
    # Register the handler
    event_type = SystemEventType.ENTITY_CREATED
    system_manager.subscribe(event_type, basic_handler)
    
    # Emit an event
    print("Emitting ENTITY_CREATED event...")
    system_manager.emit_event(event_type, {"entity_id": 123, "type": "player"})
    
    # Unsubscribe
    system_manager.unsubscribe(event_type, basic_handler)
    print("Handler unsubscribed")

def test_event_decorators():
    """Test different event decorators."""
    print("\n=== TESTING EVENT DECORATORS ===")
    
    # Test with event_decorators.safe_event_handler
    @safe_event_handler()
    def safe_handler(data):
        print(f"Safe handler received: {data}")
        if data.get("should_fail", False):
            raise ValueError("Simulated error in safe handler")
    
    # Test with event_timer
    @event_timer
    def timed_handler(data):
        print(f"Timed handler processing: {data}")
        time.sleep(0.2)  # Simulate work
    
    # Test with safe_events.safe_event_handler
    @safe_event_handler_alt()
    def alt_safe_handler(data):
        print(f"Alt safe handler received: {data}")
        if data.get("should_fail", False):
            raise ValueError("Simulated error in alt safe handler")
    
    # Register handlers
    system_manager.subscribe(SystemEventType.ENTITY_CREATED, safe_handler)
    system_manager.subscribe(SystemEventType.ENTITY_DESTROYED, timed_handler)
    system_manager.subscribe(SystemEventType.COLLISION, alt_safe_handler)
    
    # Emit events
    print("Emitting events with decorators...")
    system_manager.emit_event(SystemEventType.ENTITY_CREATED, {"entity_id": 456})
    system_manager.emit_event(SystemEventType.ENTITY_DESTROYED, {"entity_id": 456})
    system_manager.emit_event(SystemEventType.COLLISION, {"entity_id": 456, "other_id": 789})
    
    # Test error handling
    print("Testing error handling in decorators...")
    system_manager.emit_event(SystemEventType.ENTITY_CREATED, {"entity_id": 111, "should_fail": True})
    system_manager.emit_event(SystemEventType.COLLISION, {"entity_id": 222, "should_fail": True})
    
    # Unsubscribe
    system_manager.unsubscribe(SystemEventType.ENTITY_CREATED, safe_handler)
    system_manager.unsubscribe(SystemEventType.ENTITY_DESTROYED, timed_handler)
    system_manager.unsubscribe(SystemEventType.COLLISION, alt_safe_handler)

def test_event_diagnostics():
    """Test event diagnostics capabilities."""
    print("\n=== TESTING EVENT DIAGNOSTICS ===")
    
    # Get the diagnostics instance
    diagnostics = get_diagnostics_patched()
    diagnostics.set_system_manager(system_manager)
    
    # Create handlers with diagnostics wrapper
    @diagnose_event_handler_patched
    def monitored_handler(data):
        print(f"Monitored handler received: {data}")
        time.sleep(0.1)
    
    @diagnose_event_handler_patched
    def slow_monitored_handler(data):
        print(f"Slow monitored handler processing: {data}")
        time.sleep(0.5)
    
    @diagnose_event_handler_patched
    def error_monitored_handler(data):
        print(f"Error monitored handler received: {data}")
        if data.get("should_fail", False):
            raise ValueError("Simulated error in monitored handler")
    
    # Register handlers
    system_manager.subscribe(SystemEventType.ENTITY_CREATED, monitored_handler)
    system_manager.subscribe(SystemEventType.ENTITY_COLLISION, slow_monitored_handler)
    system_manager.subscribe(SystemEventType.AGENT_DAMAGED, error_monitored_handler)
    
    # Analyze handlers
    print("\nAnalyzing event handlers...")
    analysis = diagnostics.analyze_event_handlers()
    print(f"Event count: {analysis.get('event_count', 0)}")
    print(f"Total handlers: {analysis.get('total_handlers', 0)}")
    
    # Test with profiler
    print("\nTesting events with diagnostics...")
    
    # Emit test events
    system_manager.emit_event(SystemEventType.ENTITY_CREATED, {"entity_id": 1})
    system_manager.emit_event(SystemEventType.ENTITY_COLLISION, {"entity_id": 1, "other_id": 2})
    system_manager.emit_event(SystemEventType.AGENT_DAMAGED, {"agent_id": 1, "damage": 10})
    
    # Test error handling
    system_manager.emit_event(SystemEventType.AGENT_DAMAGED, {
        "agent_id": 2, 
        "damage": 20, 
        "should_fail": True
    })
    
    # Check for slowest handlers
    print("\nSlowest handlers:")
    for handler, avg_time in diagnostics.get_slowest_handlers():
        print(f"{handler}: {avg_time*1000:.2f}ms")
    
    # Generate a full report
    report = diagnostics.generate_report()
    with open("event_diagnostics_report.md", "w") as f:
        f.write(report)
    logger.info("Saved full report to event_diagnostics_report.md")
    
    # Unsubscribe handlers
    system_manager.unsubscribe(SystemEventType.ENTITY_CREATED, monitored_handler)
    system_manager.unsubscribe(SystemEventType.ENTITY_COLLISION, slow_monitored_handler)
    system_manager.unsubscribe(SystemEventType.AGENT_DAMAGED, error_monitored_handler)

def main():
    """Run all event system tests."""
    logger.info("Starting event system tests")
    
    # Test basic event handling
    test_basic_event_handling()
    
    # Test event decorators
    test_event_decorators()
    
    # Test event diagnostics
    test_event_diagnostics()
    
    logger.info("Event system tests completed")

if __name__ == "__main__":
    main() 