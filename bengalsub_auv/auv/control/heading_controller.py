class HeadingController:
    def __init__(self, pixhawk_interface):
        self.pixhawk = pixhawk_interface
        self.target_heading = 0.0
        
    def set_target_heading(self, heading):
        """Set target heading and maintain it"""
        self.target_heading = heading % 360
        current_heading = self.pixhawk.get_heading()
        
        # Calculate heading error
        heading_error = self.target_heading - current_heading
        
        # Handle wrap-around (shortest path)
        if heading_error > 180:
            heading_error -= 360
        elif heading_error < -180:
            heading_error += 360
        
        # Simple proportional control
        if abs(heading_error) < 5:  # Within 5 degrees tolerance
            r_value = 0
        else:
            r_value = max(-300, min(300, heading_error * 5))  # Proportional gain
        
        return self.pixhawk.send_manual_control(x=0, y=0, z=500, r=int(r_value))