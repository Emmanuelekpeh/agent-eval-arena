"""
Enhanced Game Loop for AI Battle Arena

This module implements a comprehensive game loop that integrates all systems:
- Agent systems (Team, MLP, Perceptron)
- Environment systems
- Learning systems with visualization
- Combat systems
- Team formation and coordination
"""

import pygame
import os
import sys
import time
import random
import numpy as np
from typing import Dict, List, Any, Tuple

# Core systems
from systems.core.system_manager import SystemManager
from systems.core.performance import PerformanceMonitor
from systems.quality_manager import QualityManager
from systems.utils.config import config
from systems.utils.logging import logger

# Agent systems
from systems.agents.agent_factory import create_agent, get_available_agent_types
from systems.agents.agent_system import AgentSystem
from systems.agents.team_system import TeamSystem
from systems.agents.team_agent import TeamAgent
from systems.agents.personality_system import PersonalitySystem
from systems.morale.morale_suppression_system import MoraleSuppressionSystem

# Environment systems
from systems.environment.environment import BattleRoyaleEnv
from systems.environment.resource_system import ResourceManager
from systems.environment.terrain_system import TerrainSystem
from systems.environment.resource_sharing import ResourceSharingSystem
from systems.environment.hazard_cover_system import HazardCoverSystem
from systems.environment.time_system import TimeSystem
from systems.environment.weather_system import WeatherSystem
from systems.environment.environment_integration import StageBasedEnvironment

# Combat systems
from systems.combat.combat_system import CombatSystem
from systems.combat.battle_mechanics import WeaponSystem, ShieldSystem
from systems.combat.team_combat_integration import TeamCombatIntegration

# Physics systems
from systems.physics.collision_system import CollisionSystem

# Learning systems
from systems.learning.learning_integration import LearningIntegration
from systems.learning.pattern_recognition_system import PatternRecognitionSystem
from systems.learning.strategy_adaptation_system import StrategyAdaptationSystem
from systems.learning.experience_memory import ExperienceMemory

# Visualization systems
from systems.visualization.visualization_system import VisualizationSystem
from systems.visualization.learning_visualizer import LearningVisualizer
from systems.visualization.visualization_integration import VisualizationIntegration
from systems.visualization.pygame_backend import PygameBackend
from systems.analytics import BattleAnalytics

class EnhancedGameLoop:
    """
    Enhanced game loop that integrates all developed systems.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the enhanced game loop.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.logger = logger
        self.config = config
        if config_path:
            self.config.load_config(config_path)
            
        # Validate configuration
        if not self.config.validate():
            self.logger.error("Invalid configuration. Please check settings.")
            sys.exit(1)
            
        # Initialize pygame
        pygame.init()
        
        # Create system manager
        self.system_manager = SystemManager()
        
        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor()
        
        # Create learning visualizer
        self.learning_visualizer = LearningVisualizer(save_dir='analytics/learning')
        
        # Analytics system
        self.battle_analytics = BattleAnalytics()
        
        # Game state
        self.running = False
        self.paused = False
        self.round_number = 0
        self.round_time = 0
        
        # Storage for agents and teams
        self.agents = {}
        self.teams = {}
        
        self.logger.info("Enhanced Game Loop initialized")
        
    def setup(self):
        """Set up all systems and prepare for the game."""
        self.logger.info("Setting up game systems")
        
        # Create display
        self.screen = pygame.display.set_mode(
            (self.config.display['SCREEN_WIDTH'], self.config.display['SCREEN_HEIGHT'])
        )
        pygame.display.set_caption("AI Battle Arena - Enhanced")
        
        # Make resources available to all systems
        self.system_manager.set_shared_state('screen', self.screen)
        self.system_manager.set_shared_state('config', self.config)
        
        # Initialize core systems
        self._init_core_systems()
        
        # Initialize environment systems
        self._init_environment_systems()
        
        # Initialize agent systems
        self._init_agent_systems()
        
        # Initialize combat systems
        self._init_combat_systems()
        
        # Initialize learning systems
        self._init_learning_systems()
        
        # Initialize visualization systems
        self._init_visualization_systems()
        
        # Create agents and teams
        self._create_agents_and_teams()
        
        # Initialize all systems
        self.system_manager.initialize_all()
        
        self.logger.info("All systems initialized")
        
    def _init_core_systems(self):
        """Initialize core systems."""
        # Register core systems
        self.system_manager.register_system("performance_monitor", self.performance_monitor, priority=10)
        
        # Initialize and Register Quality Manager
        self.quality_manager = QualityManager()
        self.system_manager.register_system("quality_manager", self.quality_manager, priority=30)
        
    def _init_environment_systems(self):
        """Initialize environment systems."""
        # Create environment
        self.environment = BattleRoyaleEnv(
            width=self.config.display['SCREEN_WIDTH'],
            height=self.config.display['SCREEN_HEIGHT'],
            target_fps=self.config.display['TARGET_FPS']
        )
        
        # Create terrain system
        self.terrain_system = TerrainSystem(
            width=self.config.display['SCREEN_WIDTH'],
            height=self.config.display['SCREEN_HEIGHT']
        )
        
        # Create resource manager
        self.resource_manager = ResourceManager(
            width=self.config.display['SCREEN_WIDTH'],
            height=self.config.display['SCREEN_HEIGHT']
        )
        
        # Create resource sharing system
        self.resource_sharing = ResourceSharingSystem()
        
        # Register environment systems
        self.system_manager.register_system("environment", self.environment)
        self.system_manager.register_system("terrain_system", self.terrain_system)
        self.system_manager.register_system("resource_manager", self.resource_manager, priority=20)
        self.system_manager.register_system("resource_sharing", self.resource_sharing, priority=25)
        
        # Initialize and Register More Env Systems
        self.hazard_cover_system = HazardCoverSystem(
             width=self.config.display['SCREEN_WIDTH'],
             height=self.config.display['SCREEN_HEIGHT']
        )
        self.time_system = TimeSystem()
        self.weather_system = WeatherSystem()
        self.stage_environment = StageBasedEnvironment()

        # Register environment systems
        self.system_manager.register_system("battle_royale_env", self.environment, priority=15)
        self.system_manager.set_shared_state('environment', self.environment)
        self.system_manager.register_system("terrain_system", self.terrain_system)
        self.system_manager.register_system("resource_manager", self.resource_manager)
        self.system_manager.register_system("resource_sharing", self.resource_sharing)
        self.system_manager.register_system("hazard_cover_system", self.hazard_cover_system)
        self.system_manager.register_system("time_system", self.time_system)
        self.system_manager.register_system("weather_system", self.weather_system)
        self.system_manager.register_system("stage_based_environment", self.stage_environment)
        
    def _init_agent_systems(self):
        """Initialize agent systems."""
        # Create personality system
        self.personality_system = PersonalitySystem()
        
        # Create team system
        self.team_system = TeamSystem()
        
        # Initialize AgentSystem
        self.agent_system = AgentSystem()
        
        # Register agent systems
        self.system_manager.register_system("personality_system", self.personality_system, priority=50)
        self.system_manager.register_system("team_system", self.team_system, priority=55)
        self.system_manager.register_system("agent_system", self.agent_system, priority=60)
        
        # Create MoraleSuppressionSystem
        self.morale_suppression_system = MoraleSuppressionSystem()
        self.system_manager.register_system("morale_suppression_system", self.morale_suppression_system, priority=55)
        
    def _init_combat_systems(self):
        """Initialize combat systems."""
        # Create combat system
        self.combat_system = CombatSystem()
        
        # Create weapon system
        self.weapon_system = WeaponSystem()
        
        # Create shield system
        self.shield_system = ShieldSystem()
        
        # Register combat systems
        self.system_manager.register_system("combat_system", self.combat_system, priority=70)
        self.system_manager.register_system("weapon_system", self.weapon_system, priority=71)
        self.system_manager.register_system("shield_system", self.shield_system, priority=72)
        
        # Create TeamCombatIntegration
        self.team_combat_integration = TeamCombatIntegration()
        self.system_manager.register_system("TeamCombatIntegration", self.team_combat_integration, priority=75)
        
    def _init_learning_systems(self):
        """Initialize learning systems."""
        # Create learning integration
        self.learning_integration = LearningIntegration(
            env=self.environment,
            personality_system=self.personality_system,
            visualizer=self.learning_visualizer
        )
        
        # Register learning systems
        self.system_manager.register_system("learning_integration", self.learning_integration, priority=67)
        
    def _init_visualization_systems(self):
        """Initialize visualization systems."""
        # Initialize VisualizationIntegration
        self.visualization_integration = VisualizationIntegration()
        
        # Register visualization systems
        self.system_manager.register_system("visualization_integration", self.visualization_integration, priority=80)
        
        # Register analytics system if needed elsewhere, or just use the instance directly
        self.system_manager.register_system("battle_analytics", self.battle_analytics, priority=95)
        
        # Inject PygameBackend
        vis_system_instance = self.system_manager.get_system("visualization_integration")
        if vis_system_instance and hasattr(vis_system_instance, 'renderer') and vis_system_instance.renderer:
            pygame_backend = PygameBackend(self.screen)
            vis_system_instance.renderer.set_backend(pygame_backend)
            self.logger.info("Pygame backend injected into VisualizationIntegration renderer.")
        else:
            vis_system_instance = self.system_manager.get_system("visualization")
            if vis_system_instance and hasattr(vis_system_instance, 'renderer') and vis_system_instance.renderer:
                pygame_backend = PygameBackend(self.screen)
                vis_system_instance.renderer.set_backend(pygame_backend)
                self.logger.info("Pygame backend injected into VisualizationSystem renderer.")
            else:
                self.logger.error("Failed to get VisualizationIntegration/VisualizationSystem or its renderer to inject backend!")
        
    def _create_agents_and_teams(self):
        """Create agents and form teams."""
        self.logger.info("Creating agents and teams")
        
        # Ensure environment is available
        if not self.environment:
            self.logger.error("Environment not initialized before creating agents.")
            return

        # Get available agent types
        agent_types = list(get_available_agent_types().keys())
        
        # Limit number of agents
        max_agents = min(self.config.performance['MAX_AGENTS'], self.config.agent['MAX_AGENTS'])
        
        # Create agents
        agent_names = []
        for i in range(max_agents):
            # Select agent type (randomly or from config)
            agent_type = random.choice(self.config.agent['AGENT_TYPES'] 
                if 'AGENT_TYPES' in self.config.agent else agent_types)
            
            # Create agent
            agent_name = f"agent_{i}"
            agent = create_agent(agent_type, name=agent_name)
            
            # Register with systems
            self.agents[agent_name] = agent
            agent_names.append(agent_name)
            
            # Generate personality traits
            if self.personality_system:
                self.personality_system.assign_personality(agent_name)
            
            # Register with learning integration
            self.learning_integration.register_agent(agent_name, agent)
            
            # Register with Morale System
            if self.morale_suppression_system:
                self.morale_suppression_system.register_agent(agent_name)

            # Register with Combat System
            if self.combat_system:
                self.combat_system.register_agent(agent_name)

            # Attempt to spawn agent in environment
            spawn_pos = self.environment._find_valid_spawn_point()
            if spawn_pos:
                self.environment.register_agent(agent, spawn_pos[0], spawn_pos[1])
                self.logger.info(f"Registered agent {agent_name} at {spawn_pos}")
                if self.agent_system:
                    self.agent_system.register_agent(agent_name, agent, spawn_pos[0], spawn_pos[1])
            else:
                self.logger.warning(f"Could not find valid spawn point for agent {agent_name}")

        # Form teams if enabled
        if self.config.agent.get('ENABLE_TEAMS', True):
            team_size = self.config.agent.get('TEAM_SIZE', 2)
            
            # Create teams
            team_count = max(1, max_agents // team_size)
            
            # Use personality system to suggest teams if available
            available_agents_for_teams = list(agent_names)
            if self.personality_system and hasattr(self.personality_system, 'suggest_team_composition'):
                suggested_teams = self.personality_system.suggest_team_composition(available_agents_for_teams, team_size)
                
                for t_idx, team_members in enumerate(suggested_teams):
                    team_id = f"team_{t_idx}"
                    if team_members:
                        team_data = self.team_system.create_team(team_id, team_members)
                        self.teams[team_id] = team_data
                        for member in team_members:
                            if member in available_agents_for_teams:
                                available_agents_for_teams.remove(member)
            else:
                for t in range(team_count):
                    team_id = f"team_{t}"
                    team_members = []
                    for i in range(team_size):
                        if available_agents_for_teams:
                            member = available_agents_for_teams.pop(0)
                            team_members.append(member)
                        else:
                            break
                    
                    if team_members:
                        team_data = self.team_system.create_team(team_id, team_members)
                        self.teams[team_id] = team_data

            # Handle remaining agents (if any) - they remain teamless
            self.logger.info(f"Agents remaining without teams: {len(available_agents_for_teams)}")
                        
        self.logger.info(f"Created {len(self.agents)} agents and {len(self.teams)} teams")
        
    def run(self):
        """Run the main game loop."""
        self.logger.info("Starting enhanced game loop")
        
        # Setup game environment
        self.setup()
        
        # Main loop variables
        self.running = True
        self.clock = pygame.time.Clock()
        self.last_time = time.time()
        
        # Run the main loop
        while self.running:
            # Calculate delta time
            current_time = time.time()
            delta_time = current_time - self.last_time
            self.last_time = current_time
            
            # Handle events
            self._process_events()
            
            # Update all systems if not paused
            if not self.paused:
                self._update_systems(delta_time)
                
            # Render the game
            self._render(self.screen)
            
            # Update display
            pygame.display.flip()
            
            # Update performance monitor
            self.performance_monitor.update()
            
            # Adjust quality settings if needed
            self._adjust_quality()
            
            # Control frame rate
            self.clock.tick(self.config.display['TARGET_FPS'])
            
        # Shutdown
        self._shutdown()
        
    def _process_events(self):
        """Process pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_p:
                    # Toggle pause
                    self.paused = not self.paused
                    self.logger.info(f"Game {'Paused' if self.paused else 'Resumed'}")
                elif event.key == pygame.K_v:
                    # Toggle visualization
                    vis_settings = self.visualization_integration.settings
                    vis_settings['show_team_formations'] = not vis_settings['show_team_formations']
                elif event.key == pygame.K_l:
                    # Save learning visualizations
                    self._save_learning_visualizations()
                    
            # Pass events to relevant systems (like VisualizationIntegration)
            if self.visualization_integration:
                self.visualization_integration.handle_event(event)
            
    def _update_systems(self, delta_time):
        """Update all systems."""
        # Update system manager (updates all registered systems)
        self.system_manager.update(delta_time)
        
        # Update round time
        self.round_time += delta_time
        
        # Check for round end by time limit
        if self.round_time >= self.config.game.get('ROUND_LENGTH', 60):
            self.logger.info(f"Round {self.round_number} ended due to time limit.")
            self._end_round()
            return # Exit early if round ended by time
        
        # Check for Win/Loss Condition (Last Agent/Team Standing)
        if self.environment and hasattr(self.environment, 'agents'):
            active_agent_ids = list(self.environment.agents.keys())
            num_active_agents = len(active_agent_ids)
            
            winner_found = False
            winner_id = "No one"
            
            # Check based on agents first
            if num_active_agents <= 1:
                winner_id = active_agent_ids[0] if num_active_agents == 1 else "No one"
                self.logger.info(f"Game Over: Last agent standing is {winner_id}. Ending game.")
                winner_found = True
                
            # Check based on teams if teams are enabled and win not found yet
            elif self.config.agent.get('ENABLE_TEAMS', True) and self.team_system:
                active_teams = set()
                for agent_id in active_agent_ids:
                    team_id = self.team_system.get_team_id_for_agent(agent_id)
                    if team_id:
                        active_teams.add(team_id)
                    else:
                        # Consider agents without teams as individual competitors
                        active_teams.add(f"agent_{agent_id}") # Unique identifier
                        
                if len(active_teams) <= 1:
                    winner_id = list(active_teams)[0] if len(active_teams) == 1 else "No one"
                    self.logger.info(f"Game Over: Last team/agent standing is {winner_id}. Ending game.")
                    winner_found = True

            if winner_found:
                self._end_game(winner_id)
                return # Exit update early
        else:
            self.logger.warning("Environment or environment.agents not available for win condition check.")
            
    def _render(self, screen):
        """Render the game."""
        # Clear screen
        screen.fill(self.config.display.get('BACKGROUND_COLOR', (0, 0, 0)))
        
        # Let VisualizationIntegration handle rendering
        if self.visualization_integration:
            self.visualization_integration.render(screen)
        else:
            if self.environment:
                self.environment.render(screen)

        # Render UI elements overlayed
        self._render_ui(screen)
        
    def _render_ui(self, screen):
        """Render UI elements."""
        try:
            font = pygame.font.Font(None, 24)
        except pygame.error as e:
            self.logger.error(f"Failed to load font: {e}. UI rendering skipped.")
            return

        # Display round information
        round_text = font.render(f"Round: {self.round_number}", True, (255, 255, 255))
        time_remaining = max(0, int(self.config.game.get('ROUND_LENGTH', 600) - self.round_time))
        time_text = font.render(f"Time Left: {time_remaining}", True, (255, 255, 255))
        
        screen.blit(round_text, (10, 10))
        screen.blit(time_text, (10, 40))
        
        # Display performance metrics
        metrics = self.performance_monitor.get_metrics()
        fps_text = font.render(f"FPS: {metrics['fps']:.1f}", True, (255, 255, 255))
        mem_text = font.render(f"Mem: {metrics['memory_mb']:.1f} MB", True, (255, 255, 255))
        cpu_text = font.render(f"CPU: {metrics['cpu_percent']:.1f}%", True, (255, 255, 255))
        
        screen.blit(fps_text, (self.config.display['SCREEN_WIDTH'] - 150, 10))
        screen.blit(mem_text, (self.config.display['SCREEN_WIDTH'] - 150, 40))
        screen.blit(cpu_text, (self.config.display['SCREEN_WIDTH'] - 150, 70))
        
        # Display pause indicator if paused
        if self.paused:
            pause_font = pygame.font.Font(None, 72)
            pause_text = pause_font.render("PAUSED", True, (255, 0, 0))
            text_rect = pause_text.get_rect(center=(self.config.display['SCREEN_WIDTH'] // 2, 
                                                   self.config.display['SCREEN_HEIGHT'] // 2))
            pause_bg = pygame.Surface(text_rect.size, pygame.SRCALPHA)
            pause_bg.fill((0, 0, 0, 180))
            screen.blit(pause_bg, text_rect.topleft)
            screen.blit(pause_text, text_rect)
            
    def _end_round(self):
        """End the current round and prepare for the next."""
        self.logger.info(f"Round {self.round_number} completed")
        
        # Update round counter
        self.round_number += 1
        self.round_time = 0
        
        # Collect analytics data
        self._collect_analytics()
        
        # Generate learning visualizations periodically
        if self.round_number % 5 == 0:
            self._save_learning_visualizations()
            
        # Check if we've reached the maximum rounds
        if self.round_number >= self.config.game.get('MAX_ROUNDS', 5):
            self.logger.info("Maximum rounds reached, ending game")
            self.running = False
            
    def _collect_analytics(self):
        """Collect analytics data for the current round."""
        # Collect battle data
        battle_data = {}
        
        for agent_name, agent in self.agents.items():
            # Collect combat stats
            combat_stats = self.combat_system.get_combat_stats(agent_name)
            
            # Get team data
            team_id = None
            for tid, team in self.teams.items():
                if agent_name in team['members']:
                    team_id = tid
                    break
                    
            # Collect stats
            battle_data[agent_name] = {
                'team': team_id,
                'score': combat_stats.get('damage_dealt', 0) + combat_stats.get('kills', 0) * 100,
                'survival_time': self.round_time,
                'kills': combat_stats.get('kills', 0),
                'damage': combat_stats.get('damage_dealt', 0),
                'accuracy': combat_stats.get('accuracy', 0),
                'won': self.round_number < self.config.game.get('MAX_ROUNDS', 5)
            }
            
        # Log battle data
        self.battle_analytics.log_battle(battle_data)
        
    def _save_learning_visualizations(self):
        """Generate and save learning visualizations."""
        self.logger.info("Generating learning visualizations")
        
        # Create directory for this round
        vis_dir = f"analytics/learning/round_{self.round_number}"
        os.makedirs(vis_dir, exist_ok=True)
        
        # Generate and save visualizations for all agents
        agent_names = list(self.agents.keys())
        
        # Learning curves
        self.learning_integration.visualize_learning_curve(
            agent_ids=agent_names,
            metric='rewards',
            save_path=f"{vis_dir}/learning_curve_rewards.png"
        )
        
        # Pattern recognition progress
        self.learning_integration.visualize_pattern_progress(
            agent_ids=agent_names,
            save_path=f"{vis_dir}/pattern_recognition.png"
        )
        
        # Strategy adaptation
        self.learning_integration.visualize_strategy_adaptation(
            agent_ids=agent_names,
            save_path=f"{vis_dir}/strategy_adaptation.png"
        )
        
        # Cross-agent comparison
        self.learning_integration.visualize_cross_agent_comparison(
            metric='rewards',
            save_path=f"{vis_dir}/cross_agent_comparison.png"
        )
        
        # For a specific agent (first one)
        if agent_names:
            self.learning_integration.visualize_pattern_clusters(
                agent_id=agent_names[0],
                save_path=f"{vis_dir}/pattern_clusters_{agent_names[0]}.png"
            )
            
        self.logger.info(f"Learning visualizations saved to {vis_dir}")
        
    def _adjust_quality(self):
        """Adjust quality settings based on performance."""
        metrics = self.performance_monitor.get_metrics()
        
        # Get quality manager if available
        quality_manager = self.system_manager.get_system("quality_manager")
        if quality_manager:
            quality_manager.adjust_quality(metrics)
            
    def _shutdown(self):
        """Shutdown all systems and clean up."""
        self.logger.info("Shutting down enhanced game loop")
        
        # Save final analytics
        self._collect_analytics()
        self.battle_analytics.generate_report()
        
        # Save final learning visualizations
        self._save_learning_visualizations()
        
        # Shutdown all systems
        self.system_manager.shutdown_all()
        
        # Quit pygame
        pygame.quit()
        
    def _end_game(self, winner_id: str):
        """Handles the game end logic."""
        self.logger.info(f"Winner: {winner_id}")
        # Perform final analytics collection
        self._collect_analytics() 
        # Potentially update analytics data with winner info
        # ...
        self.running = False # Stop the main loop
        
def main():
    """Main entry point."""
    try:
        game = EnhancedGameLoop()
        game.run()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main() 