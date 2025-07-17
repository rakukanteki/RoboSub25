"""
Common functionalities of all mission types for BengalSub AUV
"""

import time
import threading
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
from ..utils.logger import AUVLogger
from ..utils.config_manager import ConfigManager
from ..utils.safety import SafetyManager

class MissionStatus(Enum):
    """Mission Status Provider"""
    NOT_STARTED =  "not_started"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    EMERGENCY = "emergency"
    TIMEOUT = "timeout"

class BaseMission(ABC):
    def __init__(self, config: ConfigManager, safety_manager: SafetyManager):
        self.config = config
        self.safety_manager = safety_manager
        self.logger = AUVLogger.get_logger("missions")

        # State of the mission
        self.current_state = None
        self.previous_state = None
        self.state_start_time = 0.0
        self.mission_start_time = 0.0
        self.status = MissionStatus.NOT_STARTED

        # Mission Control
        self.is_running = False
        self.is_paused = False
        self.mission_thread = Optional[threading.Thread] = None

        # Mission Parameters
        self.timeout = config.get("missions.default_timeout", 180.0) # 3 min
        self.state_history = []
        self.retry_counts = {}

        # Sensor and Control Interfaces
        self.sensor_manager = None
        self.movement_controller = None
        self.vision_system = None

        self.logger.info(f"{self._class_._name_} initialized")
    
    @abstractmethod
    def get_initial_state(self):
        """Get initial state for the mission."""
        pass
    
    @abstractmethod
    def get_state_methods(self) -> Dict[str, callable]:
        """Get mapping of state names to their handled"""
        pass

    @abstractmethod
    def cleanup_resources(self):
        """Clean up mission-specific resources"""
        pass

    def start_mission(self) -> bool:
        """Start the mission"""
        if self.is_running:
            self.logger.warning(f"{self.__class__.__name__} is already running")
            return False

        self.logger.info(f"Starting {self.__class__.__name__}")
        self.is_running = True
        self.status = MissionStatus.RUNNING
        self.mission_start_time = time.time()

        # Initialize the first state
        self.transition_to_state(self.get_initial_state())

        # Start mission thread
        self.mission_thread = threading.Thread(target=self._mission_loop)
        self.mission_thread.start()

        return True
    
    def stop_mission(self):
        """Stop mission execution"""
        if self.is_running:
            self.logger.info(f"Stopping {self.__class__.__name__}")
            self.is_running = False
            if self.mission_thread:
                self.mission_thread.join(timeout=5.0)

            self.cleanup_resources()

            if self.status == MissionStatus.RUNNING:
                self.status = MissionStatus.FAILURE

    def pause_mission(self):
        """Pause the mission execution"""
        self.is_paused = True
        self.logger.info(f"Paused {self.__class__.__name__}")

    def resume_mission(self):
        """Resume the mission execution"""
        self.is_paused = False
        self.logger.info(f"Resumed {self.__class__.__name__}")
    
    def emergency_stop(self):
        """Emergency stop the mission"""

        self.logger.critical(f"Emergency stop: {self.__class__.__name__}")
        self.status = MissionStatus.EMERGENCY
        self.is_running = False

        # Stop all movement
        if self.movement_controller:
            self.movement_controller.emergency_stop()

        self.cleanup_resources()
    
    def transition_to_state(self, new_state):
        """Transition to a new state"""
        if new_state == self.current_state:
            return

        self.logger.info(f"State Transition: {self.current_state} -> {new_state}")

        self.state_history.append({
            'from_state': self.current_state,
            'to_state': new_state,
            'timestamp': time.time(),
            'duration': time.time() - self.state_start_time if self.current_state else 0
        })

        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_start_time = time.time()


        if new_state not in self.retry_counts:
            self.retry_counts[new_state] = 0

    def get_state_duration(self) -> float:
        """Get duration of current state"""
        return time.time() - self.mission_start_time
    
    def check_timeout(self) -> bool:
        """Check if mission has timed out"""
        if self.get_mission_duration() > self.timeout:
            self.logger.error(f"Mission timeout after {self.timeout}s")
            self.status = MissionStatus.TIMEOUT
            return True
        return False
    
    def retry_current_state(self, max_retries: int=3) -> bool:
        """Retry current stae if under retry limit"""
        current_retries = self.retry_counts.get(self.current_state, 0)

        if current_retries < max_retries:
            self.retry_counts[self.current_state] = current_retries + 1
            self.logger.warning(f"Retrying {self.current_state} (attempt {current_retries+1}/{max_retries})")
            self.state_start_time = time.time()
            return True
        else:
            self.logger.error(f"Max retries ({max_retries}) reached for {self.current_state}")
            return False
        
    def _mission_loop(self):
        """Main mission execution loop"""
        state_methods = self.get_state_methods()

        try:
            while self.is_running:
                if self.is_paused:
                    time.sleep(0.1)
                    continue

                if self.check_timeout():
                    self.emergency_stop()
                    break
                
                # Execute current state
                if self.current_state in state_methods:
                    try:
                        state_methods[self.current_state]()
                    except Exception as e:
                        self.logger.error(f"Error in state {self.current_state}: {e}")
                        self.emergency_stop()
                        break
                else:
                    self.logger.error(f"Unknown state: {self.current_state}")
                    self.emergency_stop()
                    break

                time.sleep(0.1)

        except Exception as e:
            self.logger.error(f"Mission loop error: {e}")
            self.emergency_stop()

        finally:
            self.is_running = False
            self.logger.info(f"Mission loop ended with status: {self.status.value}")

    def get_mission_report(self) -> Dict[str, Any]:
        """Get comprehensive mission report"""
        return {
            'mission_name': self.__class__.__name__,
            'status': self.status.value,
            'duration': self.get_mission_duration(),
            'current_state': self.current_state,
            'state_history': self.state_history,
            'retry_counts': self.retry_counts,
            'timeout': self.timeout,
            'completed': self.status in [MissionStatus.SUCCESS, MissionStatus.FAILURE]
        }