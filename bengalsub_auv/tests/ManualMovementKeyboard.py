from pymavlink import mavutil
import time
import keyboard  # pip install keyboard

# Connect to Pixhawk via MAVLink
master = mavutil.mavlink_connection('/dev/ttyACM1')  # or 'udp:0.0.0.0:14550''/dev/ttyAMA0' for serial
master.wait_heartbeat()
print(f"Connected to system {master.target_system}, component {master.target_component}")

# Arm the vehicle
master.arducopter_arm()
print("Vehicle armed!")

# Set to MANUAL mode
mode = 'MANUAL'
mode_id = master.mode_mapping()[mode]
master.set_mode(mode_id)
print(f"Mode set to {mode}")

# Default values
x = y = r = 0
z = 500           # Mid throttle (neutral heave)
speed = 500       # Default forward/backward speed (adjustable)

# Send manual control command
def send_manual_control(x=0, y=0, z=500, r=0):
    master.mav.manual_control_send(
        master.target_system,
        x,  # Forward/back
        y,  # Strafe
        z,  # Heave (up/down)
        r,  # Yaw
        0   # buttons
    )

print("""
✅ AUV Keyboard Control:
Controls:
    f = forward
    b = backward
    j = strafe left
    l = strafe right
    a = yaw left
    d = yaw right
    ↑ = float (z up)
    ↓ = dive (z down)
    t = throttle up
    g = throttle down
    space = stop
    q = quit
""")

try:
    while True:
        x = y = r = 0

        # --- Throttle adjustment ---
        if keyboard.is_pressed('t'):
            speed = min(speed + 50, 1000)
            print(f"Throttle increased: {speed}")
            time.sleep(0.2)  # Debounce
        elif keyboard.is_pressed('g'):
            speed = max(speed - 50, 100)
            print(f"Throttle decreased: {speed}")
            time.sleep(0.2)  # Debounce

        # --- Motion Controls ---
        if keyboard.is_pressed('f'):
            x = speed
        elif keyboard.is_pressed('b'):
            x = -speed

        if keyboard.is_pressed('j'):
            y = -speed
        elif keyboard.is_pressed('l'):
            y = speed

        if keyboard.is_pressed('a'):
            r = -speed
        elif keyboard.is_pressed('d'):
            r = speed

        if keyboard.is_pressed('up'):
            z = 600  # float up
        elif keyboard.is_pressed('down'):
            z = 400  # dive down
        else:
            z = 500  # neutral

        if keyboard.is_pressed('space'):
            x = y = r = 0
            z = 500
            print("Stop")

        if keyboard.is_pressed('q'):
            send_manual_control(0, 0, 500, 0)
            print("Quit")
            break

        send_manual_control(x, y, z, r)
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Keyboard interrupt. Stopping.")
    send_manual_control(0, 0, 500, 0)