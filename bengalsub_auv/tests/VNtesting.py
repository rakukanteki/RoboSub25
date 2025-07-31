import serial

def parse_vnins(line):
    try:
        parts = line.strip().split(',')
        if not line.startswith('$VNINS') or len(parts) < 15:
            return None

        yaw = float(parts[4])
        pitch = float(parts[5])
        roll = float(parts[6])
        lat = float(parts[7])
        lon = float(parts[8])
        alt = float(parts[9])
        vel_n = float(parts[10])
        vel_e = float(parts[11])
        vel_d = float(parts[12])
        accel_x = float(parts[13])
        accel_y = float(parts[14])
        accel_z = float(parts[15].split('*')[0])  # remove checksum

        return {
            "Yaw": yaw,
            "Pitch": pitch,
            "Roll": roll,
            "Latitude": lat,
            "Longitude": lon,
            "Altitude": alt,
            "Velocity": (vel_n, vel_e, vel_d),
            "Acceleration": (accel_x, accel_y, accel_z),
        }
    except Exception as e:
        print(f"[Parse Error] {e}")
        return None

def main():
    port = 'COM5'
    baud = 115200

    try:
        ser = serial.Serial(port, baud, timeout=1)
        print(f"[Connected] Reading VNINS from {port}...\n")

        while True:
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if line.startswith('$VNINS'):
                data = parse_vnins(line)
                if data:
                    print("============== VECTORNAV VNINS ==============")
                    print(f"Yaw      : {data['Yaw']:.2f}°")
                    print(f"Pitch    : {data['Pitch']:.2f}°")
                    print(f"Roll     : {data['Roll']:.2f}°")
                    print(f"Lat/Lon  : {data['Latitude']:.6f}, {data['Longitude']:.6f}")
                    print(f"Altitude : {data['Altitude']:.2f} m")
                    print(f"Velocity : N={data['Velocity'][0]:.2f}, E={data['Velocity'][1]:.2f}, D={data['Velocity'][2]:.2f} m/s")
                    print(f"Accel    : X={data['Acceleration'][0]:.2f}, Y={data['Acceleration'][1]:.2f}, Z={data['Acceleration'][2]:.2f} m/s²")
                    print("=============================================\n")

    except serial.SerialException as e:
        print(f"[Serial Error] {e}")
    except KeyboardInterrupt:
        print("\n[Terminated by User]")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
