# 🎮 Sense HAT Alert Dashboard v2.0🚨

## By Commander Crash 💉💾☠️

![Screenshot](https://github.com/CommanderCrash/SenseHat_LED_Message_System/blob/main/ScreenShots/Sensehat_alert.png "Web")

## 🌟 Features

- 🌡️ Real-time environmental monitoring
  - Temperature (°C/°F)
  - Humidity
  - Pressure
  - Dew point
  - Altitude
- 🎯 Motion sensor tracking
  - Gyroscope
  - Accelerometer
  - Magnetometer
- 💬 Message display system
  - Priority-based message queue
  - Customizable scroll speed and colors
  - Text-to-speech capability
- 🎨
  - Video background
  - Real-time updates
  - Mobile-responsive design
- 🔊 Audio feedback
  - Background music
  - Text-to-speech alerts
  - Custom sound effects

## 🔧 Prerequisites

### Hardware Requirements
- Raspberry Pi (3 or newer recommended)
- Sense HAT board
- Speakers/headphones (for audio features)

### Software Dependencies
```bash
# System packages
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev
sudo apt-get install -y espeak mplayer

# Python packages
pip3 install flask
pip3 install sense-hat
```

## 📦 Installation

1. Clone the repository:
```bash
git clone https://github.com/CommanderCrash/SenseHat_LED_Message_System.git
cd sense-hat-dashboard
```

2. Create required directories:
```bash
mkdir -p static/video static/audio
mkdir -p /mnt/ram  # For socket communication
```

3. Set up the RAM disk (optional, for better performance):
```bash
# Add to /etc/fstab:
tmpfs /mnt/ram tmpfs defaults,size=50M 0 0
```

4. Install dependencies:
```bash
pip3 install -r requirements.txt
```


## 🚀 Usage

1. Start the server:
```bash
python3 sense_hat_dashboard.py
```

2. Access the dashboard:
```
http://your-raspberry-pi-ip:5003
```

### 📝 Sending Messages

Messages can be sent through:
1. Web interface
2. Unix socket
3. TCP socket (port 5150)

Message format:
```
priority|message|[R,G,B]|speed|wav_path|use_espeak
wav path is Optional just as long as pipe "||" is used. 5 pipes ||||| needs to be set or it will not work.
```

Example:
```python
# Python example to send message
echo "0|hello |[255,0,0]|0.1|path_to_your_audio_alert_on_host.mp3|1" | nc -U /mnt/ram/sense_hat_socket # local
echo "0|hello |[255,0,0]|0.1||0" | nc -U /mnt/ram/sense_hat_socket # No audio alert and no espeak local
or
echo "0|hello |[255,0,0]|0.1|path_to_your_audio_alert_on_host.mp3|1" | nc <IP_addr> <port> # over network.
```

## 🛠️ Configuration

Default ports:
- Web interface: 5003
- TCP socket: 5150

Environment variables (optional):
```bash
export SENSE_WEB_PORT=5009
export SENSE_TCP_PORT=5159
export SENSE_SOCKET_PATH="/mnt/ram/sense_hat_socket"
```

## 📁 Project Structure

```
sense-hat-dashboard/
├── sense_hat_dashboard.py    # Main application
├── static/
│   ├── video/               # Video backgrounds
│   └── audio/               # Audio files
├── templates/
│   └── index.html           # Dashboard template
└── README.md                # This file
```

## 🔒 Security Considerations

- The server is accessible to all devices on the network
- Consider implementing authentication for production use
- TCP socket accepts connections from any IP
- Use firewall rules if needed

## 🐛 Troubleshooting

Common issues:

1. **Socket Error**
```bash
# Check socket permissions
sudo chmod 777 /mnt/ram/sense_hat_socket
```

2. **Video Not Playing**
```bash
# Verify video format
ffmpeg -i your-video.mp4 -c:v libx264 -c:a aac output.mp4
```

3. **Sense HAT Not Detected**
```bash
# Check I2C interface
sudo raspi-config
# Enable I2C under Interfacing Options
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Sense HAT team for the Python library
- Flask team for the web framework
- Tailwind CSS for styling
- Contributors and testers

## 📞 Contact

Create an issue for:
- 🐛 Bug reports
- 💡 Feature requests
- 🤔 Questions
- 💬 General feedback

## 🔄 Changelog

### v1.0.0
- ✨ Initial release
- 🎨 Cyberpunk theme
- 📊 Sensor monitoring
- 💬 Message system
- 🎵 Audio support
