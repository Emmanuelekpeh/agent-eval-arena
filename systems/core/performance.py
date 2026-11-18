import time
import psutil
import numpy as np
from collections import deque
from systems.utils.config import config

class PerformanceMonitor:
    def __init__(self, window_size=60):
        self.frame_times = deque(maxlen=window_size)
        self.memory_usage = deque(maxlen=window_size)
        self.cpu_usage = deque(maxlen=window_size)
        self.last_time = time.time()
        self.process = psutil.Process()
        
    def update(self):
        current_time = time.time()
        frame_time = current_time - self.last_time
        self.last_time = current_time
        
        self.frame_times.append(frame_time)
        self.memory_usage.append(self.process.memory_info().rss / 1024 / 1024)  # MB
        self.cpu_usage.append(self.process.cpu_percent())
        
    def get_metrics(self):
        return {
            'fps': 1.0 / np.mean(self.frame_times) if self.frame_times else 0,
            'frame_time_ms': np.mean(self.frame_times) * 1000,
            'memory_mb': np.mean(self.memory_usage),
            'cpu_percent': np.mean(self.cpu_usage),
            'frame_time_std': np.std(self.frame_times) * 1000
        }
    
    def should_adjust_quality(self):
        if not self.frame_times:
            return False
        
        avg_fps = 1.0 / np.mean(self.frame_times)
        return avg_fps < config.display['MIN_FPS']
