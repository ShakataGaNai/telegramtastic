# telegramtastic
What do you get when you mash a receipt printer with Meshtastic? We'll find out!

## Requirements
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager

## Installation
1. Install uv if you haven't already:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Clone and setup the project:
   ```bash
   git clone https://github.com/shakataganai/telegramtastic.git
   cd telegramtastic
   uv sync
   ```

## Configuration
1. Copy the environment template:
   ```bash
   cp env.sample .env
   ```

2. Edit `.env` with your configuration:
   - `PRINTER_IP`: IP address of your thermal printer
   - `MQTT_SRV`: MQTT broker hostname
   - `MQTT_USER`: MQTT username
   - `MQTT_PASS`: MQTT password
   - `MQTT_PORT`: MQTT port (default: 1883)
   - `MQTT_TOPICS`: Comma-separated list of MQTT topics to subscribe to
   - `CHANNEL_KEY`: Base64 encoded channel key for decryption

## Usage

### Test Printer Connection
Before running the main application, test your printer connection:
```bash
uv run test-printer.py
```
This will print a test page with various formatting examples to verify your printer is working correctly.

### Run Main Application
```bash
uv run meshtelegram.py
```

### Print Messages Utility
```bash
uv run print-messages.py
```
