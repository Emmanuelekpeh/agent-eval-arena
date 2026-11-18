"""
Relationship System for AI Battle Arena.

This module provides mechanisms for tracking and managing relationships between agents,
influencing team dynamics, cooperation levels, and strategic decision-making.
"""

from typing import Dict, List, Tuple, Optional, Any, Set
from collections import defaultdict
import numpy as np
import math
import time

class RelationshipType:
    """Defines the types of relationships between agents."""
    TEAMMATE = "teammate"
    RIVAL = "rival"
    ALLY = "ally"
    ENEMY = "enemy"
    NEUTRAL = "neutral"

class RelationshipFactor:
    """Factors that influence relationship changes."""
    SHARED_VICTORY = "shared_victory"
    ASSISTANCE = "assistance"
    RESOURCE_SHARING = "resource_sharing"
    BETRAYAL = "betrayal"
    ABANDONMENT = "abandonment"
    COOPERATION = "cooperation"
    COMPETITION = "competition"

class RelationshipMetric:
    """Metrics for measuring different aspects of relationships."""
    TRUST = "trust"
    AFFINITY = "affinity"
    SYNERGY = "synergy"
    RIVALRY = "rivalry"
    COOPERATION = "cooperation"

class AgentRelationship:
    """
    Represents the relationship between two agents.
    
    Attributes:
        agent1_id: First agent's identifier
        agent2_id: Second agent's identifier
        trust: Trust level between agents (0-100)
        affinity: How well agents work together (0-100)
        synergy: Combat effectiveness bonus when working together (0-100)
        history: List of significant interactions
    """
    
    def __init__(self, 
                 agent1_id: str, 
                 agent2_id: str, 
                 initial_trust: float = 50.0,
                 initial_affinity: float = 50.0):
        """
        Initialize a new relationship between two agents.
        
        Args:
            agent1_id: ID of the first agent
            agent2_id: ID of the second agent
            initial_trust: Starting trust level (0-100)
            initial_affinity: Starting affinity level (0-100)
        """
        self.agent1_id = agent1_id
        self.agent2_id = agent2_id
        self.trust = initial_trust
        self.affinity = initial_affinity
        self.synergy = (initial_trust + initial_affinity) / 4  # Start at 25% of combined values
        self.interaction_count = 0
        self.history = []
        self.last_update = time.time()
        self.relationship_type = RelationshipType.NEUTRAL
        
        # Specific metrics
        self.metrics = {
            RelationshipMetric.TRUST: initial_trust,
            RelationshipMetric.AFFINITY: initial_affinity,
            RelationshipMetric.SYNERGY: self.synergy,
            RelationshipMetric.RIVALRY: 0.0,
            RelationshipMetric.COOPERATION: 50.0
        }
        
    def update_relationship(self, 
                            factor: str, 
                            magnitude: float,
                            context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Update relationship based on an interaction.
        
        Args:
            factor: The type of interaction (use RelationshipFactor constants)
            magnitude: The strength of the interaction (positive or negative)
            context: Additional contextual information about the interaction
            
        Returns:
            Dictionary of metrics that were changed and their delta values
        """
        changes = {}
        self.interaction_count += 1
        
        # Default impact values for different factors on different metrics
        factor_impacts = {
            RelationshipFactor.SHARED_VICTORY: {
                RelationshipMetric.TRUST: 0.8,
                RelationshipMetric.AFFINITY: 1.0,
                RelationshipMetric.SYNERGY: 1.2,
                RelationshipMetric.COOPERATION: 1.0,
                RelationshipMetric.RIVALRY: -0.5
            },
            RelationshipFactor.ASSISTANCE: {
                RelationshipMetric.TRUST: 1.2,
                RelationshipMetric.AFFINITY: 0.8,
                RelationshipMetric.COOPERATION: 1.5
            },
            RelationshipFactor.RESOURCE_SHARING: {
                RelationshipMetric.TRUST: 1.0,
                RelationshipMetric.AFFINITY: 0.6,
                RelationshipMetric.COOPERATION: 1.2
            },
            RelationshipFactor.BETRAYAL: {
                RelationshipMetric.TRUST: -2.0,
                RelationshipMetric.AFFINITY: -1.5,
                RelationshipMetric.COOPERATION: -2.0,
                RelationshipMetric.RIVALRY: 1.5
            },
            RelationshipFactor.ABANDONMENT: {
                RelationshipMetric.TRUST: -1.5,
                RelationshipMetric.AFFINITY: -1.0,
                RelationshipMetric.COOPERATION: -1.5
            },
            RelationshipFactor.COOPERATION: {
                RelationshipMetric.TRUST: 0.5,
                RelationshipMetric.AFFINITY: 0.7,
                RelationshipMetric.SYNERGY: 0.9,
                RelationshipMetric.COOPERATION: 1.0
            },
            RelationshipFactor.COMPETITION: {
                RelationshipMetric.RIVALRY: 1.0,
                RelationshipMetric.COOPERATION: -0.3
            }
        }
        
        # Get impact modifiers for this factor
        impact_modifiers = factor_impacts.get(factor, {})
        
        # Update each metric based on the factor impacts
        for metric, impact in impact_modifiers.items():
            # Calculate change based on magnitude and impact
            delta = magnitude * impact
            
            # Apply change to metric
            old_value = self.metrics[metric]
            self.metrics[metric] = max(0.0, min(100.0, old_value + delta))
            
            # Record the change
            changes[metric] = self.metrics[metric] - old_value
        
        # Update main attributes from metrics for backwards compatibility
        self.trust = self.metrics[RelationshipMetric.TRUST]
        self.affinity = self.metrics[RelationshipMetric.AFFINITY]
        self.synergy = self.metrics[RelationshipMetric.SYNERGY]
        
        # Determine relationship type based on current metrics
        self._update_relationship_type()
        
        # Add to history
        self.history.append({
            'timestamp': time.time(),
            'factor': factor,
            'magnitude': magnitude,
            'context': context,
            'changes': changes
        })
        
        self.last_update = time.time()
        return changes
    
    def _update_relationship_type(self) -> None:
        """Update the relationship type based on current metrics."""
        trust = self.metrics[RelationshipMetric.TRUST]
        affinity = self.metrics[RelationshipMetric.AFFINITY]
        rivalry = self.metrics[RelationshipMetric.RIVALRY]
        
        if trust > 75 and affinity > 75:
            self.relationship_type = RelationshipType.ALLY
        elif trust > 60 and affinity > 50:
            self.relationship_type = RelationshipType.TEAMMATE
        elif rivalry > 75:
            self.relationship_type = RelationshipType.RIVAL
        elif trust < 25 and affinity < 25:
            self.relationship_type = RelationshipType.ENEMY
        else:
            self.relationship_type = RelationshipType.NEUTRAL
    
    def get_compatibility_score(self) -> float:
        """
        Calculate overall compatibility score between agents.
        
        Returns:
            A score from 0-100 indicating how well the agents work together
        """
        weights = {
            RelationshipMetric.TRUST: 0.3,
            RelationshipMetric.AFFINITY: 0.3,
            RelationshipMetric.SYNERGY: 0.2,
            RelationshipMetric.COOPERATION: 0.2
        }
        
        score = sum(self.metrics[metric] * weight 
                   for metric, weight in weights.items())
                   
        # Rivalry reduces compatibility
        score -= self.metrics[RelationshipMetric.RIVALRY] * 0.2
        
        return max(0.0, min(100.0, score))
    
    def get_combat_synergy_bonus(self) -> float:
        """
        Calculate combat effectiveness bonus when agents fight together.
        
        Returns:
            A multiplier for combat effectiveness (1.0 = no bonus)
        """
        synergy = self.metrics[RelationshipMetric.SYNERGY]
        cooperation = self.metrics[RelationshipMetric.COOPERATION]
        
        # Max bonus is 30% increase in combat effectiveness
        bonus = 1.0 + ((synergy + cooperation) / 2) * 0.003
        return bonus
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert relationship to dictionary for serialization."""
        return {
            'agent1_id': self.agent1_id,
            'agent2_id': self.agent2_id,
            'metrics': self.metrics,
            'interaction_count': self.interaction_count,
            'relationship_type': self.relationship_type,
            'last_update': self.last_update
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentRelationship':
        """Create relationship object from dictionary."""
        relationship = cls(
            agent1_id=data['agent1_id'],
            agent2_id=data['agent2_id'],
            initial_trust=data['metrics'].get(RelationshipMetric.TRUST, 50.0),
            initial_affinity=data['metrics'].get(RelationshipMetric.AFFINITY, 50.0)
        )
        relationship.metrics = data['metrics']
        relationship.interaction_count = data['interaction_count']
        relationship.relationship_type = data['relationship_type']
        relationship.last_update = data['last_update']
        return relationship

class RelationshipSystem:
    """
    System for managing relationships between agents.
    
    This system tracks all agent relationships, provides mechanisms to update
    and query them, and influences team formation and combat behavior.
    """
    
    def __init__(self):
        """Initialize the relationship system."""
        self.relationships = {}  # Map of (agent1_id, agent2_id) -> AgentRelationship
        self.agent_teams = {}  # Map of agent_id -> team_id
        self.team_members = defaultdict(set)  # Map of team_id -> set of agent_ids
        self.relationship_events = []  # Recent relationship events
        self.event_history_size = 100
        
    def register_agent(self, 
                       agent_id: str, 
                       team_id: Optional[str] = None) -> None:
        """
        Register an agent with the relationship system.
        
        Args:
            agent_id: Unique identifier for the agent
            team_id: Team identifier (if agent belongs to a team)
        """
        if team_id:
            self.agent_teams[agent_id] = team_id
            self.team_members[team_id].add(agent_id)
            
            # Initialize relationships with team members
            for member_id in self.team_members[team_id]:
                if member_id != agent_id:
                    self.get_or_create_relationship(agent_id, member_id)
    
    def get_or_create_relationship(self, 
                                  agent1_id: str, 
                                  agent2_id: str) -> AgentRelationship:
        """
        Get or create a relationship between two agents.
        
        Args:
            agent1_id: First agent's ID
            agent2_id: Second agent's ID
            
        Returns:
            The relationship object
        """
        # Always store relationship with lower ID first for consistency
        key = tuple(sorted([agent1_id, agent2_id]))
        
        if key not in self.relationships:
            # Check if agents are on the same team for initial values
            team1 = self.agent_teams.get(agent1_id)
            team2 = self.agent_teams.get(agent2_id)
            
            initial_trust = 70.0 if team1 and team1 == team2 else 50.0
            initial_affinity = 70.0 if team1 and team1 == team2 else 50.0
            
            self.relationships[key] = AgentRelationship(
                key[0], key[1], initial_trust, initial_affinity
            )
            
        return self.relationships[key]
    
    def update_relationship(self, 
                           agent1_id: str, 
                           agent2_id: str, 
                           factor: str, 
                           magnitude: float,
                           context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Update the relationship between two agents.
        
        Args:
            agent1_id: First agent ID
            agent2_id: Second agent ID
            factor: The relationship factor to update
            magnitude: Strength of the update (positive or negative)
            context: Additional information about the update
            
        Returns:
            Changes to relationship metrics
        """
        relationship = self.get_or_create_relationship(agent1_id, agent2_id)
        changes = relationship.update_relationship(factor, magnitude, context)
        
        # Log significant relationship changes
        significant = any(abs(delta) > 5.0 for delta in changes.values())
        if significant and len(self.relationship_events) < self.event_history_size:
            self.relationship_events.append({
                'agent1_id': agent1_id,
                'agent2_id': agent2_id,
                'factor': factor,
                'magnitude': magnitude,
                'changes': changes,
                'timestamp': time.time()
            })
            
        return changes
    
    def get_relationship(self, 
                        agent1_id: str, 
                        agent2_id: str) -> Optional[AgentRelationship]:
        """
        Get the relationship between two agents if it exists.
        
        Args:
            agent1_id: First agent ID
            agent2_id: Second agent ID
            
        Returns:
            Relationship object or None if no relationship exists
        """
        key = tuple(sorted([agent1_id, agent2_id]))
        return self.relationships.get(key)
    
    def get_team_relationships(self, team_id: str) -> Dict[Tuple[str, str], AgentRelationship]:
        """
        Get all relationships between members of a team.
        
        Args:
            team_id: Team identifier
            
        Returns:
            Dictionary of agent pairs to their relationships
        """
        team_relationships = {}
        members = list(self.team_members.get(team_id, set()))
        
        for i, agent1_id in enumerate(members):
            for agent2_id in members[i+1:]:
                relationship = self.get_relationship(agent1_id, agent2_id)
                if relationship:
                    team_relationships[(agent1_id, agent2_id)] = relationship
                    
        return team_relationships
    
    def calculate_team_synergy(self, team_id: str) -> float:
        """
        Calculate the overall synergy level for a team.
        
        Args:
            team_id: Team identifier
            
        Returns:
            Team synergy score (0-100)
        """
        team_relationships = self.get_team_relationships(team_id)
        if not team_relationships:
            return 0.0
            
        # Average compatibility scores for all agent pairs
        compatibility_scores = [rel.get_compatibility_score() 
                              for rel in team_relationships.values()]
        return sum(compatibility_scores) / len(compatibility_scores)
    
    def get_team_combat_bonus(self, team_id: str) -> float:
        """
        Calculate the combat effectiveness bonus for a team.
        
        Args:
            team_id: Team identifier
            
        Returns:
            Combat effectiveness multiplier (1.0 = no bonus)
        """
        team_relationships = self.get_team_relationships(team_id)
        if not team_relationships:
            return 1.0
            
        # Average combat synergy bonuses for all agent pairs
        combat_bonuses = [rel.get_combat_synergy_bonus() 
                         for rel in team_relationships.values()]
        return sum(combat_bonuses) / len(combat_bonuses)
    
    def suggest_team_formation(self, 
                              agents: List[str], 
                              team_size: int) -> List[List[str]]:
        """
        Suggest optimal team formations based on agent relationships.
        
        Args:
            agents: List of agent IDs
            team_size: Size of each team
            
        Returns:
            List of suggested teams (lists of agent IDs)
        """
        # Calculate compatibility scores for all agent pairs
        compatibility_scores = {}
        for i, agent1_id in enumerate(agents):
            for agent2_id in agents[i+1:]:
                relationship = self.get_or_create_relationship(agent1_id, agent2_id)
                compatibility_scores[(agent1_id, agent2_id)] = relationship.get_compatibility_score()
        
        # Simple greedy algorithm - start with highest compatibility pairs
        # and build teams around them
        remaining_agents = set(agents)
        teams = []
        
        while remaining_agents and len(teams) < (len(agents) // team_size):
            # Find highest compatibility pair from remaining agents
            best_pair = None
            best_score = -1
            
            for pair, score in sorted(compatibility_scores.items(), 
                                    key=lambda x: x[1], reverse=True):
                if pair[0] in remaining_agents and pair[1] in remaining_agents:
                    best_pair = pair
                    best_score = score
                    break
            
            if not best_pair:
                # No compatible pairs left, add remaining agents individually
                for agent_id in list(remaining_agents):
                    if len(teams) > 0 and len(teams[-1]) < team_size:
                        teams[-1].append(agent_id)
                    else:
                        teams.append([agent_id])
                    remaining_agents.remove(agent_id)
                break
                
            # Start a new team with the best pair
            new_team = list(best_pair)
            remaining_agents.remove(best_pair[0])
            remaining_agents.remove(best_pair[1])
            
            # Add compatible agents to fill the team
            while len(new_team) < team_size and remaining_agents:
                best_agent = None
                best_compat = -1
                
                for agent_id in remaining_agents:
                    # Calculate average compatibility with current team
                    agent_compat = 0
                    for team_agent in new_team:
                        key = tuple(sorted([agent_id, team_agent]))
                        agent_compat += compatibility_scores.get(key, 50.0)
                    agent_compat /= len(new_team)
                    
                    if agent_compat > best_compat:
                        best_compat = agent_compat
                        best_agent = agent_id
                
                if best_agent:
                    new_team.append(best_agent)
                    remaining_agents.remove(best_agent)
                else:
                    break
            
            teams.append(new_team)
        
        # Handle any remaining agents
        for agent_id in list(remaining_agents):
            # Find team with highest average compatibility
            best_team_idx = -1
            best_compat = -1
            
            for idx, team in enumerate(teams):
                if len(team) < team_size:
                    team_compat = 0
                    for team_agent in team:
                        key = tuple(sorted([agent_id, team_agent]))
                        team_compat += compatibility_scores.get(key, 50.0)
                    team_compat /= len(team)
                    
                    if team_compat > best_compat:
                        best_compat = team_compat
                        best_team_idx = idx
            
            if best_team_idx >= 0:
                teams[best_team_idx].append(agent_id)
                remaining_agents.remove(agent_id)
            else:
                # Start a new team if all teams are full
                teams.append([agent_id])
                remaining_agents.remove(agent_id)
        
        return teams
    
    def get_preferred_teammates(self, 
                               agent_id: str, 
                               count: int = 3) -> List[Tuple[str, float]]:
        """
        Get the preferred teammates for an agent, based on relationship scores.
        
        Args:
            agent_id: Agent's ID
            count: Number of preferred teammates to return
            
        Returns:
            List of (agent_id, compatibility_score) tuples
        """
        teammates = []
        
        for key, relationship in self.relationships.items():
            if agent_id in key:
                other_id = key[0] if key[1] == agent_id else key[1]
                compatibility = relationship.get_compatibility_score()
                teammates.append((other_id, compatibility))
        
        # Sort by compatibility and return top agents
        return sorted(teammates, key=lambda x: x[1], reverse=True)[:count]
    
    def get_agent_relationships(self, 
                              agent_id: str) -> Dict[str, AgentRelationship]:
        """
        Get all relationships for a specific agent.
        
        Args:
            agent_id: Agent's ID
            
        Returns:
            Dictionary of other agent IDs to relationships
        """
        agent_relationships = {}
        
        for key, relationship in self.relationships.items():
            if agent_id in key:
                other_id = key[0] if key[1] == agent_id else key[1]
                agent_relationships[other_id] = relationship
                
        return agent_relationships
    
    def get_relationship_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the relationship system.
        
        Returns:
            Dictionary of relationship statistics
        """
        stats = {
            'total_relationships': len(self.relationships),
            'total_agents': len(set(agent_id for key in self.relationships 
                                for agent_id in key)),
            'teams': len(self.team_members),
            'relationship_types': defaultdict(int),
            'average_metrics': defaultdict(float)
        }
        
        # Count relationship types
        for relationship in self.relationships.values():
            stats['relationship_types'][relationship.relationship_type] += 1
            
            # Sum metrics for averaging
            for metric, value in relationship.metrics.items():
                stats['average_metrics'][metric] += value
        
        # Calculate averages
        if stats['total_relationships'] > 0:
            for metric in stats['average_metrics']:
                stats['average_metrics'][metric] /= stats['total_relationships']
        
        return stats
    
    def export_relationships(self) -> Dict[str, Any]:
        """
        Export all relationships for serialization.
        
        Returns:
            Dictionary of relationship data
        """
        return {
            'relationships': {
                str(key): relationship.to_dict() 
                for key, relationship in self.relationships.items()
            },
            'agent_teams': self.agent_teams,
            'team_members': {
                team_id: list(members) 
                for team_id, members in self.team_members.items()
            }
        }
    
    def import_relationships(self, data: Dict[str, Any]) -> None:
        """
        Import serialized relationship data.
        
        Args:
            data: Relationship data from export_relationships
        """
        self.relationships = {}
        for key_str, rel_data in data['relationships'].items():
            key = tuple(eval(key_str))
            self.relationships[key] = AgentRelationship.from_dict(rel_data)
            
        self.agent_teams = data['agent_teams']
        self.team_members = defaultdict(set)
        for team_id, members in data['team_members'].items():
            self.team_members[team_id] = set(members) 