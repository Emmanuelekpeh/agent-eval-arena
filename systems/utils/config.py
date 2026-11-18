import json
import os
import logging

class Config:
    """
    Configuration manager for the AI Battle Arena.
    Handles loading and validation of game settings.
    """
    
    def __init__(self):
        """Initialize with default configuration values"""
        # Display settings
        self.display = {
            'SCREEN_WIDTH': 1280,
            'SCREEN_HEIGHT': 720,
            'TARGET_FPS': 60,
            'FULLSCREEN': False,
            'SHOW_DEBUG': False,
        }
        
        # Performance settings
        self.performance = {
            'MAX_AGENTS': 8,
            'MAX_PARTICLES': 2000,
            'ENABLE_VISUAL_EFFECTS': True,
            'MULTI_THREADING': True,
        }
        
        # Game settings
        self.game = {
            'ROUND_LENGTH': 60,  # seconds
            'MAX_ROUNDS': 5,
            'ZONE_SHRINK_RATE': 0.5,  # per second
            'ZONE_DAMAGE': 1.0,  # per second
        }
        
        # Agent settings
        self.agent = {
            'MAX_AGENTS': 16,
            'AGENT_TYPES': [
                'BasicAgent',
                'NeuralAgent',
                'EvolutionaryAgent',
                'FuzzyAgent',
                'RuleBasedAgent',
            ],
            'ENABLE_TEAMS': True,
            'TEAM_SIZE': 2,
        }
        
        # Resource settings
        self.resource = {
            'MAX_NODES': 10,
            'SPAWN_INTERVAL': 5,  # seconds
            'RESOURCE_TYPES': ['energy', 'health', 'shield'],
        }
        
        # Combat settings
        self.combat = {
            'DAMAGE_MULTIPLIER': 1.0,
            'CRITICAL_CHANCE': 0.05,
            'CRITICAL_MULTIPLIER': 2.0,
        }
        
        # Load custom settings if available
        self._load_from_file()
        
    def _load_from_file(self):
        """Load configuration from config.json if it exists"""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.json')
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    
                # Update configuration with loaded data
                for section, values in data.items():
                    if hasattr(self, section):
                        section_dict = getattr(self, section)
                        section_dict.update(values)
                        
                logging.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logging.error(f"Failed to load configuration: {str(e)}")
                
    def validate(self):
        """
        Validate the configuration settings.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # Check screen dimensions
        if self.display['SCREEN_WIDTH'] < 800 or self.display['SCREEN_HEIGHT'] < 600:
            logging.error("Screen dimensions too small (minimum 800x600)")
            return False
            
        # Check FPS
        if self.display['TARGET_FPS'] < 30:
            logging.error("Target FPS too low (minimum 30)")
            return False
            
        # Check agent limits
        if self.performance['MAX_AGENTS'] > 32:
            logging.warning("MAX_AGENTS set very high, may impact performance")
            
        # Check round length
        if self.game['ROUND_LENGTH'] < 30:
            logging.warning("Round length very short, may affect gameplay")
            
        return True
        
    def save(self):
        """Save current configuration to config.json"""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.json')
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        try:
            data = {
                'display': self.display,
                'performance': self.performance,
                'game': self.game,
                'agent': self.agent,
                'resource': self.resource,
                'combat': self.combat,
            }
            
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=4)
                
            logging.info(f"Saved configuration to {config_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to save configuration: {str(e)}")
            return False


# Create singleton instance
config = Config() 