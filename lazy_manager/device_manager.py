import asyncio
import json
import logging
from time import time
from egm import EGM
from websockets import ClientConnection, ConnectionClosed
from connection_manager import Agent

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

    async def register(self, agent: Agent, data):
        logger.info(f"Registering device {agent.id}")

        properties = data["result"]

        if agent.ip in self.devices:
            await self.devices[agent.ip].agent.close()

        egm = EGM(agent=agent, **properties)
        self.devices[agent.ip] = egm

        if not self.ping_loop:
            self.ping_loop = asyncio.create_task(self.ping_devices())

    async def handle(self, agent: Agent, data: dict):
        if data["command"] == "register":
            await self.register(agent, data)

        if data["command"] == "ping":
            self.devices[agent.ip].status = "Online"
            self.devices[agent.ip].last_seen = time()

    async def ping_devices(self):
        while True:
            device_ips = list(self.devices.keys())

            for ip in device_ips:
                device = self.devices[ip]

                if time() - device.last_seen < 10:
                    continue  # Recently seen, skip ping

                try:
                    message = {
                        "sender": "manager",
                        "command": "ping",
                    }
                    await device.agent.send(json.dumps(message))
                    device.last_seen = time()
                    device.status = "Online"
                except ConnectionClosed:
                    logger.warning(f"{device.ip} Ping failed: Connection closed.")
                    device.status = "Offline"
                    await device.agent.close()
                except Exception as e:
                    device.status = "Offline"
                    logger.error(f"{device.ip} Ping failed: Error : {e}")

                await asyncio.sleep(1)
            await asyncio.sleep(1)
