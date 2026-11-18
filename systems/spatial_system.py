import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
import random

@dataclass
class AABB:
    """Axis-Aligned Bounding Box"""
    center_x: float
    center_y: float
    half_width: float
    half_height: float

    def __post_init__(self):
        self.west: float = self.center_x - self.half_width
        self.east: float = self.center_x + self.half_width
        self.north: float = self.center_y - self.half_height
        self.south: float = self.center_y + self.half_height

    def contains(self, point):
        px, py = point
        return (self.west <= px < self.east and
                self.north <= py < self.south)

    def intersects(self, other_aabb):
        # Check for no overlap along x-axis
        if self.east < other_aabb.west or self.west > other_aabb.east:
            return False
        # Check for no overlap along y-axis
        if self.south < other_aabb.north or self.north > other_aabb.south:
            return False
        # If neither axis shows no overlap, they must intersect
        return True

class QuadTree:
    """A QuadTree for 2D spatial partitioning."""
    def __init__(self, boundary: AABB, capacity: int):
        """
        Initialize the QuadTree.

        Args:
            boundary (AABB): The rectangular boundary of this QuadTree node.
            capacity (int): The maximum number of points before subdividing.
        """
        self.boundary = boundary
        self.capacity = capacity
        self.points = [] # List of points (x, y) stored in this node
        self.entities = [] # List of associated entity data tuples (id, radius, type)
        self.divided = False
        self.northwest = None
        self.northeast = None
        self.southwest = None
        self.southeast = None

    def clear(self):
        """Removes all points and subdivisions from the tree."""
        self.points = []
        self.entities = []
        self.divided = False
        self.northwest = None
        self.northeast = None
        self.southwest = None
        self.southeast = None

    def subdivide(self):
        """Divide this node into four child QuadTrees."""
        cx = self.boundary.center_x
        cy = self.boundary.center_y
        hw = self.boundary.half_width / 2
        hh = self.boundary.half_height / 2

        # Create new AABBs for the children
        nw_aabb = AABB(cx - hw, cy - hh, hw, hh)
        ne_aabb = AABB(cx + hw, cy - hh, hw, hh)
        sw_aabb = AABB(cx - hw, cy + hh, hw, hh)
        se_aabb = AABB(cx + hw, cy + hh, hw, hh)

        # Create the child QuadTrees
        self.northwest = QuadTree(nw_aabb, self.capacity)
        self.northeast = QuadTree(ne_aabb, self.capacity)
        self.southwest = QuadTree(sw_aabb, self.capacity)
        self.southeast = QuadTree(se_aabb, self.capacity)

        self.divided = True

        # Optional: Move points from this node to children if they fit
        # This can improve query performance slightly but adds complexity
        # For now, keep points in the parent node until it's full

    def insert(self, point, entity_id, entity_radius, entity_type):
        """
        Insert a point with associated entity data into the QuadTree.

        Args:
            point (tuple): The (x, y) coordinates of the point.
            entity_id: The unique identifier of the entity.
            entity_radius: The radius of the entity (for collision).
            entity_type (str): The type of the entity ('agent', 'pickup', etc.).

        Returns:
            bool: True if the point was inserted successfully, False otherwise.
        """
        # Check if the point is within the boundary of this node
        if not self.boundary.contains(point):
            return False # Point is outside this QuadTree's boundary

        # If the node has capacity and is not divided, add the point here
        if len(self.points) < self.capacity and not self.divided:
            self.points.append(point)
            self.entities.append((entity_id, entity_radius, entity_type)) # Store entity data tuple
            return True

        # If the node is full or already divided, subdivide if necessary
        if not self.divided:
            self.subdivide()

            # Redistribute existing points to children
            # Important: Clear parent points after redistribution to avoid duplicates
            old_points = self.points
            old_entities = self.entities
            self.points = []
            self.entities = []
            for i, p in enumerate(old_points):
                entity_data = old_entities[i]
                inserted = (self.northwest.insert(p, *entity_data) or
                            self.northeast.insert(p, *entity_data) or
                            self.southwest.insert(p, *entity_data) or
                            self.southeast.insert(p, *entity_data))
                # Theoretically, should always insert if p was in boundary

        # Try inserting the new point into the appropriate child quadrant
        # Use * to unpack the entity data tuple
        entity_data_tuple = (entity_id, entity_radius, entity_type)
        if self.northwest.insert(point, *entity_data_tuple): return True
        if self.northeast.insert(point, *entity_data_tuple): return True
        if self.southwest.insert(point, *entity_data_tuple): return True
        if self.southeast.insert(point, *entity_data_tuple): return True

        # Should not happen if boundary checks are correct
        # print(f"Warning: Failed to insert point {point} into any quadrant.")
        return False

    def query_range(self, range_box: AABB):
        """
        Query the QuadTree for points within a given range (AABB).

        Args:
            range_box (AABB): The rectangular range to query.

        Returns:
            list: A list of tuples (point, entity_id, entity_radius, entity_type)
                  for points found within the range.
        """
        found_entities = []

        # Check if the query range intersects with this node's boundary
        if not self.boundary.intersects(range_box):
            return found_entities # No intersection, no points can be inside

        # Check points within this node
        for i, point in enumerate(self.points):
            if range_box.contains(point):
                entity_data = self.entities[i] # (id, radius, type)
                found_entities.append((point, *entity_data)) # Append (point, id, radius, type)

        # If divided, query child nodes recursively
        if self.divided:
            found_entities.extend(self.northwest.query_range(range_box))
            found_entities.extend(self.northeast.query_range(range_box))
            found_entities.extend(self.southwest.query_range(range_box))
            found_entities.extend(self.southeast.query_range(range_box))

        return found_entities

    # Helper method (optional, for visualization or debugging)
    def get_all_points(self):
        """Returns all points in the tree (recursive)."""
        all_points = self.points[:]
        if self.divided:
            all_points.extend(self.northwest.get_all_points())
            all_points.extend(self.northeast.get_all_points())
            all_points.extend(self.southwest.get_all_points())
            all_points.extend(self.southeast.get_all_points())
        return all_points

    def _intersects(self, range_box):
        """Check if a range intersects with this node's boundary."""
        # Simple AABB intersection check
        return self.boundary.intersects(range_box)

# Example Usage (Optional - can be removed or put under if __name__ == '__main__')
if __name__ == '__main__':
    # Define the boundary of the root QuadTree
    boundary = AABB(center_x=250, center_y=250, half_width=250, half_height=250) # 500x500 area

    # Create a QuadTree with a capacity of 4 points per node
    qtree = QuadTree(boundary, capacity=4)

    # Insert some points with entity data
    points_to_insert = [
        ((100, 100), 'agent1', 10, 'agent'),
        ((150, 120), 'pickup1', 5, 'pickup'),
        ((400, 400), 'agent2', 12, 'agent'),
        ((380, 390), 'obstacle1', 20, 'obstacle'),
        ((110, 110), 'agent3', 8, 'agent'), # Near agent1
        ((105, 102), 'agent4', 9, 'agent'), # Very near agent1
        ((108, 115), 'agent5', 11, 'agent') # Near agent1 & agent3
    ]

    print("Inserting points...")
    for point, entity_id, radius, type in points_to_insert:
        qtree.insert(point, entity_id, radius, type)
        print(f"  Inserted {type} {entity_id} at {point}")

    # Define a query range
    query_area = AABB(center_x=120, center_y=110, half_width=30, half_height=30) # 60x60 box around (120, 110)

    print(f"\nQuerying area: Center=({query_area.center_x},{query_area.center_y}), HW={query_area.half_width}, HH={query_area.half_height}")
    # Query the QuadTree
    found = qtree.query_range(query_area)

    # Print the results
    print("\nEntities found in query range:")
    if found:
        for point, entity_id, radius, type in found:
            print(f"  - Point: {point}, ID: {entity_id}, Radius: {radius}, Type: {type}")
    else:
        print("  No entities found.")

    # Test clear
    print("\nClearing tree...")
    qtree.clear()
    print("Querying again after clear...")
    found_after_clear = qtree.query_range(query_area)
    print(f"Entities found: {len(found_after_clear)}") # Should be 0
    print(f"Total points in tree: {len(qtree.get_all_points())}") # Should be 0
