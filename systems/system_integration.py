"""
System Integration Module for AI Battle Arena.

This module connects various systems to enable interaction between them,
particularly focusing on integrating communication and resource sharing.
"""

from typing import Dict, Any, List, Optional, Tuple
import time

from systems.agents.communication_system import (
    CommunicationSystem, MessageType, MessagePriority, 
    AgentCommands, CommunicationInterpreter
)
from systems.environment.resource_sharing import (
    ResourceSharingSystem, ResourceType, ResourcePacket,
    TeamResourceCoordinator
)
from systems.agents.relationship_system import RelationshipSystem, RelationshipFactor

class SystemIntegration:
    """
    Integrates various systems to enable cross-system interactions.
    
    This class serves as the glue between different systems, allowing
    them to work together seamlessly. It particularly focuses on connecting
    communication, resource sharing, and relationship systems.
    """
    
    def __init__(self, 
                comm_system: CommunicationSystem,
                resource_system: ResourceSharingSystem,
                relationship_system: Optional[RelationshipSystem] = None):
        """
        Initialize the system integration module.
        
        Args:
            comm_system: Communication system instance
            resource_system: Resource sharing system instance
            relationship_system: Relationship system instance (optional)
        """
        self.comm_system = comm_system
        self.resource_system = resource_system
        self.relationship_system = relationship_system
        
        # Set up message handlers
        self.comm_interpreter = CommunicationInterpreter(comm_system)
        
        # Track pending resource requests for coordination
        self.pending_resource_requests = {}  # msg_id -> request details
        
        # Resource coordinator
        self.resource_coordinator = TeamResourceCoordinator(resource_system)
        
    def register_agent(self, 
                      agent_id: str, 
                      team_id: str,
                      position: Tuple[float, float],
                      initial_resources: Optional[Dict[str, float]] = None) -> None:
        """
        Register an agent with all relevant systems.
        
        Args:
            agent_id: Agent identifier
            team_id: Team identifier
            position: Initial agent position
            initial_resources: Initial resource values
        """
        # Register with communication system
        self.comm_system.register_agent(agent_id, team_id)
        
        # Register with resource sharing system
        self.resource_system.register_agent(
            agent_id, team_id, position, initial_resources
        )
        
        # Register with relationship system if available
        if self.relationship_system:
            self.relationship_system.register_agent(agent_id, team_id)
            
    def update(self, agent_states: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Update all systems and process cross-system interactions.
        
        Args:
            agent_states: Current states of all agents
            
        Returns:
            Dictionary of suggested actions for each agent
        """
        # Process resource transfers
        received_resources = self.resource_system.update()
        
        # Process communication
        self.comm_system.update()
        
        # Update relationship system if available
        if self.relationship_system:
            # This would generally happen elsewhere but included here for completeness
            pass
            
        # Process resource sharing based on communication
        self._process_resource_communication(agent_states)
        
        # Process automatic resource distribution
        for team_id in self.resource_system.team_members:
            self.resource_system.auto_distribute_resources(team_id)
            
        # Update resource coordinator
        self.resource_coordinator.update()
        
        # Build suggested actions for each agent
        suggested_actions = {}
        
        for agent_id, state in agent_states.items():
            # Update agent position in resource system
            if 'position' in state:
                self.resource_system.update_agent_position(agent_id, state['position'])
            
            # Get communication-based actions
            comm_actions = self.comm_interpreter.process_messages(agent_id, state)
            
            # Process resource receipt notifications
            if agent_id in received_resources:
                for resource_type, amount in received_resources[agent_id]:
                    # Send thank you message if we know who sent it
                    for packet in self.resource_system.active_transfers:
                        if (packet.recipient == agent_id and 
                            packet.resource_type == resource_type):
                            self._send_acknowledgment(
                                agent_id, packet.sender, resource_type, amount
                            )
                            
                            # Update relationship if system is available
                            if self.relationship_system:
                                self.relationship_system.update_relationship(
                                    agent_id, packet.sender,
                                    RelationshipFactor.RESOURCE_SHARING, 
                                    min(10.0, amount * 0.1)  # Scale impact by amount
                                )
            
            # Combine all suggested actions
            suggested_actions[agent_id] = comm_actions
            
        return suggested_actions
    
    def _process_resource_communication(self, agent_states: Dict[str, Dict[str, Any]]) -> None:
        """
        Process communication related to resource sharing.
        
        Args:
            agent_states: Current states of all agents
        """
        # Check for resource offers that haven't been fulfilled
        for request_id, request_data in list(self.comm_system.pending_responses.items()):
            request = request_data['request']
            
            # Only handle resource requests
            if (request.message_type != MessageType.REQUEST or
                request.content.get('request') != 'resource'):
                continue
                
            # Check if request has responses with offers
            for response in request_data['responses']:
                if response.content.get('response') == 'resource_offer':
                    resource_type = response.content.get('resource_type')
                    amount = response.content.get('amount', 0)
                    sender_id = response.sender_id
                    recipient_id = response.recipient_id
                    
                    # Verify both agents exist and have positions
                    if (sender_id in self.resource_system.agent_positions and 
                        recipient_id in self.resource_system.agent_positions):
                        
                        # Initiate resource transfer
                        success = self.resource_system.share_resource(
                            sender_id, recipient_id, resource_type, amount
                        )
                        
                        if success:
                            # Mark request as fulfilled
                            self.comm_system.mark_request_fulfilled(request_id)
                            
                            # Update relationship if available
                            if self.relationship_system:
                                self.relationship_system.update_relationship(
                                    sender_id, recipient_id,
                                    RelationshipFactor.RESOURCE_SHARING, 
                                    min(10.0, amount * 0.1)  # Scale impact by amount
                                )
    
    def request_resource(self, 
                       requester_id: str, 
                       resource_type: str,
                       amount: float,
                       urgency: float = 1.0) -> str:
        """
        Request a resource from team members.
        
        Args:
            requester_id: Agent requesting the resource
            resource_type: Type of resource needed
            amount: Amount needed
            urgency: How urgent the need is (0-1)
            
        Returns:
            ID of the sent message
        """
        # Register need with resource coordinator
        self.resource_coordinator.register_resource_need(
            requester_id, resource_type, amount, urgency
        )
        
        # Create request content
        content = AgentCommands.request_resource(resource_type, amount)
        content['urgency'] = urgency
        
        # Determine priority based on urgency
        priority = MessagePriority.MEDIUM
        if urgency > 0.7:
            priority = MessagePriority.HIGH
        elif urgency > 0.9:
            priority = MessagePriority.URGENT
            
        # Send team broadcast
        msg_id = self.comm_system.broadcast_to_team(
            sender_id=requester_id,
            message_type=MessageType.REQUEST,
            content=content,
            priority=priority
        )
        
        # Also try direct request through resource system
        self.resource_system.request_resource(
            requester_id, resource_type, amount
        )
        
        return msg_id
    
    def report_resource_location(self, 
                               reporter_id: str, 
                               resource_type: str,
                               position: Tuple[float, float],
                               amount: float = 100.0) -> str:
        """
        Report a resource location to team members.
        
        Args:
            reporter_id: Agent reporting the resource
            resource_type: Type of resource
            position: Position of the resource
            amount: Estimated amount available
            
        Returns:
            ID of the sent message
        """
        # Register with resource coordinator
        self.resource_coordinator.register_resource_location(
            position, resource_type
        )
        
        # Create report content
        content = AgentCommands.report_resource(
            resource_type, position, amount
        )
        
        # Share with team
        return self.comm_system.broadcast_to_team(
            sender_id=reporter_id,
            message_type=MessageType.INFORM,
            content=content
        )
    
    def _send_acknowledgment(self, 
                           receiver_id: str, 
                           sender_id: str,
                           resource_type: str,
                           amount: float) -> None:
        """
        Send acknowledgment for received resources.
        
        Args:
            receiver_id: Agent who received the resource
            sender_id: Agent who sent the resource
            resource_type: Type of resource received
            amount: Amount received
        """
        content = {
            'response': 'resource_received',
            'resource_type': resource_type,
            'amount': amount,
            'message': 'Thank you for the resources!'
        }
        
        self.comm_system.send_message(
            sender_id=receiver_id,
            recipient_id=sender_id,
            message_type=MessageType.RESPONSE,
            content=content
        )
    
    def suggest_resource_gathering(self, 
                                 team_id: str,
                                 leader_id: str) -> Optional[Dict[str, Any]]:
        """
        Suggest resource gathering coordination for a team.
        
        Args:
            team_id: Team identifier
            leader_id: Team leader agent ID
            
        Returns:
            Suggested coordination plan if needed
        """
        # Calculate team resource levels
        team_resources = self.resource_system.calculate_team_resources(team_id)
        
        # Identify most needed resource
        needed_resource = None
        lowest_level = float('inf')
        
        for res_type, amount in team_resources.items():
            per_agent = amount / len(self.resource_system.team_members[team_id])
            if per_agent < lowest_level:
                lowest_level = per_agent
                needed_resource = res_type
                
        if not needed_resource or lowest_level > 50:
            return None  # No critical resource needs
            
        # Check if any agent has an assignment to gather this resource
        for agent_id in self.resource_system.team_members[team_id]:
            assignment = self.resource_coordinator.get_agent_assignment(agent_id)
            if (assignment and 
                assignment.get('need') and 
                assignment['need'].resource_type == needed_resource):
                return None  # Someone is already assigned
                
        # Suggest coordination to gather this resource
        return {
            'action': 'coordinate_gathering',
            'resource_type': needed_resource,
            'team_id': team_id,
            'priority': 1 if lowest_level < 20 else 0.5
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics from all systems.
        
        Returns:
            Combined statistics dictionary
        """
        stats = {
            'communication': self.comm_system.get_communication_stats(),
            'resource_sharing': self.resource_system.get_sharing_stats()
        }
        
        if self.relationship_system:
            stats['relationships'] = self.relationship_system.get_relationship_stats()
            
        # Add integration-specific stats
        stats['integration'] = {
            'pending_resource_requests': len(self.pending_resource_requests),
            'cross_system_events': {
                'resource_messages_processed': sum(1 for req in self.comm_system.pending_responses.values() 
                                               if req['request'].content.get('request') == 'resource')
            }
        }
        
        return stats 