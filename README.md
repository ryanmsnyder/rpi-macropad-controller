# Raspberry Pi Macro Pad Controller

A Raspberry Pi Zero W project that transforms a BNK8 macro pad into a powerful desktop automation tool:
- **Buttons**: Switch monitor inputs via DDC/CI and control a USB switch
- **Rotary Encoder**: Control Philips Hue lightstrip brightness via MQTT

## System Architecture

```
                              ┌─────────────────────────────────────────────────────────┐
                              │                    Raspberry Pi Zero W                   │
                              │                                                          │
[BNK8 Macro Pad] ──(USB)───>  │  ┌─────────────────┐     ┌────────────────────────┐     │
                              │  │ ddc_switcher.py │     │ hue_lightstrip_encoder │     │
  Buttons ─────────────────>  │  │                 │     │         .py            │     │
  (F22, F23, F24)             │  │  • DDC/CI cmds  │     │  • MQTT publish        │     │
                              │  │  • GPIO pulses  │     │  • Event batching      │     │
  Encoder ─────────────────>  │  └────────┬────────┘     └───────────┬────────────┘     │
  (Brightness Up/Down)        │           │                          │                  │
                              └───────────┼──────────────────────────┼──────────────────┘
                                          │                          │
                           ┌──────────────┼──────────────┐           │
                           │              │              │           │
                           ▼              ▼              ▼           ▼
                      [Monitor]    [USB Switch]    [GPIO]      [MQTT Broker]
                       DDC/CI       via GPIO      Optocouplers       │
                                                                     ▼
                                                              [Home Assistant]
                                                                     │
                                                                     ▼
                                                              [Hue Lightstrip]
```

## Features

### Monitor & USB Switching (Buttons)
- **One-button switching** between DisplayPort, USB-C, and HDMI inputs
- **USB switch control** via GPIO optocouplers for keyboard/mouse switching
- **HDMI + Standby mode** - Switch to HDMI and activate monitor standby with a single button
- **Automatic startup** on Pi boot
- **Comprehensive logging** with automatic rotation

### Hue Lightstrip Control (Rotary Encoder)
- **Brightness control** via rotary encoder rotation
- **MQTT integration** with Home Assistant/Node-RED
- **Smart batching** - Accumulates rapid turns and sends one command (300ms delay)
- **Configurable step size** - Default 5% brightness per click

## Hardware Requirements

### Core Components
| Component | Purpose | Notes |
|-----------|---------|-------|
| Raspberry Pi Zero W | Main controller | WiFi for SSH and MQTT |
| Binepad BNK8 Macro Pad | Input device | QMK-compatible with rotary encoder |
| Micro USB OTG Adapter | Macro pad connection | Enables USB host mode |
| Mini HDMI Cable | Pi to monitor | For DDC/CI communication |
| DDC/CI Compatible Monitor | Display | Tested with Dell U2720Q |

### For USB Switching (Optional)
| Component | Purpose |
|-----------|---------|
| Optocouplers (2x) | Isolated GPIO switching |
| USB Switch | Multi-computer USB sharing |

### For Hue Lightstrip Control
| Component | Purpose |
|-----------|---------|
| MQTT Broker | Message transport (e.g., Mosquitto) |
| Home Assistant | Automation platform with Hue integration |
| Philips Hue Lightstrip | Controllable light |
| Node-RED (Optional) | Flow-based MQTT to Hue bridge |

## Quick Start

### 1. Hardware Setup
See [docs/hardware-setup.md](docs/hardware-setup.md) for detailed hardware configuration.

### 2. Software Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ddc-monitor-switcher.git
cd ddc-monitor-switcher

# Install dependencies
sudo apt update
sudo apt install python3-evdev python3-paho-mqtt i2c-tools

# Enable I2C interface
sudo raspi-config
# Navigate to: Interface Options > I2C > Enable

# Copy scripts to home directory
cp ddc_switcher.py ~/
cp hue_lightstrip_encoder.py ~/
chmod +x ~/ddc_switcher.py ~/hue_lightstrip_encoder.py
```

### 3. Configure Your Monitor

```bash
# Find your monitor's I2C bus
sudo i2cdetect -l

# Test DDC communication (replace X with your bus number)
sudo ddcutil detect --bus=X

# Test input switching
sudo ddcutil setvcp 60 15 --bus=X  # DisplayPort
sudo ddcutil setvcp 60 27 --bus=X  # USB-C
```

### 4. Program Your Macro Pad (QMK)

The BNK8 requires QMK firmware changes for the encoder to send brightness keys:

**In your keymap (`keymap.c`):**
```c
const uint16_t PROGMEM encoder_map[][NUM_ENCODERS][NUM_DIRECTIONS] = {
    [0] = {ENCODER_CCW_CW(KC_BRID, KC_BRIU)},  // Brightness Down/Up
    [1] = {ENCODER_CCW_CW(RM_VALD, RM_VALU)}   // RGB brightness (Layer 1)
};
```

**In `rules.mk`:**
```makefile
ENCODER_MAP_ENABLE = yes
```

**In `keyboard.json` (fix double-triggering):**
```json
"encoder": {
    "rotary": [
        {"pin_a": "A7", "pin_b": "A0", "resolution": 4}
    ]
}
```

Button mappings (via VIA or QMK):
- **Button 1**: F23 (DisplayPort + USB Input 1)
- **Button 2**: F24 (USB-C + USB Input 2)
- **Button 3**: F22 (HDMI + Standby)

### 5. Configure MQTT (for Lightstrip)

Edit `~/hue_lightstrip_encoder.py` with your MQTT settings:

```python
MQTT_BROKER = "192.168.1.2"  # Your MQTT broker IP
MQTT_PORT = 1883
MQTT_USER = "your-username"
MQTT_PASSWORD = "your-password"
MQTT_TOPIC = "office/desk-lightstrip/brightness"
```

### 6. Configure Node-RED Flow

Create a flow to translate MQTT messages to Hue commands:

```
[MQTT In] → [Function] → [Call Service]
```

**Function node:**
```javascript
msg.payload = { brightness_step_pct: parseInt(msg.payload) };
return msg;
```

**Call Service node:**
- Domain: `light`
- Service: `turn_on`
- Entity: `light.your_hue_lightstrip_entity_id`

### 7. Install as System Services

```bash
# Copy service files
sudo cp ddc-switcher.service /etc/systemd/system/
sudo cp hue-lightstrip-encoder.service /etc/systemd/system/

# Enable and start the services
sudo systemctl daemon-reload
sudo systemctl enable ddc-switcher.service hue-lightstrip-encoder.service
sudo systemctl start ddc-switcher.service hue-lightstrip-encoder.service

# Check service status
sudo systemctl status ddc-switcher.service
sudo systemctl status hue-lightstrip-encoder.service
```

## Usage

### Monitor/USB Switching (Buttons)
| Button | Action |
|--------|--------|
| Button 1 (F23) | Switch to DisplayPort + USB Input 1 (Computer A) |
| Button 2 (F24) | Switch to USB-C + USB Input 2 (Computer B) |
| Button 3 (F22) | Switch to HDMI + Standby mode |

### Lightstrip Control (Encoder)
| Action | Result |
|--------|--------|
| Rotate clockwise | Increase brightness |
| Rotate counter-clockwise | Decrease brightness |

The encoder uses batching: rapid rotations are accumulated and sent as a single MQTT message after 300ms of inactivity. This prevents overwhelming the Hue bridge with commands.

## Configuration

### Monitor Input Codes (`ddc_switcher.py`)

```python
self.inputs = {
    'displayport': 15,  # VCP code for DisplayPort
    'usbc': 27,         # VCP code for USB-C
    'hdmi': 17,         # VCP code for HDMI
}
```

### Button Mapping (`ddc_switcher.py`)

```python
self.button_mapping = {
    evdev.ecodes.KEY_F23: 'displayport',
    evdev.ecodes.KEY_F24: 'usbc',
    evdev.ecodes.KEY_F22: 'hdmi_standby',
}
```

### Encoder Settings (`hue_lightstrip_encoder.py`)

```python
BATCH_DELAY = 0.3  # Seconds to wait before sending accumulated value
STEP_SIZE = 5      # Brightness percentage per encoder click
```

### Encoder Device Path

The encoder is on a separate input device from the buttons:
```python
ENCODER_DEVICE = '/dev/input/by-id/usb-binepad_BNK8_...-event-if01'
```

Find your device with:
```bash
ls /dev/input/by-id/ | grep BNK8
```

## Monitoring

```bash
# View service status
sudo systemctl status ddc-switcher.service
sudo systemctl status hue-lightstrip-encoder.service

# View real-time logs
sudo journalctl -u ddc-switcher.service -f
sudo journalctl -u hue-lightstrip-encoder.service -f

# View log files
tail -f /var/log/ddc_switcher.log
tail -f /var/log/hue_lightstrip_encoder.log
```

## Troubleshooting

### Service Not Starting
```bash
# Check service logs
sudo journalctl -u ddc-switcher.service -n 50
sudo journalctl -u hue-lightstrip-encoder.service -n 50

# Test scripts manually
sudo python3 ~/ddc_switcher.py
sudo python3 ~/hue_lightstrip_encoder.py
```

### Encoder Not Working
- Verify encoder is on the correct device (`-event-if01`, not `-event-if00`)
- Check QMK firmware has `ENCODER_MAP_ENABLE = yes`
- Ensure encoder resolution is set to 4 (not 2) to prevent double-triggering

### MQTT Connection Failed
```bash
# Test MQTT connectivity
mosquitto_pub -h YOUR_BROKER -u USER -P PASS -t test -m "hello"

# Check broker is reachable
ping YOUR_MQTT_BROKER_IP
```

### DDC Commands Failing
```bash
# Check I2C bus
sudo i2cdetect -l

# Test DDC communication
sudo ddcutil detect

# Check monitor capabilities
sudo ddcutil capabilities
```

## Project Structure

```
ddc-monitor-switcher/
├── README.md                       # This file
├── ddc_switcher.py                 # Monitor + USB switch control (buttons)
├── hue_lightstrip_encoder.py       # Hue lightstrip brightness (encoder)
├── ddc-switcher.service            # Systemd service for DDC switcher
├── hue-lightstrip-encoder.service  # Systemd service for encoder
└── docs/
    └── hardware-setup.md           # Detailed hardware guide
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [ddcutil](http://www.ddcutil.com/) for DDC/CI communication
- [evdev](https://python-evdev.readthedocs.io/) for input device handling
- [QMK](https://qmk.fm/) for macro pad firmware
- [paho-mqtt](https://eclipse.org/paho/) for MQTT client
- [Home Assistant](https://www.home-assistant.io/) for home automation
