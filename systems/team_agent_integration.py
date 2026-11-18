"""
Integration module that connects the TeamSystem with agent personalities.

This module provides a TeamAgentManager class that handles the creation, management,
and updating of teams with personality-influenced agents.
"""

import numpy as np
import random
import math
import time
from typing import Dict, List, Tuple, Any, Optional

from systems.agents.base_agent import BaseAgent
from systems.agents.team_system import TeamSystem
from systems.agents.team_agent import TeamAgent
from systems.agents.personality_system import PersonalitySystem, PersonalityProfile, PersonalityTrait
from systems.agents.agent_factory import create_agent # Assuming agent factory is used
from systems.utils.logging import logger

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
        self.agents: Dict[str, BaseAgent] = {}
        
        # Store agent positions for simulation
        self.agent_positions: Dict[str, Tuple[float, float]] = {}
        
        # Mapping of agents to their teams
        self.agent_team_map: Dict[str, str] = {}
        
        # Team compatibility scores
        self.team_compatibility: Dict[str, float] = {}
        
        # Agent compatibility pairs
        self.agent_compatibility: Dict[Tuple[str, str], float] = {}
        
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
        
        # Create the team with all members at once
        self.team_system.create_team(team_id, agent_names)
        
        # Set formation if different from default
        if formation != "triangle":
            self.team_system.change_formation(team_id, formation)
        
        # Calculate team compatibility score
        self.team_compatibility[team_id] = self.calculate_team_compatibility(agent_names)
        
        # Return team data
        return {
            "id": team_id,
            "members": agent_names,
            "formation": formation,
            "leader": self.team_system.teams[team_id]['leader'],
            "roles": self.team_system.teams[team_id]['roles'],
            "compatibility": self.team_compatibility[team_id]
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
        self.personality_system.register_agent(agent_name, profile)
    
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
        
        # Find most suitable leader (high leadership and adaptability)
        leader_scores = {}
        for agent_name, profile in personalities.items():
            leadership_score = (
                profile.get_trait(PersonalityTrait.LEADERSHIP) * 0.7 +
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
                "attacker": [],  # High aggression, low conscientiousness
                "defender": [],  # High loyalty, high conscientiousness
                "support": [],   # High agreeableness, high adaptability
                "flanker": [],   # High risk tolerance, high openness
                "scout": []      # High adaptability, high risk tolerance, high openness
            }
            
            # Score each agent for each role
            for agent_name in remaining_agents:
                profile = personalities.get(agent_name)
                if not profile:
                    continue
                    
                # Calculate role scores
                attacker_score = (
                    profile.get_trait(PersonalityTrait.AGGRESSION) * 0.7 + 
                    (1.0 - profile.get_trait(PersonalityTrait.CONSCIENTIOUSNESS)) * 0.3
                )
                
                defender_score = (
                    profile.get_trait(PersonalityTrait.LOYALTY) * 0.5 +
                    profile.get_trait(PersonalityTrait.CONSCIENTIOUSNESS) * 0.5
                )
                
                support_score = (
                    profile.get_trait(PersonalityTrait.AGREEABLENESS) * 0.6 +
                    profile.get_trait(PersonalityTrait.ADAPTABILITY) * 0.4
                )
                
                flanker_score = (
                    profile.get_trait(PersonalityTrait.RISK_TOLERANCE) * 0.5 +
                    profile.get_trait(PersonalityTrait.OPENNESS) * 0.5
                )
                
                scout_score = (
                    profile.get_trait(PersonalityTrait.ADAPTABILITY) * 0.4 +
                    profile.get_trait(PersonalityTrait.RISK_TOLERANCE) * 0.3 +
                    profile.get_trait(PersonalityTrait.OPENNESS) * 0.3
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
    
    def calculate_team_compatibility(self, agent_names: List[str]) -> float:
        """
        Calculate team compatibility score based on personality traits.
        
        This analyzes how well agent personalities work together as a team,
        considering trait complementarity and potential conflicts.
        
        Args:
            agent_names: List of agent names
            
        Returns:
            Team compatibility score (0.0 to 1.0, where 1.0 is perfect compatibility)
        """
        if len(agent_names) <= 1:
            return 1.0  # Perfect compatibility for single-agent teams
            
        # Calculate pairwise compatibility between all agents
        compatibility_sum = 0.0
        pair_count = 0
        
        for i in range(len(agent_names)):
            for j in range(i+1, len(agent_names)):
                agent1 = agent_names[i]
                agent2 = agent_names[j]
                
                pair_key = tuple(sorted([agent1, agent2]))
                
                # Check if we've already calculated this pair's compatibility
                if pair_key in self.agent_compatibility:
                    compatibility = self.agent_compatibility[pair_key]
                else:
                    # Calculate compatibility between these two agents
                    compatibility = self._calculate_agent_compatibility(agent1, agent2)
                    # Store for future reference
                    self.agent_compatibility[pair_key] = compatibility
                
                compatibility_sum += compatibility
                pair_count += 1
        
        # Calculate average compatibility
        if pair_count == 0:
            return 0.0
        
        return compatibility_sum / pair_count
    
    def _calculate_agent_compatibility(self, agent1: str, agent2: str) -> float:
        """
        Calculate compatibility between two agents based on their personalities.
        
        This considers both complementary traits (traits where differences can be beneficial)
        and synergistic traits (similarities that enhance cooperation).
        
        Args:
            agent1: First agent name
            agent2: Second agent name
            
        Returns:
            Compatibility score between 0.0 and 1.0
        """
        profile1 = self.personality_system.get_agent_personality(agent1)
        profile2 = self.personality_system.get_agent_personality(agent2)
        
        if not profile1 or not profile2:
            return 0.5  # Default neutral compatibility
        
        # Complementary trait pairs (traits where differences can be beneficial)
        complementary_pairs = [
            # Leadership and Support traits
            (PersonalityTrait.LEADERSHIP, PersonalityTrait.AGREEABLENESS),
            # Risk and Caution
            (PersonalityTrait.RISK_TOLERANCE, PersonalityTrait.CONSCIENTIOUSNESS),
            # Independence and Teamwork
            (PersonalityTrait.OPENNESS, PersonalityTrait.LOYALTY),
        ]
        
        # Synergistic trait pairs (traits where similarity is beneficial)
        synergistic_traits = [
            PersonalityTrait.ADAPTABILITY,  # Always good to have similar adaptability
            PersonalityTrait.OPENNESS,      # Similar openness improves communication
        ]
        
        # Potentially conflicting trait pairs (traits where similarity can cause issues)
        conflict_traits = [
            PersonalityTrait.AGGRESSION,    # Two highly aggressive agents may compete
        ]
        
        # Calculate complementary trait scores
        complementary_score = 0.0
        for trait1, trait2 in complementary_pairs:
            # For complementary traits, we want a balance (one high, one low)
            value1a = profile1.get_trait(trait1)
            value2a = profile2.get_trait(trait1)
            value1b = profile1.get_trait(trait2)
            value2b = profile2.get_trait(trait2)
            
            # Calculate how well they complement each other
            # Ideal is if one is high in trait1 and the other is high in trait2
            complementarity = ((value1a > 0.5 and value2b > 0.5) or 
                              (value2a > 0.5 and value1b > 0.5))
            
            complementary_score += 1.0 if complementarity else 0.0
        
        # Normalize complementary score
        complementary_score /= len(complementary_pairs)
        
        # Calculate synergistic trait score
        synergistic_score = 0.0
        for trait in synergistic_traits:
            value1 = profile1.get_trait(trait)
            value2 = profile2.get_trait(trait)
            
            # For synergistic traits, similarity is good
            # Convert difference to similarity (0 difference = 1.0 similarity)
            similarity = 1.0 - abs(value1 - value2)
            synergistic_score += similarity
        
        # Normalize synergistic score
        synergistic_score /= len(synergistic_traits)
        
        # Calculate conflict potential
        conflict_score = 0.0
        for trait in conflict_traits:
            value1 = profile1.get_trait(trait)
            value2 = profile2.get_trait(trait)
            
            # If both have high values in conflict traits, it's a problem
            # Otherwise, it's fine
            if value1 > 0.7 and value2 > 0.7:
                conflict_score += 1.0
            elif value1 < 0.3 and value2 < 0.3:
                # Both very low can also cause issues (e.g., both passive)
                conflict_score += 0.5
            else:
                # One high, one low or both moderate is good
                conflict_score += 0.0
        
        # Normalize conflict score and invert (higher conflict = lower compatibility)
        conflict_score = 1.0 - (conflict_score / len(conflict_traits))
        
        # Combine scores (weighted average)
        final_score = (
            complementary_score * 0.5 +  # 50% weight to complementary traits
            synergistic_score * 0.3 +    # 30% weight to synergistic traits
            conflict_score * 0.2         # 20% weight to conflict potential
        )
        
        return final_score
    
    def form_optimal_teams(self, agent_names: List[str], team_count: int) -> List[List[str]]:
        """
        Form optimal teams based on personality compatibility.
        
        This method attempts to create teams with the highest overall 
        compatibility scores by considering personality traits.
        
        Args:
            agent_names: List of all available agent names
            team_count: Number of teams to form
            
        Returns:
            List of teams, where each team is a list of agent names
        """
        if team_count <= 0 or not agent_names:
            return []
            
        # Calculate all pairwise compatibilities
        for i in range(len(agent_names)):
            for j in range(i+1, len(agent_names)):
                agent1 = agent_names[i]
                agent2 = agent_names[j]
                pair_key = tuple(sorted([agent1, agent2]))
                
                if pair_key not in self.agent_compatibility:
                    compatibility = self._calculate_agent_compatibility(agent1, agent2)
                    self.agent_compatibility[pair_key] = compatibility
        
        # Determine team size (try to make teams equal size)
        base_team_size = len(agent_names) // team_count
        extra_agents = len(agent_names) % team_count
        
        # Initialize teams
        teams = [[] for _ in range(team_count)]
        remaining_agents = agent_names.copy()
        
        # Start by choosing team leaders
        potential_leaders = []
        for agent in agent_names:
            profile = self.personality_system.get_agent_personality(agent)
            if profile:
                leadership_score = (
                    profile.get_trait(PersonalityTrait.LEADERSHIP) * 0.7 +
                    profile.get_trait(PersonalityTrait.ADAPTABILITY) * 0.3
                )
                potential_leaders.append((agent, leadership_score))
        
        # Sort by leadership score
        potential_leaders.sort(key=lambda x: x[1], reverse=True)
        
        # Assign leaders to teams
        for i in range(min(team_count, len(potential_leaders))):
            leader = potential_leaders[i][0]
            teams[i].append(leader)
            remaining_agents.remove(leader)
        
        # Now build teams one by one, adding the agent with highest compatibility
        for team_idx in range(team_count):
            current_team = teams[team_idx]
            
            # Skip if no leader was assigned (shouldn't happen if we have enough agents)
            if not current_team:
                continue
                
            # Determine target size for this team
            target_size = base_team_size + (1 if team_idx < extra_agents else 0)
            
            # Add members until team reaches target size
            while len(current_team) < target_size and remaining_agents:
                best_agent = None
                best_compatibility = -1.0
                
                # Find agent with highest average compatibility with current team
                for agent in remaining_agents:
                    total_compatibility = 0.0
                    
                    for team_member in current_team:
                        pair_key = tuple(sorted([agent, team_member]))
                        compatibility = self.agent_compatibility.get(pair_key, 0.5)
                        total_compatibility += compatibility
                    
                    avg_compatibility = total_compatibility / len(current_team)
                    
                    if avg_compatibility > best_compatibility:
                        best_compatibility = avg_compatibility
                        best_agent = agent
                
                if best_agent:
                    current_team.append(best_agent)
                    remaining_agents.remove(best_agent)
                else:
                    break  # No more agents to add
        
        # Distribute any remaining agents
        while remaining_agents:
            agent = remaining_agents.pop(0)
            # Find team with fewest members
            smallest_team_idx = min(range(team_count), key=lambda i: len(teams[i]))
            teams[smallest_team_idx].append(agent)
        
        return teams
    
    def recommend_team_adjustments(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Recommend team adjustments to improve compatibility.
        
        This suggests agent swaps or role reassignments that would
        improve overall team compatibility.
        
        Args:
            team_id: The team to analyze
            
        Returns:
            List of adjustment recommendations
        """
        if team_id not in self.teams:
            return []
            
        team_members = self.team_system.get_team_members(team_id)
        if not team_members or len(team_members) <= 1:
            return []
            
        recommendations = []
        team_compatibility = self.calculate_team_compatibility(team_members)
        
        # Check if role reassignments would improve compatibility
        current_roles = self.team_system.get_team_roles(team_id)
        
        # Try swapping roles between pairs of agents
        for i in range(len(team_members)):
            for j in range(i+1, len(team_members)):
                agent1 = team_members[i]
                agent2 = team_members[j]
                
                # Skip if one of them is the leader
                if agent1 == self.team_system.get_team_leader(team_id) or \
                   agent2 == self.team_system.get_team_leader(team_id):
                    continue
                
                # Get current roles
                role1 = current_roles.get(agent1, "support")
                role2 = current_roles.get(agent2, "support")
                
                # Skip if they have the same role
                if role1 == role2:
                    continue
                
                # Create a copy of the roles with these two swapped
                test_roles = current_roles.copy()
                test_roles[agent1] = role2
                test_roles[agent2] = role1
                
                # Calculate how this would affect team performance
                profile1 = self.personality_system.get_agent_personality(agent1)
                profile2 = self.personality_system.get_agent_personality(agent2)
                
                if not profile1 or not profile2:
                    continue
                
                # Calculate suitability for swapped roles
                suitability_improvement = self._calculate_role_suitability_change(
                    agent1, role1, role2, profile1) + \
                    self._calculate_role_suitability_change(
                        agent2, role2, role1, profile2)
                
                # Add recommendation if significant improvement
                if suitability_improvement > 0.2:
                    recommendations.append({
                        "type": "role_swap",
                        "agents": [agent1, agent2],
                        "from_roles": [role1, role2],
                        "to_roles": [role2, role1],
                        "improvement": suitability_improvement
                    })
        
        # Sort recommendations by improvement
        recommendations.sort(key=lambda x: x["improvement"], reverse=True)
        
        return recommendations
    
    def _calculate_role_suitability_change(self, agent_name: str, 
                                        current_role: str, 
                                        new_role: str,
                                        profile: PersonalityProfile) -> float:
        """
        Calculate how much an agent's role suitability would change with a new role.
        
        Args:
            agent_name: Agent name
            current_role: Current role
            new_role: Potential new role
            profile: Agent's personality profile
            
        Returns:
            Change in suitability (-1.0 to 1.0, positive is improvement)
        """
        # Calculate suitability scores for current and new roles
        current_suitability = 0.0
        new_suitability = 0.0
        
        # Role suitability formulas (similar to those in _assign_roles_based_on_personality)
        if current_role == "attacker":
            current_suitability = (
                profile.get_trait(PersonalityTrait.AGGRESSION) * 0.7 + 
                (1.0 - profile.get_trait(PersonalityTrait.CONSCIENTIOUSNESS)) * 0.3
            )
        elif current_role == "defender":
            current_suitability = (
                profile.get_trait(PersonalityTrait.LOYALTY) * 0.5 +
                profile.get_trait(PersonalityTrait.CONSCIENTIOUSNESS) * 0.5
            )
        elif current_role == "support":
            current_suitability = (
                profile.get_trait(PersonalityTrait.AGREEABLENESS) * 0.6 +
                profile.get_trait(PersonalityTrait.ADAPTABILITY) * 0.4
            )
        elif current_role == "flanker":
            current_suitability = (
                profile.get_trait(PersonalityTrait.RISK_TOLERANCE) * 0.5 +
                profile.get_trait(PersonalityTrait.OPENNESS) * 0.5
            )
        elif current_role == "scout":
            current_suitability = (
                profile.get_trait(PersonalityTrait.ADAPTABILITY) * 0.4 +
                profile.get_trait(PersonalityTrait.RISK_TOLERANCE) * 0.3 +
                profile.get_trait(PersonalityTrait.OPENNESS) * 0.3
            )
        
        # Calculate suitability for new role
        if new_role == "attacker":
            new_suitability = (
                profile.get_trait(PersonalityTrait.AGGRESSION) * 0.7 + 
                (1.0 - profile.get_trait(PersonalityTrait.CONSCIENTIOUSNESS)) * 0.3
            )
        elif new_role == "defender":
            new_suitability = (
                profile.get_trait(PersonalityTrait.LOYALTY) * 0.5 +
                profile.get_trait(PersonalityTrait.CONSCIENTIOUSNESS) * 0.5
            )
        elif new_role == "support":
            new_suitability = (
                profile.get_trait(PersonalityTrait.AGREEABLENESS) * 0.6 +
                profile.get_trait(PersonalityTrait.ADAPTABILITY) * 0.4
            )
        elif new_role == "flanker":
            new_suitability = (
                profile.get_trait(PersonalityTrait.RISK_TOLERANCE) * 0.5 +
                profile.get_trait(PersonalityTrait.OPENNESS) * 0.5
            )
        elif new_role == "scout":
            new_suitability = (
                profile.get_trait(PersonalityTrait.ADAPTABILITY) * 0.4 +
                profile.get_trait(PersonalityTrait.RISK_TOLERANCE) * 0.3 +
                profile.get_trait(PersonalityTrait.OPENNESS) * 0.3
            )
        
        return new_suitability - current_suitability
    
    def update_agent_position(self, agent_name: str, position: Tuple[float, float]) -> None:
        """
        Update an agent's position.
        
        Args:
            agent_name: Name of the agent
            position: (x, y) position
        """
        self.agent_positions[agent_name] = position
        
        # No need to update the TeamSystem directly, as it doesn't track individual positions
        # Instead, we'll update any formation targets after position changes
        team_id = self.agent_team_map.get(agent_name)
        if team_id:
            # If this agent is the team leader, update formation targets for all team members
            if self.team_system.teams[team_id]['leader'] == agent_name:
                self.update_formation_targets(team_id)
    
    def update_formation_targets(self, team_id: str) -> None:
        """
        Update formation targets for a team based on the leader's position.
        
        Args:
            team_id: Team identifier
        """
        if team_id not in self.team_system.teams:
            return
            
        team = self.team_system.teams[team_id]
        leader = team['leader']
        if not leader:
            return
            
        leader_pos = self.agent_positions.get(leader)
        if not leader_pos:
            return
            
        # Get formation positions from team system
        formation_positions = self.team_system.get_formation_positions(team_id, leader_pos)
        
        # Assign formation positions to team members
        members = team['members']
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
                
        # Assign positions to members by setting the formation_target attribute
        for i, member in enumerate(members_without_leader):
            if i < len(formation_positions) and member in self.agents:
                agent = self.agents[member]
                agent.formation_target = formation_positions[i]
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
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
        if team_id not in self.team_system.teams:
            return 0.0
            
        team = self.team_system.teams[team_id]
        members = team['members']
        if not members:
            return 0.0
            
        # Get leader and formation positions
        leader = team['leader']
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
    
    def handle_combat_event(self, combat_data: Dict[str, Any]) -> None:
        """
        Handle a combat event by adjusting team formations based on the situation.
        
        Args:
            combat_data: Dictionary with combat event data
        """
        # Extract relevant data
        teams = combat_data.get('teams', [])
        enemy_positions = combat_data.get('enemy_positions', [])
        
        if not teams or not enemy_positions:
            return
            
        # Process each team in the combat event
        for team_id in teams:
            if team_id not in self.team_system.teams:
                continue
                
            # Decide on appropriate formation based on the situation
            if len(enemy_positions) > 3:
                # Many enemies - use defensive formation
                new_formation = "shield"
            elif len(enemy_positions) == 1:
                # Single enemy - use aggressive formation
                new_formation = "arrow"
            else:
                # Default - balanced formation
                new_formation = "circle"
                
            # Change the formation
            self.team_system.change_formation(team_id, new_formation)
            
            # Get leader position
            team = self.team_system.teams[team_id]
            leader_name = team['leader']
            if leader_name and leader_name in self.agent_positions:
                # Update formation targets based on new formation
                self.update_formation_targets(team_id)
    
    def suggest_team_ability(self, team_id: str) -> Optional[Tuple[str, str, Tuple[float, float]]]:
        """
        Suggest a team ability based on the current situation.
        
        Args:
            team_id: Team identifier
            
        Returns:
            Tuple of (ability_name, initiator_name, target_position) or None
        """
        if team_id not in self.team_system.teams:
            return None
            
        team = self.team_system.teams[team_id]
        members = team['members']
        
        if not members:
            return None
            
        # Simple logic: suggest a random ability with the leader as initiator
        leader_name = team['leader']
        if not leader_name or leader_name not in self.agent_positions:
            return None
            
        # Get leader position
        leader_pos = self.agent_positions[leader_name]
        
        # Simple target position: a bit in front of the leader
        target_pos = (leader_pos[0] + 100.0, leader_pos[1])
        
        # Choose a random ability from the available ones
        ability_names = list(self.team_system.team_abilities.keys())
        if not ability_names:
            return None
            
        ability_name = ability_names[0]  # Just use the first one for simplicity
        
        return (ability_name, leader_name, target_pos)
    
    def execute_team_ability(self, team_id: str, ability_name: str, 
                           initiator_name: str, target_pos: Tuple[float, float]) -> bool:
        """
        Execute a team ability.
        
        Args:
            team_id: Team identifier
            ability_name: Name of the ability to use
            initiator_name: Name of the agent initiating the ability
            target_pos: Target position for the ability
            
        Returns:
            True if the ability was executed successfully
        """
        if team_id not in self.team_system.teams:
            return False
            
        # Validate the initiator is in the team
        team = self.team_system.teams[team_id]
        if initiator_name not in team['members']:
            return False
            
        # Try to use the ability
        return self.team_system.use_team_ability(team_id, ability_name, initiator_name, target_pos)
    
    def cleanup(self) -> None:
        """Clean up resources and references."""
        self.agents.clear()
        self.agent_positions.clear()
        self.agent_team_map.clear()
        self.team_compatibility.clear()
        self.agent_compatibility.clear() 