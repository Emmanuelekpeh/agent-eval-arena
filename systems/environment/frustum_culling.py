"""
Frustum Culling System for Battle Royale Environment

This module provides frustum culling optimization for the battle royale environment,
allowing for stage-based rendering with significant performance improvements.
"""

import math
import numpy as np
import logging
from typing import Dict, List, Tuple, Any, Optional, Set
import random

logger = logging.getLogger(__name__)

class Plane:
    """Represents a plane in 3D space defined by a normal vector and distance from origin"""
    
    def __init__(self, normal=(0, 1, 0), distance=0):
        """
        Initialize a plane with normal vector and distance
        
        Args:
            normal: Normal vector of the plane (pointing in the direction considered "outside")
            distance: Distance from origin to the nearest point on the plane
        """
        self.normal = np.array(normal, dtype=np.float32)
        self.normal = self.normal / np.linalg.norm(self.normal)  # Normalize
        self.distance = distance
    
    def get_signed_distance_to_point(self, point):
        """
        Calculate signed distance from a point to the plane
        Positive if point is on the side the normal points to (outside)
        Negative if point is on the opposite side (inside)
        
        Args:
            point: 3D point to test
            
        Returns:
            Signed distance from point to plane
        """
        return np.dot(self.normal, point) + self.distance

class Frustum:
    """Represents a camera frustum defined by six planes"""
    
    def __init__(self):
        """Initialize an empty frustum with default planes"""
        self.top_face = Plane()
        self.bottom_face = Plane()
        self.right_face = Plane()
        self.left_face = Plane()
        self.far_face = Plane()
        self.near_face = Plane()

class AABB:
    """Axis-Aligned Bounding Box for collision detection"""
    
    def __init__(self, center, extents_x, extents_y, extents_z):
        """
        Initialize an AABB with center position and extents
        
        Args:
            center: Center position of the box
            extents_x: Half-width along x-axis
            extents_y: Half-width along y-axis
            extents_z: Half-width along z-axis
        """
        self.center = np.array(center, dtype=np.float32)
        self.extents = np.array([extents_x, extents_y, extents_z], dtype=np.float32)
    
    def is_on_or_forward_plane(self, plane):
        """
        Test if AABB is on or in front of the plane
        
        Args:
            plane: Plane to test against
            
        Returns:
            True if AABB is on or in front of the plane
        """
        # Calculate projection interval radius
        r = (self.extents[0] * abs(plane.normal[0]) + 
             self.extents[1] * abs(plane.normal[1]) + 
             self.extents[2] * abs(plane.normal[2]))
        
        # Check if center is within radius distance from plane
        return -r <= plane.get_signed_distance_to_point(self.center)
    
    def is_in_frustum(self, frustum):
        """
        Test if AABB is inside the frustum
        
        Args:
            frustum: Frustum to test against
            
        Returns:
            True if AABB is inside the frustum
        """
        return (self.is_on_or_forward_plane(frustum.left_face) and
                self.is_on_or_forward_plane(frustum.right_face) and
                self.is_on_or_forward_plane(frustum.top_face) and
                self.is_on_or_forward_plane(frustum.bottom_face) and
                self.is_on_or_forward_plane(frustum.near_face) and
                self.is_on_or_forward_plane(frustum.far_face))

class QuadTreeNode:
    """Node in a quadtree spatial partitioning structure"""
    
    def __init__(self, bounds, max_objects=10, max_depth=4, depth=0):
        """
        Initialize a quadtree node
        
        Args:
            bounds: Rectangle bounds of this node (x, y, width, height)
            max_objects: Maximum objects before splitting
            max_depth: Maximum depth of the tree
            depth: Current depth in the tree
        """
        self.bounds = bounds  # (x, y, width, height)
        self.max_objects = max_objects
        self.max_depth = max_depth
        self.depth = depth
        self.objects = []
        self.nodes = []  # Child nodes
        self.is_divided = False
        
    def insert(self, entity):
        """
        Insert an entity into the quadtree
        
        Args:
            entity: Entity to insert (must have 'position' property)
            
        Returns:
            True if insertion was successful
        """
        # If this node has children, try to insert in them
        if self.is_divided:
            quadrant = self._get_quadrant(entity['position'])
            if quadrant != -1:
                return self.nodes[quadrant].insert(entity)
        
        # Otherwise add to this node
        self.objects.append(entity)
        
        # Split if needed
        if len(self.objects) > self.max_objects and self.depth < self.max_depth:
            if not self.is_divided:
                self._split()
            
            # Redistribute objects
            i = 0
            while i < len(self.objects):
                quadrant = self._get_quadrant(self.objects[i]['position'])
                if quadrant != -1:
                    obj = self.objects.pop(i)
                    self.nodes[quadrant].insert(obj)
                else:
                    i += 1
        
        return True
    
    def _split(self):
        """Split this node into four child nodes"""
        x, y, width, height = self.bounds
        half_width = width / 2
        half_height = height / 2
        
        # Create child nodes
        self.nodes.append(QuadTreeNode(
            (x + half_width, y, half_width, half_height),
            self.max_objects, self.max_depth, self.depth + 1))  # Top right
        
        self.nodes.append(QuadTreeNode(
            (x, y, half_width, half_height),
            self.max_objects, self.max_depth, self.depth + 1))  # Top left
        
        self.nodes.append(QuadTreeNode(
            (x, y + half_height, half_width, half_height),
            self.max_objects, self.max_depth, self.depth + 1))  # Bottom left
        
        self.nodes.append(QuadTreeNode(
            (x + half_width, y + half_height, half_width, half_height),
            self.max_objects, self.max_depth, self.depth + 1))  # Bottom right
        
        self.is_divided = True
    
    def _get_quadrant(self, position):
        """
        Get the quadrant index for a position
        
        Args:
            position: 2D position to check
            
        Returns:
            Quadrant index (0-3) or -1 if outside bounds
        """
        x, y, width, height = self.bounds
        pos_x, pos_y = position
        
        # Check if inside bounds
        if pos_x < x or pos_x > x + width or pos_y < y or pos_y > y + height:
            return -1
        
        # Determine quadrant
        mid_x = x + width / 2
        mid_y = y + height / 2
        
        if pos_y < mid_y:
            if pos_x < mid_x:
                return 1  # Top left
            else:
                return 0  # Top right
        else:
            if pos_x < mid_x:
                return 2  # Bottom left
            else:
                return 3  # Bottom right
    
    def query_range(self, x, y, radius):
        """
        Find all objects within radius of a point
        
        Args:
            x, y: Center point
            radius: Search radius
            
        Returns:
            List of objects within radius
        """
        result = []
        
        # Check if circle intersects this node
        bx, by, bw, bh = self.bounds
        if (x + radius < bx or x - radius > bx + bw or
            y + radius < by or y - radius > by + bh):
            return result
        
        # Check objects in this node
        for obj in self.objects:
            pos_x, pos_y = obj['position']
            dist_sq = (pos_x - x)**2 + (pos_y - y)**2
            if dist_sq <= radius**2:
                result.append(obj)
        
        # Check children if divided
        if self.is_divided:
            for node in self.nodes:
                result.extend(node.query_range(x, y, radius))
        
        return result
    
    def clear(self):
        """Clear all objects and child nodes"""
        self.objects = []
        for node in self.nodes:
            node.clear()
        self.nodes = []
        self.is_divided = False

def create_frustum_from_camera(camera_pos, camera_front, camera_up, camera_right, 
                             aspect, fov_y, z_near, z_far):
    """
    Create a frustum from camera parameters
    
    Args:
        camera_pos: Camera position
        camera_front: Camera front direction
        camera_up: Camera up direction
        camera_right: Camera right direction
        aspect: Aspect ratio (width/height)
        fov_y: Field of view in radians
        z_near: Near plane distance
        z_far: Far plane distance
        
    Returns:
        Frustum object
    """
    frustum = Frustum()
    
    # Calculate frustum corners
    half_v_side = z_far * math.tan(fov_y * 0.5)
    half_h_side = half_v_side * aspect
    front_mult_far = z_far * camera_front
    
    # Calculate planes - ensure normal points outside the frustum
    # Near face - normal points inward (opposite of front)
    frustum.near_face = Plane(
        normal=camera_front,
        distance=-np.dot(camera_front, camera_pos + z_near * camera_front)
    )
    
    # Far face - normal points backward (same as front)
    frustum.far_face = Plane(
        normal=-camera_front,
        distance=np.dot(-camera_front, camera_pos + front_mult_far)
    )
    
    # Right face - cross product to get perpendicular normal
    right_normal = np.cross(
        np.cross(camera_up, front_mult_far + camera_right * half_h_side),
        camera_up
    )
    right_normal = right_normal / np.linalg.norm(right_normal)
    frustum.right_face = Plane(
        normal=right_normal,
        distance=-np.dot(right_normal, camera_pos)
    )
    
    # Left face - cross product to get perpendicular normal
    left_normal = np.cross(
        camera_up, 
        np.cross(front_mult_far - camera_right * half_h_side, camera_up)
    )
    left_normal = left_normal / np.linalg.norm(left_normal)
    frustum.left_face = Plane(
        normal=left_normal,
        distance=-np.dot(left_normal, camera_pos)
    )
    
    # Top face - cross product to get perpendicular normal
    top_normal = np.cross(
        np.cross(camera_right, front_mult_far - camera_up * half_v_side),
        camera_right
    )
    top_normal = top_normal / np.linalg.norm(top_normal)
    frustum.top_face = Plane(
        normal=top_normal,
        distance=-np.dot(top_normal, camera_pos)
    )
    
    # Bottom face - cross product to get perpendicular normal
    bottom_normal = np.cross(
        camera_right,
        np.cross(front_mult_far + camera_up * half_v_side, camera_right)
    )
    bottom_normal = bottom_normal / np.linalg.norm(bottom_normal)
    frustum.bottom_face = Plane(
        normal=bottom_normal,
        distance=-np.dot(bottom_normal, camera_pos)
    )
    
    return frustum

class StageSector:
    """Represents a sector of the stage for hierarchical culling"""
    
    def __init__(self, bounds, entities=None):
        """
        Initialize a stage sector
        
        Args:
            bounds: AABB bounds of this sector
            entities: List of entities in this sector
        """
        self.bounds = bounds  # AABB
        self.entities = entities or []
        self.child_sectors = []
        self.is_visible = False
    
    def add_child(self, child_sector):
        """Add a child sector to this sector"""
        self.child_sectors.append(child_sector)
    
    def is_in_frustum(self, frustum):
        """Test if this sector is in the frustum"""
        return self.bounds.is_in_frustum(frustum)
    
    def get_visible_entities(self, frustum):
        """
        Get all visible entities in this sector and its children
        
        Args:
            frustum: View frustum
            
        Returns:
            List of visible entities
        """
        visible = []
        
        # If this sector isn't in view, skip entirely
        if not self.is_in_frustum(frustum):
            self.is_visible = False
            return visible
        
        self.is_visible = True
        
        # If this sector has children, check them
        if self.child_sectors:
            for child in self.child_sectors:
                visible.extend(child.get_visible_entities(frustum))
        
        # Otherwise check individual entities
        else:
            for entity in self.entities:
                if entity['aabb'].is_in_frustum(frustum):
                    visible.append(entity)
        
        return visible

class StageManager:
    """Manager for stage-based rendering with culling optimization"""
    
    def __init__(self, width=1000, height=1000):
        """
        Initialize a stage manager
        
        Args:
            width: Width of the stage
            height: Height of the stage
        """
        self.width = width
        self.height = height
        self.entities = {}
        self.current_stage = 0
        self.frustum = None
        
        # Quadtree for spatial partitioning
        self.quad_tree = QuadTreeNode((0, 0, width, height), max_depth=5, max_objects=10)
        
        # Root sector for hierarchical culling
        self.root_sector = None
        
        # Statistics
        self.total_entities = 0
        self.rendered_entities = 0
        self.last_camera_pos = None
        
        logger.info(f"StageManager initialized with dimensions {width}x{height}")
    
    def create_random_stage(self, num_entities, hierarchical=True, depth=2):
        """
        Generate a new random stage with the specified number of entities
        
        Args:
            num_entities: Number of entities to generate
            hierarchical: Whether to use hierarchical sectors
            depth: Depth of hierarchical sectors
        """
        self.clear_entities()
        self.total_entities = num_entities
        
        logger.info(f"Creating random stage with {num_entities} entities")
        
        if hierarchical:
            # Create hierarchical sectors
            root_bounds = AABB((self.width/2, self.height/2, 0), self.width/2, self.height/2, 100)
            self.root_sector = StageSector(root_bounds)
            self._divide_sector(self.root_sector, depth, num_entities)
        else:
            # Create flat list of entities
            # Group creation to minimize individual entity overhead
            terrain_entities = []
            cover_entities = []
            obstacle_entities = []
            
            # Create groups of similar entities in batches
            entity_types = ["terrain", "cover", "obstacle"]
            type_counts = {
                "terrain": int(num_entities * 0.6),  # 60% terrain
                "cover": int(num_entities * 0.3),    # 30% cover
                "obstacle": int(num_entities * 0.1)  # 10% obstacles
            }
            
            # Adjust to make sure we get exactly num_entities
            remaining = num_entities - sum(type_counts.values())
            type_counts["terrain"] += remaining
            
            for entity_type in entity_types:
                count = type_counts[entity_type]
                logger.debug(f"Generating {count} entities of type {entity_type}")
                
                for i in range(count):
                    pos_x = random.uniform(0, self.width)
                    pos_y = random.uniform(0, self.height)
                    
                    # Use a basic bounding box for culling
                    entity_width = random.uniform(10, 50)
                    entity_height = random.uniform(10, 50)
                    entity_depth = random.uniform(5, 20)
                    
                    entity = {
                        'id': f"{entity_type}_{len(self.entities)}",
                        'position': (pos_x, pos_y),
                        'type': entity_type,
                        'aabb': AABB((pos_x, pos_y, 0), entity_width/2, entity_height/2, entity_depth/2),
                        'radius': max(entity_width, entity_height)/2,
                        'durability': 100 if entity_type == "cover" else 0,
                        'protection': random.uniform(0.1, 0.5) if entity_type == "cover" else 0,
                        'destructible': entity_type == "cover",
                        'height': entity_height
                    }
                    
                    # Add to appropriate group
                    if entity_type == "terrain":
                        terrain_entities.append(entity)
                    elif entity_type == "cover":
                        cover_entities.append(entity)
                    else:
                        obstacle_entities.append(entity)
                    
                    # Add to main entity dictionary
                    self.entities[entity['id']] = entity
                    
                    # Add to quadtree for spatial queries
                    self.quad_tree.insert(entity)
        
        logger.info(f"Random stage created with {len(self.entities)} entities")
    
    def _divide_sector(self, sector, depth, entities_left, min_size=50):
        """
        Recursively divide a sector into subsectors
        
        Args:
            sector: Sector to divide
            depth: Remaining depth
            entities_left: Number of entities to create in this branch
            min_size: Minimum sector size before stopping division
        """
        if depth <= 0 or entities_left <= 10 or min(sector.bounds.extents[0], sector.bounds.extents[1]) < min_size:
            # Create entities in this leaf sector
            center = sector.bounds.center
            extents = sector.bounds.extents
            
            for i in range(entities_left):
                pos_x = random.uniform(center[0] - extents[0], center[0] + extents[0])
                pos_y = random.uniform(center[1] - extents[1], center[1] + extents[1])
                
                entity_type = random.choice(["terrain", "cover", "obstacle"])
                entity_width = random.uniform(10, 30)
                entity_height = random.uniform(10, 30)
                entity_depth = random.uniform(5, 15)
                
                entity = {
                    'id': f"{entity_type}_{len(self.entities)}",
                    'position': (pos_x, pos_y),
                    'type': entity_type,
                    'aabb': AABB((pos_x, pos_y, 0), entity_width/2, entity_height/2, entity_depth/2),
                    'radius': max(entity_width, entity_height)/2,
                    'durability': 100 if entity_type == "cover" else 0,
                    'protection': random.uniform(0.1, 0.5) if entity_type == "cover" else 0,
                    'destructible': entity_type == "cover",
                    'height': entity_height
                }
                
                sector.entities.append(entity)
                self.entities[entity['id']] = entity
                self.quad_tree.insert(entity)
            
            return
        
        # Divide sector into 4 subsectors
        center = sector.bounds.center
        extents = sector.bounds.extents
        half_extents = (extents[0]/2, extents[1]/2, extents[2])
        
        # Create child sectors
        sectors = []
        for i in range(4):
            x_offset = half_extents[0] * (1 if i % 2 == 0 else -1)
            y_offset = half_extents[1] * (1 if i < 2 else -1)
            
            child_center = (center[0] + x_offset, center[1] + y_offset, center[2])
            child_bounds = AABB(child_center, half_extents[0], half_extents[1], half_extents[2])
            child_sector = StageSector(child_bounds)
            
            sectors.append(child_sector)
            sector.add_child(child_sector)
        
        # Distribute entities among children based on area covered
        entities_per_child = entities_left // 4
        remaining = entities_left % 4
        
        for i, child in enumerate(sectors):
            child_entities = entities_per_child + (1 if i < remaining else 0)
            self._divide_sector(child, depth - 1, child_entities, min_size)
    
    def update_frustum(self, camera_pos, camera_front, camera_up, camera_right, aspect, fov_y, z_near, z_far):
        """
        Update the view frustum for culling
        
        Args:
            camera_pos: Position of the camera
            camera_front: Forward vector of the camera
            camera_up: Up vector of the camera
            camera_right: Right vector of the camera
            aspect: Aspect ratio of the viewport
            fov_y: Vertical field of view in radians
            z_near: Near plane distance
            z_far: Far plane distance
        """
        self.frustum = create_frustum_from_camera(
            camera_pos, camera_front, camera_up, camera_right, 
            aspect, fov_y, z_near, z_far
        )
        
        # Store camera position for spatial queries
        self.last_camera_pos = camera_pos
    
    def get_visible_entities(self):
        """
        Return only entities visible within the current frustum
        
        Returns:
            List of visible entities
        """
        if not self.frustum:
            logger.warning("Attempted to get visible entities without updating frustum first")
            return list(self.entities.values())
        
        visible_entities = []
        self.rendered_entities = 0
        
        # Check if we have a hierarchical structure
        if self.root_sector:
            # Use hierarchical culling
            visible_entities = self.root_sector.get_visible_entities(self.frustum)
        else:
            # Use quadtree to get potential visible entities first
            # Get camera position and create a search area
            if self.last_camera_pos is None:
                logger.warning("Camera position not set, checking all entities")
                potential_entities = list(self.entities.values())
            else:
                # Use quadtree to narrow down potential entities
                search_radius = 1000  # Adjust based on your far plane
                potential_entities = self.quad_tree.query_range(
                    self.last_camera_pos[0], self.last_camera_pos[1], search_radius
                )
            
            # Only test frustum for entities in potential range
            for entity in potential_entities:
                if entity['aabb'].is_in_frustum(self.frustum):
                    visible_entities.append(entity)
        
        self.rendered_entities = len(visible_entities)
        
        # Log culling efficiency
        if self.total_entities > 0:
            culling_ratio = self.rendered_entities / self.total_entities
            logger.debug(f"Culling efficiency: {self.rendered_entities}/{self.total_entities} " +
                        f"({culling_ratio:.2%}) entities rendered")
        
        return visible_entities
    
    def clear_entities(self):
        """Clear all entities from the current stage"""
        self.entities = {}
        self.quad_tree.clear()
        self.total_entities = 0
        self.rendered_entities = 0
        self.root_sector = None

class FrustumCullingSystem:
    """System for managing frustum culling in the battle royale environment"""
    
    def __init__(self, environment):
        """
        Initialize the frustum culling system
        
        Args:
            environment: Reference to the battle royale environment
        """
        self.environment = environment
        self.stage_manager = StageManager(
            width=environment.width if hasattr(environment, 'width') else 1000,
            height=environment.height if hasattr(environment, 'height') else 1000
        )
        
        # Performance metrics
        self.render_time = 0.0
        self.culling_enabled = True
        self.show_debug = True
        
        # Camera parameters (extracted from environment when available)
        self.camera_pos = np.array([0, 0, 0])
        self.camera_front = np.array([0, 0, -1])
        self.camera_up = np.array([0, 1, 0])
        self.camera_right = np.array([1, 0, 0])
        self.aspect = 16/9
        self.fov_y = math.radians(60)
        self.z_near = 0.1
        self.z_far = 1000.0
        
        logger.info("FrustumCullingSystem initialized")
    
    def generate_stage(self, num_entities=1000, hierarchical=True):
        """
        Generate a new stage with the specified number of entities
        
        Args:
            num_entities: Number of entities to generate
            hierarchical: Whether to use hierarchical culling structure
        """
        self.stage_manager.create_random_stage(num_entities, hierarchical)
        
        # Update the environment with the generated entities if needed
        if hasattr(self.environment, 'add_entities'):
            for entity_id, entity in self.stage_manager.entities.items():
                self.environment.add_entities(entity)
    
    def update_camera(self, camera_data=None):
        """
        Update camera parameters for culling calculations
        
        Args:
            camera_data: Optional dictionary with camera parameters
        """
        if camera_data:
            # Use provided camera data
            self.camera_pos = camera_data.get('position', self.camera_pos)
            self.camera_front = camera_data.get('front', self.camera_front)
            self.camera_up = camera_data.get('up', self.camera_up)
            self.camera_right = camera_data.get('right', self.camera_right)
            self.aspect = camera_data.get('aspect', self.aspect)
            self.fov_y = camera_data.get('fov_y', self.fov_y)
            self.z_near = camera_data.get('z_near', self.z_near)
            self.z_far = camera_data.get('z_far', self.z_far)
        elif hasattr(self.environment, 'camera'):
            # Extract from environment camera
            camera = self.environment.camera
            if hasattr(camera, 'position'):
                self.camera_pos = np.array(camera.position)
            if hasattr(camera, 'front'):
                self.camera_front = np.array(camera.front)
            if hasattr(camera, 'up'):
                self.camera_up = np.array(camera.up)
            if hasattr(camera, 'right'):
                self.camera_right = np.array(camera.right)
            if hasattr(camera, 'aspect'):
                self.aspect = camera.aspect
            if hasattr(camera, 'fov'):
                self.fov_y = math.radians(camera.fov)
            if hasattr(camera, 'near'):
                self.z_near = camera.near
            if hasattr(camera, 'far'):
                self.z_far = camera.far
        
        # Update frustum with current camera parameters
        self.stage_manager.update_frustum(
            self.camera_pos, self.camera_front, self.camera_up, self.camera_right,
            self.aspect, self.fov_y, self.z_near, self.z_far
        )
    
    def get_visible_entities(self):
        """
        Get all entities visible from the current camera position
        
        Returns:
            List of visible entities
        """
        if not self.culling_enabled:
            return list(self.stage_manager.entities.values())
        
        return self.stage_manager.get_visible_entities()
    
    def update_performance_metrics(self, render_time):
        """
        Update performance metrics for dynamic adjustment
        
        Args:
            render_time: Time taken to render the last frame in seconds
        """
        self.render_time = render_time
        
        # Calculate rendering ratio
        if self.stage_manager.total_entities > 0:
            render_ratio = self.stage_manager.rendered_entities / self.stage_manager.total_entities
            
            # If rendering too many entities (>25% of total), adjust culling parameters
            if render_ratio > 0.25 and self.render_time > 0.016:  # 16ms = ~60fps
                self.adjust_culling_parameters(more_aggressive=True)
            # If rendering few entities with good performance, can relax culling
            elif render_ratio < 0.1 and self.render_time < 0.008:  # 8ms
                self.adjust_culling_parameters(more_aggressive=False)
    
    def adjust_culling_parameters(self, more_aggressive=True):
        """
        Dynamically adjust culling parameters based on performance
        
        Args:
            more_aggressive: Whether to make culling more aggressive
        """
        if more_aggressive:
            # Reduce far plane distance
            self.z_far = max(500, self.z_far * 0.9)
            logger.debug(f"Adjusting culling to be more aggressive: z_far = {self.z_far}")
        else:
            # Increase far plane distance
            self.z_far = min(2000, self.z_far * 1.1)
            logger.debug(f"Adjusting culling to be less aggressive: z_far = {self.z_far}")
        
        # Update frustum with new parameters
        self.update_camera()
    
    def toggle_culling(self):
        """Toggle frustum culling on/off"""
        self.culling_enabled = not self.culling_enabled
        logger.info(f"Frustum culling {'enabled' if self.culling_enabled else 'disabled'}")
    
    def toggle_debug(self):
        """Toggle debug visualization"""
        self.show_debug = not self.show_debug
        logger.info(f"Debug visualization {'enabled' if self.show_debug else 'disabled'}") 