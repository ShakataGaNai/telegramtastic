# All-in-One Meshtastic Setup

This directory contains a complete Docker Compose setup that runs:
- **Mosquitto MQTT Broker** - Local message broker
- **Meshtastic Daemon** - Connects to your Meshtastic radio and publishes to MQTT
- **Telegramtastic** - Receipt printer integration

## Prerequisites

- Docker and Docker Compose installed
- Meshtastic radio device connected via USB
- Thermal receipt printer (network or USB)

## Quick Start

1. **Configure your hardware connections**:
   
   Edit `docker-compose.yml` to uncomment the appropriate device for your Meshtastic radio:
   ```yaml
   # For USB serial devices
   - /dev/ttyUSB0:/dev/ttyUSB0
   # For USB ACM devices  
   - /dev/ttyACM0:/dev/ttyACM0
   ```

2. **Configure your printer**:
   
   Edit `.env` file:
   ```bash
   # For network printer
   PRINTER_TYPE=network
   PRINTER_IP=192.168.1.100
   
   # For USB printer, uncomment and configure:
   # PRINTER_TYPE=usb
   # PRINTER_USB_VENDOR_ID=0x04b8
   # PRINTER_USB_PRODUCT_ID=0x0202
   ```

3. **Configure your Meshtastic settings**:
   
   Edit `meshtasticd.yaml` to match your setup:
   ```yaml
   device:
     port: /dev/ttyUSB0  # Your device port
   
   mqtt:
     topic: "msh/US/bayarea/2/e"  # Your region/channel
   
   channels:
     - name: "Default"
       psk: "YOUR_CHANNEL_KEY"  # Your channel encryption key
   ```

4. **Update the environment**:
   
   Edit `.env` to match your channel settings:
   ```bash
   MQTT_TOPICS=msh/US/bayarea/2/e/#
   CHANNEL_KEY=YOUR_CHANNEL_KEY
   ```

5. **Start the services**:
   ```bash
   docker-compose up -d
   ```

## Service Details

### Mosquitto MQTT Broker
- **Port**: 1883 (MQTT), 9001 (WebSocket)
- **Config**: `mosquitto.conf`
- **Authentication**: Anonymous (for local development)

### Meshtastic Daemon
- **Image**: `meshtastic/meshtasticd:2.7.1-alpha-alpine`
- **Config**: `meshtasticd.yaml`
- **Purpose**: Connects to your radio and publishes messages to MQTT

### Telegramtastic
- **Image**: `ghcr.io/shakataganai/telegramtastic:latest`
- **Config**: `.env`
- **Purpose**: Prints received messages to thermal printer

## Configuration Files

### `docker-compose.yml`
Main orchestration file that defines all services and their dependencies.

### `mosquitto.conf`
MQTT broker configuration:
- Anonymous access enabled
- Logging to stdout and file
- WebSocket support on port 9001

### `meshtasticd.yaml`
Meshtastic daemon configuration:
- Serial device connection
- MQTT broker settings
- Channel configuration
- Module settings

### `.env`
Telegramtastic configuration:
- Printer settings
- MQTT connection details
- Rate limiting settings

## Finding Your Device

### Linux
```bash
# List USB devices
lsusb

# List serial devices
ls -l /dev/ttyUSB* /dev/ttyACM*

# Monitor device connections
dmesg | grep -i "usb\|tty"
```

### macOS
```bash
# List USB devices
system_profiler SPUSBDataType

# List serial devices
ls -l /dev/tty.usb* /dev/cu.*
```

## Troubleshooting

### Meshtastic Daemon Won't Start
1. **Check device permissions**:
   ```bash
   ls -l /dev/ttyUSB0
   # Should show permissions like crw-rw----
   ```

2. **Verify device connection**:
   ```bash
   # Check if device is detected
   dmesg | tail -20
   
   # Test device communication
   screen /dev/ttyUSB0 115200
   ```

3. **Check container logs**:
   ```bash
   docker-compose logs meshtasticd
   ```

### MQTT Connection Issues
1. **Check Mosquitto logs**:
   ```bash
   docker-compose logs mosquitto
   ```

2. **Test MQTT connection**:
   ```bash
   # Subscribe to test topic
   mosquitto_sub -h localhost -t "test/topic"
   
   # Publish test message
   mosquitto_pub -h localhost -t "test/topic" -m "Hello"
   ```

### Printer Not Working
1. **Test printer connection**:
   ```bash
   # For network printers
   ping 192.168.1.100
   
   # For USB printers
   ls -l /dev/usb/lp* /dev/lp*
   ```

2. **Check telegramtastic logs**:
   ```bash
   docker-compose logs telegramtastic
   ```

## Monitoring

### View all logs
```bash
docker-compose logs -f
```

### View specific service logs
```bash
docker-compose logs -f mosquitto
docker-compose logs -f meshtasticd
docker-compose logs -f telegramtastic
```

### Check service status
```bash
docker-compose ps
```

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Security Notes

⚠️ **This setup is designed for local development/testing**

- MQTT broker allows anonymous connections
- No TLS/SSL encryption
- Default channel keys used

For production use, configure:
- MQTT authentication
- TLS encryption
- Unique channel keys
- Firewall rules