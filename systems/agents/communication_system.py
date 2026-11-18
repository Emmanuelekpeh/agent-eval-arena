"""
Communication System for AI Battle Arena.

This module provides mechanisms for agents to communicate with each other,
enabling coordination, information sharing, and team-based decision making.
"""

import time
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict, deque
import math

class MessageType(Enum):
    """Types of messages that agents can exchange."""
    INFORM = "inform"           # Sharing information
    REQUEST = "request"         # Asking for something
    COMMAND = "command"         # Directing other agents
    RESPONSE = "response"       # Responding to a request
    ALERT = "alert"             # Warning about danger
    COORDINATE = "coordinate"   # Coordinating actions

class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    URGENT = 3

class Message:
    """
    Represents a communication message between agents.
    
    Attributes:
        sender_id: ID of the sending agent
        recipient_id: ID of the receiving agent (or team ID for broadcasts)
        message_type: Type of message (inform, request, etc.)
        content: The message content (dictionary with details)
        priority: Message priority level
        timestamp: When the message was created
        expiration: When the message expires (seconds)
        is_team_message: Whether the message is for the whole team
    """
    
    def __init__(self, 
                sender_id: str, 
                recipient_id: str, 
                message_type: MessageType,
                content: Dict[str, Any],
                priority: MessagePriority = MessagePriority.MEDIUM,
                expiration: float = 5.0,
                is_team_message: bool = False):
        """
        Initialize a new message.
        
        Args:
            sender_id: ID of the sending agent
            recipient_id: ID of the receiving agent or team
            message_type: Type of message
            content: Message content (dictionary)
            priority: Priority level
            expiration: Time until message expires (seconds)
            is_team_message: Whether message is for whole team
        """
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.message_type = message_type
        self.content = content
        self.priority = priority
        self.timestamp = time.time()
        self.expiration = expiration
        self.is_team_message = is_team_message
        self.id = f"{sender_id}_{recipient_id}_{int(self.timestamp * 1000)}"
        self.read_by = set()  # IDs of agents who have read the message
        self.responses = []   # List of response messages
        
    def is_expired(self) -> bool:
        """Check if the message has expired."""
        return (time.time() - self.timestamp) > self.expiration
    
    def mark_as_read(self, agent_id: str) -> None:
        """Mark the message as read by an agent."""
        self.read_by.add(agent_id)
    
    def add_response(self, response: 'Message') -> None:
        """Add a response to this message."""
        self.responses.append(response)
        
    def get_age(self) -> float:
        """Get the age of the message in seconds."""
        return time.time() - self.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'message_type': self.message_type.value,
            'content': self.content,
            'priority': self.priority.value,
            'timestamp': self.timestamp,
            'expiration': self.expiration,
            'is_team_message': self.is_team_message,
            'read_by': list(self.read_by)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        msg = cls(
            sender_id=data['sender_id'],
            recipient_id=data['recipient_id'],
            message_type=MessageType(data['message_type']),
            content=data['content'],
            priority=MessagePriority(data['priority']),
            expiration=data['expiration'],
            is_team_message=data['is_team_message']
        )
        msg.id = data['id']
        msg.timestamp = data['timestamp']
        msg.read_by = set(data['read_by'])
        return msg

class CommunicationChannel:
    """
    Represents a communication channel between agents.
    
    Attributes:
        channel_id: Unique identifier for the channel
        members: Set of agent IDs in this channel
        messages: Queue of messages in the channel
        channel_type: Type of channel (team, direct, etc.)
    """
    
    def __init__(self, 
                channel_id: str, 
                members: Set[str], 
                channel_type: str = "team"):
        """
        Initialize a communication channel.
        
        Args:
            channel_id: Unique identifier
            members: Set of agent IDs
            channel_type: Type of channel
        """
        self.channel_id = channel_id
        self.members = members
        self.messages = deque(maxlen=100)  # Store last 100 messages
        self.channel_type = channel_type
        self.created_at = time.time()
        self.active = True
        
    def add_message(self, message: Message) -> None:
        """Add a message to the channel."""
        self.messages.append(message)
        
    def get_messages(self, 
                    agent_id: str, 
                    unread_only: bool = False, 
                    since_timestamp: Optional[float] = None) -> List[Message]:
        """
        Get messages from the channel.
        
        Args:
            agent_id: ID of the agent retrieving messages
            unread_only: Whether to get only unread messages
            since_timestamp: Only get messages after this time
            
        Returns:
            List of Message objects
        """
        result = []
        
        for message in self.messages:
            # Skip expired messages
            if message.is_expired():
                continue
                
            # Skip messages from before timestamp
            if since_timestamp and message.timestamp < since_timestamp:
                continue
                
            # Skip read messages if only wanting unread
            if unread_only and agent_id in message.read_by:
                continue
                
            result.append(message)
            
        return result
    
    def add_member(self, agent_id: str) -> None:
        """Add a member to the channel."""
        self.members.add(agent_id)
        
    def remove_member(self, agent_id: str) -> None:
        """Remove a member from the channel."""
        if agent_id in self.members:
            self.members.remove(agent_id)
            
    def is_active(self) -> bool:
        """Check if the channel is active (has members)."""
        return self.active and len(self.members) > 0

class CommunicationSystem:
    """
    System for managing agent communication.
    
    This system handles message passing between agents, maintains
    communication channels, and processes communication patterns.
    """
    
    def __init__(self):
        """Initialize the communication system."""
        self.channels = {}  # Map of channel_id -> CommunicationChannel
        self.agent_teams = {}  # Map of agent_id -> team_id
        self.team_channels = {}  # Map of team_id -> channel_id
        self.direct_channels = {}  # Map of (agent1, agent2) -> channel_id
        
        self.message_history = {}  # Map of message_id -> Message
        self.pending_responses = {}  # Map of request_id -> pending response info
        
        # Reliability settings
        self.transmission_reliability = 0.95  # Chance message is transmitted
        self.noise_factor = 0.05  # Chance of message corruption
        
        # Analysis data
        self.communication_stats = defaultdict(int)
        self.agent_activity = defaultdict(int)
        
    def register_agent(self, 
                      agent_id: str, 
                      team_id: Optional[str] = None) -> None:
        """
        Register an agent with the communication system.
        
        Args:
            agent_id: Unique identifier for the agent
            team_id: Team identifier (if agent belongs to a team)
        """
        if team_id:
            self.agent_teams[agent_id] = team_id
            
            # Add agent to team channel or create one
            if team_id in self.team_channels:
                channel_id = self.team_channels[team_id]
                self.channels[channel_id].add_member(agent_id)
            else:
                channel_id = f"team_{team_id}"
                self.channels[channel_id] = CommunicationChannel(
                    channel_id=channel_id,
                    members={agent_id},
                    channel_type="team"
                )
                self.team_channels[team_id] = channel_id
                
    def send_message(self, 
                    sender_id: str, 
                    recipient_id: str, 
                    message_type: MessageType,
                    content: Dict[str, Any],
                    priority: MessagePriority = MessagePriority.MEDIUM,
                    expiration: float = 5.0) -> Optional[str]:
        """
        Send a message from one agent to another or to a team.
        
        Args:
            sender_id: ID of the sending agent
            recipient_id: ID of the receiving agent or team
            message_type: Type of message
            content: Message content
            priority: Priority level
            expiration: Time until message expires (seconds)
            
        Returns:
            Message ID if sent successfully, None otherwise
        """
        # Check if sender is registered
        if sender_id not in self.agent_teams:
            return None
            
        is_team_message = recipient_id in self.team_channels
        
        # Create the message
        message = Message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content,
            priority=priority,
            expiration=expiration,
            is_team_message=is_team_message
        )
        
        # Apply transmission reliability
        if self._simulate_transmission(sender_id, recipient_id, priority):
            # Store in history
            self.message_history[message.id] = message
            
            # Add to appropriate channel
            if is_team_message:
                channel_id = self.team_channels[recipient_id]
                self.channels[channel_id].add_message(message)
            else:
                # Get or create direct channel
                channel_key = tuple(sorted([sender_id, recipient_id]))
                if channel_key not in self.direct_channels:
                    channel_id = f"direct_{sender_id}_{recipient_id}"
                    self.channels[channel_id] = CommunicationChannel(
                        channel_id=channel_id,
                        members={sender_id, recipient_id},
                        channel_type="direct"
                    )
                    self.direct_channels[channel_key] = channel_id
                else:
                    channel_id = self.direct_channels[channel_key]
                    
                self.channels[channel_id].add_message(message)
            
            # Update stats
            self.communication_stats[message_type.value] += 1
            self.agent_activity[sender_id] += 1
            
            # If it's a request, track for pending response
            if message_type == MessageType.REQUEST:
                self.pending_responses[message.id] = {
                    'request': message,
                    'responses': [],
                    'fulfilled': False
                }
                
            return message.id
            
        return None
        
    def _simulate_transmission(self, 
                             sender_id: str, 
                             recipient_id: str,
                             priority: MessagePriority) -> bool:
        """
        Simulate message transmission with potential failures.
        
        Args:
            sender_id: ID of the sending agent
            recipient_id: ID of the receiving agent or team
            priority: Message priority
            
        Returns:
            True if transmission succeeds, False otherwise
        """
        import random
        
        # Higher priority messages are more likely to be transmitted
        reliability = self.transmission_reliability
        if priority == MessagePriority.HIGH:
            reliability += 0.03
        elif priority == MessagePriority.URGENT:
            reliability += 0.05
            
        return random.random() < reliability
    
    def get_messages(self, 
                    agent_id: str, 
                    unread_only: bool = False, 
                    since_timestamp: Optional[float] = None) -> List[Message]:
        """
        Get messages for an agent from all channels.
        
        Args:
            agent_id: ID of the agent retrieving messages
            unread_only: Whether to get only unread messages
            since_timestamp: Only get messages after this time
            
        Returns:
            List of Message objects
        """
        if agent_id not in self.agent_teams:
            return []
            
        # Get team channel messages
        team_id = self.agent_teams[agent_id]
        channel_id = self.team_channels.get(team_id)
        
        messages = []
        if channel_id and channel_id in self.channels:
            messages.extend(
                self.channels[channel_id].get_messages(
                    agent_id, unread_only, since_timestamp
                )
            )
            
        # Get direct messages
        for channel_key, channel_id in self.direct_channels.items():
            if agent_id in channel_key and channel_id in self.channels:
                messages.extend(
                    self.channels[channel_id].get_messages(
                        agent_id, unread_only, since_timestamp
                    )
                )
                
        # Sort by priority and time
        messages.sort(key=lambda m: (m.priority.value, m.timestamp), reverse=True)
        return messages
    
    def mark_as_read(self, agent_id: str, message_id: str) -> bool:
        """
        Mark a message as read by an agent.
        
        Args:
            agent_id: ID of the agent
            message_id: ID of the message
            
        Returns:
            True if successful, False otherwise
        """
        if message_id in self.message_history:
            message = self.message_history[message_id]
            message.mark_as_read(agent_id)
            return True
        return False
        
    def respond_to_message(self, 
                         original_message_id: str,
                         sender_id: str,
                         content: Dict[str, Any],
                         priority: MessagePriority = MessagePriority.MEDIUM) -> Optional[str]:
        """
        Respond to a specific message.
        
        Args:
            original_message_id: ID of the message being responded to
            sender_id: ID of the agent sending the response
            content: Response content
            priority: Response priority
            
        Returns:
            Message ID if sent successfully, None otherwise
        """
        if original_message_id not in self.message_history:
            return None
            
        original_message = self.message_history[original_message_id]
        
        # Create response message
        response = Message(
            sender_id=sender_id,
            recipient_id=original_message.sender_id,
            message_type=MessageType.RESPONSE,
            content={
                'response_to': original_message_id,
                **content
            },
            priority=priority,
            is_team_message=False
        )
        
        # Apply transmission reliability
        if self._simulate_transmission(sender_id, original_message.sender_id, priority):
            # Store in history
            self.message_history[response.id] = response
            
            # Add to appropriate channel
            channel_key = tuple(sorted([sender_id, original_message.sender_id]))
            if channel_key in self.direct_channels:
                channel_id = self.direct_channels[channel_key]
                self.channels[channel_id].add_message(response)
            
            # Link response to original
            original_message.add_response(response)
            
            # Update pending response if applicable
            if original_message_id in self.pending_responses:
                self.pending_responses[original_message_id]['responses'].append(response)
                
            # Update stats
            self.communication_stats["response"] += 1
            self.agent_activity[sender_id] += 1
            
            return response.id
            
        return None
    
    def update(self) -> None:
        """Update the communication system (clean up expired messages)."""
        # Remove expired messages from history
        current_time = time.time()
        for message_id in list(self.message_history.keys()):
            message = self.message_history[message_id]
            if message.is_expired():
                del self.message_history[message_id]
                
        # Clean up pending responses
        for request_id in list(self.pending_responses.keys()):
            request_data = self.pending_responses[request_id]
            
            # Remove if request expired or fulfilled
            if request_data['request'].is_expired() or request_data['fulfilled']:
                del self.pending_responses[request_id]
        
        # Clean up inactive channels
        for channel_id in list(self.channels.keys()):
            channel = self.channels[channel_id]
            if not channel.is_active():
                del self.channels[channel_id]
                
                # Also remove from mappings
                for team_id, team_channel in list(self.team_channels.items()):
                    if team_channel == channel_id:
                        del self.team_channels[team_id]
                        
                for direct_key, direct_channel in list(self.direct_channels.items()):
                    if direct_channel == channel_id:
                        del self.direct_channels[direct_key]
    
    def broadcast_to_team(self, 
                         sender_id: str, 
                         message_type: MessageType,
                         content: Dict[str, Any],
                         priority: MessagePriority = MessagePriority.MEDIUM) -> Optional[str]:
        """
        Broadcast a message to the sender's team.
        
        Args:
            sender_id: ID of the sending agent
            message_type: Type of message
            content: Message content
            priority: Priority level
            
        Returns:
            Message ID if sent successfully, None otherwise
        """
        if sender_id not in self.agent_teams:
            return None
            
        team_id = self.agent_teams[sender_id]
        return self.send_message(
            sender_id=sender_id,
            recipient_id=team_id,
            message_type=message_type,
            content=content,
            priority=priority,
            is_team_message=True
        )
        
    def get_communication_stats(self) -> Dict[str, Any]:
        """
        Get statistics about communication.
        
        Returns:
            Dictionary of communication statistics
        """
        stats = {
            'message_counts': dict(self.communication_stats),
            'active_agents': len(self.agent_activity),
            'active_channels': len(self.channels),
            'pending_responses': len(self.pending_responses),
            'most_active_agents': self._get_most_active_agents(5)
        }
        return stats
    
    def _get_most_active_agents(self, count: int = 5) -> List[Tuple[str, int]]:
        """Get the most active communicating agents."""
        return sorted(
            self.agent_activity.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:count]
        
    def check_request_fulfilled(self, request_id: str) -> bool:
        """
        Check if a request has been fulfilled.
        
        Args:
            request_id: ID of the request message
            
        Returns:
            True if request has been fulfilled, False otherwise
        """
        if request_id not in self.pending_responses:
            return False
            
        return self.pending_responses[request_id]['fulfilled']
    
    def mark_request_fulfilled(self, request_id: str) -> bool:
        """
        Mark a request as fulfilled.
        
        Args:
            request_id: ID of the request message
            
        Returns:
            True if successful, False otherwise
        """
        if request_id not in self.pending_responses:
            return False
            
        self.pending_responses[request_id]['fulfilled'] = True
        return True
    
    def get_channel_messages(self, 
                           channel_id: str, 
                           agent_id: str, 
                           unread_only: bool = False) -> List[Message]:
        """
        Get messages from a specific channel.
        
        Args:
            channel_id: ID of the channel
            agent_id: ID of the agent retrieving messages
            unread_only: Whether to get only unread messages
            
        Returns:
            List of Message objects
        """
        if channel_id not in self.channels:
            return []
            
        channel = self.channels[channel_id]
        
        # Check if agent is a member of this channel
        if agent_id not in channel.members:
            return []
            
        return channel.get_messages(agent_id, unread_only)
    
    def export_communication_data(self) -> Dict[str, Any]:
        """
        Export communication data for serialization.
        
        Returns:
            Dictionary of communication data
        """
        return {
            'messages': {
                message_id: message.to_dict()
                for message_id, message in self.message_history.items()
            },
            'stats': self.get_communication_stats(),
            'channels': {
                channel_id: {
                    'members': list(channel.members),
                    'type': channel.channel_type,
                    'active': channel.active
                }
                for channel_id, channel in self.channels.items()
            }
        }

class AgentCommands:
    """
    Common command structures for agent communication.
    
    This class provides standard message formats for common
    commands and actions that agents can use to communicate.
    """
    
    @staticmethod
    def move_to_position(position: Tuple[float, float]) -> Dict[str, Any]:
        """
        Create a command to move to a position.
        
        Args:
            position: Target position (x, y)
            
        Returns:
            Command content dictionary
        """
        return {
            'command': 'move_to',
            'position': position,
            'timestamp': time.time()
        }
    
    @staticmethod
    def gather_resource(resource_type: str, position: Tuple[float, float]) -> Dict[str, Any]:
        """
        Create a command to gather a resource.
        
        Args:
            resource_type: Type of resource to gather
            position: Position of the resource
            
        Returns:
            Command content dictionary
        """
        return {
            'command': 'gather',
            'resource_type': resource_type,
            'position': position,
            'timestamp': time.time()
        }
    
    @staticmethod
    def attack_target(target_id: str, position: Tuple[float, float]) -> Dict[str, Any]:
        """
        Create a command to attack a target.
        
        Args:
            target_id: ID of the target
            position: Position of the target
            
        Returns:
            Command content dictionary
        """
        return {
            'command': 'attack',
            'target_id': target_id,
            'position': position,
            'timestamp': time.time()
        }
    
    @staticmethod
    def form_up(formation_type: str, position: Tuple[float, float]) -> Dict[str, Any]:
        """
        Create a command to form up in a formation.
        
        Args:
            formation_type: Type of formation
            position: Center position for the formation
            
        Returns:
            Command content dictionary
        """
        return {
            'command': 'form_up',
            'formation': formation_type,
            'position': position,
            'timestamp': time.time()
        }
    
    @staticmethod
    def assist_ally(ally_id: str) -> Dict[str, Any]:
        """
        Create a command to assist an ally.
        
        Args:
            ally_id: ID of the ally to assist
            
        Returns:
            Command content dictionary
        """
        return {
            'command': 'assist',
            'ally_id': ally_id,
            'timestamp': time.time()
        }
    
    @staticmethod
    def request_resource(resource_type: str, amount: float) -> Dict[str, Any]:
        """
        Create a request for resources.
        
        Args:
            resource_type: Type of resource needed
            amount: Amount needed
            
        Returns:
            Request content dictionary
        """
        return {
            'request': 'resource',
            'resource_type': resource_type,
            'amount': amount,
            'urgency': 1.0,  # Default urgency
            'timestamp': time.time()
        }
    
    @staticmethod
    def report_enemy(enemy_id: str, position: Tuple[float, float], 
                   health: float, threat_level: float) -> Dict[str, Any]:
        """
        Create an information report about an enemy.
        
        Args:
            enemy_id: ID of the enemy
            position: Position of the enemy
            health: Health level of the enemy
            threat_level: Estimated threat level (0-1)
            
        Returns:
            Information content dictionary
        """
        return {
            'info': 'enemy',
            'enemy_id': enemy_id,
            'position': position,
            'health': health,
            'threat_level': threat_level,
            'timestamp': time.time()
        }
    
    @staticmethod
    def report_resource(resource_type: str, position: Tuple[float, float], 
                      amount: float) -> Dict[str, Any]:
        """
        Create an information report about a resource.
        
        Args:
            resource_type: Type of resource
            position: Position of the resource
            amount: Estimated amount available
            
        Returns:
            Information content dictionary
        """
        return {
            'info': 'resource',
            'resource_type': resource_type,
            'position': position,
            'amount': amount,
            'timestamp': time.time()
        }
    
    @staticmethod
    def report_status(health: float, energy: float, 
                    position: Tuple[float, float]) -> Dict[str, Any]:
        """
        Create a status report.
        
        Args:
            health: Current health level
            energy: Current energy level
            position: Current position
            
        Returns:
            Status information dictionary
        """
        return {
            'info': 'status',
            'health': health,
            'energy': energy,
            'position': position,
            'timestamp': time.time()
        }

class CommunicationInterpreter:
    """
    Interprets and processes agent communication messages.
    
    This class helps agents understand and respond to
    messages based on their content and context.
    """
    
    def __init__(self, communication_system: CommunicationSystem):
        """
        Initialize the communication interpreter.
        
        Args:
            communication_system: Reference to the communication system
        """
        self.comms = communication_system
        self.command_handlers = {
            'move_to': self._handle_move_command,
            'gather': self._handle_gather_command,
            'attack': self._handle_attack_command,
            'form_up': self._handle_formation_command,
            'assist': self._handle_assist_command
        }
        
    def process_messages(self, 
                       agent_id: str, 
                       agent_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process messages for an agent and generate responses.
        
        Args:
            agent_id: ID of the agent
            agent_state: Current state of the agent
            
        Returns:
            List of suggested actions based on messages
        """
        # Get unread messages
        messages = self.comms.get_messages(agent_id, unread_only=True)
        
        suggested_actions = []
        
        for message in messages:
            # Mark as read
            self.comms.mark_as_read(agent_id, message.id)
            
            # Process by message type
            if message.message_type == MessageType.COMMAND:
                if 'command' in message.content:
                    command_type = message.content['command']
                    if command_type in self.command_handlers:
                        action = self.command_handlers[command_type](
                            message, agent_id, agent_state
                        )
                        if action:
                            suggested_actions.append(action)
                            
            elif message.message_type == MessageType.REQUEST:
                # Handle resource requests
                if message.content.get('request') == 'resource':
                    action = self._handle_resource_request(
                        message, agent_id, agent_state
                    )
                    if action:
                        suggested_actions.append(action)
                        
            elif message.message_type == MessageType.INFORM:
                # Process information messages
                if 'info' in message.content:
                    info_type = message.content['info']
                    action = self._process_information(
                        info_type, message, agent_id, agent_state
                    )
                    if action:
                        suggested_actions.append(action)
        
        return suggested_actions
    
    def _handle_move_command(self, 
                            message: Message, 
                            agent_id: str, 
                            agent_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a move command."""
        if 'position' in message.content:
            return {
                'action': 'move',
                'target': message.content['position'],
                'priority': message.priority.value
            }
        return None
    
    def _handle_gather_command(self, 
                              message: Message, 
                              agent_id: str, 
                              agent_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a resource gathering command."""
        if 'position' in message.content and 'resource_type' in message.content:
            return {
                'action': 'gather',
                'resource_type': message.content['resource_type'],
                'target': message.content['position'],
                'priority': message.priority.value
            }
        return None
    
    def _handle_attack_command(self, 
                              message: Message, 
                              agent_id: str, 
                              agent_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle an attack command."""
        if 'target_id' in message.content and 'position' in message.content:
            return {
                'action': 'attack',
                'target_id': message.content['target_id'],
                'target': message.content['position'],
                'priority': message.priority.value
            }
        return None
    
    def _handle_formation_command(self, 
                                message: Message, 
                                agent_id: str, 
                                agent_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a formation command."""
        if 'formation' in message.content and 'position' in message.content:
            return {
                'action': 'formation',
                'formation_type': message.content['formation'],
                'target': message.content['position'],
                'priority': message.priority.value
            }
        return None
    
    def _handle_assist_command(self, 
                             message: Message, 
                             agent_id: str, 
                             agent_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle an assist command."""
        if 'ally_id' in message.content:
            return {
                'action': 'assist',
                'target_id': message.content['ally_id'],
                'priority': message.priority.value
            }
        return None
    
    def _handle_resource_request(self, 
                               message: Message, 
                               agent_id: str, 
                               agent_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a resource request."""
        if ('resource_type' in message.content and 
            'amount' in message.content):
            
            resource_type = message.content['resource_type']
            amount = message.content['amount']
            
            # Check if agent has enough of the resource
            agent_resources = agent_state.get('resources', {})
            available = agent_resources.get(resource_type, 0)
            
            if available >= amount * 0.5:  # Can fulfill at least half
                share_amount = min(available * 0.8, amount)
                
                # Send response
                self.comms.respond_to_message(
                    original_message_id=message.id,
                    sender_id=agent_id,
                    content={
                        'response': 'resource_offer',
                        'resource_type': resource_type,
                        'amount': share_amount
                    }
                )
                
                return {
                    'action': 'share_resource',
                    'target_id': message.sender_id,
                    'resource_type': resource_type,
                    'amount': share_amount,
                    'priority': message.priority.value
                }
        
        return None
    
    def _process_information(self, 
                           info_type: str, 
                           message: Message, 
                           agent_id: str, 
                           agent_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an information message."""
        if info_type == 'enemy' and 'position' in message.content:
            # Update knowledge about enemy position
            return {
                'action': 'update_knowledge',
                'knowledge_type': 'enemy',
                'enemy_id': message.content.get('enemy_id'),
                'position': message.content['position'],
                'threat_level': message.content.get('threat_level', 0.5)
            }
            
        elif info_type == 'resource' and 'position' in message.content:
            # Update knowledge about resource location
            return {
                'action': 'update_knowledge',
                'knowledge_type': 'resource',
                'resource_type': message.content.get('resource_type'),
                'position': message.content['position'],
                'amount': message.content.get('amount', 0)
            }
        
        return None 