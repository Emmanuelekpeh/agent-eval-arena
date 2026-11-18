#!/usr/bin/env python3
"""
Migration script to convert from old configuration format to new unified format.
This script will read both settings.py and config.py, and generate a new game_config.json
file in the unified format.
"""

import json
import os
import sys
from pathlib import Path
import importlib.util
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('config_migration')

def import_module_from_path(module_name, module_path):
    """Import a module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def migrate_config():
    """Migrate from old config format to new unified format."""
    try:
        # Get the config directory
        config_dir = Path(__file__).parent
        
        # Path to the new config file
        new_config_path = config_dir / 'game_config.json'
        
        # Check if old config modules exist
        settings_path = config_dir / 'settings.py'
        config_path = Path(__file__).parent.parent / 'config.py'
        
        if not settings_path.exists() and not config_path.exists():
            logger.error("Could not find old configuration files (settings.py or config.py)")
            return False
        
        # Initialize the new config structure
        new_config = {
            'version': '1.0.0',
            'display': {},
            'performance': {},
            'agent': {},
            'environment': {}
        }
        
        # Import the old settings module if it exists
        old_settings = None
        if settings_path.exists():
            try:
                old_settings = import_module_from_path('settings', settings_path)
                logger.info(f"Imported old settings from {settings_path}")
            except Exception as e:
                logger.error(f"Failed to import settings.py: {str(e)}")
        
        # Import the old config module if it exists
        old_config = None
        if config_path.exists():
            try:
                old_config = import_module_from_path('old_config', config_path)
                logger.info(f"Imported old config from {config_path}")
            except Exception as e:
                logger.error(f"Failed to import config.py: {str(e)}")
        
        # Migrate settings from GameConfig
        if old_settings and hasattr(old_settings, 'config'):
            logger.info("Migrating settings from GameConfig...")
            
            # Get GameConfig instance
            game_config = old_settings.config
            
            # Map display settings
            if hasattr(game_config, 'SCREEN_WIDTH'):
                new_config['display']['SCREEN_WIDTH'] = game_config.SCREEN_WIDTH
            if hasattr(game_config, 'SCREEN_HEIGHT'):
                new_config['display']['SCREEN_HEIGHT'] = game_config.SCREEN_HEIGHT
            if hasattr(game_config, 'TARGET_FPS'):
                new_config['display']['TARGET_FPS'] = game_config.TARGET_FPS
            if hasattr(game_config, 'MAX_FPS'):
                new_config['display']['MAX_FPS'] = game_config.MAX_FPS
            if hasattr(game_config, 'MIN_FPS'):
                new_config['display']['MIN_FPS'] = game_config.MIN_FPS
            
            # Map performance settings
            if hasattr(game_config, 'PERFORMANCE'):
                perf = game_config.PERFORMANCE
                for key, value in perf.items():
                    new_config['performance'][key] = value
            
            # Map agent settings
            if hasattr(game_config, 'AGENT_CONFIG'):
                agent_cfg = game_config.AGENT_CONFIG
                for key, value in agent_cfg.items():
                    new_config['agent'][key] = value
        
        # Migrate settings from Config
        if old_config and hasattr(old_config, 'config'):
            logger.info("Migrating settings from Config...")
            
            # Get Config instance
            config_obj = old_config.config
            
            # Map game_config to display/performance
            if hasattr(config_obj, 'game_config'):
                game_cfg = config_obj.game_config
                for key, value in game_cfg.items():
                    if key in ['SCREEN_WIDTH', 'SCREEN_HEIGHT', 'TARGET_FPS', 'MAX_FPS', 'MIN_FPS']:
                        new_config['display'][key] = value
                    else:
                        new_config['performance'][key] = value
            
            # Map agent_config to agent section
            if hasattr(config_obj, 'agent_config'):
                agent_cfg = config_obj.agent_config
                for key, value in agent_cfg.items():
                    new_config['agent'][key] = value
        
        # Save the new configuration
        with open(new_config_path, 'w') as f:
            json.dump(new_config, f, indent=4)
        
        logger.info(f"Successfully migrated configuration to {new_config_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to migrate configuration: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = migrate_config()
    sys.exit(0 if success else 1) 