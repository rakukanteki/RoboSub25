import yaml
import os

class ConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as file:
                    return yaml.safe_load(file)
            else:
                # Return default config if file doesn't exist
                return self.get_default_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.get_default_config()
    
    def get_default_config(self):
        """Return default configuration"""
        return {
            'pixhawk': {
                'connection': '/dev/ttyACM1',
                'timeout': 10
            },
            'mission': {
                'target_depth': 1.0,
                'stabilize_duration': 5,
                'forward_distance': 5.0,
                'hold_duration': 3,
                'spin_degrees': 720,
                'surface_timeout': 45
            },
            'cameras': {
                'front_device': 0,
                'down_device': 1,
                'resolution_front': [1280, 720],
                'resolution_down': [640, 480],
                'fps': 30
            },
            'control': {
                'depth_tolerance': 0.1,
                'heading_tolerance': 5,
                'default_speed': 500,
                'yaw_speed': 300
            }
        }
    
    def get(self, key_path, default=None):
        """Get configuration value using dot notation (e.g., 'pixhawk.connection')"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value