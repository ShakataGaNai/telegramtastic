# telegramtastic
What do you get when you mash a receipt printer with Meshtastic? We'll find out!

## Requirements
- **Docker** (recommended) or Python 3.13+ with [uv](https://github.com/astral-sh/uv)
- Thermal printer (network or USB)
- Access to Meshtastic MQTT broker

## Installation

### Option 1: Docker (Recommended)
1. Pull the pre-built image from GitHub Container Registry:
   ```bash
   docker pull ghcr.io/shakataganai/telegramtastic:latest
   ```

2. Create your configuration file:
   ```bash
   cp env.sample .env
   # Edit .env with your configuration
   # IMPORTANT: No spaces around = signs (KEY=value not KEY = value)
   ```

3. Run the container:
   ```bash
   docker run -d --name telegramtastic \
     --env-file .env \
     -v $(pwd)/data:/app/data \
     --device /dev/usb/lp0:/dev/usb/lp0 \
     ghcr.io/shakataganai/telegramtastic:latest
   ```

### Option 2: Local Development
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

   **Important**: When editing the .env file, ensure there are no spaces around the `=` signs. Use `KEY=value` format, not `KEY = value`. This is required for Docker compatibility.

2. Edit `.env` with your configuration:
   
   **Printer Configuration:**
   - `PRINTER_TYPE`: Set to either "network" or "usb"
   - For network printers:
     - `PRINTER_IP`: IP address of your thermal printer
   - For USB printers:
     - `PRINTER_USB_VENDOR_ID`: Vendor ID in hex format (e.g., 0x04b8)
     - `PRINTER_USB_PRODUCT_ID`: Product ID in hex format (e.g., 0x0202)
     - OR `PRINTER_USB_DEVICE`: Device path (e.g., /dev/usb/lp0)
   
   **Message Rate Limiting:**
   - `MESSAGE_RATE_LIMIT_SECONDS`: Minimum seconds between printed messages from the same node (default: 60)
   
   **MQTT Configuration:**
   - `MQTT_SRV`: MQTT broker hostname
   - `MQTT_USER`: MQTT username
   - `MQTT_PASS`: MQTT password
   - `MQTT_PORT`: MQTT port (default: 1883)
   - `MQTT_TOPICS`: Comma-separated list of MQTT topics to subscribe to
   - `CHANNEL_KEY`: Base64 encoded channel key for decryption

## Features

- **Multi-printer Support**: Connect via network (IP) or USB
- **Message Rate Limiting**: Prevents spam by limiting messages per node (configurable)
- **Real-time MQTT Integration**: Connects to Meshtastic MQTT brokers
- **Database Tracking**: Stores node information and tracks message history
- **Packet Decryption**: Supports encrypted channel messages

## Usage

### Test Printer Connection
Before running the main application, test your printer connection:
```bash
uv run test-printer.py
```
This will print a test page with various formatting examples to verify your printer is working correctly. The test script supports both network and USB printers based on your `.env` configuration.

**Finding USB Printer IDs:**
- **Linux**: Use `lsusb` to find vendor and product IDs
- **macOS**: Use System Information → Hardware → USB to find vendor and product IDs
- **Windows**: Use Device Manager to find hardware IDs

### Run Main Application
```bash
uv run app.py
```

### Print Messages Utility
```bash
uv run print-messages.py
```

## Docker Usage

### Building the Image Locally
```bash
docker build -t telegramtastic .
```

### Running with Docker
For **network printers**:
```bash
docker run -d --name telegramtastic \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  telegramtastic
```

For **USB printers**:
```bash
docker run -d --name telegramtastic \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  --device /dev/usb/lp0:/dev/usb/lp0 \
  --privileged \
  telegramtastic
```

### Docker Compose
Create a `docker-compose.yml`:
```yaml
version: '3.8'
services:
  telegramtastic:
    image: ghcr.io/shakataganai/telegramtastic:latest
    container_name: telegramtastic
    env_file: .env
    volumes:
      - ./data:/app/data
    devices:
      - /dev/usb/lp0:/dev/usb/lp0  # For USB printers
    restart: unless-stopped
```

Run with: `docker-compose up -d`

### Logs and Monitoring
```bash
# View logs
docker logs telegramtastic

# Follow logs
docker logs -f telegramtastic

# Container status
docker ps
```

## Container Registry

Docker images are automatically built and published to GitHub Container Registry on every push to main:

- **Latest release**: `ghcr.io/shakataganai/telegramtastic:latest`
- **Specific version**: `ghcr.io/shakataganai/telegramtastic:v1.0.0`
- **Development**: `ghcr.io/shakataganai/telegramtastic:main`

### Multi-Architecture Support
Images are built for:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64/AArch64)

### Image Tags
- `latest` - Latest stable release
- `main` - Latest development build
- `v*.*.*` - Specific version tags
- `sha-*` - Specific commit builds

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally with `uv run app.py`
5. Commit and push your changes
6. Create a pull request

Docker images will be automatically built and tested on pull requests.
