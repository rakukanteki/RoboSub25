import cv2
import threading
import time
from datetime import datetime
import os

class CameraRecorder:
    def __init__(self):
        self.front_camera = None
        self.down_camera = None
        self.recording = False
        self.front_writer = None
        self.down_writer = None
        self.record_thread = None
        
    def initialize(self):
        """Initialize both cameras"""
        try:
            # Initialize OAK-D front camera (usually /dev/video0 or specific OAK-D interface)
            self.front_camera = cv2.VideoCapture(0)  # Adjust device index
            if not self.front_camera.isOpened():
                raise Exception("Failed to open front camera")
            
            # Initialize downward camera (USB connected)
            self.down_camera = cv2.VideoCapture(1)  # Adjust device index
            if not self.down_camera.isOpened():
                print("Warning: Downward camera not available")
                self.down_camera = None
            
            # Set camera properties
            self.front_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.front_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.front_camera.set(cv2.CAP_PROP_FPS, 30)
            
            if self.down_camera:
                self.down_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.down_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.down_camera.set(cv2.CAP_PROP_FPS, 30)
            
            print("✅ Cameras initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Camera initialization failed: {e}")
            return False
    
    def start_recording(self):
        """Start recording from both cameras"""
        if self.recording:
            print("Already recording")
            return
        
        try:
            # Create timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create directories if they don't exist
            os.makedirs("data/recordings/front_camera", exist_ok=True)
            os.makedirs("data/recordings/down_camera", exist_ok=True)
            
            # Setup video writers
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            
            # Front camera writer
            front_filename = f"data/recordings/front_camera/mission_{timestamp}.avi"
            self.front_writer = cv2.VideoWriter(front_filename, fourcc, 30.0, (1280, 720))
            
            # Downward camera writer (if available)
            if self.down_camera:
                down_filename = f"data/recordings/down_camera/mission_{timestamp}.avi"
                self.down_writer = cv2.VideoWriter(down_filename, fourcc, 30.0, (640, 480))
            
            # Start recording thread
            self.recording = True
            self.record_thread = threading.Thread(target=self._recording_loop)
            self.record_thread.daemon = True
            self.record_thread.start()
            
            print(f"✅ Recording started - {timestamp}")
            
        except Exception as e:
            print(f"❌ Failed to start recording: {e}")
    
    def _recording_loop(self):
        """Main recording loop"""
        while self.recording:
            try:
                # Record front camera
                ret_front, frame_front = self.front_camera.read()
                if ret_front and self.front_writer:
                    self.front_writer.write(frame_front)
                
                # Record downward camera
                if self.down_camera and self.down_writer:
                    ret_down, frame_down = self.down_camera.read()
                    if ret_down:
                        self.down_writer.write(frame_down)
                
                time.sleep(1/30)  # 30 FPS
                
            except Exception as e:
                print(f"Recording error: {e}")
                break
    
    def stop_recording(self):
        """Stop recording and save videos"""
        if not self.recording:
            return
        
        self.recording = False
        
        # Wait for recording thread to finish
        if self.record_thread:
            self.record_thread.join(timeout=2)
        
        # Release video writers
        if self.front_writer:
            self.front_writer.release()
            self.front_writer = None
        
        if self.down_writer:
            self.down_writer.release()
            self.down_writer = None
        
        print("✅ Recording stopped and saved")
    
    def cleanup(self):
        """Clean up camera resources"""
        self.stop_recording()
        
        if self.front_camera:
            self.front_camera.release()
        if self.down_camera:
            self.down_camera.release()