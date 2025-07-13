# Importing Libraries
import time
import threading
import numpy as np
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

# Creating Function Classes.
class MovementDirection(Enum):
    """Movement direction naming"""
    FORWARD = "forward"
    BACKWARD = "backward"
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    STOP = "stop"

@dataclass
class MovementCommand:
    """Movement commands that will be sent to PixHawk."""
    direction: MovementDirection
    power: float # Range: (0-100)%
    duration: Optional[float] = None # Unit: seconds
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class VelocityData:
    """Velocity Measurements"""
    vx: float = 0.0 # Forward/Backward (m/s)
    vy: float = 0.0 # Left/Right (m/s)
    vz: float = 0.0 # Up/Down (m/s)
    speed: float = 0.0 # Speed magnitude (m/s)
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        self.speed = np.sqrt(self.vx**2 + self.vy**2 + self.vz**2)

