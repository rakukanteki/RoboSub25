from pymavlink import mavutil
import time
import threading

class PixhawkInterface:
    def __init__(self, connection_string='/dev/ttyACM1'):
        self.connection_string = connection_string
        self.master = None
        self.is_connected_flag = False
        self.heartbeat_thread = None
        self.stop_heartbeat = False
        
    def connect(self, timeout=10):
        """Connect to Pixhawk"""
        try:
            self.master = mavutil.mavlink_connection(self.connection_string, timeout=timeout)
            heartbeat = self.master.wait_heartbeat(timeout=timeout)
            if heartbeat:
                self.is_connected_flag = True
                self.start_heartbeat_monitor()
                return True
            return False
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def start_heartbeat_monitor(self):
        """Start heartbeat monitoring thread"""
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_monitor)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
    
    def _heartbeat_monitor(self):
        """Monitor heartbeat messages"""
        last_heartbeat = time.time()
        while not self.stop_heartbeat and self.is_connected_flag:
            msg = self.master.recv_match(type='HEARTBEAT', blocking=False)
            if msg:
                last_heartbeat = time.time()
            elif time.time() - last_heartbeat > 5:  # 5 seconds timeout
                self.is_connected_flag = False
                break
            time.sleep(0.1)
    
    def is_connected(self):
        return self.is_connected_flag
    
    def arm(self):
        """Arm the vehicle"""
        try:
            self.master.arducopter_arm()
            # Wait for confirmation
            start_time = time.time()
            while time.time() - start_time < 10:
                msg = self.master.recv_match(type='HEARTBEAT', blocking=False)
                if msg and msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:
                    return True
                time.sleep(0.1)
            return False
        except Exception:
            return False
    
    def disarm(self):
        """Disarm the vehicle"""
        try:
            self.master.arducopter_disarm()
            time.sleep(1)  # Give time for disarm
            return True
        except Exception:
            return False
    
    def set_mode(self, mode):
        """Set flight mode"""
        try:
            if mode not in self.master.mode_mapping():
                return False
            mode_id = self.master.mode_mapping()[mode]
            self.master.set_mode(mode_id)
            return True
        except Exception:
            return False
    
    def send_manual_control(self, x=0, y=0, z=500, r=0):
        """Send manual control command"""
        try:
            self.master.mav.manual_control_send(
                self.master.target_system,
                int(x), int(y), int(z), int(r), 0
            )
            return True
        except Exception:
            return False
    
    def get_heading(self):
        """Get current heading from IMU"""
        try:
            msg = self.master.recv_match(type='ATTITUDE', blocking=False)
            if msg:
                # Convert radians to degrees
                heading = (msg.yaw * 180 / 3.14159) % 360
                return heading
            return 0.0
        except Exception:
            return 0.0
    
    def close(self):
        """Close connection"""
        self.stop_heartbeat = True
        self.is_connected_flag = False
        if self.master:
            self.master.close()