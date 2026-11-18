import sys
import os
import unittest
from unittest.mock import Mock

# Add parent directory to path to import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from systems.core.system_manager import SystemManager, SystemEventType
from systems.core.base_system import BaseSystem

# Mock implementations for testing
class MockSystem(BaseSystem):
    def __init__(self, name, priority=0):
        super().__init__(name, priority)
        self.initialize_called = False
        self.update_called = False
        self.shutdown_called = False
    
    def _initialize(self):
        self.initialize_called = True
    
    def _update(self, delta_time):
        self.update_called = True
    
    def _shutdown(self):
        self.shutdown_called = True

class TestSystemManager(unittest.TestCase):
    def setUp(self):
        # Create a fresh system manager for each test
        self.manager = SystemManager()
    
    def test_register_system(self):
        # Test registering a system
        system = MockSystem("test_system")
        self.manager.register_system("test_system", system)
        
        # Check that the system was registered
        self.assertIn("test_system", self.manager.systems)
        self.assertEqual(self.manager.get_system("test_system"), system)
    
    def test_register_priority_order(self):
        # Test that systems are registered in priority order
        system1 = MockSystem("system1", 10)
        system2 = MockSystem("system2", 5)
        system3 = MockSystem("system3", 20)
        
        self.manager.register_system("system1", system1, 10)
        self.manager.register_system("system2", system2, 5)
        self.manager.register_system("system3", system3, 20)
        
        # Check that the update order is based on priority
        self.assertEqual(self.manager.update_order, ["system2", "system1", "system3"])
    
    def test_unregister_system(self):
        # Register and then unregister a system
        system = MockSystem("test_system")
        self.manager.register_system("test_system", system)
        
        # Unregister the system
        result = self.manager.unregister_system("test_system")
        
        # Check that the system was unregistered
        self.assertTrue(result)
        self.assertNotIn("test_system", self.manager.systems)
        self.assertNotIn("test_system", self.manager.update_order)
    
    def test_update(self):
        # Register multiple systems
        system1 = MockSystem("system1")
        system2 = MockSystem("system2")
        
        self.manager.register_system("system1", system1)
        self.manager.register_system("system2", system2)
        
        # Update all systems
        self.manager.update(0.016)
        
        # Check that the update method was called on each system
        self.assertTrue(system1.update_called)
        self.assertTrue(system2.update_called)
    
    def test_initialize_shutdown(self):
        # Register systems
        system1 = MockSystem("system1")
        system2 = MockSystem("system2")
        
        self.manager.register_system("system1", system1)
        self.manager.register_system("system2", system2)
        
        # Initialize all systems
        self.manager.initialize_all()
        
        # Check that initialize was called
        self.assertTrue(system1.initialize_called)
        self.assertTrue(system2.initialize_called)
        
        # Shutdown all systems
        self.manager.shutdown_all()
        
        # Check that shutdown was called
        self.assertTrue(system1.shutdown_called)
        self.assertTrue(system2.shutdown_called)
    
    def test_shared_state(self):
        # Test setting and getting shared state
        self.manager.set_shared_state("test_key", "test_value")
        
        # Check that the state was set
        self.assertEqual(self.manager.get_shared_state("test_key"), "test_value")
        
        # Test getting a nonexistent key with a default
        self.assertEqual(self.manager.get_shared_state("nonexistent", "default"), "default")
    
    def test_events(self):
        # Create mock event listeners
        listener1 = Mock()
        listener2 = Mock()
        
        # Subscribe to events
        self.manager.subscribe(SystemEventType.ENTITY_CREATED, listener1)
        self.manager.subscribe(SystemEventType.ENTITY_CREATED, listener2)
        
        # Emit an event
        event_data = {"entity_id": 123, "position": (10, 20)}
        self.manager.emit_event(SystemEventType.ENTITY_CREATED, event_data)
        
        # Check that both listeners were called with the event data
        listener1.assert_called_once_with(event_data)
        listener2.assert_called_once_with(event_data)
        
        # Unsubscribe one listener
        self.manager.unsubscribe(SystemEventType.ENTITY_CREATED, listener1)
        
        # Emit another event
        event_data2 = {"entity_id": 456, "position": (30, 40)}
        self.manager.emit_event(SystemEventType.ENTITY_CREATED, event_data2)
        
        # The first listener should not be called again
        listener1.assert_called_once()  
        
        # The second listener should be called again with the new data
        self.assertEqual(listener2.call_count, 2)
        listener2.assert_called_with(event_data2)

class TestBaseSystem(unittest.TestCase):
    def setUp(self):
        # Create a fresh system manager for each test
        self.manager = SystemManager()
    
    def test_auto_registration(self):
        # Create a system - it should auto-register with the manager
        system = MockSystem("test_system")
        
        # Check that it's registered
        self.assertIn("test_system", self.manager.systems)
    
    def test_initialization_flow(self):
        # Create a system
        system = MockSystem("test_system")
        
        # Initialize the system
        system.initialize()
        
        # Check that the _initialize method was called
        self.assertTrue(system.initialize_called)
        
        # Trying to initialize again should do nothing
        system.initialize_called = False
        system.initialize()
        self.assertFalse(system.initialize_called)
    
    def test_update_flow(self):
        # Create a system
        system = MockSystem("test_system")
        
        # Initialize the system
        system.initialize()
        
        # Update the system
        system.update(0.016)
        
        # Check that the _update method was called
        self.assertTrue(system.update_called)
        
        # Disable the system and try to update again
        system.update_called = False
        system.disable()
        system.update(0.016)
        
        # Check that the _update method wasn't called
        self.assertFalse(system.update_called)
    
    def test_shutdown_flow(self):
        # Create a system
        system = MockSystem("test_system")
        
        # Initialize the system
        system.initialize()
        
        # Shutdown the system
        system.shutdown()
        
        # Check that the _shutdown method was called
        self.assertTrue(system.shutdown_called)
        
        # Trying to shutdown again should do nothing
        system.shutdown_called = False
        system.shutdown()
        self.assertFalse(system.shutdown_called)

if __name__ == "__main__":
    unittest.main() 