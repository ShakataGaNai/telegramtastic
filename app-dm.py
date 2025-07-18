import meshtastic
from meshtastic.tcp_interface import TCPInterface
from meshtastic.serial_interface import SerialInterface
from pprint import pprint
from pubsub import pub
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

from database.connection import setup_database
from database.repository import NodeRepository
from common.common import printThis

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
    level=logging.INFO,  # Set root logger to INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger('escpos').setLevel(logging.WARNING)

logger = logging.getLogger('telegramtastic-dm')
logger.setLevel(LOG_LEVEL)  # Set only this logger to DEBUG
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

# Initialize Meshtastic interface
# interface = TCPInterface("localhost")
interface = SerialInterface()

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


def getRole(val):
    for name, num in meshtastic.config_pb2.Config.DeviceConfig.Role.items():
        if num == val:
            return name
    return None

def getRegion(val):
    for name, num in meshtastic.config_pb2.Config.LoRaConfig.RegionCode.items():
        if num == val:
            return name
    return None

def getPreset(val):
    for name, num in meshtastic.config_pb2.Config.LoRaConfig.ModemPreset.items():
        if num == val:
            return name
    return None


# def receive_message(packet):
#     if "text" in packet["decoded"]["payload"]:
#         text = packet["decoded"]["payload"]["text"]
#         node = packet["fromId"]
#         messages.append((node, text))
#         users[node] = packet["from"]

# # Add receive_message callback
# interface.on_receive = receive_message

# def initialize_config():
#     global config
#     lc = interface.localNode.localConfig
#     lora = getattr(lc, "lora")
#     meta = interface.localNode.getMetadata()
#     nodeinfo = interface.getMyNodeInfo()
#     config = {
#         "Lora Region": getRegion(getattr(lora, "region")),
#         "Modem Preset": getPreset(getattr(lora, "modem_preset")),
#         "Max Hops": getattr(lora, "hop_limit"),
#         "Role": getRole(interface.localNode.localConfig.device.role),
#         "Long Name": interface.getLongName(),
#         "Short Name": interface.getShortName()
#     }

def initialize_users():
    logger.debug("Initializing users from current nodes")
    nodes = interface.nodes
    for node in nodes.values():
        try:
            # Store in database
            success = node_repo.save_or_update_node(
                node_id=node["num"],
                short_name=node["user"]["shortName"],
                long_name=node["user"]["longName"],
                hw_model_name=node["user"]["hwModel"]
            )
            if not success:
                logger.warning(f"Failed to save node {node} to database")
            # else:
            #     logger.debug("Updated!")
        except Exception as e:
            logger.warning(f"Error updating node on start: {e}")

def wakeUpAndSayHello(interface):
    me = interface.nodesByNum[interface.localNode.nodeNum]["user"]
    u = mesh_pb2.User()
    u.id         = me["id"]
    u.long_name  = me["longName"].encode('utf-8')
    u.short_name = me["shortName"].encode('utf-8')
    u.hw_model   = mesh_pb2.HardwareModel.Value(me["hwModel"])
    u.public_key = base64.b64decode(me["publicKey"])

    interface.sendData(u,
               portNum=meshtastic.protobuf.portnums_pb2.NODEINFO_APP,
               wantAck=False, wantResponse=True)

    time.sleep(5) # Give time for the nodeinfo to propagate

    #interface.sendText("Telegram Bot Online")


def main():
    wakeUpAndSayHello(interface)

    print("Running. Press Ctrl-C to quit.")

    while True:
        time.sleep(0.1)


def handleDM(packet, interface):
    sender = lookupNode(packet["from"])

    try:
        try:
            payload = packet['decoded']['text'].decode("utf-8")
        except:
            payload = str(packet['decoded']['text'])
        logger.debug(f"DM: {payload}")
        
        # Get the sender node ID for rate limiting
        sender_node_id = packet["from"]
        
        # Check if this node can print a message (rate limiting)
        if node_repo.can_print_message(sender_node_id, MESSAGE_RATE_LIMIT_SECONDS):
            # Update the last print timestamp in database
            if node_repo.update_last_print(sender_node_id):
                logger.info(f"Printing message from node {sender_node_id} ({sender.short_name}): {payload}")
                # printThis(sender, payload, printer)
                interface.sendText("Your telegram has been printed. Stop by the Meshtastic booth to pick it up! Main Hall E12 (Right in the middle)",destinationId=packet['fromId']) # Send read receipt
                # interface.sendText("Telegram Printed!",destinationId=packet['fromId'],wantAck=True,wantResponse=True) # Send read receipt
            else:
                logger.warning(f"Failed to update last_print for node {sender_node_id}, skipping print")
        else:
            logger.info(f"Rate limiting: Skipping message from node {sender_node_id} ({sender.short_name}) - {MESSAGE_RATE_LIMIT_SECONDS}s cooldown active")

    except Exception as e:
        logger.warning(f"Error processing MESSAGE_APP packet ({packet}): {e}")

def handleText(packet, interface):
    sender = lookupNode(packet["from"]).long_name
    print(f"Text From {sender}: {packet['decoded']['text']}")

def handleOther(packet, interface):
    pass
    # sender = lookupNode(packet["from"]).long_name
    # print(f"Packet From {sender} -- {packet['decoded']['portnum']}")

def handleNodeInfo(packet, interface):
    """Proccess NODEINFO_APP packets and update the database"""
    try:
        u = packet['decoded']['user']
        node_id = packet['from']
        hex_id = u['id']
        short_name = u['shortName']
        long_name = u['longName']
        hw_model_name = u['hwModel']

        logger.debug(f"Node ID: {node_id}")
        logger.debug(f"Long Name: {long_name}")
        logger.debug(f"Short Name: {short_name}")
        logger.debug(f"HW Model: {hw_model_name}")
        
        # Store in database
        success = node_repo.save_or_update_node(
            node_id=node_id,
            short_name=short_name,
            long_name=long_name,
            hw_model_name=hw_model_name
        )
        if not success:
            logger.warning(f"Failed to save node {node_id} to database")
    except Exception as e:
        logger.warning(f"Error processing NODEINFO_APP packet ({packet}): {e}")
    return True


def onReceive(packet, interface):
    """called when a packet arrives"""
    #print(f"Received: {packet}")
    sender = lookupNode(packet["from"]).long_name
    print(f"Packet From {sender} -- {packet['decoded']['portnum']}")

    if packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
        if packet.get('to') == interface.localNode.nodeNum: # Direct message to me
            handleDM(packet, interface)
        else:
            handleText(packet, interface)
    elif packet['decoded']['portnum'] == 'NODEINFO_APP':
        handleNodeInfo(packet, interface)
    else:
        handleOther(packet, interface)

def onConnection(interface, topic=pub.AUTO_TOPIC):
    """called when we (re)connect to the radio"""
    messages.append(("SYSTEM", "Connected to radio!"))

if __name__ == "__main__":
    print("Starting up")
    # initialize_config()
    initialize_users()
    pub.subscribe(onConnection, "meshtastic.connection.established")
    pub.subscribe(onReceive, "meshtastic.receive")
    #pub.subscribe(onText, "meshtastic.receive.text")
    main()