import numpy as np
import random
import json
import os
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class PersonalitySystem:
    """
    System that manages personality traits for agents.
    Personality traits influence agent behavior, decision-making, and learning.
    """
    
    # Define personality trait ranges and their effects
    TRAIT_DEFINITIONS = {
        # Core traits (Big Five model)
        "openness": {
            "description": "Willingness to try new strategies and explore",
            "min": 0.0,  # Conventional, cautious
            "max": 1.0,  # Innovative, curious
            "effects": {
                "exploration_rate": (0.05, 0.3),  # Low to high exploration in learning
                "strategy_diversity": (1, 5),     # Number of strategies to consider
                "pattern_recognition": (0.5, 1.5)  # Multiplier for recognizing patterns
            }
        },
        "conscientiousness": {
            "description": "Tendency to be organized and goal-oriented",
            "min": 0.0,  # Impulsive, disorganized
            "max": 1.0,  # Disciplined, organized
            "effects": {
                "planning_horizon": (1, 10),  # How many steps ahead to plan
                "resource_management": (0.7, 1.3),  # Effectiveness at managing resources
                "consistency": (0.6, 1.4)  # Consistency in applying learned tactics
            }
        },
        "extraversion": {
            "description": "Tendency to be sociable and team-oriented",
            "min": 0.0,  # Reserved, independent
            "max": 1.0,  # Outgoing, team-focused
            "effects": {
                "team_coordination": (0.7, 1.3),  # Effectiveness in team actions
                "information_sharing": (0.5, 1.5),  # Willingness to share patterns
                "leadership_score": (0.2, 1.0)  # Contribution to leadership potential
            }
        },
        "agreeableness": {
            "description": "Tendency to be cooperative and supportive",
            "min": 0.0,  # Competitive, challenging
            "max": 1.0,  # Cooperative, supportive
            "effects": {
                "team_support": (0.6, 1.4),  # Effectiveness in support actions
                "defensive_behavior": (1.2, 0.8),  # Inverse effect: higher trait means less defensive
                "resource_sharing": (0.5, 1.5)  # Willingness to share resources
            }
        },
        "neuroticism": {
            "description": "Tendency to experience negative emotions and stress",
            "min": 0.0,  # Stable, calm
            "max": 1.0,  # Anxious, reactive
            "effects": {
                "risk_aversion": (0.7, 1.3),  # Higher means more risk-averse
                "stress_adaptation": (1.3, 0.7),  # Inverse: higher trait means slower adaptation
                "decision_speed": (1.2, 0.8)  # Inverse: higher trait means slower decisions
            }
        },
        
        # Secondary traits (game-specific)
        "aggression": {
            "description": "Tendency to engage in offensive actions",
            "min": 0.0,  # Passive, defensive
            "max": 1.0,  # Aggressive, offensive
            "effects": {
                "attack_frequency": (0.7, 1.3),  # Rate of initiating attacks
                "damage_bonus": (0.9, 1.1),  # Damage effectiveness
                "target_selection": (0.8, 1.2)  # Effectiveness in choosing targets
            }
        },
        "caution": {
            "description": "Tendency to avoid risks and prioritize safety",
            "min": 0.0,  # Reckless
            "max": 1.0,  # Extremely cautious
            "effects": {
                "retreat_threshold": (0.2, 0.5),  # Health percentage to trigger retreat
                "scouting_priority": (0.7, 1.3),  # Priority given to scouting
                "cover_usage": (0.6, 1.4)  # Effectiveness in using cover
            }
        },
        "adaptability": {
            "description": "Ability to adapt to changing circumstances",
            "min": 0.0,  # Rigid, inflexible
            "max": 1.0,  # Highly adaptable
            "effects": {
                "learning_rate": (0.05, 0.2),  # Speed of learning
                "strategy_switching": (0.5, 1.5),  # Willingness to switch strategies
                "environmental_awareness": (0.7, 1.3)  # Awareness of environment changes
            }
        }
    }
    
    def __init__(self, seed=None):
        """Initialize the personality system"""
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
            
        self.agent_personalities = {}  # Map of agent_id to personality traits
        self.predefined_types = self._create_predefined_types()
        
        logger.info("PersonalitySystem initialized")
        
    def _create_predefined_types(self):
        """Create predefined personality types"""
        types = {
            "balanced": {trait: 0.5 for trait in self.TRAIT_DEFINITIONS},
            "leader": {
                "openness": 0.7, "conscientiousness": 0.8, "extraversion": 0.9,
                "agreeableness": 0.6, "neuroticism": 0.3, "aggression": 0.7,
                "caution": 0.5, "adaptability": 0.7
            },
            "scout": {
                "openness": 0.9, "conscientiousness": 0.6, "extraversion": 0.5,
                "agreeableness": 0.6, "neuroticism": 0.4, "aggression": 0.3,
                "caution": 0.7, "adaptability": 0.9
            },
            "attacker": {
                "openness": 0.6, "conscientiousness": 0.7, "extraversion": 0.6,
                "agreeableness": 0.3, "neuroticism": 0.4, "aggression": 0.9,
                "caution": 0.2, "adaptability": 0.6
            },
            "defender": {
                "openness": 0.4, "conscientiousness": 0.8, "extraversion": 0.5,
                "agreeableness": 0.7, "neuroticism": 0.5, "aggression": 0.3,
                "caution": 0.9, "adaptability": 0.5
            },
            "support": {
                "openness": 0.6, "conscientiousness": 0.7, "extraversion": 0.8,
                "agreeableness": 0.9, "neuroticism": 0.3, "aggression": 0.2,
                "caution": 0.6, "adaptability": 0.7
            }
        }
        return types
        
    def generate_random_personality(self, bias=None):
        """
        Generate a random personality with optional bias towards a specific type.
        
        Args:
            bias (str, optional): A predefined personality type to bias towards.
                                  If None, completely random traits are generated.
        
        Returns:
            dict: A dictionary of personality traits and their values
        """
        personality = {}
        
        if bias and bias in self.predefined_types:
            # Start with the predefined type
            base_traits = self.predefined_types[bias]
            
            # Add random variation
            for trait, value in base_traits.items():
                # Add random variation of ±20%
                variation = random.uniform(-0.2, 0.2)
                personality[trait] = max(0.0, min(1.0, value + variation))
        else:
            # Generate completely random traits
            for trait in self.TRAIT_DEFINITIONS:
                personality[trait] = random.uniform(0.0, 1.0)
                
        return personality
        
    def assign_personality(self, agent_id, personality_type=None, custom_traits=None):
        """
        Assign a personality to an agent.
        
        Args:
            agent_id: The unique identifier for the agent
            personality_type (str, optional): A predefined personality type
            custom_traits (dict, optional): Custom trait values to override
        
        Returns:
            dict: The assigned personality traits
        """
        if custom_traits:
            # Use custom traits directly
            personality = {trait: max(0.0, min(1.0, value)) 
                          for trait, value in custom_traits.items() 
                          if trait in self.TRAIT_DEFINITIONS}
            
            # Fill in any missing traits with defaults
            for trait in self.TRAIT_DEFINITIONS:
                if trait not in personality:
                    personality[trait] = 0.5  # Default value
        elif personality_type and personality_type in self.predefined_types:
            # Use predefined type
            personality = self.predefined_types[personality_type].copy()
        else:
            # Generate random personality with optional bias
            personality = self.generate_random_personality(bias=personality_type)
            
        # Store the personality for this agent
        self.agent_personalities[agent_id] = personality
        
        logger.debug(f"Assigned personality to agent {agent_id}: {personality}")
        return personality
        
    def get_personality(self, agent_id):
        """Get the personality traits for an agent"""
        return self.agent_personalities.get(agent_id, None)
        
    def get_trait(self, agent_id, trait):
        """Get a specific trait value for an agent"""
        personality = self.get_personality(agent_id)
        if personality and trait in personality:
            return personality[trait]
        return 0.5  # Default value if not found
        
    def get_effect_value(self, agent_id, effect_name):
        """
        Calculate the effect value for a specific agent based on their personality traits.
        
        Args:
            agent_id: The unique identifier for the agent
            effect_name (str): The name of the effect to calculate
            
        Returns:
            float: The calculated effect value
        """
        personality = self.get_personality(agent_id)
        if not personality:
            return 1.0  # Default neutral value
            
        # Find which traits influence this effect
        effect_value = 1.0
        traits_affecting = []
        
        for trait, definition in self.TRAIT_DEFINITIONS.items():
            if effect_name in definition["effects"]:
                traits_affecting.append((trait, definition["effects"][effect_name]))
                
        if not traits_affecting:
            return effect_value  # No traits affect this effect
            
        # Calculate the weighted effect from each trait
        for trait, effect_range in traits_affecting:
            trait_value = personality.get(trait, 0.5)
            min_effect, max_effect = effect_range
            
            # Linear interpolation based on trait value
            trait_effect = min_effect + trait_value * (max_effect - min_effect)
            
            # Apply contribution to overall effect
            # Using multiplication for compounding effects
            effect_value *= trait_effect ** (1.0 / len(traits_affecting))
            
        return effect_value
        
    def get_leadership_score(self, agent_id):
        """
        Calculate a leadership score for an agent based on their personality.
        Higher scores indicate better leadership potential.
        
        Args:
            agent_id: The unique identifier for the agent
            
        Returns:
            float: Leadership score between 0 and 1
        """
        personality = self.get_personality(agent_id)
        if not personality:
            return 0.0
            
        # Traits that positively influence leadership
        positive_traits = {
            "extraversion": 0.25,
            "conscientiousness": 0.25,
            "openness": 0.15,
            "agreeableness": 0.15,
            "adaptability": 0.2
        }
        
        # Traits that negatively influence leadership
        negative_traits = {
            "neuroticism": 0.3
        }
        
        # Calculate positive contributions
        leadership_score = 0.0
        for trait, weight in positive_traits.items():
            trait_value = personality.get(trait, 0.5)
            leadership_score += trait_value * weight
            
        # Apply negative modifiers
        for trait, weight in negative_traits.items():
            trait_value = personality.get(trait, 0.5)
            leadership_score *= (1 - trait_value * weight)
            
        return max(0.0, min(1.0, leadership_score))
        
    def get_combat_style(self, agent_id):
        """
        Determine an agent's preferred combat style based on personality.
        
        Args:
            agent_id: The unique identifier for the agent
            
        Returns:
            str: The preferred combat style
        """
        personality = self.get_personality(agent_id)
        if not personality:
            return "balanced"
            
        # Calculate style scores
        styles = {
            "aggressive": personality.get("aggression", 0.5) * 1.5 + 
                         personality.get("extraversion", 0.5) * 0.5,
                         
            "defensive": personality.get("caution", 0.5) * 1.5 + 
                        personality.get("conscientiousness", 0.5) * 0.5,
                        
            "tactical": personality.get("openness", 0.5) * 0.7 + 
                       personality.get("conscientiousness", 0.5) * 0.8 + 
                       personality.get("adaptability", 0.5) * 0.5,
                       
            "support": personality.get("agreeableness", 0.5) * 1.2 + 
                      personality.get("extraversion", 0.5) * 0.8
        }
        
        # Find the highest scoring style
        preferred_style = max(styles.items(), key=lambda x: x[1])[0]
        return preferred_style
        
    def calculate_risk_tolerance(self, agent_id, situation=None):
        """
        Calculate an agent's risk tolerance in a given situation.
        
        Args:
            agent_id: The unique identifier for the agent
            situation (dict, optional): Context about the current situation
            
        Returns:
            float: Risk tolerance value between 0 (very risk-averse) and 1 (very risk-tolerant)
        """
        personality = self.get_personality(agent_id)
        if not personality:
            return 0.5  # Default middle value
            
        # Base risk tolerance calculation
        base_tolerance = (
            (1.0 - personality.get("neuroticism", 0.5)) * 0.3 +
            (1.0 - personality.get("caution", 0.5)) * 0.3 +
            personality.get("aggression", 0.5) * 0.2 +
            personality.get("openness", 0.5) * 0.2
        )
        
        # Apply situational modifiers if provided
        if situation:
            # Example: reduce risk tolerance when low on health
            if "health_percentage" in situation:
                health_factor = situation["health_percentage"]
                # More cautious when health is low
                base_tolerance *= (0.5 + 0.5 * health_factor)
                
            # Example: increase risk tolerance when team has advantage
            if "team_advantage" in situation:
                advantage = situation["team_advantage"]  # -1 to 1 range
                # More risk-tolerant when team has advantage
                modifier = 1.0 + max(0, advantage) * 0.3
                base_tolerance *= modifier
                
        return max(0.0, min(1.0, base_tolerance))
        
    def get_learning_parameters(self, agent_id):
        """
        Get learning parameters adjusted based on agent's personality.
        
        Args:
            agent_id: The unique identifier for the agent
            
        Returns:
            dict: Learning parameters
        """
        # Base learning parameters
        base_params = {
            "learning_rate": 0.1,
            "exploration_rate": 0.15,
            "discount_factor": 0.9,
            "pattern_recognition_threshold": 0.7,
            "strategy_update_frequency": 5
        }
        
        # Apply personality-based modifications
        personality = self.get_personality(agent_id)
        if not personality:
            return base_params
            
        # Apply modifications based on traits
        params = base_params.copy()
        
        # Learning rate affected by adaptability and openness
        adaptability = personality.get("adaptability", 0.5)
        openness = personality.get("openness", 0.5)
        params["learning_rate"] *= (0.5 + adaptability * 1.0)
        
        # Exploration rate affected by openness and inversely by neuroticism
        neuroticism = personality.get("neuroticism", 0.5)
        params["exploration_rate"] = params["exploration_rate"] * (0.5 + openness) * (1.5 - neuroticism)
        
        # Discount factor affected by conscientiousness (long-term planning)
        conscientiousness = personality.get("conscientiousness", 0.5)
        params["discount_factor"] = min(0.99, params["discount_factor"] + (conscientiousness - 0.5) * 0.1)
        
        # Pattern recognition threshold affected by openness and conscientiousness
        params["pattern_recognition_threshold"] -= (openness - 0.5) * 0.2
        params["pattern_recognition_threshold"] += (conscientiousness - 0.5) * 0.1
        
        # Strategy update frequency affected by adaptability and extraversion
        extraversion = personality.get("extraversion", 0.5)
        update_modifier = max(0.5, 1.0 + (adaptability - 0.5) * 0.7 - (extraversion - 0.5) * 0.3)
        params["strategy_update_frequency"] = max(1, int(params["strategy_update_frequency"] / update_modifier))
        
        return params
        
    def get_team_compatibility(self, agent_id1, agent_id2):
        """
        Calculate the compatibility between two agents for team activities.
        
        Args:
            agent_id1: First agent's ID
            agent_id2: Second agent's ID
            
        Returns:
            float: Compatibility score between 0 (incompatible) and 1 (highly compatible)
        """
        personality1 = self.get_personality(agent_id1)
        personality2 = self.get_personality(agent_id2)
        
        if not personality1 or not personality2:
            return 0.5  # Default middle value
            
        # Calculate similarity on key traits
        similarity = 0.0
        
        # Similar agreeableness is good for teamwork
        agreeableness_diff = abs(personality1.get("agreeableness", 0.5) - 
                               personality2.get("agreeableness", 0.5))
        similarity += (1.0 - agreeableness_diff) * 0.3
        
        # Similar conscientiousness helps with coordinated effort
        conscientiousness_diff = abs(personality1.get("conscientiousness", 0.5) - 
                                   personality2.get("conscientiousness", 0.5))
        similarity += (1.0 - conscientiousness_diff) * 0.2
        
        # Calculate complementary traits
        complementary = 0.0
        
        # Different extraversion can be complementary (one talks, one listens)
        extraversion_diff = abs(personality1.get("extraversion", 0.5) - 
                              personality2.get("extraversion", 0.5))
        complementary += extraversion_diff * 0.15
        
        # Different aggression/caution can form balanced teams
        aggression_diff = abs(personality1.get("aggression", 0.5) - 
                            personality2.get("aggression", 0.5))
        complementary += aggression_diff * 0.15
        
        # Different openness can provide diverse perspectives
        openness_diff = abs(personality1.get("openness", 0.5) - 
                          personality2.get("openness", 0.5))
        complementary += openness_diff * 0.1
        
        # Calculate negative factors
        negative = 0.0
        
        # Both high in neuroticism can be problematic
        if personality1.get("neuroticism", 0.5) > 0.7 and personality2.get("neuroticism", 0.5) > 0.7:
            negative += 0.2
            
        # Both very low in agreeableness can lead to conflicts
        if personality1.get("agreeableness", 0.5) < 0.3 and personality2.get("agreeableness", 0.5) < 0.3:
            negative += 0.2
            
        # Calculate overall compatibility
        compatibility = (similarity * 0.6) + (complementary * 0.4) - negative
        return max(0.0, min(1.0, compatibility))
        
    def save_personalities(self, filepath):
        """Save all agent personalities to a file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.agent_personalities, f, indent=2)
            logger.info(f"Saved {len(self.agent_personalities)} personalities to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save personalities: {e}")
            return False
            
    def load_personalities(self, filepath):
        """Load agent personalities from a file"""
        try:
            if not os.path.exists(filepath):
                logger.warning(f"Personality file {filepath} does not exist")
                return False
                
            with open(filepath, 'r') as f:
                personalities = json.load(f)
                
            # Validate and convert keys to appropriate types
            valid_personalities = {}
            for agent_id, personality in personalities.items():
                # Convert string keys back to appropriate type if needed
                try:
                    # Use int if the original was an integer
                    if agent_id.isdigit():
                        agent_id = int(agent_id)
                except:
                    pass  # Keep as string if conversion fails
                    
                # Validate that all required traits are present
                valid_personality = {}
                for trait in self.TRAIT_DEFINITIONS:
                    if trait in personality:
                        valid_personality[trait] = max(0.0, min(1.0, personality[trait]))
                    else:
                        valid_personality[trait] = 0.5  # Default if missing
                        
                valid_personalities[agent_id] = valid_personality
                
            self.agent_personalities = valid_personalities
            logger.info(f"Loaded {len(self.agent_personalities)} personalities from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load personalities: {e}")
            return False 