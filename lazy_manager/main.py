from distutils import command
import json
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

AGENT_IPS = ["127.0.0.1"]  # For testing purposes


class LazyManager(ConnectionManager):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, agent_port=AGENT_PORT, app_port=APP_PORT, agent_ips=AGENT_IPS, **kwargs)
        self.device_manager = DeviceManager()

    async def handle_agent_message(self, message: str, agent: Agent):
        data = json.loads(message)

        if "app_ip" in data:
            app_ip = data["app_ip"]
            app = self.apps.get(app_ip, None)

            if app:
                logger.info(f"Forwarding result from device {agent.ip} to app {app.ip}")
                data.update(sender_ip=agent.ip)
                await app.send(json.dumps(data))
            else:
                logger.warning(f"App '{app_ip}' not found for forwarding result of device {agent.ip}")
            
            return

        await self.device_manager.handle(agent, data)

    async def handle_app_message(self, message: str, app: App):
        data = json.loads(message)
        
        if data['command'] == "device_info":
            logger.info(f"Listing {len(self.device_manager.devices)} devices for app {app.ip}")
            
            for egm in self.device_manager.devices.values():
                message = {
                    "sender": "manager",
                    "command": "device_info",
                    "result": egm.serialize()
                }
                await app.send(json.dumps(message))
            return

        target = data.get("target")
        device = self.device_manager.devices.get(target, None)
        if not device:
            logger.warning(f"Device {target} not found for command {data['command']}")
            message  = dict(
                sender="manager",
                result=f"Device {target} not found",
                **data
            )
            await app.send(json.dumps(message))
            return

        data.update(sender_ip=app.ip)
        await device.agent.send(json.dumps(data))

    async def on_agent_connect(self, agent: Agent):
        logger.info(f"Agent connected: {agent}")
        message = {
            "sender": "manager",
            "command": "register",
        }
        await agent.send(json.dumps(message))

    async def on_app_connect(self, app: App):
        logger.info(f"App connected: {app}")
        message = {
            "sender": "manager",
            "command": "register",
        }
        await app.send(json.dumps(message))


if __name__ == "__main__":
    server = LazyManager()
    server.start()
