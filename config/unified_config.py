import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Explicitly get the logger configured in utils
from systems.utils.logging import logger as system_logger

class UnifiedConfig:
    """
    Unified configuration system for the AI Battle Arena.
    Provides a hierarchical structure for all game settings.
    """
    def __init__(self, config_path: Optional[Path] = None):
        self.logger = system_logger # Use the specific logger
        # Set up configuration path
        self.config_path = config_path if config_path else Path(__file__).parent
        self.config_file = self.config_path / 'game_config.json'
        
        # Initialize configuration sections
        self.display = {
            'SCREEN_WIDTH': 1200,
            'SCREEN_HEIGHT': 800,
            'TARGET_FPS': 30,
            'MAX_FPS': 60,
            'MIN_FPS': 20,
        }
        
        self.performance = {
            'MIN_FPS': 25,
            'MAX_MEMORY_MB': 1500,
            'MAX_AGENTS': 10,
            'MAX_ENEMIES': 15, # Added: Max number of enemies
            'MIN_DECISION_TIME_MS': 16,
            'MEMORY_WARNING_THRESHOLD': 0.8,
            'QUADTREE_CAPACITY': 4 # Default capacity
        }
        
        self.agent = {
            'MIN_MEMORY_PER_AGENT': 50 * 1024,
            'MAX_AGENTS': 50,
            'STATE_SIZE': 96,
            'AGENT_TYPES': [
                'MLPAgent1', 
                'MLPAgent2', 
                'PerceptronAgent1', 
                'PerceptronAgent2', 
                'PerceptronAgent3',
                'ConvolutionalAgent',
                'EvolutionaryAgent',
                'FuzzyAgent'
            ], # Default list
            'BEHAVIOR_METRICS': {
                'exploration_weight': 0.3,
                'tactical_bonus': 0.25,
                'team_synergy': 0.2,
                'resource_efficiency': 0.15,
                'combat_effectiveness': 0.1
            }
        }
        
        self.environment = {
            'GRID_SIZE': 32,
            'HAZARD_DAMAGE': 1,
            'ZONE_SHRINK_RATE': 0.99,
            'RESOURCE_SPAWN_INTERVAL': 300,
            'ENEMY_SPAWN_INTERVAL_SECONDS': 5 # Added: Enemy spawn interval
        }

        # --- NEW: Colors Section ---
        self.colors = {
            'RED': [255, 0, 0],
            'GREEN': [0, 255, 0],
            'BLUE': [0, 0, 255],
            'WHITE': [255, 255, 255],
            'BLACK': [0, 0, 0],
            'YELLOW': [255, 255, 0],
            'CYAN': [0, 255, 255],
            'MAGENTA': [255, 0, 255],
            'GREY': [128, 128, 128]
        }
        # --- End Colors Section ---
        
        # --- NEW: Combat Section ---
        self.combat = {
            "BASE_ACCURACY": 0.8,
            "BASE_DAMAGE": 10,
            "CRITICAL_CHANCE": 0.1,
            "CRITICAL_MULTIPLIER": 2.0,
            "OUTSIDE_ZONE_VULNERABILITY": 1.1, # Added: 10% damage increase outside zone
            "CRITICAL_STATUS_CHANCE": 0.3, # Added: Chance for crit to apply status
            "CRITICAL_STATUS_EFFECTS": [ # Added: Possible effects from crits
                 {"type": "burn", "duration": 2.0, "strength": 0.8},
                 {"type": "slow", "duration": 2.0, "strength": 0.5},
                 {"type": "disable", "duration": 1.0, "strength": 1.0}
            ],
            "STATUS_EFFECTS": { # Definitions for status effects
                "vulnerable": {
                    "damage_taken_multiplier": 1.2 # Target takes 20% more damage
                },
                "fortified": {
                    "damage_taken_multiplier": 0.8 # Target takes 20% less damage
                },
                "frenzy": { # Attacker effect
                     "damage_dealt_multiplier": 1.15 # Attacker deals 15% more damage
                },
                "weakened": { # Attacker effect
                     "damage_dealt_multiplier": 0.75 # Attacker deals 25% less damage
                }
                # Add other effects like 'resistant', etc. here
            },
            "WEAPONS": {
                "standard": {
                    "damage_multiplier": 1.0,
                    "crit_chance_mod": 1.0,
                    "crit_multiplier_mod": 1.0,
                    "tags": ["physical"]
                },
                "heavy": {
                    "damage_multiplier": 1.5,
                    "crit_chance_mod": 0.9, # Slightly lower crit chance?
                    "crit_multiplier_mod": 1.1, # Slightly higher crit damage?
                    "tags": ["physical", "heavy"]
                },
                "rapid": {
                    "damage_multiplier": 0.6,
                    "crit_chance_mod": 1.1, # Slightly higher crit chance?
                    "crit_multiplier_mod": 0.9, # Slightly lower crit damage?
                    "tags": ["physical", "rapid"]
                },
                "sniper": {
                    "damage_multiplier": 2.0,
                    "crit_chance_mod": 1.2, # Higher crit chance
                    "crit_multiplier_mod": 1.5, # Higher crit damage
                    "tags": ["physical", "sniper"]
                },
                # Add placeholders for effects mentioned in attack()
                "fire": {
                    "damage_multiplier": 1.0,
                    "crit_chance_mod": 1.0,
                    "crit_multiplier_mod": 1.0,
                    "applies_status": {"type": "burn", "duration": 3.0, "strength": 1.0},
                    "tags": ["elemental", "fire"]
                },
                "ice": {
                    "damage_multiplier": 1.0,
                    "crit_chance_mod": 1.0,
                    "crit_multiplier_mod": 1.0,
                    "applies_status": {"type": "slow", "duration": 2.0, "strength": 0.5},
                    "tags": ["elemental", "ice"]
                },
                "electric": {
                    "damage_multiplier": 1.0,
                    "crit_chance_mod": 1.0,
                    "crit_multiplier_mod": 1.0,
                    "applies_status": {"type": "disable", "duration": 1.0, "strength": 1.0},
                    "tags": ["elemental", "electric"]
                }
            }
        }
        # --- End Combat Section ---
        
        # --- NEW: Enemy Section ---
        self.enemy = {
            'ENEMY_TYPES': [
                 'Enemy',          # Base enemy class name
                 'FastEnemy', 
                 'TankEnemy', 
                 'SniperEnemy'
            ],
            'ENEMY_SPAWN_WEIGHTS': [0.4, 0.3, 0.2, 0.1] # Weights must match order in ENEMY_TYPES
        }
        # --- End Enemy Section ---
        
        # Version tracking
        self.version = '1.0.0'
        
        # Load custom configuration
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from file, merging with defaults."""
        print("DEBUG: Entering load_config method...") 
        
        # DEBUG: Check file path and existence **BEFORE** the if check
        self.logger.debug(f"Attempting to load config from: {self.config_file}")
        self.logger.debug(f"Config file exists: {self.config_file.exists()}")
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    custom_config = json.load(f)
                self.logger.debug(f"Loaded custom_config from JSON: {custom_config}") # Use specific logger
                
                # Update version if present
                if 'version' in custom_config:
                    self.version = custom_config.pop('version')
                
                # Update each section with custom values, adding new keys if necessary
                for section_name, section_data in custom_config.items():
                    if hasattr(self, section_name):
                        section_dict = getattr(self, section_name)
                        if isinstance(section_dict, dict):
                            if section_name == 'agent': self.logger.debug(f"Processing 'agent' section...")
                            for key, value in section_data.items():
                                if section_name == 'agent': self.logger.debug(f"  Processing key: '{key}'")
                                if key in section_dict and isinstance(value, dict) and isinstance(section_dict[key], dict):
                                    self._deep_update(section_dict[key], value)
                                    if section_name == 'agent': self.logger.debug(f"    Deep updated '{key}'")
                                else:
                                    section_dict[key] = value
                                    if section_name == 'agent': self.logger.debug(f"    Set/Added '{key}' = {value}")
                        # else: handle cases where attribute is not a dict if needed
                    # else: handle cases where section from JSON doesn't exist as an attribute if needed

                self.logger.debug(f"Final self.agent state: {self.agent}") # Use specific logger
                self.logger.info(f"Loaded configuration from {self.config_file}") # Use specific logger
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"Error loading configuration: {str(e)}") # Use specific logger
        else: # Add an else block for clarity
            self.logger.warning(f"Configuration file not found at {self.config_file}. Using default settings.")
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            config_data = {
                'version': self.version,
                'display': self.display,
                'performance': self.performance,
                'agent': self.agent,
                'environment': self.environment,
                'colors': self.colors, # Add colors section to save data
                'combat': self.combat, # Add combat section to save data
                'enemy': self.enemy, # Add enemy section to save data
                'personality': {
                    "ARCHETYPE_VARIATION": 0.15,
                    "ARCHETYPE_DISTRIBUTION": {
                        "balanced": 0.3,
                        "aggressive": 0.2,
                        "defensive": 0.2,
                        "supportive": 0.15,
                        "scout": 0.15
                    },
                    "DECISION_INFLUENCE": 0.3
                },
                "morale_suppression": {
                     "INITIAL_MORALE": 0.5,
                     "MORALE_MAX": 1.0,
                     "MORALE_MIN": 0.0, # Changed to 0-1 scale
                     "MORALE_PASSIVE_RATE": 0.0, # Passive change per second (can be negative)
                     "SUPPRESSION_MAX": 1.0,
                     "SUPPRESSION_DECAY_RATE": 0.15, # Decay per second
                     "MORALE_EVENT_MODIFIERS": {
                         "deal_damage_minor": 0.01,
                         "deal_damage_major": 0.05,
                         "take_damage_minor": -0.02,
                         "take_damage_major": -0.08,
                         "kill_enemy": 0.15,
                         "ally_death": -0.20,
                         "team_victory": 0.3,
                         "team_defeat": -0.3,
                         "receive_heal": 0.05,
                         "objective_complete": 0.2,
                         "objective_fail": -0.15
                     },
                     "SUPPRESSION_EVENT_MODIFIERS": {
                         "near_miss_bullet": 0.1, # Base increase for a near miss
                         "direct_hit_no_damage": 0.05, # e.g., hit shield
                         "nearby_explosion": 0.3 # Added for explosions
                         # heavy_fire_volume might need to be calculated dynamically
                     },
                     "PERSONALITY_INFLUENCE_WEIGHTS": {
                         "morale_gain": 0.6, # How much personality affects positive morale changes
                         "morale_loss": 0.7, # How much personality affects negative morale changes
                         "suppression_gain": 0.5, # How much personality affects suppression gain
                         "suppression_decay": 0.4 # How much personality affects suppression decay
                     },
                     "SUPPRESSION_EFFECT_ACCURACY_MAX_PENALTY": 0.6, # 60% max accuracy reduction
                     "SUPPRESSION_EFFECT_SPEED_MAX_PENALTY": 0.5 # 50% max speed reduction
                }
            }
            
            # Ensure the config directory exists before trying to write
            config_dir = self.config_file.parent
            try:
                 config_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                 self.logger.error(f"Error creating config directory {config_dir}: {e}")
                 return # Abort saving if directory cannot be created

            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            self.logger.info(f"Saved configuration to {self.config_file}")
        except IOError as e:
            self.logger.error(f"Error saving configuration: {str(e)}")
    
    def _deep_update(self, target: Dict, source: Dict) -> None:
        """Recursively update nested dictionaries."""
        for key, value in source.items():
            if key in target and isinstance(value, dict) and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value from a specific section, handling nested keys.

        Args:
            section: The top-level configuration section (e.g., 'combat', 'display').
            key: The configuration key, potentially nested (e.g., 'WEAPONS.standard.damage_multiplier').
            default: Default value if the section or key doesn't exist.

        Returns:
            The configuration value or default.
        """
        # Check if the top-level section exists as an attribute and is a dict
        if not hasattr(self, section) or not isinstance(getattr(self, section), dict):
            self.logger.debug(f"Section '{section}' not found or not a dictionary.")
            return default

        section_dict = getattr(self, section)

        # Handle nested vs. non-nested keys
        parts = key.split('.')
        current_level = section_dict

        for part in parts:
            if isinstance(current_level, dict) and part in current_level:
                current_level = current_level[part]
            else:
                # Key path not found at this part
                self.logger.debug(f"Key part '{part}' not found in path '{key}' within section '{section}'. Returning default.")
                return default

        # If the loop completes, current_level holds the final value
        return current_level
    
    def set(self, section: str, key: str, value: Any) -> bool:
        """
        Set a configuration value in a specific section.
        
        Args:
            section: The configuration section
            key: The configuration key
            value: The new value
            
        Returns:
            True if successful, False otherwise
        """
        if hasattr(self, section) and isinstance(getattr(self, section), dict):
            section_dict = getattr(self, section)
            section_dict[key] = value
            return True
        # Handle setting nested keys like combat.WEAPONS.standard.damage_multiplier
        parts = key.split('.')
        if len(parts) > 1 and hasattr(self, section) and isinstance(getattr(self, section), dict):
             current_level = getattr(self, section)
             for i, part in enumerate(parts):
                 if i == len(parts) - 1: # Last part, set the value
                     if isinstance(current_level, dict):
                         current_level[part] = value
                         return True
                     else:
                         return False # Cannot set value on non-dict
                 else: # Navigate deeper
                     if isinstance(current_level, dict) and part in current_level:
                         current_level = current_level[part]
                     else:
                         # Optionally create intermediate dicts if needed
                         # current_level[part] = {}
                         # current_level = current_level[part]
                         # For now, fail if path doesn't exist
                         return False
        return False
    
    def validate(self) -> bool:
        """
        Validate the configuration values.
        
        Returns:
            True if valid, False otherwise
        """
        # Basic validation rules
        is_valid = True
        
        # Display validation
        if self.display['SCREEN_WIDTH'] <= 0 or self.display['SCREEN_HEIGHT'] <= 0:
            self.logger.error("Screen dimensions must be positive")
            is_valid = False
        
        if not (10 <= self.display['MIN_FPS'] <= self.display['TARGET_FPS'] <= self.display['MAX_FPS']):
            self.logger.error("FPS settings must satisfy: MIN_FPS <= TARGET_FPS <= MAX_FPS")
            is_valid = False
        
        # Performance validation
        if self.performance['MAX_AGENTS'] < 1:
            self.logger.error("MAX_AGENTS must be at least 1")
            is_valid = False
        if self.performance['QUADTREE_CAPACITY'] < 1:
            self.logger.error("QUADTREE_CAPACITY must be at least 1")
            is_valid = False
        
        # Agent validation
        if self.agent['MIN_MEMORY_PER_AGENT'] <= 0:
            self.logger.error("MIN_MEMORY_PER_AGENT must be positive")
            is_valid = False
        
        return is_valid

# Global configuration instance
config = UnifiedConfig() 