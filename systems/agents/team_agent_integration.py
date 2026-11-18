"""
Integration module that connects the TeamSystem with agent personalities.

This module provides a TeamAgentManager class that handles the creation, management,
and updating of teams with personality-influenced agents.
"""

import random
from typing import Dict, List, Tuple, Any, Optional

from systems.agents.team_system import TeamSystem
from systems.agents.agent import Agent
from systems.agents.team_agent import TeamAgent
from systems.agents.personality_system import PersonalitySystem, PersonalityProfile, PersonalityTrait

class TeamAgentManager:
    """
    Manager class that integrates the team system with personality-influenced agents.
    
    This class is responsible for:
    - Creating teams with agents
    - Managing agent positions
    - Updating formation targets
    - Facilitating communication between agents and teams
    """
    
    def __init__(self, team_system: TeamSystem):
        """Initialize the team agent manager with a team system."""
        self.team_system = team_system
        self.personality_system = PersonalitySystem()
        
        # Store agent instances
        self.agents: Dict[str, Agent] = {}
        
        # Store agent positions for simulation
        self.agent_positions: Dict[str, Tuple[float, float]] = {}
        
        # Mapping of agents to their teams
        self.agent_team_map: Dict[str, str] = {}
        
    def create_team_with_agents(self, team_id: str, agent_count: int, 
                             formation: str = "triangle") -> Dict[str, Any]:
        """
        Create a team with a specified number of agents.
        
        Args:
            team_id: Unique identifier for the team
            agent_count: Number of agents to create
            formation: Formation pattern for the team
            
        Returns:
            Dictionary containing team information
        """
        # Create the team
        self.team_system.create_team(team_id, formation)
        
        # Create agents
        agent_names = []
        for i in range(agent_count):
            agent_name = f"{team_id}_agent_{i}"
            
            # Create agent with team awareness
            agent = TeamAgent(agent_name)
            self.agents[agent_name] = agent
            
            # Generate random position for the agent
            x, y = random.uniform(100, 700), random.uniform(100, 500)
            self.agent_positions[agent_name] = (x, y)
            
            # Generate personality for the agent
            self._generate_personality_for_agent(agent_name)
            
            # Map agent to team
            self.agent_team_map[agent_name] = team_id
            agent_names.append(agent_name)
        
        # Add members to the team
        for agent_name in agent_names:
            self.team_system.add_member(team_id, agent_name)
        
        # Assign roles based on personalities
        self._assign_roles_based_on_personality(team_id, agent_names)
        
        # Return team data
        return {
            "id": team_id,
            "members": agent_names,
            "formation": formation,
            "leader": self.team_system.get_team_leader(team_id),
            "roles": self.team_system.get_team_roles(team_id)
        }
    
    def _generate_personality_for_agent(self, agent_name: str) -> None:
        """
        Generate a random personality for an agent with some biases.
        
        Args:
            agent_name: Name of the agent
        """
        traits = {}
        
        # Generate random traits with some tendencies
        for trait in PersonalityTrait:
            # Generate random value between 0.2 and 0.8
            base_value = random.uniform(0.2, 0.8)
            traits[trait] = base_value
        
        # Create the personality profile
        profile = PersonalityProfile(agent_name)
        
        # Set all traits
        for trait, value in traits.items():
            profile.set_trait(trait, value)
            
        # Register with personality system
        self.personality_system.register_agent_personality(agent_name, profile)
    
    def _assign_roles_based_on_personality(self, team_id: str, agent_names: List[str]) -> None:
        """
        Assign team roles based on agent personalities.
        
        Args:
            team_id: Team identifier
            agent_names: List of agent names in the team
        """
        if not agent_names:
            return
            
        # Get personalities
        personalities = {}
        for agent_name in agent_names:
            profile = self.personality_system.get_agent_personality(agent_name)
            if profile:
                personalities[agent_name] = profile
        
        # Find most suitable leader (high assertiveness and adaptability)
        leader_scores = {}
        for agent_name, profile in personalities.items():
            leadership_score = (
                profile.get_trait(PersonalityTrait.ASSERTIVENESS) * 0.7 +
                profile.get_trait(PersonalityTrait.ADAPTABILITY) * 0.3
            )
            leader_scores[agent_name] = leadership_score
        
        # Select leader as agent with highest leadership score
        if leader_scores:
            leader = max(leader_scores.items(), key=lambda x: x[1])[0]
            self.team_system.set_team_leader(team_id, leader)
            
            # Assign other roles based on personality traits
            remaining_agents = [a for a in agent_names if a != leader]
            
            role_assignments = {
                "attacker": [],  # High aggression, low cautiousness
                "defender": [],  # High loyalty, high cautiousness
                "support": [],   # High empathy, high adaptability
                "flanker": [],   # High risk tolerance, high independence
                "scout": []      # High adaptability, high risk tolerance, high independence
            }
            
            # Score each agent for each role
            for agent_name in remaining_agents:
                profile = personalities.get(agent_name)
                if not profile:
                    continue
                    
                # Calculate role scores
                attacker_score = (
                    profile.get_trait(PersonalityTrait.AGGRESSION) * 0.7 + 
                    (1.0 - profile.get_trait(PersonalityTrait.CAUTIOUSNESS)) * 0.3
                )
                
                defender_score = (
                    profile.get_trait(PersonalityTrait.LOYALTY) * 0.5 +
                    profile.get_trait(PersonalityTrait.CAUTIOUSNESS) * 0.5
                )
                
                support_score = (
                    profile.get_trait(PersonalityTrait.EMPATHY) * 0.6 +
                    profile.get_trait(PersonalityTrait.ADAPTABILITY) * 0.4
                )
                
                flanker_score = (
                    profile.get_trait(PersonalityTrait.RISK_TOLERANCE) * 0.5 +
                    profile.get_trait(PersonalityTrait.INDEPENDENCE) * 0.5
                )
                
                scout_score = (
                    profile.get_trait(PersonalityTrait.ADAPTABILITY) * 0.4 +
                    profile.get_trait(PersonalityTrait.RISK_TOLERANCE) * 0.3 +
                    profile.get_trait(PersonalityTrait.INDEPENDENCE) * 0.3
                )
                
                # Store scores
                role_assignments["attacker"].append((agent_name, attacker_score))
                role_assignments["defender"].append((agent_name, defender_score))
                role_assignments["support"].append((agent_name, support_score))
                role_assignments["flanker"].append((agent_name, flanker_score))
                role_assignments["scout"].append((agent_name, scout_score))
            
            # Sort role candidates by score
            for role in role_assignments:
                role_assignments[role].sort(key=lambda x: x[1], reverse=True)
            
            # Assign roles in order of priority
            assigned_agents = set([leader])
            roles_priority = ["defender", "attacker", "support", "flanker", "scout"]
            
            # Calculate how many of each role we need
            total_to_assign = len(remaining_agents)
            defender_count = max(1, total_to_assign // 5)
            attacker_count = max(1, total_to_assign // 4)
            remaining_count = total_to_assign - defender_count - attacker_count
            
            # Distribute remaining roles
            support_count = remaining_count // 3
            flanker_count = remaining_count // 3
            scout_count = remaining_count - support_count - flanker_count
            
            role_counts = {
                "defender": defender_count,
                "attacker": attacker_count,
                "support": support_count,
                "flanker": flanker_count,
                "scout": scout_count
            }
            
            # Assign roles
            for role in roles_priority:
                count = role_counts[role]
                assigned = 0
                
                for agent_name, score in role_assignments[role]:
                    if agent_name not in assigned_agents and assigned < count:
                        self.team_system.assign_role(team_id, agent_name, role)
                        assigned_agents.add(agent_name)
                        assigned += 1
            
            # Assign any unassigned agents to "support"
            for agent_name in agent_names:
                if agent_name not in assigned_agents:
                    self.team_system.assign_role(team_id, agent_name, "support")
    
    def update_agent_position(self, agent_name: str, position: Tuple[float, float]) -> None:
        """
        Update an agent's position.
        
        Args:
            agent_name: Name of the agent
            position: (x, y) position
        """
        self.agent_positions[agent_name] = position
        
        # Update team system with the new position
        team_id = self.agent_team_map.get(agent_name)
        if team_id:
            self.team_system.update_member_position(team_id, agent_name, position)
    
    def update_formation_targets(self, team_id: str) -> None:
        """
        Update formation targets for a team based on the leader's position.
        
        Args:
            team_id: Team identifier
        """
        leader = self.team_system.get_team_leader(team_id)
        if not leader:
            return
            
        leader_pos = self.agent_positions.get(leader)
        if not leader_pos:
            return
            
        # Get formation positions from team system
        formation_positions = self.team_system.get_formation_positions(team_id, leader_pos)
        
        # Assign formation positions to team members
        members = self.team_system.get_team_members(team_id)
        if not members:
            return
            
        # Leader is already positioned, so we don't need a formation position for them
        members_without_leader = [m for m in members if m != leader]
        
        # Ensure we have enough positions
        if len(formation_positions) < len(members_without_leader):
            # Generate more positions if needed
            additional_needed = len(members_without_leader) - len(formation_positions)
            for _ in range(additional_needed):
                # Add a random offset from the leader
                offset_x = random.uniform(-50, 50)
                offset_y = random.uniform(-50, 50)
                formation_positions.append((leader_pos[0] + offset_x, leader_pos[1] + offset_y))
                
        # Assign positions to members
        for i, member in enumerate(members_without_leader):
            if i < len(formation_positions):
                self.team_system.set_formation_position(team_id, member, formation_positions[i])
    
    def get_agent(self, agent_name: str) -> Optional[Agent]:
        """Get an agent by name."""
        return self.agents.get(agent_name)
        
    def get_team_id_for_agent(self, agent_name: str) -> Optional[str]:
        """Get the team ID for an agent."""
        return self.agent_team_map.get(agent_name)
        
    def get_formation_compliance(self, team_id: str) -> float:
        """
        Calculate how well a team is maintaining its formation.
        
        Returns a value between 0 and 1, where 1 means perfect formation.
        """
        members = self.team_system.get_team_members(team_id)
        if not members:
            return 0.0
            
        # Get leader and formation positions
        leader = self.team_system.get_team_leader(team_id)
        if not leader or leader not in self.agent_positions:
            return 0.0
            
        leader_pos = self.agent_positions[leader]
        formation_positions = self.team_system.get_formation_positions(team_id, leader_pos)
        
        # Calculate average distance to assigned formation positions
        total_distance = 0.0
        valid_members = 0
        
        for i, member in enumerate(members):
            if member == leader:
                continue
                
            # Get member position
            member_pos = self.agent_positions.get(member)
            if not member_pos:
                continue
                
            # Get formation position
            if i-1 < len(formation_positions):  # -1 because leader is not included
                formation_pos = formation_positions[i-1]
                
                # Calculate distance
                dx = member_pos[0] - formation_pos[0]
                dy = member_pos[1] - formation_pos[1]
                distance = (dx**2 + dy**2)**0.5
                
                # Add to total
                total_distance += distance
                valid_members += 1
        
        if valid_members == 0:
            return 0.0
            
        # Calculate average distance
        avg_distance = total_distance / valid_members
        
        # Convert to a compliance score (inverse of distance)
        # Normalize to 0-1 range, where 1 is perfect formation
        max_distance = 200  # Maximum expected distance
        compliance = max(0.0, 1.0 - (avg_distance / max_distance))
        
        return compliance 