class DepthController:
    def __init__(self, pixhawk_interface):
        self.pixhawk = pixhawk_interface
        self.target_depth = 0.0
        self.current_depth = 0.0
        
    def set_target_depth(self, depth):
        """Set target depth and maintain it"""
        from auv.sensors.bar30_depth import Bar30Sensor
        
        self.target_depth = depth
        
        # Get current depth (this would normally be passed in or obtained from sensor)
        depth_sensor = Bar30Sensor()
        self.current_depth = depth_sensor.get_depth()
        
        # Simple depth control
        depth_error = self.target_depth - self.current_depth
        
        if abs(depth_error) < 0.1:  # Within 10cm tolerance
            # Maintain neutral
            z_value = 500
        elif depth_error > 0:  # Need to go deeper
            z_value = 500 - min(400, abs(depth_error) * 200)  # Proportional control
        else:  # Need to surface
            z_value = 500 + min(400, abs(depth_error) * 200)  # Proportional control
        
        return self.pixhawk.send_manual_control(x=0, y=0, z=int(z_value), r=0)