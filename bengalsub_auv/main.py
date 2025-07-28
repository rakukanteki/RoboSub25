# main.py - Main mission execution script
import sys
import time
import threading
import signal
import argparse
from datetime import datetime
import os

# Import AUV modules
from auv.control.pixhawk_interface import PixhawkInterface
from auv.control.movement_controller import MovementController
from auv.control.depth_controller import DepthController
from auv.control.heading_controller import HeadingController
from auv.sensors.bar30_depth import Bar30Sensor
from auv.vision.camera_recorder import CameraRecorder
from auv.utils.logger import Logger
from auv.utils.safety import SafetyManager
from auv.utils.config_manager import ConfigManager

class AUVMissionController:
    def __init__(self, config_path="config/main_config.yaml"):
        """Initialize AUV Mission Controller"""
        self.config = ConfigManager(config_path)
        self.logger = Logger("mission_controller")
        
        # Initialize components
        self.pixhawk = PixhawkInterface()
        self.movement = MovementController(self.pixhawk)
        self.depth_controller = DepthController(self.pixhawk)
        self.heading_controller = HeadingController(self.pixhawk)
        self.depth_sensor = Bar30Sensor()
        self.camera_recorder = CameraRecorder()
        self.safety = SafetyManager(self.pixhawk)
        
        # Mission state
        self.is_armed = False
        self.mission_active = False
        self.emergency_stop = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Handle emergency shutdown"""
        self.logger.warning(f"Received signal {signum}. Emergency shutdown initiated.")
        self.emergency_shutdown()
        sys.exit(0)
    
    def initialize_systems(self):
        """Initialize all AUV systems"""
        self.logger.info("Initializing AUV systems...")
        
        try:
            # Connect to Pixhawk
            if not self.pixhawk.connect():
                raise Exception("Failed to connect to Pixhawk")
            
            # Initialize depth sensor
            if not self.depth_sensor.initialize():
                raise Exception("Failed to initialize depth sensor")
            
            # Initialize cameras
            if not self.camera_recorder.initialize():
                raise Exception("Failed to initialize cameras")
            
            # Set initial mode
            if not self.pixhawk.set_mode('STABILIZE'):
                raise Exception("Failed to set STABILIZE mode")
            
            self.logger.info("✅ All systems initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ System initialization failed: {e}")
            return False
    
    def manual_arm(self):
        """Manual arm function"""
        if self.is_armed:
            self.logger.warning("AUV is already armed")
            return True
        
        try:
            self.logger.info("Manual arming initiated...")
            
            # Pre-arm checks
            if not self.safety.pre_arm_checks():
                self.logger.error("Pre-arm checks failed")
                return False
            
            # Arm the vehicle
            if not self.pixhawk.arm():
                self.logger.error("Failed to arm vehicle")
                return False
            
            # Start camera recording
            self.camera_recorder.start_recording()
            
            self.is_armed = True
            self.logger.info("✅ AUV armed successfully - Cameras recording")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Arming failed: {e}")
            return False
    
    def manual_disarm(self):
        """Manual disarm function"""
        if not self.is_armed:
            self.logger.warning("AUV is already disarmed")
            return True
        
        try:
            self.logger.info("Manual disarming initiated...")
            
            # Stop all movement
            self.movement.stop_all_movement()
            
            # Stop camera recording
            self.camera_recorder.stop_recording()
            
            # Disarm the vehicle
            if not self.pixhawk.disarm():
                self.logger.error("Failed to disarm vehicle")
                return False
            
            self.is_armed = False
            self.logger.info("✅ AUV disarmed successfully - Recording saved")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Disarming failed: {e}")
            return False
    
    def dive_to_depth(self, target_depth=1.0, timeout=30):
        """Step 1: Dive to specified depth (meters)"""
        self.logger.info(f"🏊 Step 1: Diving to {target_depth}m depth...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.emergency_stop:
                return False
            
            current_depth = self.depth_sensor.get_depth()
            self.logger.info(f"Current depth: {current_depth:.2f}m, Target: {target_depth}m")
            
            # Use depth controller to maintain target depth
            if self.depth_controller.set_target_depth(target_depth):
                if abs(current_depth - target_depth) < 0.1:  # Within 10cm tolerance
                    self.logger.info(f"✅ Reached target depth: {current_depth:.2f}m")
                    return True
            
            time.sleep(0.5)
        
        self.logger.error(f"❌ Failed to reach target depth within {timeout} seconds")
        return False
    
    def stabilize_position(self, duration=5):
        """Step 2: Stabilize at current position"""
        self.logger.info(f"⚖️  Step 2: Stabilizing for {duration} seconds...")
        
        # Get current position as reference
        current_depth = self.depth_sensor.get_depth()
        current_heading = self.pixhawk.get_heading()
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            if self.emergency_stop:
                return False
            
            # Maintain depth and heading
            self.depth_controller.set_target_depth(current_depth)
            self.heading_controller.set_target_heading(current_heading)
            
            remaining = duration - (time.time() - start_time)
            self.logger.info(f"Stabilizing... {remaining:.1f}s remaining")
            
            time.sleep(0.5)
        
        self.logger.info("✅ Stabilization complete")
        return True
    
    def move_forward_distance(self, distance=5.0, timeout=60):
        """Step 3: Move forward specified distance while maintaining depth"""
        self.logger.info(f"➡️  Step 3: Moving forward {distance}m while maintaining depth...")
        
        # Get initial position reference
        initial_depth = self.depth_sensor.get_depth()
        initial_heading = self.pixhawk.get_heading()
        
        # Calculate movement time based on speed (assuming 0.5 m/s forward speed)
        estimated_time = distance / 0.5
        
        start_time = time.time()
        
        while time.time() - start_time < min(estimated_time * 1.5, timeout):
            if self.emergency_stop:
                return False
            
            # Move forward while maintaining depth and heading
            self.movement.move_forward(speed=500)  # Medium forward speed
            self.depth_controller.set_target_depth(initial_depth)
            self.heading_controller.set_target_heading(initial_heading)
            
            elapsed = time.time() - start_time
            estimated_distance = elapsed * 0.5  # Rough distance estimation
            
            self.logger.info(f"Moving forward... Est. distance: {estimated_distance:.1f}m/{distance}m")
            
            if estimated_distance >= distance:
                self.movement.stop_all_movement()
                self.logger.info(f"✅ Completed {distance}m forward movement")
                return True
            
            time.sleep(0.1)
        
        self.movement.stop_all_movement()
        self.logger.error(f"❌ Failed to complete forward movement within timeout")
        return False
    
    def hold_position_and_spin(self, hold_duration=3, spin_degrees=720):
        """Step 4: Hold position for 3 seconds, then perform 720° yaw"""
        self.logger.info(f"🔄 Step 4: Holding position for {hold_duration}s, then spinning {spin_degrees}°...")
        
        current_depth = self.depth_sensor.get_depth()
        initial_heading = self.pixhawk.get_heading()
        
        # Phase 1: Hold position
        self.logger.info(f"Holding position for {hold_duration} seconds...")
        start_time = time.time()
        
        while time.time() - start_time < hold_duration:
            if self.emergency_stop:
                return False
            
            self.depth_controller.set_target_depth(current_depth)
            self.heading_controller.set_target_heading(initial_heading)
            
            remaining = hold_duration - (time.time() - start_time)
            self.logger.info(f"Holding... {remaining:.1f}s remaining")
            time.sleep(0.5)
        
        # Phase 2: Perform 720° spin
        self.logger.info(f"Starting {spin_degrees}° yaw rotation...")
        
        # Calculate target heading (720° = 2 full rotations)
        target_heading = (initial_heading + spin_degrees) % 360
        spin_speed = 300  # Moderate yaw speed
        
        # Estimated time for 720° at moderate speed (assuming ~90°/sec)
        estimated_spin_time = abs(spin_degrees) / 90.0
        start_spin_time = time.time()
        
        while time.time() - start_spin_time < estimated_spin_time * 1.5:  # 1.5x safety margin
            if self.emergency_stop:
                return False
            
            # Maintain depth while spinning
            self.depth_controller.set_target_depth(current_depth)
            
            # Continuous yaw movement
            self.movement.yaw_right(spin_speed)
            
            elapsed_spin = time.time() - start_spin_time
            estimated_rotation = elapsed_spin * 90  # Rough estimation
            
            self.logger.info(f"Spinning... Est. rotation: {estimated_rotation:.0f}°/{spin_degrees}°")
            
            if estimated_rotation >= spin_degrees:
                break
            
            time.sleep(0.1)
        
        # Stop spinning and return to original heading
        self.movement.stop_all_movement()
        self.heading_controller.set_target_heading(initial_heading)
        
        # Brief stabilization after spin
        time.sleep(2)
        
        self.logger.info("✅ Position hold and spin maneuver complete")
        return True
    
    def surface_and_disarm(self, timeout=45):
        """Step 5: Surface vertically and disarm"""
        self.logger.info("🔝 Step 5: Surfacing and disarming...")
        
        current_heading = self.pixhawk.get_heading()
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.emergency_stop:
                return False
            
            current_depth = self.depth_sensor.get_depth()
            
            # Surface by moving up and maintaining heading
            if current_depth > 0.2:  # Continue surfacing until 20cm depth
                self.movement.move_up(speed=400)  # Moderate ascent speed
                self.heading_controller.set_target_heading(current_heading)
                
                self.logger.info(f"Surfacing... Current depth: {current_depth:.2f}m")
            else:
                # Reached surface
                self.movement.stop_all_movement()
                self.logger.info("✅ Reached surface")
                
                # Disarm the vehicle
                return self.manual_disarm()
            
            time.sleep(0.5)
        
        self.logger.error("❌ Failed to surface within timeout")
        return False
    
    def run_automated_mission(self):
        """Execute the complete automated mission sequence"""
        if not self.is_armed:
            self.logger.error("❌ AUV must be armed before starting mission")
            return False
        
        self.mission_active = True
        self.logger.info("🚀 Starting automated mission sequence...")
        
        try:
            # Mission Steps
            steps = [
                ("Dive to 1m depth", lambda: self.dive_to_depth(1.0)),
                ("Stabilize position", lambda: self.stabilize_position(5)),
                ("Move forward 5m", lambda: self.move_forward_distance(5.0)),
                ("Hold and spin 720°", lambda: self.hold_position_and_spin(3, 720)),
                ("Surface and disarm", lambda: self.surface_and_disarm())
            ]
            
            for step_name, step_func in steps:
                if self.emergency_stop:
                    self.logger.error("❌ Mission aborted due to emergency stop")
                    return False
                
                self.logger.info(f"\n{'='*50}")
                self.logger.info(f"Executing: {step_name}")
                self.logger.info(f"{'='*50}")
                
                if not step_func():
                    self.logger.error(f"❌ Mission failed at step: {step_name}")
                    self.emergency_shutdown()
                    return False
                
                self.logger.info(f"✅ Completed: {step_name}")
                time.sleep(1)  # Brief pause between steps
            
            self.logger.info("\n🎉 MISSION COMPLETED SUCCESSFULLY! 🎉")
            self.mission_active = False
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Mission failed with exception: {e}")
            self.emergency_shutdown()
            return False
    
    def emergency_shutdown(self):
        """Emergency shutdown procedure"""
        self.logger.warning("🚨 EMERGENCY SHUTDOWN INITIATED")
        self.emergency_stop = True
        self.mission_active = False
        
        try:
            # Stop all movement immediately
            self.movement.stop_all_movement()
            
            # Emergency surface
            self.logger.info("Emergency surfacing...")
            start_time = time.time()
            while time.time() - start_time < 30:  # 30 second timeout
                depth = self.depth_sensor.get_depth()
                if depth <= 0.3:  # Close to surface
                    break
                self.movement.move_up(speed=600)  # Fast ascent
                time.sleep(0.1)
            
            # Stop movement and disarm
            self.movement.stop_all_movement()
            self.manual_disarm()
            
        except Exception as e:
            self.logger.error(f"Error during emergency shutdown: {e}")
    
    def print_status(self):
        """Print current AUV status"""
        print(f"\n{'='*50}")
        print(f"AUV STATUS")
        print(f"{'='*50}")
        print(f"Armed: {'✅' if self.is_armed else '❌'}")
        print(f"Mission Active: {'✅' if self.mission_active else '❌'}")
        print(f"Depth: {self.depth_sensor.get_depth():.2f}m")
        print(f"Heading: {self.pixhawk.get_heading():.1f}°")
        print(f"Connection: {'✅' if self.pixhawk.is_connected() else '❌'}")
        print(f"{'='*50}\n")

def main():
    parser = argparse.ArgumentParser(description='AUV Mission Controller')
    parser.add_argument('--arm', action='store_true', help='Arm the AUV')
    parser.add_argument('--disarm', action='store_true', help='Disarm the AUV')
    parser.add_argument('--mission', action='store_true', help='Run automated mission')
    parser.add_argument('--status', action='store_true', help='Show AUV status')
    
    args = parser.parse_args()
    
    # Initialize AUV controller
    auv = AUVMissionController()
    
    # Initialize systems
    if not auv.initialize_systems():
        print("❌ Failed to initialize AUV systems")
        sys.exit(1)
    
    try:
        if args.arm:
            auv.manual_arm()
        elif args.disarm:
            auv.manual_disarm()
        elif args.mission:
            if not auv.is_armed:
                print("Arming AUV for mission...")
                if not auv.manual_arm():
                    print("❌ Failed to arm AUV")
                    sys.exit(1)
            auv.run_automated_mission()
        elif args.status:
            auv.print_status()
        else:
            # Interactive mode
            print("""
🤖 AUV Mission Controller
Commands:
  arm     - Arm the AUV and start recording
  disarm  - Disarm the AUV and stop recording  
  mission - Run automated mission sequence
  status  - Show current status
  quit    - Exit program
            """)
            
            while True:
                try:
                    command = input("\nEnter command: ").strip().lower()
                    
                    if command == 'arm':
                        auv.manual_arm()
                    elif command == 'disarm':
                        auv.manual_disarm()
                    elif command == 'mission':
                        if not auv.is_armed:
                            print("Arming AUV for mission...")
                            if not auv.manual_arm():
                                continue
                        auv.run_automated_mission()
                    elif command == 'status':
                        auv.print_status()
                    elif command in ['quit', 'exit', 'q']:
                        break
                    else:
                        print("Invalid command")
                        
                except KeyboardInterrupt:
                    break
    
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    
    finally:
        # Ensure safe shutdown
        if auv.is_armed:
            auv.emergency_shutdown()

if __name__ == "__main__":
    main()