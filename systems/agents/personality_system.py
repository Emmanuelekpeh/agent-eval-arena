"""
Personality System for AI Battle Arena.

This module defines agent personalities, traits, and compatibility calculations
to influence relationships, team formation, and decision making.
"""

from enum import Enum
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import math
import json
import random

class PersonalityTrait(Enum):
    """Core personality traits that define agent behavior and compatibility."""
    OPENNESS = "openness"           # Creativity, curiosity, open-mindedness
    CONSCIENTIOUSNESS = "conscientiousness"  # Organization, responsibility, thoroughness
    EXTRAVERSION = "extraversion"   # Sociability, assertiveness, energy
    AGREEABLENESS = "agreeableness" # Cooperation, compassion, empathy
    NEUROTICISM = "neuroticism"     # Anxiety, emotional instability, stress response
    
    # Additional traits specific to combat and team dynamics
    RISK_TOLERANCE = "risk_tolerance"  # Willingness to take risks
    LEADERSHIP = "leadership"       # Tendency to lead or follow
    LOYALTY = "loyalty"             # Commitment to team and allies
    ADAPTABILITY = "adaptability"   # Flexibility in changing situations
    AGGRESSION = "aggression"       # Tendency toward aggressive actions

class PersonalityProfile:
    """
    Represents an agent's personality as a collection of trait values.
    Traits are measured on a scale of 0.0 to 1.0.
    """
    
    def __init__(self, agent_id: str, traits: Optional[Dict[PersonalityTrait, float]] = None):
        """
        Initialize a personality profile.
        
        Args:
            agent_id: Unique identifier for the agent
            traits: Dictionary mapping traits to values (0.0-1.0)
                    If None, generates random traits
        """
        self.agent_id = agent_id
        self.traits = traits or self._generate_random_traits()
        self.trait_weights = self._initialize_trait_weights()
        
    def _generate_random_traits(self) -> Dict[PersonalityTrait, float]:
        """Generate random personality traits."""
        return {trait: random.uniform(0.0, 1.0) for trait in PersonalityTrait}
    
    def _initialize_trait_weights(self) -> Dict[str, Dict[PersonalityTrait, float]]:
        """Initialize weights for how traits affect different behaviors."""
        return {
            "combat": {
                PersonalityTrait.RISK_TOLERANCE: 0.3,
                PersonalityTrait.AGGRESSION: 0.3,
                PersonalityTrait.NEUROTICISM: -0.2,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.2,
            },
            "teamwork": {
                PersonalityTrait.AGREEABLENESS: 0.4,
                PersonalityTrait.EXTRAVERSION: 0.2,
                PersonalityTrait.LOYALTY: 0.3,
                PersonalityTrait.LEADERSHIP: 0.1,
            },
            "exploration": {
                PersonalityTrait.OPENNESS: 0.4,
                PersonalityTrait.RISK_TOLERANCE: 0.3,
                PersonalityTrait.EXTRAVERSION: 0.2,
                PersonalityTrait.ADAPTABILITY: 0.1,
            },
            "resource_sharing": {
                PersonalityTrait.AGREEABLENESS: 0.4,
                PersonalityTrait.LOYALTY: 0.3,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.2,
                PersonalityTrait.NEUROTICISM: -0.1,
            }
        }
    
    def get_trait(self, trait: PersonalityTrait) -> float:
        """Get the value of a specific trait."""
        return self.traits.get(trait, 0.5)  # Default to middle value if trait not found
    
    def set_trait(self, trait: PersonalityTrait, value: float) -> None:
        """Set the value of a specific trait, clamped to [0.0, 1.0]."""
        self.traits[trait] = max(0.0, min(1.0, value))
    
    def adjust_trait(self, trait: PersonalityTrait, amount: float) -> None:
        """Adjust a trait by the given amount, clamped to [0.0, 1.0]."""
        current = self.get_trait(trait)
        self.set_trait(trait, current + amount)
    
    def calculate_behavior_score(self, behavior_type: str) -> float:
        """
        Calculate a score for a specific behavior based on personality traits.
        
        Args:
            behavior_type: Type of behavior to score (combat, teamwork, etc.)
            
        Returns:
            Score between 0.0 and 1.0
        """
        if behavior_type not in self.trait_weights:
            return 0.5  # Default middle value for unknown behaviors
            
        weights = self.trait_weights[behavior_type]
        score = 0.0
        total_weight = 0.0
        
        for trait, weight in weights.items():
            trait_value = self.get_trait(trait)
            # For negative weights, invert the trait value's effect
            if weight < 0:
                score += (1.0 - trait_value) * abs(weight)
            else:
                score += trait_value * weight
            total_weight += abs(weight)
        
        # Normalize the score
        if total_weight > 0:
            score /= total_weight
            
        return score
    
    def get_dominant_traits(self, threshold: float = 0.7) -> List[PersonalityTrait]:
        """Get list of traits that exceed the given threshold."""
        return [trait for trait, value in self.traits.items() if value >= threshold]
    
    def get_compatibility(self, other: 'PersonalityProfile') -> float:
        """
        Calculate compatibility score with another personality.
        
        Args:
            other: Another personality profile
            
        Returns:
            Compatibility score between 0.0 (incompatible) and 1.0 (highly compatible)
        """
        # Complementary traits: some differences are good
        complementary_pairs = [
            (PersonalityTrait.EXTRAVERSION, PersonalityTrait.AGREEABLENESS),
            (PersonalityTrait.LEADERSHIP, PersonalityTrait.LOYALTY),
            (PersonalityTrait.RISK_TOLERANCE, PersonalityTrait.CONSCIENTIOUSNESS)
        ]
        
        # Similar traits: similarity is good for these
        similarity_traits = [
            PersonalityTrait.OPENNESS,
            PersonalityTrait.ADAPTABILITY
        ]
        
        # Calculate complementary score
        complementary_score = 0.0
        for trait1, trait2 in complementary_pairs:
            # High score when one is high and one is low
            value1 = abs(self.get_trait(trait1) - other.get_trait(trait1))
            value2 = abs(self.get_trait(trait2) - other.get_trait(trait2))
            complementary_score += (value1 + value2) / 2.0
            
        complementary_score /= len(complementary_pairs)
        
        # Calculate similarity score
        similarity_score = 0.0
        for trait in similarity_traits:
            # High score when both have similar values
            similarity = 1.0 - abs(self.get_trait(trait) - other.get_trait(trait))
            similarity_score += similarity
            
        similarity_score /= len(similarity_traits)
        
        # Calculate conflict score (neuroticism and aggression)
        conflict_score = 0.0
        for trait in [PersonalityTrait.NEUROTICISM, PersonalityTrait.AGGRESSION]:
            # High neuroticism or aggression in both is bad
            if self.get_trait(trait) > 0.7 and other.get_trait(trait) > 0.7:
                conflict_score += 1.0
                
        conflict_score = max(0.0, 1.0 - (conflict_score / 2.0))
        
        # Combine scores with appropriate weights
        compatibility = (
            (complementary_score * 0.4) + 
            (similarity_score * 0.4) + 
            (conflict_score * 0.2)
        )
        
        return compatibility
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary."""
        return {
            "agent_id": self.agent_id,
            "traits": {trait.value: value for trait, value in self.traits.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonalityProfile':
        """Create a personality profile from a dictionary."""
        traits = {PersonalityTrait(trait_name): value 
                 for trait_name, value in data.get("traits", {}).items()}
        return cls(data.get("agent_id", "unknown"), traits)

class PersonalityArchetype:
    """
    Predefined personality archetypes that can be used to quickly create
    personalities with specific characteristics.
    """
    
    @staticmethod
    def get_archetypes() -> Dict[str, Dict[PersonalityTrait, float]]:
        """Get all predefined personality archetypes."""
        return {
            "LEADER": {
                PersonalityTrait.LEADERSHIP: 0.9,
                PersonalityTrait.EXTRAVERSION: 0.8,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.7,
                PersonalityTrait.OPENNESS: 0.6,
                PersonalityTrait.AGREEABLENESS: 0.5,
                PersonalityTrait.NEUROTICISM: 0.3,
                PersonalityTrait.RISK_TOLERANCE: 0.6,
                PersonalityTrait.LOYALTY: 0.7,
                PersonalityTrait.ADAPTABILITY: 0.6,
                PersonalityTrait.AGGRESSION: 0.5
            },
            "SUPPORTER": {
                PersonalityTrait.LEADERSHIP: 0.3,
                PersonalityTrait.EXTRAVERSION: 0.5,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.8,
                PersonalityTrait.OPENNESS: 0.5,
                PersonalityTrait.AGREEABLENESS: 0.9,
                PersonalityTrait.NEUROTICISM: 0.4,
                PersonalityTrait.RISK_TOLERANCE: 0.3,
                PersonalityTrait.LOYALTY: 0.9,
                PersonalityTrait.ADAPTABILITY: 0.7,
                PersonalityTrait.AGGRESSION: 0.2
            },
            "AGGRESSIVE": {
                PersonalityTrait.LEADERSHIP: 0.6,
                PersonalityTrait.EXTRAVERSION: 0.7,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.4,
                PersonalityTrait.OPENNESS: 0.5,
                PersonalityTrait.AGREEABLENESS: 0.3,
                PersonalityTrait.NEUROTICISM: 0.6,
                PersonalityTrait.RISK_TOLERANCE: 0.8,
                PersonalityTrait.LOYALTY: 0.5,
                PersonalityTrait.ADAPTABILITY: 0.5,
                PersonalityTrait.AGGRESSION: 0.9
            },
            "EXPLORER": {
                PersonalityTrait.LEADERSHIP: 0.5,
                PersonalityTrait.EXTRAVERSION: 0.6,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.5,
                PersonalityTrait.OPENNESS: 0.9,
                PersonalityTrait.AGREEABLENESS: 0.6,
                PersonalityTrait.NEUROTICISM: 0.2,
                PersonalityTrait.RISK_TOLERANCE: 0.8,
                PersonalityTrait.LOYALTY: 0.5,
                PersonalityTrait.ADAPTABILITY: 0.9,
                PersonalityTrait.AGGRESSION: 0.4
            },
            "CAUTIOUS": {
                PersonalityTrait.LEADERSHIP: 0.4,
                PersonalityTrait.EXTRAVERSION: 0.3,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.9,
                PersonalityTrait.OPENNESS: 0.4,
                PersonalityTrait.AGREEABLENESS: 0.6,
                PersonalityTrait.NEUROTICISM: 0.7,
                PersonalityTrait.RISK_TOLERANCE: 0.2,
                PersonalityTrait.LOYALTY: 0.7,
                PersonalityTrait.ADAPTABILITY: 0.5,
                PersonalityTrait.AGGRESSION: 0.3
            }
        }
    
    @classmethod
    def create_from_archetype(cls, agent_id: str, archetype_name: str, 
                             variation: float = 0.1) -> PersonalityProfile:
        """
        Create a personality profile based on a predefined archetype.
        
        Args:
            agent_id: Unique identifier for the agent
            archetype_name: Name of the archetype to use
            variation: Random variation to apply to traits (0.0-1.0)
            
        Returns:
            PersonalityProfile based on the archetype with variation
        """
        archetypes = cls.get_archetypes()
        if archetype_name not in archetypes:
            archetype_name = random.choice(list(archetypes.keys()))
            
        base_traits = archetypes[archetype_name]
        
        # Apply random variation
        traits = {}
        for trait, value in base_traits.items():
            # Add random variation within bounds
            var = random.uniform(-variation, variation)
            traits[trait] = max(0.0, min(1.0, value + var))
            
        return PersonalityProfile(agent_id, traits)

class PersonalitySystem:
    """
    System that manages agent personalities and their influence on behaviors,
    relationships, and team dynamics.
    """
    
    def __init__(self):
        """Initialize the personality system."""
        self.agent_personalities = {}
        self.team_personalities = {}
        self.archetype_distribution = self._default_archetype_distribution()
        
    def _default_archetype_distribution(self) -> Dict[str, float]:
        """Default probability distribution for personality archetypes."""
        return {
            "LEADER": 0.15,
            "SUPPORTER": 0.25,
            "AGGRESSIVE": 0.2,
            "EXPLORER": 0.2,
            "CAUTIOUS": 0.2
        }
    
    def register_agent(self, agent_id: str, 
                      personality: Optional[PersonalityProfile] = None,
                      archetype: Optional[str] = None) -> PersonalityProfile:
        """
        Register an agent with the personality system.
        
        Args:
            agent_id: Unique identifier for the agent
            personality: Optional pre-defined personality profile
            archetype: Optional name of personality archetype to use
            
        Returns:
            The agent's personality profile
        """
        if agent_id in self.agent_personalities:
            return self.agent_personalities[agent_id]
            
        if personality:
            self.agent_personalities[agent_id] = personality
        elif archetype:
            self.agent_personalities[agent_id] = PersonalityArchetype.create_from_archetype(
                agent_id, archetype
            )
        else:
            # Choose a random archetype based on distribution
            archetype = self._select_random_archetype()
            self.agent_personalities[agent_id] = PersonalityArchetype.create_from_archetype(
                agent_id, archetype
            )
            
        return self.agent_personalities[agent_id]
    
    def _select_random_archetype(self) -> str:
        """Select a random archetype based on probability distribution."""
        archetypes = list(self.archetype_distribution.keys())
        weights = list(self.archetype_distribution.values())
        return random.choices(archetypes, weights, k=1)[0]
    
    def get_agent_personality(self, agent_id: str) -> Optional[PersonalityProfile]:
        """Get an agent's personality profile."""
        return self.agent_personalities.get(agent_id)
    
    def calculate_team_compatibility(self, agent_ids: List[str]) -> float:
        """
        Calculate overall compatibility score for a team.
        
        Args:
            agent_ids: List of agent IDs in the team
            
        Returns:
            Team compatibility score (0.0-1.0)
        """
        if len(agent_ids) < 2:
            return 1.0  # Single agent teams are perfectly compatible
            
        # Get all unique pairs of agents
        pairs = [(a, b) for i, a in enumerate(agent_ids) for b in agent_ids[i+1:]]
        
        # Calculate compatibility for each pair
        compatibility_scores = []
        for agent1_id, agent2_id in pairs:
            personality1 = self.get_agent_personality(agent1_id)
            personality2 = self.get_agent_personality(agent2_id)
            
            if personality1 and personality2:
                compatibility = personality1.get_compatibility(personality2)
                compatibility_scores.append(compatibility)
                
        # Average the compatibility scores
        if compatibility_scores:
            return sum(compatibility_scores) / len(compatibility_scores)
        else:
            return 0.5  # Default middle value
    
    def suggest_team_composition(self, available_agents: List[str], 
                               team_size: int) -> List[str]:
        """
        Suggest an optimal team composition based on personality compatibility.
        
        Args:
            available_agents: List of available agent IDs
            team_size: Desired team size
            
        Returns:
            List of agent IDs forming an optimal team
        """
        if len(available_agents) <= team_size:
            return available_agents
            
        if team_size < 2:
            return available_agents[:team_size]
            
        # Get all possible combinations of teams
        from itertools import combinations
        possible_teams = list(combinations(available_agents, team_size))
        
        # Calculate compatibility score for each team
        team_scores = []
        for team in possible_teams:
            score = self.calculate_team_compatibility(list(team))
            team_scores.append((team, score))
            
        # Sort teams by compatibility score (descending)
        team_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return the team with the highest compatibility score
        return list(team_scores[0][0]) if team_scores else available_agents[:team_size]
    
    def update_team_personalities(self, team_id: str, agent_ids: List[str]) -> None:
        """
        Update the collective personality profile for a team.
        
        Args:
            team_id: Unique identifier for the team
            agent_ids: List of agent IDs in the team
        """
        if not agent_ids:
            return
            
        # Get personality profiles for all agents in the team
        personalities = [self.get_agent_personality(agent_id) 
                        for agent_id in agent_ids 
                        if self.get_agent_personality(agent_id)]
        
        if not personalities:
            return
            
        # Calculate average traits across the team
        team_traits = {}
        for trait in PersonalityTrait:
            trait_values = [p.get_trait(trait) for p in personalities]
            team_traits[trait] = sum(trait_values) / len(trait_values)
            
        # Create a team personality profile
        team_personality = PersonalityProfile(f"team:{team_id}", team_traits)
        self.team_personalities[team_id] = team_personality
    
    def get_team_personality(self, team_id: str) -> Optional[PersonalityProfile]:
        """Get a team's collective personality profile."""
        return self.team_personalities.get(team_id)
    
    def influence_decision(self, agent_id: str, decision_type: str, 
                         options: List[Any], scores: List[float]) -> List[float]:
        """
        Influence agent decisions based on personality.
        
        Args:
            agent_id: ID of the agent making the decision
            decision_type: Type of decision being made
            options: List of options to choose from
            scores: Base scores for each option
            
        Returns:
            Adjusted scores based on personality
        """
        personality = self.get_agent_personality(agent_id)
        if not personality:
            return scores
            
        # Get behavior score for this decision type
        behavior_score = personality.calculate_behavior_score(decision_type)
        
        # Adjust scores based on personality traits
        adjusted_scores = scores.copy()
        
        # Different adjustments for different decision types
        if decision_type == "combat":
            risk_tolerance = personality.get_trait(PersonalityTrait.RISK_TOLERANCE)
            aggression = personality.get_trait(PersonalityTrait.AGGRESSION)
            
            # Risky options get boosted by risk tolerance
            # Here we assume first options are riskier, adjust as needed
            for i in range(len(adjusted_scores)):
                risk_factor = 1.0 - (i / len(adjusted_scores))
                adjusted_scores[i] *= 1.0 + ((risk_tolerance - 0.5) * risk_factor * 0.5)
                
                # Aggressive options get boosted by aggression
                if i < len(adjusted_scores) // 2:  # First half are more aggressive
                    adjusted_scores[i] *= 1.0 + ((aggression - 0.5) * 0.3)
                
        elif decision_type == "team":
            agreeableness = personality.get_trait(PersonalityTrait.AGREEABLENESS)
            loyalty = personality.get_trait(PersonalityTrait.LOYALTY)
            
            # Team-oriented options get boosted by agreeableness and loyalty
            # Here we assume later options are more team-oriented
            for i in range(len(adjusted_scores)):
                team_factor = i / len(adjusted_scores)
                adjusted_scores[i] *= 1.0 + ((agreeableness - 0.5) * team_factor * 0.4)
                adjusted_scores[i] *= 1.0 + ((loyalty - 0.5) * team_factor * 0.3)
                
        # Normalize scores if necessary
        total = sum(adjusted_scores)
        if total > 0:
            adjusted_scores = [s / total * len(adjusted_scores) for s in adjusted_scores]
            
        return adjusted_scores
    
    def get_leadership_hierarchy(self, agent_ids: List[str]) -> List[Tuple[str, float]]:
        """
        Determine leadership hierarchy in a group based on personality traits.
        
        Args:
            agent_ids: List of agent IDs in the group
            
        Returns:
            List of (agent_id, leadership_score) tuples, sorted by leadership
        """
        leadership_scores = []
        
        for agent_id in agent_ids:
            personality = self.get_agent_personality(agent_id)
            if personality:
                # Calculate leadership score based on relevant traits
                leadership = personality.get_trait(PersonalityTrait.LEADERSHIP)
                extraversion = personality.get_trait(PersonalityTrait.EXTRAVERSION)
                conscientiousness = personality.get_trait(PersonalityTrait.CONSCIENTIOUSNESS)
                
                # Weighted sum of traits relevant to leadership
                score = (leadership * 0.5) + (extraversion * 0.3) + (conscientiousness * 0.2)
                leadership_scores.append((agent_id, score))
                
        # Sort by leadership score (descending)
        leadership_scores.sort(key=lambda x: x[1], reverse=True)
        return leadership_scores
    
    def evolve_personality(self, agent_id: str, 
                         experiences: Dict[str, List[float]]) -> None:
        """
        Evolve an agent's personality based on experiences.
        
        Args:
            agent_id: ID of the agent
            experiences: Dictionary mapping experience types to outcome values
        """
        personality = self.get_agent_personality(agent_id)
        if not personality:
            return
            
        # Adjustments for different experience types
        adjustments = {
            # Risk-related experiences affect risk tolerance
            "risk_success": (PersonalityTrait.RISK_TOLERANCE, 0.01),
            "risk_failure": (PersonalityTrait.RISK_TOLERANCE, -0.01),
            
            # Combat experiences affect aggression and neuroticism
            "combat_success": [(PersonalityTrait.AGGRESSION, 0.005), 
                             (PersonalityTrait.NEUROTICISM, -0.005)],
            "combat_failure": [(PersonalityTrait.AGGRESSION, -0.005), 
                             (PersonalityTrait.NEUROTICISM, 0.008)],
            
            # Team experiences affect agreeableness and loyalty
            "team_success": [(PersonalityTrait.AGREEABLENESS, 0.007), 
                           (PersonalityTrait.LOYALTY, 0.01)],
            "team_betrayal": [(PersonalityTrait.AGREEABLENESS, -0.02), 
                           (PersonalityTrait.LOYALTY, -0.03)],
            
            # Leadership experiences affect leadership trait
            "leadership_success": (PersonalityTrait.LEADERSHIP, 0.015),
            "leadership_failure": (PersonalityTrait.LEADERSHIP, -0.01)
        }
        
        # Apply adjustments based on experiences
        for exp_type, outcomes in experiences.items():
            if not outcomes:
                continue
                
            # Get average outcome value
            avg_outcome = sum(outcomes) / len(outcomes)
            
            # Skip if experience type not in adjustments
            if exp_type not in adjustments:
                continue
                
            adjustment = adjustments[exp_type]
            
            # Handle single trait adjustment
            if isinstance(adjustment, tuple):
                trait, factor = adjustment
                # Apply adjustment scaled by outcome
                personality.adjust_trait(trait, factor * avg_outcome)
                
            # Handle multiple trait adjustments
            elif isinstance(adjustment, list):
                for trait, factor in adjustment:
                    # Apply adjustment scaled by outcome
                    personality.adjust_trait(trait, factor * avg_outcome)
    
    def export_personalities(self) -> Dict[str, Any]:
        """Export all personality data to a serializable format."""
        return {
            "agents": {
                agent_id: personality.to_dict()
                for agent_id, personality in self.agent_personalities.items()
            },
            "teams": {
                team_id: personality.to_dict()
                for team_id, personality in self.team_personalities.items()
            }
        }
    
    def import_personalities(self, data: Dict[str, Any]) -> None:
        """Import personality data from a serializable format."""
        # Import agent personalities
        for agent_id, personality_data in data.get("agents", {}).items():
            self.agent_personalities[agent_id] = PersonalityProfile.from_dict(personality_data)
            
        # Import team personalities
        for team_id, personality_data in data.get("teams", {}).items():
            self.team_personalities[team_id] = PersonalityProfile.from_dict(personality_data)

    def get_effect_value(self, agent_id: str, effect_name: str) -> float:
        """
        Calculate the value of a specific derived effect based on the agent's personality.

        Args:
            agent_id: The ID of the agent.
            effect_name: The name of the effect to calculate (e.g., 'neuroticism_morale_impact').

        Returns:
            A float value representing the effect modifier (often centered around 0, 
            where positive increases effect, negative decreases).
        """
        personality = self.get_agent_personality(agent_id)
        if not personality:
            return 0.0 # Default neutral effect if no personality

        # Define effect calculations based on traits
        # These mappings determine how personality influences morale/suppression etc.
        effect_mappings = {
            # --- Morale Effects --- #
            # Neuroticism: High value -> more sensitive to negative morale, less to positive?
            'neuroticism_morale_impact': lambda p: (p.get_trait(PersonalityTrait.NEUROTICISM) - 0.5) * 2.0, # Range -1 to 1 (modifies base change multiplier)
            # Agreeableness: High value -> more sensitive to positive morale changes?
            'agreeableness_morale_impact': lambda p: (p.get_trait(PersonalityTrait.AGREEABLENESS) - 0.5) * 0.5, # Range -0.25 to 0.25 (modifies base change multiplier)
            # --- Suppression Effects --- #
            # Neuroticism: High value -> gains suppression faster
            'neuroticism_suppression_impact': lambda p: (p.get_trait(PersonalityTrait.NEUROTICISM) - 0.5) * 1.5, # Range -0.75 to 0.75 (modifies base gain multiplier)
            # Adaptability: High value -> suppression decays faster
            'suppression_decay_bonus': lambda p: (p.get_trait(PersonalityTrait.ADAPTABILITY) - 0.5) * 1.0, # Range -0.5 to 0.5 (modifies decay rate multiplier)
            # --- Combat Effects (Examples from CombatSystem) --- #
            # Aggression: High value -> slightly higher crit chance
            'critical_chance_bonus': lambda p: (p.get_trait(PersonalityTrait.AGGRESSION) - 0.5) * 0.3, # Range -0.15 to 0.15 (added to base crit chance multiplier)
            # Aggression: High value -> slightly higher damage dealt
            'damage_bonus': lambda p: (p.get_trait(PersonalityTrait.AGGRESSION) - 0.5) * 0.2, # Range -0.1 to 0.1 (added to base damage multiplier)
            # Conscientiousness/Loyalty: High value -> slightly higher damage reduction
            'damage_reduction': lambda p: ((p.get_trait(PersonalityTrait.CONSCIENTIOUSNESS) - 0.5) * 0.1 + \
                                        (p.get_trait(PersonalityTrait.LOYALTY) - 0.5) * 0.05), # Corrected parenthesis
            # --- Accuracy Effect (Example for _resolve_hit) --- #
            # Conscientiousness: High value -> slightly higher base accuracy
            'accuracy_bonus': lambda p: (p.get_trait(PersonalityTrait.CONSCIENTIOUSNESS) - 0.5) * 0.2 # Range -0.1 to 0.1 (added to base accuracy multiplier)
        } # Closed dictionary brace

        calculation_func = effect_mappings.get(effect_name)
        if calculation_func:
            try:
                return float(calculation_func(personality))
            except Exception as e:
                logger.error(f"Error calculating effect '{effect_name}' for agent {agent_id}: {e}")
                return 0.0
        else:
            # logger.warning(f"Unknown effect requested: '{effect_name}'") # Optional warning
            return 0.0 # Default neutral effect for unknown names 