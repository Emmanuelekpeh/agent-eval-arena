import numpy as np
import random
import math
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class DecisionPersonalityIntegration:
    """
    Integrates the decision-making system with personality traits to influence
    decision outcomes based on agent personality.
    """
    
    def __init__(self, decision_system, personality_system):
        """
        Initialize the decision-personality integration.
        
        Args:
            decision_system: The decision system that generates action decisions
            personality_system: The personality system that manages agent traits
        """
        self.decision_system = decision_system
        self.personality_system = personality_system
        
        # Decision modifiers based on personality traits
        self.decision_modifiers = {
            "attack": {
                "base_weight": 1.0,
                "trait_effects": {
                    "aggression": 0.4,
                    "extraversion": 0.2,
                    "neuroticism": -0.1,
                    "caution": -0.3
                }
            },
            "defend": {
                "base_weight": 1.0,
                "trait_effects": {
                    "caution": 0.4,
                    "conscientiousness": 0.2,
                    "aggression": -0.2,
                    "neuroticism": 0.1
                }
            },
            "explore": {
                "base_weight": 1.0,
                "trait_effects": {
                    "openness": 0.4,
                    "extraversion": 0.2,
                    "neuroticism": -0.2,
                    "caution": -0.2
                }
            },
            "gather": {
                "base_weight": 1.0,
                "trait_effects": {
                    "conscientiousness": 0.3,
                    "openness": 0.2,
                    "extraversion": -0.1,
                    "aggression": -0.2
                }
            },
            "flee": {
                "base_weight": 1.0,
                "trait_effects": {
                    "neuroticism": 0.4,
                    "caution": 0.3,
                    "aggression": -0.3,
                    "extraversion": -0.1
                }
            },
            "support": {
                "base_weight": 1.0,
                "trait_effects": {
                    "agreeableness": 0.4,
                    "extraversion": 0.2,
                    "conscientiousness": 0.1,
                    "aggression": -0.2
                }
            },
            "use_cover": {
                "base_weight": 1.0,
                "trait_effects": {
                    "caution": 0.4,
                    "conscientiousness": 0.2,
                    "aggression": -0.3,
                    "neuroticism": 0.2
                }
            }
        }
        
        logger.info("Decision-Personality Integration system initialized")
        
    def get_decision_weights(self, agent_id, state=None):
        """
        Get personality-modified weights for different decision options.
        
        Args:
            agent_id: The agent's unique identifier
            state (dict, optional): Current state information
            
        Returns:
            dict: Action types and their modified weights
        """
        personality = self.personality_system.get_personality(agent_id)
        if not personality:
            # Return default weights if no personality found
            return {action: modifier["base_weight"] for action, modifier in self.decision_modifiers.items()}
            
        # Calculate personality-adjusted weights
        weights = {}
        for action, modifier in self.decision_modifiers.items():
            weight = modifier["base_weight"]
            
            # Apply trait modifications
            for trait, effect in modifier["trait_effects"].items():
                trait_value = personality.get(trait, 0.5)
                
                # Center around 0.5 as the neutral point
                centered_trait = trait_value - 0.5
                
                # Apply the effect (positive or negative)
                weight += centered_trait * effect * 2.0  # *2 to scale from [-0.5,0.5] to [-1,1]
                
            # Ensure weight is positive
            weights[action] = max(0.1, weight)
            
        # Adjust based on state if provided
        if state:
            self._adjust_for_state(weights, agent_id, state, personality)
            
        return weights
        
    def _adjust_for_state(self, weights, agent_id, state, personality):
        """
        Adjust decision weights based on current state and personality.
        
        Args:
            weights (dict): Current action weights
            agent_id: The agent's unique identifier
            state (dict): Current state information
            personality (dict): Agent's personality traits
        """
        # Health-based adjustments
        if "health_percentage" in state:
            health = state["health_percentage"]
            
            # Low health increases flee weight and decreases attack weight
            if health < 0.3:
                flee_modifier = (0.3 - health) * 3.0 * (0.5 + personality.get("caution", 0.5))
                weights["flee"] += flee_modifier
                weights["attack"] *= max(0.2, health * 2)
                weights["use_cover"] += (0.3 - health) * 2.0
            elif health > 0.7:
                # High health increases attack weight for aggressive agents
                attack_modifier = (health - 0.7) * 2.0 * personality.get("aggression", 0.5)
                weights["attack"] += attack_modifier
                
        # Team-based adjustments
        if "team_advantage" in state:
            advantage = state["team_advantage"]  # -1 to 1 range
            
            # Adjust based on team advantage and extraversion/agreeableness
            extraversion = personality.get("extraversion", 0.5)
            agreeableness = personality.get("agreeableness", 0.5)
            
            if advantage < 0:  # Disadvantage
                # More team-oriented agents will support more when at disadvantage
                support_mod = -advantage * (extraversion + agreeableness) * 0.5
                weights["support"] += support_mod
            else:  # Advantage
                # More aggressive agents will attack more when at advantage
                attack_mod = advantage * personality.get("aggression", 0.5)
                weights["attack"] += attack_mod
                
        # Resource-based adjustments
        if "resource_scarcity" in state:
            scarcity = state["resource_scarcity"]  # 0 to 1 range
            
            # Conscientious agents prioritize gathering when resources are scarce
            conscientiousness = personality.get("conscientiousness", 0.5)
            weights["gather"] += scarcity * conscientiousness
            
        # Hazard awareness based on neuroticism and caution
        if "hazards_nearby" in state and state["hazards_nearby"]:
            neuroticism = personality.get("neuroticism", 0.5)
            caution = personality.get("caution", 0.5)
            
            # More neurotic and cautious agents will avoid hazards more
            hazard_response = (neuroticism + caution) * 0.5
            weights["flee"] += hazard_response * 0.5
            weights["use_cover"] += hazard_response * 0.7
        
    def make_decision(self, agent_id, state, available_actions=None):
        """
        Make a personality-influenced decision for the agent.
        
        Args:
            agent_id: The agent's unique identifier
            state (dict): Current state information
            available_actions (list, optional): List of available actions
                                               If None, all actions are considered
        
        Returns:
            str: The selected action type
        """
        # Get base decision from decision system
        base_decision = self.decision_system.decide_action(agent_id, state)
        
        # Get personality-adjusted weights
        weights = self.get_decision_weights(agent_id, state)
        
        # Filter to available actions if specified
        if available_actions:
            weights = {action: weight for action, weight in weights.items() 
                      if action in available_actions}
                      
            # If no valid actions remain after filtering, return base decision
            if not weights:
                return base_decision
        
        # Adjust base decision weight to give it priority
        if base_decision in weights:
            # Give the base decision a boost
            personality = self.personality_system.get_personality(agent_id)
            
            # The boost depends on conscientiousness (higher means more likely to follow the plan)
            if personality:
                conscientiousness = personality.get("conscientiousness", 0.5)
                weights[base_decision] *= 1.0 + conscientiousness
            else:
                weights[base_decision] *= 1.5  # Default boost
        
        # Calculate probabilities based on weights
        total_weight = sum(weights.values())
        probabilities = {action: weight / total_weight for action, weight in weights.items()}
        
        # Select action based on probabilities
        actions = list(probabilities.keys())
        probs = [probabilities[action] for action in actions]
        
        selected_action = np.random.choice(actions, p=probs)
        
        # Log the decision process
        logger.debug(f"Agent {agent_id} decision: base={base_decision}, chosen={selected_action}, " 
                    f"weights={weights}")
        
        return selected_action
        
    def get_action_parameters(self, agent_id, action_type, state):
        """
        Get personality-influenced parameters for the selected action.
        
        Args:
            agent_id: The agent's unique identifier
            action_type (str): The type of action to perform
            state (dict): Current state information
            
        Returns:
            dict: Parameters for the action
        """
        # Start with base parameters from decision system
        base_params = self.decision_system.get_action_parameters(agent_id, action_type, state)
        
        personality = self.personality_system.get_personality(agent_id)
        if not personality:
            return base_params
            
        # Create a copy to modify
        params = base_params.copy() if base_params else {}
        
        # Adjust parameters based on personality and action type
        if action_type == "attack":
            # Aggression influences target selection and force
            aggression = personality.get("aggression", 0.5)
            caution = personality.get("caution", 0.5)
            
            # Higher aggression means more damage but less precision
            if "damage_multiplier" in params:
                params["damage_multiplier"] *= 0.8 + aggression * 0.4
                
            if "accuracy" in params:
                params["accuracy"] *= 1.2 - aggression * 0.4
                
            # Caution influences range preference
            if "preferred_range" in params:
                # More cautious agents prefer longer range
                params["preferred_range"] *= 0.7 + caution * 0.6
                
        elif action_type == "defend":
            # Conscientiousness and caution influence defensive positioning
            conscientiousness = personality.get("conscientiousness", 0.5)
            
            if "positioning_quality" in params:
                params["positioning_quality"] *= 0.7 + conscientiousness * 0.6
                
            if "reaction_time" in params:
                # Lower values are better
                params["reaction_time"] *= 1.2 - conscientiousness * 0.4
                
        elif action_type == "explore":
            # Openness influences exploration patterns
            openness = personality.get("openness", 0.5)
            extraversion = personality.get("extraversion", 0.5)
            
            if "exploration_range" in params:
                params["exploration_range"] *= 0.7 + openness * 0.6
                
            if "risk_threshold" in params:
                # Extraverted agents are more willing to take risks when exploring
                params["risk_threshold"] *= 0.7 + extraversion * 0.6
                
        elif action_type == "flee":
            # Neuroticism affects flee distance and path planning
            neuroticism = personality.get("neuroticism", 0.5)
            
            if "flee_distance" in params:
                params["flee_distance"] *= 0.8 + neuroticism * 0.4
                
            if "path_randomness" in params:
                # More neurotic agents have more erratic escape paths
                params["path_randomness"] *= 0.7 + neuroticism * 0.6
                
        elif action_type == "use_cover":
            # Caution and conscientiousness affect cover usage
            caution = personality.get("caution", 0.5)
            conscientiousness = personality.get("conscientiousness", 0.5)
            
            if "cover_preference" in params:
                # Higher values prioritize better cover over closer cover
                params["cover_preference"] *= 0.7 + caution * 0.6
                
            if "reposition_frequency" in params:
                # More conscientious agents reposition more optimally
                params["reposition_frequency"] *= 0.8 + conscientiousness * 0.4
                
        # Return the personality-modified parameters
        return params
        
    def evaluate_decision_outcome(self, agent_id, action_type, outcome, state_before, state_after):
        """
        Evaluate the outcome of a decision and feed it back to the decision system.
        
        Args:
            agent_id: The agent's unique identifier
            action_type (str): The action that was performed
            outcome (dict): Information about the action's outcome
            state_before (dict): State before the action
            state_after (dict): State after the action
            
        Returns:
            float: Personality-adjusted reward value
        """
        # Get base reward from decision system
        base_reward = self.decision_system.evaluate_outcome(agent_id, action_type, outcome)
        
        personality = self.personality_system.get_personality(agent_id)
        if not personality:
            return base_reward
            
        # Adjust reward based on personality preferences and values
        adjusted_reward = base_reward
        
        # Different personalities value different outcomes
        if "health_change" in outcome:
            health_change = outcome["health_change"]
            
            # Cautious agents care more about health loss
            caution = personality.get("caution", 0.5)
            if health_change < 0:
                adjusted_reward += health_change * (0.5 + caution)  # More negative for cautious agents
            
        if "damage_dealt" in outcome and outcome["damage_dealt"] > 0:
            # Aggressive agents value dealing damage more
            aggression = personality.get("aggression", 0.5)
            adjusted_reward += outcome["damage_dealt"] * (0.5 + aggression * 0.5)
            
        if "resources_gained" in outcome and outcome["resources_gained"] > 0:
            # Conscientious agents value resources more
            conscientiousness = personality.get("conscientiousness", 0.5)
            adjusted_reward += outcome["resources_gained"] * (0.5 + conscientiousness * 0.5)
            
        if "team_benefit" in outcome and outcome["team_benefit"] > 0:
            # Agreeable and extraverted agents value team benefits more
            agreeableness = personality.get("agreeableness", 0.5)
            extraversion = personality.get("extraversion", 0.5)
            team_value = (agreeableness + extraversion) * 0.5
            adjusted_reward += outcome["team_benefit"] * (0.5 + team_value)
            
        # Feed back the personality-adjusted reward to the decision system
        self.decision_system.update_policy(agent_id, action_type, state_before, adjusted_reward)
        
        return adjusted_reward 