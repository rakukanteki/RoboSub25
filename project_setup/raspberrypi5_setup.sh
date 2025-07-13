# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    i2c-tools \
    build-essential \
    git

# Enable I2C for barometer
sudo raspi-config nonint do_i2c 0