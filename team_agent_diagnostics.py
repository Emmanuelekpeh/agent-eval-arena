"""
Team Agent Example with Event Diagnostics

This script runs the team agent example with event diagnostics enabled
to analyze and monitor the event system during execution.
"""

import logging
import sys
from utils.event_diagnostics import (
    get_diagnostics, 
    diagnose_event_handler, 
    EventProfiler
)
from systems.core.system_manager import system_manager, SystemEventType
from examples.team_agent_example import main as run_team_agent_example

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('team_agent_diagnostics')

def setup_diagnostics():
    """
    Set up event diagnostics before running the example
    """
    # Get the diagnostics instance
    diagnostics = get_diagnostics()
    diagnostics.set_system_manager(system_manager)
    
    # Analyze the initial state of handlers
    logger.info("Analyzing initial event handlers...")
    initial_analysis = diagnostics.analyze_event_handlers()
    print("\n=== INITIAL EVENT HANDLER ANALYSIS ===")
    print(f"Total events: {initial_analysis.get('event_count', 0)}")
    print(f"Total handlers: {initial_analysis.get('total_handlers', 0)}")
    
    return diagnostics

def run_with_diagnostics():
    """
    Run the team agent example with diagnostics enabled
    """
    # Set up diagnostics
    diagnostics = setup_diagnostics()
    
    # Create the profiler for tracking events during execution
    profiler = EventProfiler()
    
    try:
        # Start the profiler
        with profiler:
            # Run the team agent example
            logger.info("Running team agent example with diagnostics...")
            run_team_agent_example()
    except Exception as e:
        logger.error(f"Error running team agent example: {e}")
        import traceback
        traceback.print_exc()
    
    # Print profiler report
    print("\n=== EVENT PROFILER REPORT ===")
    print(profiler.get_report())
    
    # Final analysis of handlers
    logger.info("Performing final analysis of event handlers...")
    final_analysis = diagnostics.analyze_event_handlers()
    print("\n=== FINAL EVENT HANDLER ANALYSIS ===")
    print(f"Total events: {final_analysis.get('event_count', 0)}")
    print(f"Total handlers: {final_analysis.get('total_handlers', 0)}")
    
    # Check for conflicts
    conflicts = diagnostics.find_conflicting_handlers()
    if conflicts:
        print("\n=== HANDLER CONFLICTS ===")
        for conflict in conflicts:
            print(f"Handler {conflict['handler']} is subscribed to multiple events: {conflict['events']}")
    
    # Get slowest handlers
    slowest = diagnostics.get_slowest_handlers()
    if slowest:
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
    with open("team_agent_diagnostics_report.md", "w") as f:
        f.write(report)
    logger.info("Saved full report to team_agent_diagnostics_report.md")

if __name__ == "__main__":
    run_with_diagnostics() 