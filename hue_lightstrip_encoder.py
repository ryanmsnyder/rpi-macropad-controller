#!/usr/bin/env python3
"""
BNK8 Encoder to MQTT - Philips Hue Desk Lightstrip Brightness Control
Listens for rotary encoder events and publishes to MQTT for Home Assistant
"""

import evdev
import logging
from logging.handlers import RotatingFileHandler
import paho.mqtt.client as mqtt
import signal
import sys
import threading

# Configure logging
log_handler = RotatingFileHandler(
    "/var/log/hue_lightstrip_encoder.log", maxBytes=1024 * 1024, backupCount=3
)
console_handler = logging.StreamHandler()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[log_handler, console_handler],
)

# MQTT Configuration
MQTT_BROKER = "YOUR_MQTT_BROKER_IP"  # e.g., "192.168.1.100"
MQTT_PORT = 1883
MQTT_USER = "your-mqtt-username"
MQTT_PASSWORD = "your-mqtt-password"
MQTT_TOPIC = "office/desk-lightstrip/brightness"

# Encoder device path
ENCODER_DEVICE = (
    "/dev/input/by-id/usb-binepad_BNK8_240036000C0000325953574E00000000-event-if01"
)

# Batching configuration
BATCH_DELAY = 0.3  # seconds to wait before sending accumulated value
STEP_SIZE = 5  # brightness percentage per encoder click


def main():
    mqtt_client = None
    device = None
    accumulated_steps = 0
    batch_timer = None
    lock = threading.Lock()

    def send_accumulated():
        nonlocal accumulated_steps
        with lock:
            if accumulated_steps != 0:
                total_change = accumulated_steps * STEP_SIZE
                logging.info(f"Sending batched brightness change: {total_change}%")
                mqtt_client.publish(MQTT_TOPIC, str(total_change))
                accumulated_steps = 0

    def handle_encoder_event(direction):
        nonlocal accumulated_steps, batch_timer
        with lock:
            accumulated_steps += direction
            logging.info(
                f"Encoder {'CW' if direction > 0 else 'CCW'} (accumulated: {accumulated_steps})"
            )

            # Cancel existing timer and start a new one
            if batch_timer:
                batch_timer.cancel()
            batch_timer = threading.Timer(BATCH_DELAY, send_accumulated)
            batch_timer.start()

    def cleanup(sig=None, frame=None):
        nonlocal batch_timer
        logging.info("Shutting down...")
        if batch_timer:
            batch_timer.cancel()
        if device:
            device.close()
        if mqtt_client:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Connect to MQTT
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        logging.info(f"Connected to MQTT broker at {MQTT_BROKER}")
    except Exception as e:
        logging.error(f"Failed to connect to MQTT: {e}")
        return

    # Open encoder device
    try:
        device = evdev.InputDevice(ENCODER_DEVICE)
        logging.info(f"Listening to encoder: {device.name}")
    except Exception as e:
        logging.error(f"Failed to open encoder device: {e}")
        return

    # Main event loop
    logging.info("Hue desk lightstrip brightness controller started (with batching)")
    try:
        for event in device.read_loop():
            if event.type == evdev.ecodes.EV_KEY and event.value == 1:
                if event.code == evdev.ecodes.KEY_BRIGHTNESSUP:
                    handle_encoder_event(1)
                elif event.code == evdev.ecodes.KEY_BRIGHTNESSDOWN:
                    handle_encoder_event(-1)
    except Exception as e:
        logging.error(f"Error in event loop: {e}")
    finally:
        cleanup()


if __name__ == "__main__":
    main()
