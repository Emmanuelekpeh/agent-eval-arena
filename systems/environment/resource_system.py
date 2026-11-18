import pygame
import random
import math
from systems.visualization.visualization_system import Color

class ResourceNode:
    def __init__(self, x, y, resource_type):
        self.x = x
        self.y = y
        self.type = resource_type
        self.amount = 100
        self.regen_rate = 0.1
        self.depletion_rate = 10
        self.radius = 30
        self.pulse = 0
        self.pulse_speed = 0.1
        
    def update(self):
        self.pulse = (self.pulse + self.pulse_speed) % (math.pi * 2)
        if self.amount < 100:
            self.amount = min(100, self.amount + self.regen_rate)
    
    def extract(self, amount):
        if self.amount >= amount:
            self.amount -= amount
            return amount
        return 0
    
    def draw(self, screen):
        # Pulse effect
        pulse_scale = (math.sin(self.pulse) + 1) * 0.2 + 0.8
        size = int(self.radius * pulse_scale)
        
        # Resource type colors
        colors = {
            'energy': (0, 255, 255),
            'health': (0, 255, 0),
            'shield': (255, 255, 0)
        }
        
        color = colors.get(self.type, (255, 255, 255))
        
        # Draw node with amount indicator
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), size)
        pygame.draw.arc(screen, (255, 255, 255),
                       (self.x - self.radius, self.y - self.radius,
                        self.radius * 2, self.radius * 2),
                       0, math.pi * 2 * (self.amount / 100), 2)

class ResourceManager:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.nodes = []
        self.spawn_timer = 0
        self.spawn_interval = 300  # 5 seconds
        self.resource_types = ['energy', 'health', 'shield']
        self.max_nodes = 10  # Maximum number of resource nodes
        self.min_distance = 50  # Minimum distance between nodes
        
    def spawn_node(self, x, y, resource_type):
        """
        Spawn a new resource node at the specified position.
        
        Args:
            x (float): X position for the resource node
            y (float): Y position for the resource node
            resource_type (str): Type of resource ('energy', 'health', 'shield')
            
        Returns:
            ResourceNode: The newly created resource node
        """
        # Validate resource type
        if resource_type not in self.resource_types:
            resource_type = random.choice(self.resource_types)
        
        # Create the new node
        new_node = ResourceNode(x, y, resource_type)
        self.nodes.append(new_node)
        
        # Remove oldest node if we're over the limit
        if len(self.nodes) > self.max_nodes:
            self.nodes.pop(0)
            
        return new_node
    
    def update(self, delta_time: float = 0.0):
        """Update all resource nodes and spawn new ones over time"""
        # Update existing nodes
        for node in self.nodes:
            node.update()
            
        # Check if any nodes are depleted
        self.nodes = [node for node in self.nodes if node.amount > 0]
        
        # Spawn new nodes periodically
        self.spawn_timer += delta_time
        if self.spawn_timer >= self.spawn_interval and len(self.nodes) < self.max_nodes:
            self.spawn_timer = 0
            self._spawn_random_node()
    
    def _spawn_random_node(self):
        """Spawn a resource node at a random position"""
        # Try to find a suitable position
        for _ in range(10):  # Try 10 times
            x = random.randint(50, self.width - 50)
            y = random.randint(50, self.height - 50)
            
            # Check minimum distance from other nodes
            if self._check_min_distance(x, y):
                resource_type = random.choice(self.resource_types)
                self.spawn_node(x, y, resource_type)
                break
    
    def _check_min_distance(self, x, y):
        """Check if position is far enough from other nodes"""
        for node in self.nodes:
            dx = node.x - x
            dy = node.y - y
            distance = math.sqrt(dx*dx + dy*dy)
            if distance < self.min_distance:
                return False
        return True
    
    def get_closest_node(self, x, y, resource_type=None):
        """
        Find the closest resource node to the given position.
        
        Args:
            x (float): X position
            y (float): Y position
            resource_type (str, optional): Specific resource type to find
            
        Returns:
            tuple: (ResourceNode, distance) or (None, float('inf')) if no nodes
        """
        closest_node = None
        min_distance = float('inf')
        
        for node in self.nodes:
            # Skip if not the requested type
            if resource_type and node.type != resource_type:
                continue
                
            dx = node.x - x
            dy = node.y - y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance < min_distance:
                min_distance = distance
                closest_node = node
                
        return closest_node, min_distance
    
    def extract_resource(self, x, y, amount):
        """Extract resources from the nearest node"""
        closest_node, dist = self.get_closest_node(x, y)
        
        if closest_node and dist < closest_node.radius + 10:
            extracted = closest_node.extract(amount)
            if extracted > 0:
                # Remove node if depleted
                if closest_node.amount <= 0:
                    self.nodes.remove(closest_node)
                return closest_node.type, extracted
        return None, 0
    
    def draw(self, renderer):
        """
        Draw resource nodes using the provided Renderer.
        
        Args:
            renderer: The Renderer instance to use for drawing.
        """
        if not renderer or not renderer.is_initialized():
            # logger.warning("ResourceManager.draw: Renderer not available.")
            return
            
        for node in self.nodes:
            # Use renderer's draw methods
            # Assuming renderer has a draw_resource or similar method
            # If not, we might need to implement it or use draw_circle/draw_polygon
            
            # Example using draw_resource (if it exists and takes these args):
            if hasattr(renderer, 'draw_resource'):
                node_color_tuple = node.get_color() # Assuming node has a method to get color tuple
                node_color = Color(*node_color_tuple)
                renderer.draw_resource(node.x, node.y, node.type, node.radius, node_color)
                # Maybe add amount visualization?
                # renderer.draw_text(node.x, node.y + node.radius + 5, f'{node.amount:.0f}', Color(255,255,255), size=10)
            else:
                # Fallback using draw_circle
                node_color_tuple = node.get_color() # Assuming node has a method to get color tuple
                node_color = Color(*node_color_tuple)
                renderer.draw_circle(node.x, node.y, node.radius, node_color)
                # Add amount visualization as text
                renderer.draw_text(node.x, node.y + node.radius + 5, f'{node.amount:.0f}', Color(255,255,255), size=10, centered=True)
