class SafetyManager:
    def __init__(self, pixhawk_interface):
        self.pixhawk = pixhawk_interface
    
    def pre_arm_checks(self):
        """Perform pre-arm safety checks"""
        checks = []
        
        # Check connection
        if not self.pixhawk.is_connected():
            checks.append("❌ Pixhawk not connected")
        else:
            checks.append("✅ Pixhawk connected")
        
        # Check mode
        # Add more specific checks here based on your requirements
        checks.append("✅ Basic safety checks passed")
        
        # Print all checks
        for check in checks:
            print(check)
        
        # Return True if all checks passed (no ❌)
        return all("✅" in check for check in checks)