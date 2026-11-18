from typing import Callable, Dict, List
from dataclasses import dataclass
from enum import Enum, auto
from collections import defaultdict

class EventType(Enum):
    PLAYER_DEATH = auto()
    PLAYER_SPAWN = auto()
    ENEMY_DEATH = auto()
    WEAPON_FIRED = auto()
    POWERUP_COLLECTED = auto()

class EventSystem:
    def __init__(self):
        self.listeners: Dict[EventType, List[Callable]] = defaultdict(list)
        
    def subscribe(self, event_type: EventType, callback: Callable):
        self.listeners[event_type].append(callback)
        
    def emit(self, event_type: EventType, data: dict):
        for callback in self.listeners[event_type]:
            callback(data)
