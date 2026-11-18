import time
from typing import Dict, Any

class QualityManager:
    def __init__(self):
        self.settings = {
            'particle_count': 100,
            'max_entities': 50,
            'visual_effects': True,
            'draw_distance': 1000,
            'update_rate': 60
        }
        
        self.thresholds = {
            'min_fps': 30,
            'max_memory_mb': 1000,
            'cpu_threshold': 80
        }
        
        self.last_adjustment = time.time()
        self.adjustment_cooldown = 5.0  # Seconds between adjustments
        
    def adjust_quality(self, metrics: Dict[str, Any]) -> None:
        current_time = time.time()
        if current_time - self.last_adjustment < self.adjustment_cooldown:
            return
            
        if metrics['fps'] < self.thresholds['min_fps']:
            self._reduce_quality()
        elif metrics['memory_mb'] > self.thresholds['max_memory_mb']:
            self._reduce_quality()
        elif metrics['cpu_percent'] > self.thresholds['cpu_threshold']:
            self._reduce_quality()
            
        self.last_adjustment = current_time
    
    def _reduce_quality(self) -> None:
        if self.settings['particle_count'] > 20:
            self.settings['particle_count'] *= 0.8
        if self.settings['max_entities'] > 20:
            self.settings['max_entities'] -= 5
        if self.settings['draw_distance'] > 500:
            self.settings['draw_distance'] *= 0.9
        
    def get_settings(self) -> Dict[str, Any]:
        return self.settings.copy()
