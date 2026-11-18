"""
Team Agent Example

This example demonstrates how to use the TeamAgent and TeamAgentManager
to create and control teams of agents that maintain formations and
coordinate actions.
"""

import numpy as np
import math
import time

from systems.agents.team_system import TeamSystem
from systems.team_agent_integration import TeamAgentManager
from systems.agents.team_agent import TeamAgent

def main():
    """Run the team agent example."""
    print("Team Agent Example")
    print("-----------------")
    
    # Create the team system
    team_system = TeamSystem()
    team_system._initialize()  # Initialize the system
    
    # Create the team agent manager
    manager = TeamAgentManager(team_system)
    
    # Create a team with 5 agents
    print("Creating team 'alpha' with 5 agents...")
    team = manager.create_team_with_agents('alpha', 5, 'arrow')
    
    # Print team information
    print(f"Team created: {team['id']}")
    print(f"Formation: {team['formation']}")
    print(f"Leader: {team['leader']}")
    print(f"Roles:")
    for agent_name, role in team['roles'].items():
        agent = manager.get_agent(agent_name)
        print(f"  {agent_name}: {role} ({agent.__class__.__name__})")
    
    # Simulate agent movement
    print("\nSimulating agent movement...")
    
    # Set initial leader position
    leader_name = team['leader']
    leader_pos = (100.0, 100.0)
    manager.update_agent_position(leader_name, leader_pos)
    
    # Update formation targets for all agents
    manager.update_formation_targets('alpha')
    
    # Print formation positions
    print(f"Formation centered at {leader_pos}:")
    for agent_name in team['members']:
        agent = manager.get_agent(agent_name)
        print(f"  {agent_name} target position: {agent.formation_target}")
    
    # Simulate agent decisions
    print("\nSimulating agent decisions...")
    
    # Create a simple state vector
    state = np.zeros(10)
    state[0] = 0.1  # x position
    state[1] = 0.1  # y position
    state[2] = 0.8  # energy
    state[3] = 0.0  # facing angle (0 radians, facing east)
    
    # Initialize agents with state and action dimensions
    for agent_name in team['members']:
        agent = manager.get_agent(agent_name)
        agent.initialize_agent(state_size=10, action_size=5)
    
    # Get actions for each agent
    print("Agent actions:")
    for agent_name in team['members']:
        agent = manager.get_agent(agent_name)
        action = agent.get_action(state)
        
        # Map action to description
        action_desc = {
            0: "idle",
            1: "move forward",
            2: "rotate left",
            3: "rotate right",
            4: "shoot"
        }.get(action, "unknown")
        
        print(f"  {agent_name} ({agent.role}): {action_desc}")
    
    # Simulate leader moving
    print("\nSimulating leader movement...")
    for i in range(5):
        # Update leader position
        leader_pos = (
            leader_pos[0] + 20.0,  # Move right
            leader_pos[1] + 10.0   # Move down slightly
        )
        manager.update_agent_position(leader_name, leader_pos)
        
        # Update formation targets
        manager.update_formation_targets('alpha')
        
        # Print new leader position
        print(f"Step {i+1}: Leader moved to {leader_pos}")
        
        # Get each agent's target
        if i == 4:  # Only print detailed info for the last step
            print("Final formation positions:")
            for agent_name in team['members']:
                agent = manager.get_agent(agent_name)
                print(f"  {agent_name} target: {agent.formation_target}")
    
    # Simulate combat event
    print("\nSimulating combat event...")
    combat_data = {
        'teams': ['alpha'],
        'enemy_positions': [(300, 300), (320, 280), (280, 320)]
    }
    
    # Handle combat event
    manager.handle_combat_event(combat_data)
    
    # Print new formation
    print(f"Formation changed to: {team_system.teams['alpha']['formation']}")
    
    # Suggest team ability
    print("\nChecking for team ability suggestions...")
    suggestion = manager.suggest_team_ability('alpha')
    
    if suggestion:
        ability, initiator, target = suggestion
        print(f"Suggested ability: {ability} by {initiator} at {target}")
        
        # Execute ability
        success = manager.execute_team_ability('alpha', ability, initiator, target)
        print(f"Ability execution {'succeeded' if success else 'failed'}")
    else:
        print("No ability suggested at this time")
    
    # Clean up
    team_system._shutdown()
    manager.cleanup()
    print("\nExample completed")

if __name__ == "__main__":
    main() 