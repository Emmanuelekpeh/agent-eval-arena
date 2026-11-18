"""
Resource Sharing System for AI Battle Arena.

This module provides mechanisms for agents to share resources,
distribute energy, and coordinate resource gathering within teams.
"""

from typing import Dict, List, Tuple, Optional, Any, Set
from collections import defaultdict
import numpy as np
import math
import time

class ResourceType:
    """Defines available resource types in the game."""
    ENERGY = "energy"
    HEALTH = "health"
    SHIELD = "shield"
    AMMO = "ammo"
    SPECIAL = "special"

class ResourcePacket:
    """
    Represents a resource packet being transferred between agents.
    
    Attributes:
        resource_type: Type of resource being transferred
        amount: Amount of resource
        sender: ID of the agent sending the resource
        recipient: ID of the agent receiving the resource
        position: Current position of the packet
        destination: Target position (recipient location)
        speed: Speed at which the packet travels
        ttl: Time to live (seconds before packet expires)
    """
    
    def __init__(self, 
               resource_type: str, 
               amount: float,
               sender: str,
               recipient: str,
               position: Tuple[float, float],
               destination: Tuple[float, float],
               speed: float = 3.0,
               ttl: float = 5.0):
        """
        Initialize a resource packet.
        
        Args:
            resource_type: Type of resource being transferred
            amount: Amount of resource
            sender: ID of the agent sending the resource
            recipient: ID of the agent receiving the resource
            position: Current position of the packet
            destination: Target position (recipient location)
            speed: Speed at which the packet travels
            ttl: Time to live (seconds before packet expires)
        """
        self.resource_type = resource_type
        self.original_amount = amount
        self.amount = amount
        self.sender = sender
        self.recipient = recipient
        self.position = list(position)
        self.destination = destination
        self.speed = speed
        self.ttl = ttl
        self.creation_time = time.time()
        self.distance_traveled = 0.0
        self.color = self._get_resource_color(resource_type)
        
    def _get_resource_color(self, resource_type: str) -> Tuple[int, int, int]:
        """Get color based on resource type."""
        colors = {
            ResourceType.ENERGY: (0, 255, 255),  # Cyan for energy
            ResourceType.HEALTH: (0, 255, 0),    # Green for health
            ResourceType.SHIELD: (255, 255, 0),  # Yellow for shield
            ResourceType.AMMO: (255, 128, 0),    # Orange for ammo
            ResourceType.SPECIAL: (255, 0, 255)  # Magenta for special
        }
        return colors.get(resource_type, (255, 255, 255))
        
    def update(self) -> bool:
        """
        Update packet position towards destination.
        
        Returns:
            True if the packet has reached its destination, False otherwise
        """
        # Check if we've already arrived
        dx = self.destination[0] - self.position[0]
        dy = self.destination[1] - self.position[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance < 1.0:
            return True
            
        # Move towards destination
        direction = [dx/distance, dy/distance]
        movement = min(self.speed, distance)
        
        self.position[0] += direction[0] * movement
        self.position[1] += direction[1] * movement
        self.distance_traveled += movement
        
        # Reduce TTL
        self.ttl -= 0.016  # Assuming ~60 FPS
        
        return False
        
    def is_expired(self) -> bool:
        """Check if the packet has expired."""
        return self.ttl <= 0

class ResourceSharingSystem:
    """
    System for managing resource sharing between agents.
    
    This system handles resource transfers between agents, tracks team
    resources, and coordinates sharing of resources based on team needs.
    """
    
    def __init__(self):
        """Initialize the resource sharing system."""
        self.agent_resources = {}  # Map of agent_id -> resource dictionary
        self.agent_positions = {}  # Map of agent_id -> (x, y) position
        self.agent_teams = {}  # Map of agent_id -> team_id
        self.team_members = defaultdict(set)  # Map of team_id -> set of agent_ids
        self.active_transfers = []  # List of ResourcePacket objects
        self.resource_requests = []  # List of pending resource requests
        self.transfer_stats = defaultdict(int)  # Statistics on transfers
        self.transfer_efficiency = 0.8  # Efficiency multiplier (0-1)
        
    def register_agent(self, 
                     agent_id: str, 
                     team_id: str,
                     position: Tuple[float, float],
                     initial_resources: Optional[Dict[str, float]] = None) -> None:
        """
        Register an agent with the resource sharing system.
        
        Args:
            agent_id: Unique identifier for the agent
            team_id: Team identifier
            position: Initial position (x, y)
            initial_resources: Initial resource values
        """
        default_resources = {
            ResourceType.ENERGY: 100.0,
            ResourceType.HEALTH: 100.0,
            ResourceType.SHIELD: 50.0,
            ResourceType.AMMO: 50.0,
            ResourceType.SPECIAL: 0.0
        }
        
        self.agent_resources[agent_id] = initial_resources or default_resources
        self.agent_positions[agent_id] = position
        self.agent_teams[agent_id] = team_id
        self.team_members[team_id].add(agent_id)
        
    def update_agent_resources(self, 
                            agent_id: str, 
                            resources: Dict[str, float]) -> None:
        """
        Update an agent's resource levels.
        
        Args:
            agent_id: Agent identifier
            resources: Dictionary of resource values
        """
        if agent_id in self.agent_resources:
            self.agent_resources[agent_id].update(resources)
            
    def update_agent_position(self, 
                           agent_id: str, 
                           position: Tuple[float, float]) -> None:
        """
        Update an agent's position.
        
        Args:
            agent_id: Agent identifier
            position: New position (x, y)
        """
        self.agent_positions[agent_id] = position
        
        # Update destinations for any packets targeting this agent
        for packet in self.active_transfers:
            if packet.recipient == agent_id:
                packet.destination = position
            
    def update(self, delta_time: float = 0.0) -> Dict[str, List[Tuple[str, float]]]:
        """
        Update resource transfers and process resource requests.
        
        Returns:
            Dictionary mapping agent IDs to list of (resource_type, amount) received
        """
        received_resources = defaultdict(list)
        
        # Update active transfers
        for packet in self.active_transfers[:]:
            arrived = packet.update()
            
            if arrived:
                # Deliver the resource to the recipient
                if packet.recipient in self.agent_resources:
                    # Apply transfer efficiency
                    effective_amount = packet.amount * self.transfer_efficiency
                    
                    # Update recipient's resources
                    self.agent_resources[packet.recipient][packet.resource_type] += effective_amount
                    
                    # Record statistics
                    self.transfer_stats[packet.resource_type] += effective_amount
                    
                    # Record received resources
                    received_resources[packet.recipient].append(
                        (packet.resource_type, effective_amount)
                    )
                
                # Remove the packet
                self.active_transfers.remove(packet)
            elif packet.is_expired():
                # Packet expired before reaching destination
                self.active_transfers.remove(packet)
                
        # Process resource requests
        self._process_resource_requests()
                
        return dict(received_resources)
        
    def share_resource(self, 
                    sender_id: str, 
                    recipient_id: str, 
                    resource_type: str, 
                    amount: float) -> bool:
        """
        Share a resource from one agent to another.
        
        Args:
            sender_id: ID of the agent sending the resource
            recipient_id: ID of the agent receiving the resource
            resource_type: Type of resource to share
            amount: Amount of resource to share
            
        Returns:
            True if the resource was shared successfully, False otherwise
        """
        # Validate sender and recipient
        if (sender_id not in self.agent_resources or 
            recipient_id not in self.agent_resources):
            return False
        
        # Check if sender has enough of the resource
        if self.agent_resources[sender_id][resource_type] < amount:
            # Adjust amount to what's available
            amount = self.agent_resources[sender_id][resource_type]
            if amount <= 0:
                return False
                
        # Check if sender and recipient are close enough
        sender_pos = self.agent_positions[sender_id]
        recipient_pos = self.agent_positions[recipient_id]
        
        # Create a resource packet
        packet = ResourcePacket(
            resource_type=resource_type,
            amount=amount,
            sender=sender_id,
            recipient=recipient_id,
            position=sender_pos,
            destination=recipient_pos
        )
        
        # Deduct the resource from the sender
        self.agent_resources[sender_id][resource_type] -= amount
        
        # Add the packet to active transfers
        self.active_transfers.append(packet)
        return True
        
    def auto_distribute_resources(self, team_id: str) -> int:
        """
        Automatically distribute resources within a team based on need.
        
        Args:
            team_id: Team identifier
            
        Returns:
            Number of resource transfers initiated
        """
        if team_id not in self.team_members:
            return 0
            
        team_agents = list(self.team_members[team_id])
        if len(team_agents) <= 1:
            return 0
            
        transfers_initiated = 0
        
        # For each resource type, calculate average level across team
        for resource_type in [ResourceType.ENERGY, ResourceType.HEALTH, 
                             ResourceType.SHIELD, ResourceType.AMMO]:
            # Calculate average level
            total = sum(self.agent_resources[agent_id][resource_type] 
                      for agent_id in team_agents)
            average = total / len(team_agents)
            
            # Find agents with excess resources
            donors = []
            for agent_id in team_agents:
                level = self.agent_resources[agent_id][resource_type]
                if level > average * 1.2:  # 20% above average
                    excess = level - average
                    donors.append((agent_id, excess))
            
            # Find agents in need
            recipients = []
            for agent_id in team_agents:
                level = self.agent_resources[agent_id][resource_type]
                if level < average * 0.8:  # 20% below average
                    deficit = average - level
                    recipients.append((agent_id, deficit))
            
            # Sort donors and recipients by excess/deficit
            donors.sort(key=lambda x: x[1], reverse=True)
            recipients.sort(key=lambda x: x[1], reverse=True)
            
            # Match donors with recipients
            for donor_id, excess in donors:
                for recipient_id, deficit in recipients[:]:
                    # Skip if donor and recipient are the same
                    if donor_id == recipient_id:
                        continue
                        
                    # Calculate amount to share
                    amount = min(excess, deficit)
                    if amount < 1.0:
                        continue
                        
                    # Share resource
                    success = self.share_resource(
                        donor_id, recipient_id, resource_type, amount
                    )
                    
                    if success:
                        transfers_initiated += 1
                        excess -= amount
                        
                        # Update recipient's deficit
                        recipients = [(r_id, r_deficit - amount) 
                                     if r_id == recipient_id else (r_id, r_deficit)
                                     for r_id, r_deficit in recipients]
                        
                        # Stop if donor has shared all excess
                        if excess < 1.0:
                            break
                            
        return transfers_initiated
        
    def request_resource(self, 
                      requester_id: str, 
                      resource_type: str,
                      amount: float) -> bool:
        """
        Request a resource from team members.
        
        Args:
            requester_id: ID of the agent requesting the resource
            resource_type: Type of resource requested
            amount: Amount of resource requested
            
        Returns:
            True if the request was successful, False otherwise
        """
        # Validate requester
        if requester_id not in self.agent_teams:
            return False
            
        team_id = self.agent_teams[requester_id]
        team_members = self.team_members[team_id]
        
        # Create request
        request = {
            'requester_id': requester_id,
            'resource_type': resource_type,
            'amount': amount,
            'team_id': team_id,
            'timestamp': time.time(),
            'urgency': 1.0  # Default urgency level
        }
        
        # Add request to queue
        self.resource_requests.append(request)
        return True
        
    def _process_resource_requests(self) -> None:
        """Process pending resource requests."""
        if not self.resource_requests:
            return
            
        # Process requests oldest first
        self.resource_requests.sort(key=lambda x: x['timestamp'])
        
        # Process each request
        for request in self.resource_requests[:]:
            requester_id = request['requester_id']
            resource_type = request['resource_type']
            amount = request['amount']
            team_id = request['team_id']
            
            # Skip if requester no longer exists
            if requester_id not in self.agent_resources:
                self.resource_requests.remove(request)
                continue
                
            # Find potential donors in the team
            donors = []
            for agent_id in self.team_members[team_id]:
                # Skip requester
                if agent_id == requester_id:
                    continue
                    
                # Calculate available amount
                available = self.agent_resources[agent_id][resource_type]
                surplus = available - 50.0  # Ensure donor keeps at least 50
                
                if surplus > 0:
                    donors.append((agent_id, surplus))
            
            # Sort donors by surplus
            donors.sort(key=lambda x: x[1], reverse=True)
            
            # Try to fulfill request
            fulfilled = 0
            for donor_id, surplus in donors:
                share_amount = min(surplus, amount - fulfilled)
                if share_amount <= 0:
                    continue
                    
                success = self.share_resource(
                    donor_id, requester_id, resource_type, share_amount
                )
                
                if success:
                    fulfilled += share_amount
                    
                # Stop if request is fulfilled
                if fulfilled >= amount:
                    break
            
            # Remove request if fulfilled or too old
            if fulfilled >= amount or (time.time() - request['timestamp']) > 10.0:
                self.resource_requests.remove(request)
                
    def collect_resource(self, 
                      agent_id: str, 
                      resource_type: str,
                      amount: float,
                      share_with_team: bool = True) -> None:
        """
        Record resource collection by an agent and optionally share with team.
        
        Args:
            agent_id: ID of the agent collecting the resource
            resource_type: Type of resource collected
            amount: Amount of resource collected
            share_with_team: Whether to share with team members
        """
        # Validate agent
        if agent_id not in self.agent_resources:
            return
            
        # Add resource to agent
        self.agent_resources[agent_id][resource_type] += amount
        
        # Check if we should share with team
        if share_with_team and resource_type in [ResourceType.ENERGY, ResourceType.SPECIAL]:
            team_id = self.agent_teams.get(agent_id)
            if not team_id:
                return
                
            team_members = list(self.team_members[team_id])
            if len(team_members) <= 1:
                return
                
            # Share 20% of collected amount with team
            share_amount = amount * 0.2
            per_member = share_amount / (len(team_members) - 1)
            
            for member_id in team_members:
                if member_id != agent_id:
                    self.share_resource(
                        agent_id, member_id, resource_type, per_member
                    )
                    
    def calculate_team_resources(self, team_id: str) -> Dict[str, float]:
        """
        Calculate total resources available to a team.
        
        Args:
            team_id: Team identifier
            
        Returns:
            Dictionary of resource totals by type
        """
        if team_id not in self.team_members:
            return {}
            
        totals = defaultdict(float)
        
        for agent_id in self.team_members[team_id]:
            for res_type, amount in self.agent_resources[agent_id].items():
                totals[res_type] += amount
                
        return dict(totals)
        
    def get_sharing_stats(self) -> Dict[str, Any]:
        """
        Get statistics about resource sharing.
        
        Returns:
            Dictionary of sharing statistics
        """
        stats = {
            'total_transfers': sum(self.transfer_stats.values()),
            'transfers_by_type': dict(self.transfer_stats),
            'active_transfers': len(self.active_transfers),
            'pending_requests': len(self.resource_requests),
            'efficiency': self.transfer_efficiency,
            'team_resources': {
                team_id: self.calculate_team_resources(team_id)
                for team_id in self.team_members
            }
        }
        
        return stats
        
    def set_transfer_efficiency(self, efficiency: float) -> None:
        """
        Set the efficiency of resource transfers.
        
        Args:
            efficiency: Efficiency multiplier (0-1)
        """
        self.transfer_efficiency = max(0.0, min(1.0, efficiency))
        
    def get_agent_resources(self, agent_id: str) -> Dict[str, float]:
        """
        Get the current resources for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Dictionary of resource values by type
        """
        return self.agent_resources.get(agent_id, {})

class ResourceNeed:
    """
    Represents a team's need for a specific resource.
    
    Attributes:
        agent_id: Agent that needs the resource
        resource_type: Type of resource needed
        amount: Amount of resource needed
        urgency: How urgent the need is (0-1)
        position: Position of the agent
    """
    
    def __init__(self, 
               agent_id: str, 
               resource_type: str,
               amount: float,
               urgency: float,
               position: Tuple[float, float]):
        """
        Initialize a resource need.
        
        Args:
            agent_id: Agent that needs the resource
            resource_type: Type of resource needed
            amount: Amount of resource needed
            urgency: How urgent the need is (0-1)
            position: Position of the agent
        """
        self.agent_id = agent_id
        self.resource_type = resource_type
        self.amount = amount
        self.urgency = urgency
        self.position = position
        self.timestamp = time.time()
        self.assigned_gatherer = None
        
    def get_priority_score(self) -> float:
        """
        Calculate priority score for this need.
        
        Returns:
            Priority score (higher = more important)
        """
        age_factor = max(0.0, 1.0 - (time.time() - self.timestamp) / 30.0)
        return self.urgency * (self.amount / 100.0) * age_factor

class TeamResourceCoordinator:
    """
    Coordinates resource gathering and distribution within a team.
    
    This class manages which agents should gather resources and which
    should receive them based on team needs and priorities.
    """
    
    def __init__(self, resource_system: ResourceSharingSystem):
        """
        Initialize team resource coordinator.
        
        Args:
            resource_system: Reference to the resource sharing system
        """
        self.resource_system = resource_system
        self.resource_needs = []  # List of ResourceNeed objects
        self.resource_locations = []  # List of known resource locations
        self.gatherer_assignments = {}  # Map of agent_id -> assignment details
        
    def register_resource_need(self, 
                            agent_id: str, 
                            resource_type: str,
                            amount: float,
                            urgency: float) -> None:
        """
        Register a need for a resource by an agent.
        
        Args:
            agent_id: Agent that needs the resource
            resource_type: Type of resource needed
            amount: Amount of resource needed
            urgency: How urgent the need is (0-1)
        """
        # Get agent's position
        position = self.resource_system.agent_positions.get(agent_id)
        if not position:
            return
            
        # Create need object
        need = ResourceNeed(
            agent_id, resource_type, amount, urgency, position
        )
        
        # Add to list
        self.resource_needs.append(need)
        
        # Try to assign a gatherer immediately
        self._assign_gatherer(need)
        
    def register_resource_location(self, 
                               position: Tuple[float, float],
                               resource_type: str) -> None:
        """
        Register a known resource location.
        
        Args:
            position: Position of the resource
            resource_type: Type of resource at this location
        """
        self.resource_locations.append({
            'position': position,
            'type': resource_type,
            'timestamp': time.time()
        })
        
    def update(self) -> None:
        """Update resource coordination."""
        # Remove old needs and locations
        current_time = time.time()
        
        # Clean up old resource needs
        self.resource_needs = [need for need in self.resource_needs
                             if (current_time - need.timestamp) < 60.0]
        
        # Clean up old resource locations
        self.resource_locations = [loc for loc in self.resource_locations
                                 if (current_time - loc['timestamp']) < 120.0]
        
        # Reassign gatherers for unassigned needs
        for need in self.resource_needs:
            if not need.assigned_gatherer:
                self._assign_gatherer(need)
                
    def _assign_gatherer(self, need: ResourceNeed) -> None:
        """
        Assign an agent to gather resources for this need.
        
        Args:
            need: Resource need to assign a gatherer for
        """
        team_id = self.resource_system.agent_teams.get(need.agent_id)
        if not team_id:
            return
            
        # Find all team members who aren't already assigned
        team_members = self.resource_system.team_members[team_id]
        available_agents = [agent_id for agent_id in team_members
                          if agent_id != need.agent_id
                          and agent_id not in self.gatherer_assignments]
        
        if not available_agents:
            return
            
        # Find nearest available resource of the needed type
        nearest_resource = None
        nearest_distance = float('inf')
        
        for loc in self.resource_locations:
            if loc['type'] == need.resource_type:
                dist = math.sqrt(
                    (loc['position'][0] - need.position[0])**2 +
                    (loc['position'][1] - need.position[1])**2
                )
                if dist < nearest_distance:
                    nearest_distance = dist
                    nearest_resource = loc
        
        if not nearest_resource:
            return
            
        # Find the agent closest to the resource
        closest_agent = None
        closest_distance = float('inf')
        
        for agent_id in available_agents:
            agent_pos = self.resource_system.agent_positions.get(agent_id)
            if not agent_pos:
                continue
                
            dist = math.sqrt(
                (agent_pos[0] - nearest_resource['position'][0])**2 +
                (agent_pos[1] - nearest_resource['position'][1])**2
            )
            if dist < closest_distance:
                closest_distance = dist
                closest_agent = agent_id
        
        if not closest_agent:
            return
            
        # Assign gatherer
        self.gatherer_assignments[closest_agent] = {
            'need': need,
            'resource_location': nearest_resource['position'],
            'timestamp': time.time()
        }
        
        need.assigned_gatherer = closest_agent
        
    def get_agent_assignment(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current resource gathering assignment for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Assignment details or None if not assigned
        """
        return self.gatherer_assignments.get(agent_id)
        
    def complete_assignment(self, agent_id: str) -> None:
        """
        Mark an agent's assignment as completed.
        
        Args:
            agent_id: Agent identifier
        """
        if agent_id in self.gatherer_assignments:
            # Remove assignment
            assignment = self.gatherer_assignments.pop(agent_id)
            
            # Clear assigned gatherer from need
            need = assignment.get('need')
            if need and need.assigned_gatherer == agent_id:
                need.assigned_gatherer = None 