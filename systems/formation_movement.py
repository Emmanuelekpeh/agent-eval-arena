"""
Formation Movement System for AI Battle Arena.

This module provides mechanisms for teams to move in coordinated formations,
maintain relative positions, and adapt formations based on the situation.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Set
import math
from collections import defaultdict
import random

class FormationPosition:
    """
    Represents a position within a formation.
    
    Attributes:
        offset_x: X offset from formation center
        offset_y: Y offset from formation center
        role: Role at this position (leader, flanker, etc.)
        index: Index in the formation
    """
    
    def __init__(self, 
               offset_x: float, 
               offset_y: float, 
               role: str = "member",
               index: int = 0):
        """
        Initialize formation position.
        
        Args:
            offset_x: X offset from formation center
            offset_y: Y offset from formation center
            role: Role at this position
            index: Position index
        """
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.role = role
        self.index = index
        
    def get_world_position(self, 
                        center_x: float, 
                        center_y: float,
                        rotation: float = 0.0,
                        spacing: float = 50.0) -> Tuple[float, float]:
        """
        Get world position based on formation center.
        
        Args:
            center_x: X coordinate of formation center
            center_y: Y coordinate of formation center
            rotation: Formation rotation in radians
            spacing: Spacing between formation positions
            
        Returns:
            (x, y) position in world coordinates
        """
        # Apply rotation
        cos_rot = math.cos(rotation)
        sin_rot = math.sin(rotation)
        
        rotated_x = self.offset_x * cos_rot - self.offset_y * sin_rot
        rotated_y = self.offset_x * sin_rot + self.offset_y * cos_rot
        
        # Apply spacing and center offset
        world_x = center_x + rotated_x * spacing
        world_y = center_y + rotated_y * spacing
        
        return (world_x, world_y)

class Formation:
    """
    Defines a team formation with positions and properties.
    
    Attributes:
        name: Formation name
        positions: List of positions in the formation
        spacing: Default spacing between positions
        tactical_properties: Tactical bonuses/penalties
    """
    
    def __init__(self, name: str, spacing: float = 50.0):
        """
        Initialize a formation.
        
        Args:
            name: Formation name
            spacing: Default spacing between positions
        """
        self.name = name
        self.positions = []
        self.spacing = spacing
        self.tactical_properties = {
            'defensive': 0.0,
            'offensive': 0.0,
            'mobility': 0.0,
            'flexibility': 0.0
        }
        self.description = ""
        
    def add_position(self, 
                  offset_x: float, 
                  offset_y: float, 
                  role: str = "member") -> None:
        """
        Add a position to the formation.
        
        Args:
            offset_x: X offset from formation center
            offset_y: Y offset from formation center
            role: Role at this position
        """
        index = len(self.positions)
        position = FormationPosition(offset_x, offset_y, role, index)
        self.positions.append(position)
        
    def get_positions(self, 
                   center_x: float, 
                   center_y: float,
                   num_agents: int,
                   rotation: float = 0.0) -> List[Tuple[float, float]]:
        """
        Get world positions for a number of agents.
        
        Args:
            center_x: X coordinate of formation center
            center_y: Y coordinate of formation center
            num_agents: Number of agents in the formation
            rotation: Formation rotation in radians
            
        Returns:
            List of (x, y) positions
        """
        positions = []
        
        # Use only as many positions as we have agents
        for i in range(min(num_agents, len(self.positions))):
            pos = self.positions[i]
            world_pos = pos.get_world_position(
                center_x, 
                center_y, 
                rotation, 
                self.spacing
            )
            positions.append(world_pos)
            
        return positions
    
    def get_role_position(self, 
                       role: str, 
                       center_x: float,
                       center_y: float,
                       rotation: float = 0.0) -> Optional[Tuple[float, float]]:
        """
        Get position for a specific role.
        
        Args:
            role: Role to find position for
            center_x: X coordinate of formation center
            center_y: Y coordinate of formation center
            rotation: Formation rotation in radians
            
        Returns:
            (x, y) position or None if role not found
        """
        for pos in self.positions:
            if pos.role == role:
                return pos.get_world_position(
                    center_x, 
                    center_y, 
                    rotation, 
                    self.spacing
                )
                
        return None
    
    def get_position_by_index(self, 
                           index: int, 
                           center_x: float,
                           center_y: float,
                           rotation: float = 0.0) -> Optional[Tuple[float, float]]:
        """
        Get position by index.
        
        Args:
            index: Index of the position
            center_x: X coordinate of formation center
            center_y: Y coordinate of formation center
            rotation: Formation rotation in radians
            
        Returns:
            (x, y) position or None if index out of range
        """
        if 0 <= index < len(self.positions):
            return self.positions[index].get_world_position(
                center_x, 
                center_y, 
                rotation, 
                self.spacing
            )
            
        return None
    
    def set_tactical_properties(self, 
                           properties: Dict[str, float]) -> None:
        """
        Set tactical properties for the formation.
        
        Args:
            properties: Dictionary of property values
        """
        self.tactical_properties.update(properties)
        
    def set_description(self, description: str) -> None:
        """
        Set formation description.
        
        Args:
            description: Formation description
        """
        self.description = description

class FormationLibrary:
    """
    Library of predefined formations.
    """
    
    def __init__(self):
        """Initialize formation library with common formations."""
        self.formations = {}
        self._initialize_formations()
        
    def _initialize_formations(self) -> None:
        """Initialize standard formations."""
        # Line formation
        line = Formation("line", spacing=40.0)
        line.add_position(0, 0, "leader")
        line.add_position(-1, 0, "defender")
        line.add_position(1, 0, "attacker")
        line.add_position(-2, 0, "support")
        line.add_position(2, 0, "flanker")
        line.set_tactical_properties({
            'defensive': 0.5,
            'offensive': 0.5,
            'mobility': 0.8,
            'flexibility': 0.6
        })
        line.set_description("Simple line formation that's flexible and mobile")
        self.formations["line"] = line
        
        # Triangle formation
        triangle = Formation("triangle", spacing=50.0)
        triangle.add_position(0, 0, "leader")
        triangle.add_position(-1, 1, "defender")
        triangle.add_position(1, 1, "attacker")
        triangle.add_position(0, 2, "support")
        triangle.set_tactical_properties({
            'defensive': 0.7,
            'offensive': 0.6,
            'mobility': 0.7,
            'flexibility': 0.5
        })
        triangle.set_description("Balanced triangle formation with good defense")
        self.formations["triangle"] = triangle
        
        # Square formation
        square = Formation("square", spacing=45.0)
        square.add_position(-0.5, -0.5, "leader")
        square.add_position(0.5, -0.5, "attacker")
        square.add_position(-0.5, 0.5, "defender")
        square.add_position(0.5, 0.5, "support")
        square.set_tactical_properties({
            'defensive': 0.8,
            'offensive': 0.4,
            'mobility': 0.5,
            'flexibility': 0.4
        })
        square.set_description("Defensive square formation with strong resilience")
        self.formations["square"] = square
        
        # Arrow formation
        arrow = Formation("arrow", spacing=45.0)
        arrow.add_position(0, 0, "leader")
        arrow.add_position(-1, 1, "defender")
        arrow.add_position(1, 1, "attacker")
        arrow.add_position(-2, 2, "support")
        arrow.add_position(2, 2, "flanker")
        arrow.add_position(0, -1, "point")
        arrow.set_tactical_properties({
            'defensive': 0.4,
            'offensive': 0.8,
            'mobility': 0.6,
            'flexibility': 0.5
        })
        arrow.set_description("Offensive arrow formation ideal for attacks")
        self.formations["arrow"] = arrow
        
        # Circle formation
        circle = Formation("circle", spacing=50.0)
        circle.add_position(0, 0, "leader")
        circle.add_position(1, 0, "attacker")
        circle.add_position(0, 1, "defender")
        circle.add_position(-1, 0, "support")
        circle.add_position(0, -1, "flanker")
        circle.set_tactical_properties({
            'defensive': 0.9,
            'offensive': 0.3,
            'mobility': 0.4,
            'flexibility': 0.7
        })
        circle.set_description("Defensive circle formation that protects all sides")
        self.formations["circle"] = circle
        
    def get_formation(self, name: str) -> Optional[Formation]:
        """
        Get a formation by name.
        
        Args:
            name: Formation name
            
        Returns:
            Formation or None if not found
        """
        return self.formations.get(name)
    
    def get_formation_names(self) -> List[str]:
        """
        Get list of available formation names.
        
        Returns:
            List of formation names
        """
        return list(self.formations.keys())
    
    def get_best_formation(self, 
                        team_size: int, 
                        situation: str = "balanced") -> str:
        """
        Get best formation for the given situation.
        
        Args:
            team_size: Number of agents in the team
            situation: Combat situation ('defensive', 'offensive', 'mobile', etc.)
            
        Returns:
            Name of recommended formation
        """
        if team_size <= 2:
            return "line"  # Default for very small teams
            
        # Match situation to tactical properties
        property_map = {
            "defensive": "defensive",
            "offensive": "offensive",
            "mobile": "mobility",
            "flexible": "flexibility",
            "balanced": None  # Special case: balanced across all
        }
        
        property_name = property_map.get(situation)
        
        if property_name:
            # Find formation with highest value for this property
            best_formation = None
            best_value = -1
            
            for name, formation in self.formations.items():
                if len(formation.positions) >= team_size:
                    value = formation.tactical_properties[property_name]
                    if value > best_value:
                        best_value = value
                        best_formation = name
                        
            if best_formation:
                return best_formation
        else:
            # For "balanced", find formation with highest average property value
            best_formation = None
            best_avg = -1
            
            for name, formation in self.formations.items():
                if len(formation.positions) >= team_size:
                    props = formation.tactical_properties
                    avg = sum(props.values()) / len(props)
                    if avg > best_avg:
                        best_avg = avg
                        best_formation = name
                        
            if best_formation:
                return best_formation
        
        # Fallback: return first formation that can fit the team
        for name, formation in self.formations.items():
            if len(formation.positions) >= team_size:
                return name
                
        # Last resort
        return "line"

class FormationMovementSystem:
    """
    System for managing coordinated team movement in formations.
    
    Features:
    - Maintain team formations during movement
    - Calculate target positions for formation members
    - Adapt formations based on environment and threats
    - Score formation quality
    """
    
    def __init__(self):
        """Initialize formation movement system."""
        self.library = FormationLibrary()
        self.team_formations = {}  # team_id -> formation name
        self.team_positions = {}  # team_id -> list of agent positions
        self.team_centers = {}  # team_id -> (x, y) center position
        self.team_rotations = {}  # team_id -> rotation in radians
        self.team_targets = {}  # team_id -> target position
        self.team_spacing = {}  # team_id -> custom spacing
        
        self.agent_teams = {}  # agent_id -> team_id
        self.agent_indices = {}  # agent_id -> index in formation
        self.agent_roles = {}  # agent_id -> role in formation
        
        # Keep formation scores here, calculated within this system
        self.formation_scores = defaultdict(lambda: 0.0)  # team_id -> current formation score
        
        # Movement parameters
        self.default_spacing = 50.0
        self.formation_tolerance = 30.0  # How much deviation is allowed
        self.rotation_speed = 0.05  # Radians per update
        
        # --- ADDED: Morale/Suppression System Reference ---
        self._morale_suppression_system: Optional["MoraleSuppressionSystem"] = None
        # --------------------------------------------------

    # --- ADDED: Lazy loader property for MoraleSuppressionSystem ---
    @property
    def morale_suppression_system(self) -> Optional["MoraleSuppressionSystem"]:
        if self._morale_suppression_system is None:
            try:
                from systems.morale.morale_suppression_system import MoraleSuppressionSystem # Import here
            except ImportError:
                 logger.warning("FormationMovementSystem: MoraleSuppressionSystem not found/importable.")
                 return None
            self._morale_suppression_system = system_manager.get_system("morale_suppression_system")
            if not self._morale_suppression_system:
                 logger.warning("FormationMovementSystem: MoraleSuppressionSystem not found via system_manager.")
        return self._morale_suppression_system
    # ------------------------------------------------------------

    def register_team(self, 
                   team_id: str, 
                   initial_formation: str = "line",
                   center_position: Tuple[float, float] = (0, 0),
                   rotation: float = 0.0) -> None:
        """
        Register a team with the formation system.
        
        Args:
            team_id: Team ID
            initial_formation: Starting formation name
            center_position: Initial center position
            rotation: Initial rotation in radians
        """
        self.team_formations[team_id] = initial_formation
        self.team_centers[team_id] = center_position
        self.team_rotations[team_id] = rotation
        self.team_positions[team_id] = []
        self.team_spacing[team_id] = self.default_spacing
        
    def register_agent(self, 
                     agent_id: str, 
                     team_id: str,
                     position: Tuple[float, float],
                     role: Optional[str] = None,
                     index: Optional[int] = None) -> None:
        """
        Register an agent with the formation system.
        
        Args:
            agent_id: Agent ID
            team_id: Team the agent belongs to
            position: Current position
            role: Optional role in formation
            index: Optional index in formation
        """
        if team_id not in self.team_formations:
            self.register_team(team_id)
            
        self.agent_teams[agent_id] = team_id
        
        # Add position to team positions
        if team_id in self.team_positions:
            positions = self.team_positions[team_id]
            positions.append((agent_id, position))
            self.team_positions[team_id] = positions
            
            # If no index specified, use the position in the array
            if index is None:
                index = len(positions) - 1
        else:
            if index is None:
                index = 0
            self.team_positions[team_id] = [(agent_id, position)]
            
        self.agent_indices[agent_id] = index
        
        # Assign role if provided
        if role:
            self.agent_roles[agent_id] = role
    
    def update_agent_position(self, 
                           agent_id: str, 
                           position: Tuple[float, float]) -> None:
        """
        Update an agent's position.
        
        Args:
            agent_id: Agent ID
            position: New position
        """
        if agent_id not in self.agent_teams:
            return
            
        team_id = self.agent_teams[agent_id]
        
        if team_id in self.team_positions:
            positions = self.team_positions[team_id]
            # Find and update this agent's position
            for i, (aid, _) in enumerate(positions):
                if aid == agent_id:
                    positions[i] = (agent_id, position)
                    break
            else:
                # Agent not found, add
                positions.append((agent_id, position))
            
            self.team_positions[team_id] = positions
    
    def set_team_formation(self, 
                        team_id: str, 
                        formation_name: str) -> bool:
        """
        Set a team's formation.
        
        Args:
            team_id: Team ID
            formation_name: Name of formation to use
            
        Returns:
            True if successful
        """
        formation = self.library.get_formation(formation_name)
        if not formation:
            return False
            
        self.team_formations[team_id] = formation_name
        # ADDED: Re-assign roles when formation is set explicitly here? Or rely on TeamSystem?
        # Let's assume TeamSystem handles role assignment on change.
        return True
    
    def get_team_formation(self, team_id: str) -> Optional[str]:
        """
        Get the currently assigned formation name for a team.
        
        Args:
            team_id: The ID of the team.
            
        Returns:
            The formation name (str) or None if the team is not registered.
        """
        return self.team_formations.get(team_id)
    
    def update_team_center(self, team_id: str) -> Tuple[float, float]:
        """
        Update a team's center position based on member positions.
        
        Args:
            team_id: Team ID
            
        Returns:
            New center position
        """
        if team_id not in self.team_positions or not self.team_positions[team_id]:
            return (0, 0)
            
        positions = [pos for _, pos in self.team_positions[team_id]]
        
        if not positions:
            return (0, 0)
            
        # Calculate centroid
        x_sum = sum(p[0] for p in positions)
        y_sum = sum(p[1] for p in positions)
        center = (x_sum / len(positions), y_sum / len(positions))
        
        self.team_centers[team_id] = center
        return center
    
    def set_team_target(self, 
                     team_id: str, 
                     target: Tuple[float, float],
                     update_rotation: bool = True) -> None:
        """
        Set a team's target position.
        
        Args:
            team_id: Team ID
            target: Target position to move toward
            update_rotation: Whether to update rotation to face target
        """
        self.team_targets[team_id] = target
        
        if update_rotation and team_id in self.team_centers:
            center = self.team_centers[team_id]
            dx = target[0] - center[0]
            dy = target[1] - center[1]
            
            # Calculate rotation to face target
            if dx != 0 or dy != 0:
                rotation = math.atan2(dy, dx)
                
                # Smooth rotation change
                current_rot = self.team_rotations.get(team_id, 0.0)
                diff = (rotation - current_rot + math.pi) % (2 * math.pi) - math.pi
                
                # Limit rotation change to rotation_speed
                if abs(diff) > self.rotation_speed:
                    rotation = current_rot + self.rotation_speed * (1 if diff > 0 else -1)
                    
                self.team_rotations[team_id] = rotation
    
    def get_agent_target_position(self, agent_id: str) -> Optional[Tuple[float, float]]:
        """
        Get an agent's target position in the formation.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Target position or None if agent not found
        """
        if agent_id not in self.agent_teams:
            return None
            
        team_id = self.agent_teams[agent_id]
        
        if team_id not in self.team_formations:
            return None
            
        formation_name = self.team_formations[team_id]
        formation = self.library.get_formation(formation_name)
        
        if not formation:
            return None
            
        # Get team center and rotation
        center = self.team_centers.get(team_id, (0, 0))
        rotation = self.team_rotations.get(team_id, 0.0)
        spacing = self.team_spacing.get(team_id, self.default_spacing)
        
        # If agent has a role, use role position
        if agent_id in self.agent_roles:
            role = self.agent_roles[agent_id]
            position = formation.get_role_position(role, center[0], center[1], rotation)
            if position:
                return position
                
        # Otherwise use index position
        index = self.agent_indices.get(agent_id, 0)
        return formation.get_position_by_index(index, center[0], center[1], rotation)
    
    def get_formation_score(self, team_id: str) -> float:
        """
        Calculate how well a team is maintaining its formation.
        
        Args:
            team_id: Team ID
            
        Returns:
            Formation score (0.0-1.0, higher is better)
        """
        if team_id not in self.team_formations:
            return 0.0
            
        if team_id not in self.team_positions or not self.team_positions[team_id]:
            return 0.0
            
        formation_name = self.team_formations[team_id]
        formation = self.library.get_formation(formation_name)
        
        if not formation:
            return 0.0
            
        # Get team center
        center = self.team_centers.get(team_id, (0, 0))
        rotation = self.team_rotations.get(team_id, 0.0)
        
        # Get actual agent positions
        agent_positions = self.team_positions[team_id]
        num_agents = len(agent_positions)
        
        # Get target positions
        target_positions = formation.get_positions(
            center[0], center[1], num_agents, rotation
        )
        
        if len(target_positions) < num_agents:
            # Formation can't accommodate all agents
            return 0.0
            
        # Calculate error between actual and target positions
        total_error = 0.0
        for i, (agent_id, actual_pos) in enumerate(agent_positions):
            target_pos = None
            
            # Try to match by role first
            if agent_id in self.agent_roles:
                role = self.agent_roles[agent_id]
                target_pos = formation.get_role_position(
                    role, center[0], center[1], rotation
                )
                
            # If no role match, use index
            if not target_pos:
                index = self.agent_indices.get(agent_id, i)
                if index < len(target_positions):
                    target_pos = target_positions[index]
                    
            if target_pos:
                # Calculate distance to target position
                dx = actual_pos[0] - target_pos[0]
                dy = actual_pos[1] - target_pos[1]
                error = math.sqrt(dx*dx + dy*dy)
                total_error += error
        
        # Normalize error to 0-1 range
        max_error = self.formation_tolerance * num_agents
        normalized_error = min(1.0, total_error / max_error)
        
        # Invert so higher is better
        score = 1.0 - normalized_error

        # --- ADDED: Incorporate Morale --- #
        morale_modifier = 1.0
        if self.morale_suppression_system:
             member_ids = [aid for aid, _ in agent_positions]
             total_morale = 0.0
             valid_morale_count = 0
             for agent_id in member_ids:
                  morale = self.morale_suppression_system.get_morale(agent_id)
                  # Assuming morale is 0-1 where 0.5 is neutral
                  total_morale += morale
                  valid_morale_count += 1

             if valid_morale_count > 0:
                  avg_morale = total_morale / valid_morale_count
                  # Adjust score based on morale. High morale helps, low morale hinders.
                  # Example: Map avg_morale (0-1) to modifier (0.7 to 1.3)
                  morale_modifier = 0.7 + (avg_morale * 0.6)
                  score *= morale_modifier
             else:
                  logger.debug(f"Could not calculate morale modifier for team {team_id} score.")
        # ---------------------------------- #

        # Save score
        self.formation_scores[team_id] = score
        
        return score
    
    def update(self) -> None:
        """Update all teams' formations and positions."""
        for team_id in list(self.team_formations.keys()):
            # Update team center
            self.update_team_center(team_id)
            
            # Update rotation if team has a target
            if team_id in self.team_targets and team_id in self.team_centers:
                target = self.team_targets[team_id]
                center = self.team_centers[team_id]
                
                dx = target[0] - center[0]
                dy = target[1] - center[1]
                
                # Update rotation to face target if team is moving
                if dx*dx + dy*dy > 25:  # Only rotate if target is at least 5 units away
                    rotation = math.atan2(dy, dx)
                    current_rot = self.team_rotations.get(team_id, 0.0)
                    
                    # Normalize angle difference to -pi to pi
                    diff = (rotation - current_rot + math.pi) % (2 * math.pi) - math.pi
                    
                    # Apply smooth rotation with max rotation speed
                    if abs(diff) > self.rotation_speed:
                        new_rot = current_rot + self.rotation_speed * (1 if diff > 0 else -1)
                    else:
                        new_rot = rotation
                        
                    self.team_rotations[team_id] = new_rot
            
            # Calculate formation score (Moved calculation here)
            self.get_formation_score(team_id)
                
    def suggest_formation(self, 
                       team_id: str, 
                       context: Dict[str, Any]) -> Optional[str]:
        """
        Suggest a formation based on combat context.
        
        Args:
            team_id: Team ID
            context: Combat context (enemies, environment, etc.)
            
        Returns:
            Suggested formation name or None
        """
        if team_id not in self.team_positions:
            return None
            
        num_agents = len(self.team_positions[team_id])
        
        # Extract context information
        enemy_count = context.get('enemy_count', 0)
        under_attack = context.get('under_attack', False)
        open_terrain = context.get('open_terrain', True)
        
        # Determine situation
        situation = "balanced"
        
        if under_attack and enemy_count > num_agents:
            situation = "defensive"
        elif enemy_count > 0 and enemy_count <= num_agents:
            situation = "offensive"
        elif not open_terrain:
            situation = "mobile"
            
        return self.library.get_best_formation(num_agents, situation)
    
    def get_tactical_advantage(self, 
                            team_id: str, 
                            enemy_formation: str) -> float:
        """
        Calculate tactical advantage against another formation.
        
        Args:
            team_id: Team ID
            enemy_formation: Enemy formation name
            
        Returns:
            Advantage score (>1.0 means advantage, <1.0 means disadvantage)
        """
        if team_id not in self.team_formations:
            return 1.0
            
        our_formation = self.team_formations[team_id]
        our_form = self.library.get_formation(our_formation)
        enemy_form = self.library.get_formation(enemy_formation)
        
        if not our_form or not enemy_form:
            return 1.0
            
        # Compare tactical properties
        our_props = our_form.tactical_properties
        enemy_props = enemy_form.tactical_properties
        
        # Calculate rock-paper-scissors style advantages
        advantage = 1.0
        
        # Offensive vs defensive
        if our_props['offensive'] > enemy_props['defensive']:
            advantage += 0.2
        elif our_props['offensive'] < enemy_props['defensive']:
            advantage -= 0.1
            
        # Mobility vs offensive
        if our_props['mobility'] > enemy_props['offensive']:
            advantage += 0.1
        elif our_props['mobility'] < enemy_props['offensive']:
            advantage -= 0.1
            
        # Defensive vs mobility
        if our_props['defensive'] > enemy_props['mobility']:
            advantage += 0.1
        elif our_props['defensive'] < enemy_props['mobility']:
            advantage -= 0.1
            
        # Current formation score multiplier
        score = self.formation_scores.get(team_id, 0.7) # Use locally calculated score
        advantage *= (0.7 + score * 0.3)  # Score can affect up to 30% of advantage
        
        return advantage
    
    def adjust_spacing(self, 
                    team_id: str, 
                    spacing: float) -> None:
        """
        Adjust spacing for a team formation.
        
        Args:
            team_id: Team ID
            spacing: New spacing value
        """
        if team_id in self.team_formations:
            self.team_spacing[team_id] = max(20.0, min(100.0, spacing))
    
    def get_formation_stats(self, team_id: str) -> Dict[str, Any]:
        """
        Get statistics about a team's formation.
        
        Args:
            team_id: Team ID
            
        Returns:
            Dictionary with formation statistics
        """
        if team_id not in self.team_formations:
            return {}
            
        formation_name = self.team_formations[team_id]
        formation = self.library.get_formation(formation_name)
        
        if not formation:
            return {}
            
        return {
            'name': formation_name,
            'score': self.formation_scores.get(team_id, 0.0),
            'positions': len(self.team_positions.get(team_id, [])),
            'center': self.team_centers.get(team_id, (0, 0)),
            'rotation': self.team_rotations.get(team_id, 0.0),
            'properties': formation.tactical_properties.copy(),
            'description': formation.description
        } 