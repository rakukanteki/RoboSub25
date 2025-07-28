# Checking Camera:
Creating new python file.<br>
`nano file_name.py`<br>

Saving the code.<br>
`CTRL + O` -> `Enter` -> `CTRL + X`

Running the code.<br>
`python3 file_name.py`<br>

Check if OAK-D Camera Detected<br>
`lsusb | grep 03e7`<br>

# Manual Test Run:
__Run Code:__
```python
sudo python3 SafeAUVControl.py
```

__If connection fails:__
```terminal
# Check device exists
ls -la /dev/ttyACM*

# Fix permissions
sudo chmod 666 /dev/ttyACM1

# Add user to dialout group
sudo usermod -a -G dialout $USER
```

__For SSH Sessions:__
```ssh
ssh -X pi@192.168.2.2
screen /dev/ttyACM1
sudo python3 SafeAUVControl.py
```