import sys
import os
import unittest
import json
from pathlib import Path

# Add parent directory to path to import our module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.unified_config import UnifiedConfig

class TestUnifiedConfig(unittest.TestCase):
    def setUp(self):
        # Create a test directory for configuration
        self.test_config_dir = Path('tests/test_config')
        self.test_config_dir.mkdir(exist_ok=True)
        self.config = UnifiedConfig(config_path=self.test_config_dir)
    
    def tearDown(self):
        # Clean up test files
        if (self.test_config_dir / 'game_config.json').exists():
            (self.test_config_dir / 'game_config.json').unlink()
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        self.assertEqual(self.config.display['SCREEN_WIDTH'], 1200)
        self.assertEqual(self.config.performance['MAX_MEMORY_MB'], 1500)
        self.assertEqual(self.config.agent['STATE_SIZE'], 30)
        self.assertEqual(self.config.environment['GRID_SIZE'], 32)
    
    def test_save_and_load(self):
        """Test saving and loading configuration."""
        # Modify some values
        self.config.display['SCREEN_WIDTH'] = 1600
        self.config.performance['MAX_MEMORY_MB'] = 2000
        
        # Save configuration
        self.config.save_config()
        
        # Create a new config instance that will load from the saved file
        new_config = UnifiedConfig(config_path=self.test_config_dir)
        
        # Check that values are loaded correctly
        self.assertEqual(new_config.display['SCREEN_WIDTH'], 1600)
        self.assertEqual(new_config.performance['MAX_MEMORY_MB'], 2000)
    
    def test_get_set_methods(self):
        """Test the get and set methods."""
        # Test get with existing value
        self.assertEqual(self.config.get('display', 'SCREEN_WIDTH'), 1200)
        
        # Test get with non-existing value and default
        self.assertEqual(self.config.get('display', 'NONEXISTENT', 'default'), 'default')
        
        # Test set method
        self.assertTrue(self.config.set('display', 'SCREEN_WIDTH', 1800))
        self.assertEqual(self.config.display['SCREEN_WIDTH'], 1800)
        
        # Test set with invalid section
        self.assertFalse(self.config.set('nonexistent', 'key', 'value'))
    
    def test_validation(self):
        """Test configuration validation."""
        # Valid configuration
        self.assertTrue(self.config.validate())
        
        # Invalid screen dimensions
        self.config.display['SCREEN_WIDTH'] = -100
        self.assertFalse(self.config.validate())
        
        # Fix screen dimensions but break FPS relationship
        self.config.display['SCREEN_WIDTH'] = 1200
        self.config.display['MIN_FPS'] = 100
        self.config.display['TARGET_FPS'] = 30
        self.assertFalse(self.config.validate())
    
    def test_deep_update(self):
        """Test deep updating of nested dictionaries."""
        # Create a test configuration file with nested data
        test_config = {
            "agent": {
                "BEHAVIOR_METRICS": {
                    "exploration_weight": 0.5,
                    "new_metric": 0.8
                },
                "MAX_AGENTS": 25
            }
        }
        
        with open(self.test_config_dir / 'game_config.json', 'w') as f:
            json.dump(test_config, f)
        
        # Load the test configuration
        test_config_instance = UnifiedConfig(config_path=self.test_config_dir)
        
        # Check that nested values are updated correctly
        self.assertEqual(test_config_instance.agent['BEHAVIOR_METRICS']['exploration_weight'], 0.5)
        self.assertEqual(test_config_instance.agent['BEHAVIOR_METRICS']['new_metric'], 0.8)
        self.assertEqual(test_config_instance.agent['MAX_AGENTS'], 25)
        
        # Check that other values remain unchanged
        self.assertEqual(test_config_instance.agent['BEHAVIOR_METRICS']['tactical_bonus'], 0.25)
        self.assertEqual(test_config_instance.display['SCREEN_WIDTH'], 1200)

if __name__ == '__main__':
    unittest.main() 