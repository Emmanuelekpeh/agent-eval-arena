# systems/constants.py
import numpy as np
import math

# --- Constants for State Vector ---
MAX_NEARBY_AGENTS = 5
MAX_NEARBY_BULLETS = 10
MAX_NEARBY_PICKUPS = 3
MAX_NEARBY_HAZARDS = 3

# Define feature count per entity type (adjust as needed)
# Agent: (rel_x, rel_y, dist, health_norm, hostility) - hostility: 1=enemy, -1=ally, 0=neutral
AGENT_FEATURES = 5
# Bullet: (rel_x, rel_y, dist, is_hostile) - is_hostile: 1=yes, 0=no
BULLET_FEATURES = 4
# Hazard: (rel_x, rel_y, dist, type_id)
HAZARD_FEATURES = 4 # Renamed from Hazard_FEATURES
# Pickup: (rel_x, rel_y, dist, type_id)
PICKUP_FEATURES = 4

# Self: health_norm, energy_norm, sin(angle), cos(angle), can_shoot
SELF_FEATURES = 5 # Increased from 4 due to angle normalization
# Env: dist_to_safe_zone_edge_norm, safe_zone_radius_norm
ENV_FEATURES = 2

# Define the number of features added by Morale/Suppression System
MORALE_SUPPRESSION_FEATURES = 2

STATE_VECTOR_SIZE = (
    SELF_FEATURES + ENV_FEATURES +
    MAX_NEARBY_AGENTS * AGENT_FEATURES +
    MAX_NEARBY_BULLETS * BULLET_FEATURES +
    MAX_NEARBY_PICKUPS * PICKUP_FEATURES +
    MAX_NEARBY_HAZARDS * HAZARD_FEATURES +
    MORALE_SUPPRESSION_FEATURES # Added morale/suppression
)

# Action Constants (assuming these are the defined actions)
ACTION_IDLE = 0
ACTION_MOVE_FORWARD = 1
ACTION_ROTATE_LEFT = 2
ACTION_ROTATE_RIGHT = 3
ACTION_SHOOT = 4
ACTION_SET_TARGET = 5
# ... add other action IDs if they exist

# --- Mappings for Type IDs ---
PICKUP_TYPE_MAP = {'health': 1.0, 'energy': 2.0, 'shield': 3.0, 'weapon': 4.0, 'unknown': 0.0}
HAZARD_TYPE_MAP = {'fire': 1.0, 'poison': 2.0, 'acid': 3.0, 'unknown': 0.0} # Example hazard types 