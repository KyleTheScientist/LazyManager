import asyncio
import logging
import psutil
from lazy_logging import get_logger
from connection_manager import ConnectionManager, App, Agent
from device_manager import DeviceManager

logger = get_logger("LazyManager")
# def is_network_adapter_active(self, adapter_name):
#     net_if_stats = psutil.net_if_stats()
#     if adapter_name in net_if_stats:
#         return net_if_stats[adapter_name].isup
#     return False

AGENT_PORT = 8765
APP_PORT = 8767

# AGENT_IPS = [f"10.0.0.{i}" for i in range(2, 28)]
# AGENT_IPS.remove("10.0.0.3")  # Exclude POS terminal

AGENT_IPS = ["127.0.0.1"] # For testing purposes



class LazyManager(ConnectionManager):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, agent_port=AGENT_PORT, app_port=APP_PORT, agent_ips=AGENT_IPS, **kwargs)
        self.device_manager = DeviceManager()

    async def handle_agent_message(self, message: str, agent: Agent):
        if 'pong' not in message:
            logger.info(f"Received message from agent {agent.ip}: {message}")
        
        sender, command = message.split(":", 1)
        if command.startswith("result:"):
            print(message)
            _, app_ip, command, result = command.split(":", 3)
            app = self.apps.get(app_ip, None)
            if not app:
                logger.warning(f"App '{app_ip}' not found for forwarding result of device {agent.ip}")
                return
            logger.info(f"Forwarding result from device {agent.ip} to app {app.ip}")
            await app.send(f"egm:result:{agent.ip}:{command}:{result}")
        
        if sender == "egm":
            await self.device_manager.handle(agent, command)

    async def handle_app_message(self, message: str, app: App):
        sender, command = message.split(":", 1)
        if command == "list_devices":
            logger.info(f"Listing {len(self.device_manager.devices)} devices for app {app.ip}")
            for egm in self.device_manager.devices.values():
                await app.send(f"manager:egm:{egm.serialize()}")
            return

        split = command.split(":", 1)
        command, target = split[0], split[1]
        device = self.device_manager.devices.get(target, None)
        if not device:
            logger.warning(f"Device {target} not found for command {command}")
            await app.send(f"manager:status:Device {target} not found")
            return
        
        await device.agent.send(f"app:{command}:{app.ip}")

    async def on_agent_connect(self, agent: Agent):
        logger.info(f"Agent connected: {agent}")
        await agent.send("manager:connected")

    async def on_app_connect(self, app: App):
        logger.info(f"App connected: {app}")
        await app.send("manager:connected")

if __name__ == "__main__":
    server = LazyManager()
    server.start()
