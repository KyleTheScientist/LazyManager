import asyncio
from distutils import command
import logging
from time import time
from egm import EGM
from websockets import ClientConnection, ConnectionClosed
from messaging import Agent

logger = logging.getLogger("DeviceManager")
logger.setLevel(logging.DEBUG)
logger.propagate = False

if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class DeviceManager:
    def __init__(self):
        self.devices = {}
        self.ping_loop = None

    async def register(self, agent: Agent, properties):
        logger.info(f"Registering device from agent {agent.ip} with properties: {properties}")
        _properties = {}
        for prop in properties.split("&"):
            k, v = prop.split("=")
            _properties[k] = v
        properties = _properties
        
        if len(properties) == 1:
            logger.warning(f"{agent} sent no properties. It probably failed to load its config.")
        
        logger.info(f"Registering device {agent.ip} with properties: {properties}")
        if agent.ip in self.devices:
            await self.devices[agent.ip].agent.close()

        egm = EGM(agent=agent, **properties)
        self.devices[agent.ip] = egm
        
        if not self.ping_loop:
            self.ping_loop = asyncio.create_task(self.ping_devices())

    async def handle(self, agent: Agent, message: str):
        split = message.split(":", 1)
        if split[0] == "register":
            await self.register(agent, split[1])
        
        if split[0] == "pong":
            self.devices[agent.ip].status = "Online"
            self.devices[agent.ip].last_seen = time()

    async def ping_devices(self):
        while True:
            print('\n'.join([d.serialize() for d in self.devices.values()]))
            device_ips = list(self.devices.keys())
            for ip in device_ips:
                device = self.devices[ip]
                try:
                    reachable = await device.is_reachable()
                    if not reachable:
                        logger.warning(f"Device {device.ip} is offline.")
                        device.status = "Offline"
                        continue
                    logger.info(f"Pinging device {device.ip} at {device.ip}")
                    await device.agent.send(f"manager:ping")
                except ConnectionClosed:
                    logger.warning(f"Connection to device {device.ip} closed.")
                    device.status = "Offline"
                    await device.agent.close()
                except Exception as e:
                    device.status = "Offline"
                    logger.error(f"Error while pinging EGM {device.ip}: {e}")
            await asyncio.sleep(5)
