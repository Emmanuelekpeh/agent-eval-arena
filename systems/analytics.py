import pandas as pd
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime

class BattleAnalytics:
    def __init__(self, save_dir='analytics'):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        self.metrics = defaultdict(list)
        self.agent_performance = defaultdict(lambda: defaultdict(list))
        
    def log_battle(self, battle_data):
        timestamp = datetime.now().isoformat()
        for agent_name, stats in battle_data.items():
            for metric, value in stats.items():
                self.agent_performance[agent_name][metric].append({
                    'value': value,
                    'timestamp': timestamp
                })
    
    def generate_report(self):
        report = {
            'agent_stats': self._analyze_agent_stats(),
            'learning_curves': self._generate_learning_curves(),
            'battle_summary': self._create_battle_summary()
        }
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(self.save_dir, f'report_{timestamp}.json')
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=4)
            
        return report
    
    def _analyze_agent_stats(self):
        stats = {}
        for agent_name, metrics in self.agent_performance.items():
            stats[agent_name] = {
                'avg_score': np.mean(metrics['score']),
                'max_score': max(metrics['score']),
                'win_rate': sum(1 for x in metrics['won'] if x) / len(metrics['won']),
                'survival_time': np.mean(metrics['survival_time'])
            }
        return stats
