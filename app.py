#!/usr/bin/env python
from escpos.printer import Network, Usb
import time
import os
import sys
import logging
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from meshtastic import mqtt_pb2, mesh_pb2
from meshtastic import protocols
import meshtastic.protobuf.portnums_pb2 as portnums_pb2
import traceback

#sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database.connection import setup_database
from database.repository import NodeRepository

from common.common import printThis

# ENVVAR Setup
load_dotenv()
PRINTER_TYPE = os.getenv("PRINTER_TYPE", "network").lower()
PRINTER_IP = os.getenv("PRINTER_IP")
PRINTER_USB_VENDOR_ID = os.getenv("PRINTER_USB_VENDOR_ID")
PRINTER_USB_PRODUCT_ID = os.getenv("PRINTER_USB_PRODUCT_ID")
PRINTER_USB_DEVICE = os.getenv("PRINTER_USB_DEVICE")
MESSAGE_RATE_LIMIT_SECONDS = int(os.getenv("MESSAGE_RATE_LIMIT_SECONDS", 60))
MQTT_SRV = os.getenv("MQTT_SRV")
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASS = os.getenv("MQTT_PASS")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))  # Default to 1883 if not set
MQTT_TOPICS = os.getenv("MQTT_TOPICS")
CHANNEL_KEY = os.getenv("CHANNEL_KEY")
BROADCAST_ID = 4294967295
LOG_LEVEL = logging.DEBUG

# LOGGER SETUP
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger().setLevel(LOG_LEVEL)
logging.getLogger('escpos').setLevel(logging.WARNING)

logger = logging.getLogger('telegramtastic')
logger.info(f"Logging level set to {logging.getLevelName(logger.getEffectiveLevel())}")
logger.debug(f"Logger running to {logging.getLevelName(logger.getEffectiveLevel())}")

# DB SETUP
db_session_factory = setup_database()
if db_session_factory:
    node_repo = NodeRepository(db_session_factory)
    logger.info("Database repositories initialized")
else:
    logger.error("Database connection failed - exiting")
    sys.exit(1)

# PRINTER SETUP
def setup_printer():
    """Setup printer connection based on configuration"""
    if PRINTER_TYPE == "network":
        if not PRINTER_IP:
            logger.error("PRINTER_IP not set for network printer")
            sys.exit(1)
        try:
            logger.info(f"Connecting to network printer at {PRINTER_IP}...")
            printer = Network(PRINTER_IP, timeout=5)
            printer.set_with_default()
            return printer
        except Exception as e:
            logger.error(f"Error connecting to network printer: {e}")
            sys.exit(1)
    
    elif PRINTER_TYPE == "usb":
        try:
            if PRINTER_USB_DEVICE:
                logger.info(f"Connecting to USB printer at device {PRINTER_USB_DEVICE}...")
                printer = Usb(PRINTER_USB_DEVICE)
            elif PRINTER_USB_VENDOR_ID and PRINTER_USB_PRODUCT_ID:
                # Convert hex strings to integers
                vendor_id = int(PRINTER_USB_VENDOR_ID, 16)
                product_id = int(PRINTER_USB_PRODUCT_ID, 16)
                logger.info(f"Connecting to USB printer (VID: {hex(vendor_id)}, PID: {hex(product_id)})...")
                printer = Usb(vendor_id, product_id)
            else:
                logger.error("USB printer requires either PRINTER_USB_DEVICE or both PRINTER_USB_VENDOR_ID and PRINTER_USB_PRODUCT_ID")
                sys.exit(1)
            
            printer.set_with_default()
            return printer
        except Exception as e:
            logger.error(f"Error connecting to USB printer: {e}")
            sys.exit(1)
    
    else:
        logger.error(f"Invalid PRINTER_TYPE: {PRINTER_TYPE}. Must be 'network' or 'usb'")
        sys.exit(1)

printer = setup_printer()

# Keep packets we've seen in memory.
seenPackets = list()

def lookupNode(id) -> object:
    """
    Look up a node ID and return a descriptive name if available.
    For broadcast IDs, returns "ALL".
    For other IDs, tries to find the node info in the database.
    """
    class Node:
        def __init__(self, short_name="UNK", long_name="UNKNOWN"):
            self.short_name = short_name
            self.long_name = long_name

    node = Node()

    if id == BROADCAST_ID:
        node.short_name = "ALL"
        node.long_name = "BROADCAST"
    else:    
        # Try to get node info from database
        try:
            db_node = node_repo.get_node_by_id(id)
            if db_node is not None:
                # Check if short_name exists and is not None
                if hasattr(db_node, 'short_name') and db_node.short_name is not None:
                    node.short_name = db_node.short_name
                # Check if long_name exists and is not None
                if hasattr(db_node, 'long_name') and db_node.long_name is not None:
                    node.long_name = db_node.long_name
        except Exception as e:
            logger.debug(f"Error looking up node in database: {e}")
    return node

# Build the HardwareModel lookup table
hwLookup = {}
if hasattr(mesh_pb2.HardwareModel, "DESCRIPTOR"):
    hwLookup = {enum_value.number: enum_value.name for enum_value in mesh_pb2.HardwareModel.DESCRIPTOR.values}
else:
    for attr in dir(mesh_pb2.HardwareModel):
        if attr.isupper():
            try:
                value = int(getattr(mesh_pb2.HardwareModel, attr))
                hwLookup[value] = attr
            except Exception:
                continue

portnumLookup = {}
if hasattr(portnums_pb2.PortNum, "DESCRIPTOR"):
    # Use the enum descriptor to build the mapping
    portnumLookup = {enum_value.number: enum_value.name for enum_value in portnums_pb2.PortNum.DESCRIPTOR.values}
else:
    # Fallback: iterate over the attributes of PortNum
    for attr in dir(portnums_pb2.PortNum):
        if attr.isupper():
            try:
                portnumLookup[int(getattr(portnums_pb2.PortNum, attr))] = attr
            except Exception:
                continue

def decode_nodeinfo_app(decoded_mp, pb):
    """Proccess NODEINFO_APP packets and update the database"""
    try:
        node_id = getattr(decoded_mp, 'from')
        short_name = pb.short_name
        long_name = pb.long_name
        hw_model_id = pb.hw_model
        hw_model_name = hwLookup.get(hw_model_id, "Unknown")

        logger.debug(f"Node ID: {node_id}")
        logger.debug(f"Long Name: {long_name}")
        logger.debug(f"Short Name: {short_name}")
        logger.debug(f"HW Model: {hw_model_name}")
        
        # Store in database
        success = node_repo.save_or_update_node(
            node_id=node_id,
            short_name=short_name,
            long_name=long_name,
            hw_model_name=hw_model_name,
            hw_model_id=hw_model_id
        )
        if not success:
            logger.warning(f"Failed to save node {node_id} to database")
    except Exception as e:
        logger.warning(f"Error processing NODEINFO_APP packet ({decoded_mp.id}): {e}")
    return True

def decode_position_app(decoded_mp, pb):
    try:
        latitude = pb.latitude_i / 1e7
        longitude = pb.longitude_i / 1e7
        altitude = pb.altitude
        logger.debug(f"-- Position: lat={latitude}, lon={longitude}, alt={altitude}")
        for k, v in pb.ListFields():
            logger.debug(f"** {k.name} = {v}")
    except Exception as e:
        logger.warning(f"Error proccessing POSITION_APP packet ({decoded_mp.id}): {e}")

def decode_telemetry_app(decoded_mp, pb):
    try:
        # Decode telemetry data
        logger.debug(f"Telemetry Data: {pb}")
        for k, v in pb.device_metrics.ListFields():
            logger.debug(f"** {k.name} = {v}")
    except Exception as e:
        logger.warning(f"Error processing TELEMETRY_APP packet ({decoded_mp.id}): {e}")

def decode_message_app(decoded_mp, pb, to, frm):
    try:
        payload = decoded_mp.decoded.payload.decode("utf-8")
        logger.debug(f"Text Message: {payload}")
        
        # Get the sender node ID for rate limiting
        sender_node_id = getattr(decoded_mp, 'from')
        
        # Check if this node can print a message (rate limiting)
        if node_repo.can_print_message(sender_node_id, MESSAGE_RATE_LIMIT_SECONDS):
            # Update the last print timestamp in database
            if node_repo.update_last_print(sender_node_id):
                logger.info(f"Printing message from node {sender_node_id} ({frm.short_name}): {payload}")
                printThis(to, frm, payload, printer)
            else:
                logger.warning(f"Failed to update last_print for node {sender_node_id}, skipping print")
        else:
            logger.info(f"Rate limiting: Skipping message from node {sender_node_id} ({frm.short_name}) - {MESSAGE_RATE_LIMIT_SECONDS}s cooldown active")
            
    except Exception as e:
        logger.warning(f"Error processing MESSAGE_APP packet ({decoded_mp.id}): {e}")

def proccessPacket(decoded_mp, handler, decrypted, portNumInt):
    packetID = decoded_mp.id
    if packetID in seenPackets:
        logger.debug("Duplicate packet, skipping...")
        return
    else:
        seenPackets.append(packetID)
        try:
            logger.debug(f"Port Int: {portnumLookup[portNumInt] if portNumInt in portnumLookup else 'Unknown'} ({portNumInt})")
            frm = lookupNode(getattr(decoded_mp, 'from')) #This is why you don't use "from" as a variable name
            to = lookupNode(decoded_mp.to)
            logger.debug(f"From: {frm.short_name} ({frm.long_name})")
            logger.debug(f"To: {to.short_name} ({to.long_name})")
            logger.debug(f"Channel: {decoded_mp.channel}")
            logger.debug(f"ID: {decoded_mp.id}")
            logger.debug(f"RX Time: {decoded_mp.rx_time}")
            logger.debug(f"RX SNR: {decoded_mp.rx_snr}")
            logger.debug(f"RX RSSI: {decoded_mp.rx_rssi}")
            logger.debug(f"Hop Limit: {decoded_mp.hop_limit}")

            pb = None
            if handler is not None and handler.protobufFactory is not None:
                pb = handler.protobufFactory()
                pb.ParseFromString(decoded_mp.decoded.payload)
            else:
                logger.debug("No handler found for this port number")

            if decoded_mp.decoded.portnum == 1:
                # TEXT_MESSAGE_APP
                decode_message_app(decoded_mp, pb, to, frm)
            elif decoded_mp.decoded.portnum == 3:
                # POSITION_APP
                decode_position_app(decoded_mp, pb)
            elif decoded_mp.decoded.portnum == 4:
                # NODEINFO_APP
                decode_nodeinfo_app(decoded_mp, pb)
            elif decoded_mp.decoded.portnum == 67:
                # TELEMETRY_APP
                decode_telemetry_app(decoded_mp, pb)
            elif decrypted == False:
                logger.debug("Encrypted Payload")
            else:
                # Other applications
                try:
                    logger.debug("Other App - Generic Payload Decode")
                    for k, v in pb.ListFields():
                        logger.debug(f"** {k.name} = {v}")
                except Exception as e:
                    logger.warning(f"Error decoding other app packet ({decoded_mp.id}): {e}")
            logger.debug("--------\n")
        except Exception as e:
            logger.debug(f"Error processing packet: {e}", exc_info=True)
            
            tb = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(f"Error in {tb.filename} at line {tb.lineno}: {e}")
        

# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.debug("Connected to MQTT broker!")
        for topic in MQTT_TOPICS.split(","):
            if len(topic)>1:
                if not topic.endswith("/#"):
                    topic += "/#"
                client.subscribe(topic)
                logger.debug(f"Subscribed to topic: {topic}")
            else:
                logger.debug(f"Invalid topic length: |{topic}|")
    else:
        logger.error(f"MQTT Failed to connect, return code: {rc}")
        sys.exit(1)

# Callback when a message is received
def on_message(client, userdata, msg):
    se = mqtt_pb2.ServiceEnvelope()
    se.ParseFromString(msg.payload)
    decoded_mp = se.packet

    decrypted = False
    # Try to decrypt the payload if it is encrypted
    if decoded_mp.HasField("encrypted") and not decoded_mp.HasField("decoded"):
        decoded_data = decrypt_packet(decoded_mp, CHANNEL_KEY)
        if decoded_data is None:
            logger.debug("Decryption failed; retaining original encrypted payload")
            pass
        else:
            decoded_mp.decoded.CopyFrom(decoded_data)
            decrypted = True

    # Attempt to process the decrypted or encrypted payload
    portNumInt = decoded_mp.decoded.portnum if decoded_mp.HasField("decoded") else None
    handler = protocols.get(portNumInt) if portNumInt else None

    proccessPacket(decoded_mp, handler, decrypted, portNumInt)


def decrypt_packet(mp, key):
    try:
        key_bytes = base64.b64decode(key.encode('ascii'))

        # Build the nonce from message ID and sender
        nonce_packet_id = getattr(mp, "id").to_bytes(8, "little")
        nonce_from_node = getattr(mp, "from").to_bytes(8, "little")
        nonce = nonce_packet_id + nonce_from_node

        # Decrypt the encrypted payload
        cipher = Cipher(algorithms.AES(key_bytes), modes.CTR(nonce), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_bytes = decryptor.update(getattr(mp, "encrypted")) + decryptor.finalize()

        # Parse the decrypted bytes into a Data object
        data = mesh_pb2.Data()
        data.ParseFromString(decrypted_bytes)
        return data

    except Exception as e:
        return None

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(MQTT_USER, MQTT_PASS)
try:
    client.connect(MQTT_SRV, MQTT_PORT, keepalive=60)
    client.loop_forever()
except Exception as e:
    logger.error(f"MQTT Connection Error: {e}")
    sys.exit(1)
