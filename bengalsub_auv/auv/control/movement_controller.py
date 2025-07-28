class MovementController:
    def __init__(self, pixhawk_interface):
        self.pixhawk = pixhawk_interface
        
    def move_forward(self, speed=500):
        """Move forward at specified speed"""
        return self.pixhawk.send_manual_control(x=speed, y=0, z=500, r=0)
    
    def move_backward(self, speed=500):
        """Move backward at specified speed"""
        return self.pixhawk.send_manual_control(x=-speed, y=0, z=500, r=0)
    
    def strafe_left(self, speed=500):
        """Strafe left at specified speed"""
        return self.pixhawk.send_manual_control(x=0, y=-speed, z=500, r=0)
    
    def strafe_right(self, speed=500):
        """Strafe right at specified speed"""
        return self.pixhawk.send_manual_control(x=0, y=speed, z=500, r=0)
    
    def move_up(self, speed=400):
        """Move up (surface) at specified speed"""
        z_value = 500 + speed  # Above neutral
        return self.pixhawk.send_manual_control(x=0, y=0, z=z_value, r=0)
    
    def move_down(self, speed=400):
        """Move down (dive) at specified speed"""
        z_value = 500 - speed  # Below neutral
        return self.pixhawk.send_manual_control(x=0, y=0, z=z_value, r=0)
    
    def yaw_left(self, speed=300):
        """Yaw left at specified speed"""
        return self.pixhawk.send_manual_control(x=0, y=0, z=500, r=-speed)
    
    def yaw_right(self, speed=300):
        """Yaw right at specified speed"""
        return self.pixhawk.send_manual_control(x=0, y=0, z=500, r=speed)
    
    def stop_all_movement(self):
        """Stop all movement - neutral position"""
        return self.pixhawk.send_manual_control(x=0, y=0, z=500, r=0)