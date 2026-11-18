"""
Example script demonstrating the integration between personality system, team system, and agents.

This script shows how to:
1. Initialize the systems
2. Create teams with personality-based agents
3. Observe how personalities influence team formation and behavior
"""

import pygame
import sys
import random
import numpy as np
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from systems.core.system_manager import SystemManager, SystemEventType
from systems.agents.team_system import TeamSystem
from systems.agents.personality_system import PersonalitySystem, PersonalityTrait, PersonalityProfile
from systems.team_agent_integration import TeamAgentManager

def main():
    # Initialize pygame
    pygame.init()
    width, height = 800, 600
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Personality & Team System Integration Demo")
    
    # Create system manager
    system_manager = SystemManager()
    
    # Create and register systems
    personality_system = PersonalitySystem()
    team_system = TeamSystem()
    
    system_manager.register_system("personality_system", personality_system)
    system_manager.register_system("team_system", team_system)
    
    # Initialize systems
    system_manager.initialize_all()
    
    # Create team manager
    team_manager = TeamAgentManager(team_system)
    
    # Create teams with different compositions
    num_teams = 3
    teams = []
    
    for i in range(num_teams):
        team_id = f"team_{i}"
        agent_count = random.randint(3, 5)
        formation = random.choice(["triangle", "line", "square", "arrow"])
        
        print(f"Creating {team_id} with {agent_count} agents using {formation} formation")
        team = team_manager.create_team_with_agents(team_id, agent_count, formation)
        teams.append(team)
        
        # Print team details
        print(f"  Leader: {team['leader']}")
        print(f"  Roles: {team['roles']}")
        
        # Print personality profiles
        print("  Personalities:")
        for agent_name in team['members']:
            profile = personality_system.get_agent_personality(agent_name)
            if profile:
                dominant_traits = [(trait.name, profile.get_trait(trait)) 
                                for trait in PersonalityTrait 
                                if profile.get_trait(trait) > 0.7]
                
                print(f"    {agent_name}: {dominant_traits}")
        
        # Assign random positions to agents
        for agent_name in team['members']:
            x = random.randint(100, width - 100)
            y = random.randint(100, height - 100)
            team_manager.update_agent_position(agent_name, (x, y))
            
        # Update formation targets
        team_manager.update_formation_targets(team_id)
        
        print("  Team Compatibility:", 
              personality_system.calculate_team_compatibility(team['members']))
        print()
    
    # Main simulation loop
    clock = pygame.time.Clock()
    running = True
    
    # Background
    background = pygame.Surface((width, height))
    background.fill((20, 20, 40))
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
        # Clear screen
        screen.blit(background, (0, 0))
        
        # Update and draw teams
        for team in teams:
            team_id = team['id']
            color = team_system.get_team_color(team_id)
            
            # Draw formation lines
            leader_name = team['leader']
            if leader_name:
                leader_pos = team_manager.agent_positions.get(leader_name)
                if leader_pos:
                    # Draw a circle at leader position
                    pygame.draw.circle(screen, (200, 200, 50), 
                                      (int(leader_pos[0]), int(leader_pos[1])), 15)
                    
                    # Draw lines to formation positions
                    formation_positions = team_system.get_formation_positions(team_id, leader_pos)
                    for pos in formation_positions:
                        # Draw target position
                        pygame.draw.circle(screen, (100, 100, 100, 50), 
                                          (int(pos[0]), int(pos[1])), 10, 1)
                        # Draw line from leader to position
                        pygame.draw.line(screen, (70, 70, 70), 
                                        (int(leader_pos[0]), int(leader_pos[1])),
                                        (int(pos[0]), int(pos[1])), 1)
            
            # Draw agents
            for agent_name in team['members']:
                pos = team_manager.agent_positions.get(agent_name)
                if pos:
                    # Draw circle for agent
                    pygame.draw.circle(screen, color, (int(pos[0]), int(pos[1])), 12)
                    
                    # Draw role indicator
                    role = team['roles'].get(agent_name)
                    role_colors = {
                        'leader': (255, 255, 0),
                        'defender': (0, 255, 0),
                        'attacker': (255, 0, 0),
                        'support': (0, 255, 255),
                        'flanker': (255, 0, 255),
                        'scout': (128, 128, 255)
                    }
                    role_color = role_colors.get(role, (200, 200, 200))
                    pygame.draw.circle(screen, role_color, (int(pos[0]), int(pos[1])), 5)
                    
                    # Get personality and adjust agent position based on personality traits
                    personality = personality_system.get_agent_personality(agent_name)
                    if personality:
                        # Move agents based on their personality
                        risk = personality.get_trait(PersonalityTrait.RISK_TOLERANCE)
                        adapt = personality.get_trait(PersonalityTrait.ADAPTABILITY)
                        loyalty = personality.get_trait(PersonalityTrait.LOYALTY)
                        
                        # Loyal agents move closer to formation position
                        if random.random() < 0.05:  # Occasional movement
                            i = team['members'].index(agent_name)
                            if i < len(formation_positions):
                                target = formation_positions[i]
                                
                                # Calculate distance to target
                                dx = target[0] - pos[0]
                                dy = target[1] - pos[1]
                                dist = (dx**2 + dy**2)**0.5
                                
                                if dist > 5:  # Only move if not too close
                                    # Determine if agent follows formation based on loyalty
                                    move_to_formation = random.random() < loyalty
                                    
                                    # Risky agents might explore more
                                    if random.random() < risk * 0.3:
                                        move_to_formation = False
                                        
                                    # Move based on decision
                                    if move_to_formation:
                                        # Move toward formation position
                                        speed = 3.0 * (0.5 + loyalty * 0.5)
                                        dir_x = dx / dist
                                        dir_y = dy / dist
                                        new_x = pos[0] + dir_x * speed
                                        new_y = pos[1] + dir_y * speed
                                    else:
                                        # Random movement
                                        angle = random.uniform(0, 2 * np.pi)
                                        speed = 2.0 * (0.5 + risk * 0.5)
                                        new_x = pos[0] + np.cos(angle) * speed
                                        new_y = pos[1] + np.sin(angle) * speed
                                    
                                    # Apply boundary limits
                                    new_x = max(50, min(width - 50, new_x))
                                    new_y = max(50, min(height - 50, new_y))
                                    
                                    # Update position
                                    team_manager.update_agent_position(agent_name, (new_x, new_y))
                                    
        # Draw info text
        font = pygame.font.SysFont('arial', 18)
        for i, team in enumerate(teams):
            team_id = team['id']
            formation = team['formation']
            compatibility = personality_system.calculate_team_compatibility(team['members'])
            formation_bonus = team_system.get_formation_bonus(team_id)
            
            text = font.render(f"{team_id} - Formation: {formation}", True, (255, 255, 255))
            screen.blit(text, (20, 20 + i * 60))
            
            text = font.render(f"  Compatibility: {compatibility:.2f}", True, (200, 200, 255))
            screen.blit(text, (20, 40 + i * 60))
            
            text = font.render(f"  Formation Bonus: {formation_bonus:.2f}", True, (200, 255, 200))
            screen.blit(text, (20, 60 + i * 60))
        
        # Update display
        pygame.display.flip()
        
        # Cap framerate
        clock.tick(30)
        
    # Clean up
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main() 