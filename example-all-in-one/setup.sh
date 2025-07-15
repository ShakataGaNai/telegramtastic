#!/bin/bash

# Telegramtastic All-in-One Setup Script
# This script helps configure the all-in-one setup

set -e

echo "🔧 Telegramtastic All-in-One Setup"
echo "=================================="
echo ""

# Create data directory
echo "📁 Creating data directory..."
mkdir -p data

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please copy and configure the .env file:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Detect serial devices
echo "🔍 Detecting Meshtastic devices..."
echo ""

# Linux detection
if [ -d "/dev" ]; then
    echo "USB Serial devices found:"
    ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "  No USB serial devices found"
    echo ""
    
    echo "USB printer devices found:"
    ls -l /dev/usb/lp* /dev/lp* 2>/dev/null || echo "  No USB printer devices found"
    echo ""
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found!"
    echo "Please install Docker and Docker Compose first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found!"
    echo "Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose found"
echo ""

# Check configuration files
echo "🔍 Checking configuration files..."
required_files=("docker-compose.yml" "mosquitto.conf" "meshtasticd.yaml")

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file missing!"
        exit 1
    fi
done

echo ""
echo "📋 Configuration Summary:"
echo "========================"

# Show printer config
echo "Printer configuration:"
grep -E "PRINTER_TYPE|PRINTER_IP|PRINTER_USB" .env | sed 's/^/  /'
echo ""

# Show MQTT config
echo "MQTT configuration:"
grep -E "MQTT_SRV|MQTT_TOPICS|CHANNEL_KEY" .env | sed 's/^/  /'
echo ""

echo "⚠️  Please ensure you have:"
echo "  1. Configured your Meshtastic device in docker-compose.yml"
echo "  2. Set your printer IP/USB settings in .env"
echo "  3. Updated your channel key and topic in .env"
echo "  4. Connected your Meshtastic radio via USB"
echo ""

read -p "Continue with setup? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting services..."
    docker-compose up -d
    
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "📊 To monitor the services:"
    echo "  docker-compose logs -f"
    echo ""
    echo "🔍 To check service status:"
    echo "  docker-compose ps"
    echo ""
    echo "🛑 To stop services:"
    echo "  docker-compose down"
    echo ""
    echo "📖 For troubleshooting, see README.md"
else
    echo "Setup cancelled."
fi