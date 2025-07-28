from pymavlink import mavutil
import time
import keyboard  
import sys
import signal

class SafeAUVController:
    def __init__(self, connection_string='/dev/ttyACM1'):
        self.master = None
        self.connection_string = connection_string
        self.is_armed = False
        self.current_mode = None
        
        # Default values
        self.x = self.y = self.r = 0
        self.z = 500           # Mid throttle (neutral heave)
        self.speed = 500       # Default forward/backward speed
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C and other termination signals"""
        print(f"\nReceived signal {signum}. Shutting down safely...")
        self.emergency_stop()
        sys.exit(0)
    
    def connect_to_pixhawk(self, timeout=10):
        """Establish connection to Pixhawk with error handling"""
        try:
            print(f"Connecting to Pixhawk at {self.connection_string}...")
            self.master = mavutil.mavlink_connection(self.connection_string, timeout=timeout)
            
            print("Waiting for heartbeat...")
            heartbeat = self.master.wait_heartbeat(timeout=timeout)
            if heartbeat is None:
                raise Exception("No heartbeat received within timeout")
                
            print(f"✅ Connected to system {self.master.target_system}, component {self.master.target_component}")
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("Tips:")
            print("- Check if device exists: ls -la /dev/ttyACM*")
            print("- Check permissions: sudo chmod 666 /dev/ttyACM1")
            print("- Add user to dialout group: sudo usermod -a -G dialout $USER")
            return False
    
    def check_pre_arm_status(self):
        """Check if vehicle is ready to arm"""
        try:
            # Request system status
            self.master.mav.command_long_send(
                self.master.target_system,
                self.master.target_component,
                mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,
                0,
                mavutil.mavlink.MAVLINK_MSG_ID_SYS_STATUS,
                0, 0, 0, 0, 0, 0
            )
            
            # Wait for response
            msg = self.master.recv_match(type='SYS_STATUS', blocking=True, timeout=5)
            if msg:
                print(f"System status received. Sensors health: {msg.onboard_control_sensors_health}")
            
        except Exception as e:
            print(f"Warning: Could not check pre-arm status: {e}")
    
    def arm_vehicle(self):
        """Arm the vehicle with verification"""
        try:
            print("Checking pre-arm status...")
            self.check_pre_arm_status()
            
            print("Attempting to arm vehicle...")
            self.master.arducopter_arm()
            
            # Wait for arm confirmation
            start_time = time.time()
            while time.time() - start_time < 10:  # 10 second timeout
                msg = self.master.recv_match(type='HEARTBEAT', blocking=False)
                if msg and msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:
                    self.is_armed = True
                    print("✅ Vehicle armed successfully!")
                    return True
                time.sleep(0.1)
            
            print("❌ Vehicle failed to arm within timeout")
            print("Common issues:")
            print("- Pre-arm checks failing")
            print("- Safety switch not pressed")
            print("- Bad GPS or compass calibration")
            print("- Low battery")
            return False
            
        except Exception as e:
            print(f"❌ Arming failed: {e}")
            return False
    
    def set_mode(self, mode='MANUAL'):
        """Set vehicle mode with verification"""
        try:
            if mode not in self.master.mode_mapping():
                print(f"❌ Invalid mode: {mode}")
                print(f"Available modes: {list(self.master.mode_mapping().keys())}")
                return False
            
            mode_id = self.master.mode_mapping()[mode]
            print(f"Setting mode to {mode}...")
            self.master.set_mode(mode_id)
            
            # Wait for mode confirmation
            start_time = time.time()
            while time.time() - start_time < 5:  # 5 second timeout
                msg = self.master.recv_match(type='HEARTBEAT', blocking=False)
                if msg:
                    current_mode = mavutil.mode_string_v10(msg)
                    if current_mode == mode:
                        self.current_mode = mode
                        print(f"✅ Mode set to {mode}")
                        return True
                time.sleep(0.1)
            
            print(f"❌ Mode change to {mode} failed or not confirmed")
            return False
            
        except Exception as e:
            print(f"❌ Mode setting failed: {e}")
            return False
    
    def send_manual_control(self, x=0, y=0, z=500, r=0):
        """Send manual control command with bounds checking"""
        try:
            # Clamp values to valid range (-1000 to 1000, except z which is 0-1000)
            x = max(-1000, min(1000, int(x)))
            y = max(-1000, min(1000, int(y)))
            z = max(0, min(1000, int(z)))
            r = max(-1000, min(1000, int(r)))
            
            self.master.mav.manual_control_send(
                self.master.target_system,
                x,  # Forward/back
                y,  # Strafe
                z,  # Heave (up/down)
                r,  # Yaw
                0   # buttons
            )
            
        except Exception as e:
            print(f"❌ Failed to send manual control: {e}")
    
    def emergency_stop(self):
        """Emergency stop - neutral all controls and disarm"""
        try:
            print("🚨 EMERGENCY STOP ACTIVATED")
            
            # Send neutral controls multiple times
            for _ in range(5):
                self.send_manual_control(0, 0, 500, 0)
                time.sleep(0.1)
            
            # Disarm if armed
            if self.is_armed:
                print("Disarming vehicle...")
                self.master.arducopter_disarm()
                self.is_armed = False
            
            # Close connection
            if self.master:
                self.master.close()
                print("Connection closed")
                
        except Exception as e:
            print(f"Error during emergency stop: {e}")
    
    def print_controls(self):
        """Display control instructions"""
        print("""
✅ AUV Keyboard Control - SAFE VERSION:
Controls:
    f = forward          b = backward
    j = strafe left      l = strafe right  
    a = yaw left         d = yaw right
    ↑ = float (z up)     ↓ = dive (z down)
    t = throttle up      g = throttle down
    space = stop         e = EMERGENCY STOP
    q = quit

Safety Features:
- Bounds checking on all control values
- Graceful shutdown on Ctrl+C
- Emergency stop function
- Connection monitoring
- Pre-arm status checking

Current Settings:
    Speed: {self.speed}
    Armed: {self.is_armed}
    Mode: {self.current_mode}
""")
    
    def run(self):
        """Main control loop"""
        # Initialize connection
        if not self.connect_to_pixhawk():
            return False
        
        # Set mode
        if not self.set_mode('MANUAL'):
            return False
        
        # Arm vehicle
        if not self.arm_vehicle():
            print("Continuing without arming (for testing)")
        
        self.print_controls()
        
        try:
            last_heartbeat = time.time()
            
            while True:
                # Reset controls
                self.x = self.y = self.r = 0
                
                # Check connection health
                current_time = time.time()
                msg = self.master.recv_match(type='HEARTBEAT', blocking=False)
                if msg:
                    last_heartbeat = current_time
                elif current_time - last_heartbeat > 5:  # 5 seconds without heartbeat
                    print("⚠️  Warning: No heartbeat received for 5 seconds")
                    last_heartbeat = current_time  # Reset to avoid spam
                
                # --- Throttle adjustment ---
                if keyboard.is_pressed('t'):
                    self.speed = min(self.speed + 50, 1000)
                    print(f"Throttle increased: {self.speed}")
                    time.sleep(0.2)  # Debounce
                elif keyboard.is_pressed('g'):
                    self.speed = max(self.speed - 50, 100)
                    print(f"Throttle decreased: {self.speed}")
                    time.sleep(0.2)  # Debounce
                
                # --- Motion Controls ---
                if keyboard.is_pressed('f'):
                    self.x = self.speed
                elif keyboard.is_pressed('b'):
                    self.x = -self.speed
                
                if keyboard.is_pressed('j'):
                    self.y = -self.speed
                elif keyboard.is_pressed('l'):
                    self.y = self.speed
                
                if keyboard.is_pressed('a'):
                    self.r = -self.speed
                elif keyboard.is_pressed('d'):
                    self.r = self.speed
                
                if keyboard.is_pressed('up'):
                    self.z = 600  # float up
                elif keyboard.is_pressed('down'):
                    self.z = 400  # dive down
                else:
                    self.z = 500  # neutral
                
                # --- Special Commands ---
                if keyboard.is_pressed('space'):
                    self.x = self.y = self.r = 0
                    self.z = 500
                    print("🛑 Stop")
                
                if keyboard.is_pressed('e'):
                    self.emergency_stop()
                    print("Emergency stop activated!")
                    break
                
                if keyboard.is_pressed('q'):
                    print("Quitting...")
                    break
                
                # Send control command
                self.send_manual_control(self.x, self.y, self.z, self.r)
                time.sleep(0.1)
        
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
        
        finally:
            self.emergency_stop()

def main():
    # Check if running as root (required for keyboard library)
    import os
    if os.geteuid() != 0:
        print("❌ This script requires root privileges for keyboard access")
        print("Please run: sudo python3 ManualMovementKeyboard.py")
        return
    
    # Create and run controller
    controller = SafeAUVController('/dev/ttyACM1')
    controller.run()

if __name__ == "__main__":
    main()