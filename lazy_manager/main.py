import asyncio
import logging
import psutil
from lazy_logging import get_logger
from messaging import Manager, App, Agent
from device_manager import DeviceManager

logger = get_logger("LazyManager")
# def is_network_adapter_active(self, adapter_name):
#     net_if_stats = psutil.net_if_stats()
#     if adapter_name in net_if_stats:
#         return net_if_stats[adapter_name].isup
#     return False

class LazyManager(Manager):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_manager = DeviceManager()

    async def handle_agent_message(self, message: str, agent: Agent):
        logger.info(f"Received message from agent {agent.ip}: {message}")
        sender, command = message.split(":", 1)
        if sender == "app":
            logger.info(f"Forwarding result from device {agent.ip} to app")
            command, app_ip, message = message.split(":", 2)
            app = self.apps[app_ip]
            await app.send(f"egm:{agent.ip}:{message}")
        
        if sender == "egm":
            await self.device_manager.handle(agent, command)

    async def handle_app_message(self, message: str, app: App):
        sender, command = message.split(":", 1)
        if command == "list_devices":
            logger.info(f"Listing devices for app {app.ip}")
            for egm in self.device_manager.devices.values():
                print(f"Sending device {egm.id} info to app {app.ip}")
                await app.send(f"manager:egm:{egm.serialize()}")
            return

        split = command.split(":", 1)
        command, target = split[0], split[1]
        device = self.device_manager.devices.get(target, None)
        print(self.device_manager.devices)
        if not device:
            logger.warning(f"Device {target} not found for command {command}")
            await app.send(f"manager:status:Device {target} not found")
            return
        
        await device.agent.send(f"app:{command}")

    async def on_agent_connect(self, agent: Agent):
        logger.info(f"Agent connected: {agent}")
        await agent.send("manager:connected")

    async def on_app_connect(self, app: App):
        logger.info(f"App connected: {app}")
        await app.send("manager:connected")

if __name__ == "__main__":
    server = LazyManager()
    server.start()
