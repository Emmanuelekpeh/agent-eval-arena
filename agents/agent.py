import time
import logging

logger = logging.getLogger(__name__)

class Agent:
    """Base agent class that all agents should inherit from"""
    
    def __init__(self, agent_id, position=None, team_id=None):
        """Initialize the agent with basic properties"""
        self.id = agent_id
        self.position = position if position is not None else [0, 0]
        self.team_id = team_id
        self.health = 100
        self.max_health = 100
        self.alive = True
        self.inventory = {}
        self.last_action = None
        self.action_cooldown = 0
        self.state = "idle"
        self.facing_direction = [1, 0]  # Unit vector, initially facing right
        
        # --- ADDED: Morale and Suppression --- #
        self.morale: float = 0.5 # Assuming 0-1 scale, 0.5 is neutral
        self.suppression: float = 0.0 # Starts at 0
        # --------------------------------------- #
        
        # Status effects
        self.status_effects = {}  # {effect_name: expiration_time}
        
        # Cover awareness
        self.in_cover = False
        self.cover_direction = None  # Direction vector of cover relative to agent
        
        # Performance metrics
        self.damage_dealt = 0
        self.damage_taken = 0
        self.kills = 0
        self.distance_traveled = 0
        self.actions_taken = 0

    def apply_damage(self, damage):
        """Apply damage to the agent"""
        # Apply damage reduction if in cover
        if self.in_cover and self.cover_direction is not None:
            # Calculate angle between incoming attack and cover direction
            # For simplicity, we're assuming the attack comes from the opposite of cover_direction
            # A more sophisticated version would use the actual attacker position
            damage *= 0.5  # Simple 50% damage reduction when in cover
            
        self.health -= damage
        self.damage_taken += damage
        
        # Check if agent died
        if self.health <= 0:
            self.health = 0
            self.alive = False
            self.state = "dead"
            
        return self.health
        
    def apply_status_effect(self, effect_name, duration=3.0):
        """Apply a status effect to the agent for the specified duration"""
        current_time = time.time()
        self.status_effects[effect_name] = current_time + duration
        logger.debug(f"Agent {self.id} afflicted with {effect_name} for {duration}s")
        
    def update_status_effects(self):
        """Update status effects and apply their ongoing effects"""
        current_time = time.time()
        effects_to_remove = []
        
        for effect, expiry_time in self.status_effects.items():
            # Check if effect has expired
            if current_time >= expiry_time:
                effects_to_remove.append(effect)
                continue
                
            # Apply ongoing effect
            if effect == 'burn':
                self.apply_damage(2)  # Burn damage per update
            elif effect == 'poison':
                self.apply_damage(1)  # Poison damage per update
            elif effect == 'disable':
                # Disabled means can't take actions, handled in the update method
                pass
                
        # Remove expired effects
        for effect in effects_to_remove:
            del self.status_effects[effect]
            logger.debug(f"Agent {self.id} recovered from {effect}")
    
    def is_disabled(self):
        """Check if agent is disabled by a status effect"""
        return 'disable' in self.status_effects
        
    def update_cover_status(self, environment):
        """Update whether the agent is in cover"""
        x, y = self.position
        self.in_cover = environment.is_position_in_cover(x, y)
        
        # In a real implementation, we would calculate the cover_direction
        # based on nearby cover objects and their orientation

    def update(self, delta_time, environment, other_agents):
        """Update agent state"""
        # Update action cooldown
        if self.action_cooldown > 0:
            self.action_cooldown -= delta_time
            
        # Check for and apply hazard effects
        if environment:
            environment.check_hazard_effects(self)
            self.update_cover_status(environment)
            
        # Update status effects
        self.update_status_effects()
        
        # Don't process further if agent is dead
        if not self.alive:
            return
            
        # Don't take actions if disabled
        if self.is_disabled():
            self.state = "disabled"
            return 