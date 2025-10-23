import asyncio
import websockets
from lazy_logging import get_logger
from zeroconf import ServiceListener, ServiceBrowser, Zeroconf


class AppListener(ServiceListener):
    def __init__(self):
        self.ips = []
        self.logger = get_logger("AppListener")

    def on_service_found(self, ip):
        pass

    def add_service(self, zeroconf, type, name):
        self.logger.info(f"Service added: {name}")
        info = zeroconf.get_service_info(type, name)
        if info:
            ip = ".".join(map(str, info.addresses[0]))
            self.logger.info(f"Discovered service: {name} at {ip}")
            if ip not in self.ips:
                self.ips.append(ip)
                self.on_service_found(ip)
            else:
                self.logger.debug(f"Service {name} at {ip} already known")

    def remove_service(self, zc, type_, name):
        self.logger.info(f"Service removed: {name}")

    def update_service(self, zc, type_, name):
        self.logger.debug(f"Service updated: {name}")
        self.add_service(zc, type_, name)


class Agent:

    def __init__(self, ip: str, connection: websockets.ServerConnection):
        self.ip = ip
        self.connection = connection
        self.id = int(ip.split(".")[-1])

    async def send(self, message: str):
        await self.connection.send(message)

    async def close(self):
        await self.connection.close()

    def __str__(self):
        return f"Agent({self.id})"


class App:

    def __init__(self, ip: str, connection: websockets.ServerConnection):
        self.ip = ip
        self.connection = connection
        self.octet = int(ip.split(".")[-1])

    async def send(self, message: str):
        await self.connection.send(message)

    def __str__(self):
        return f"App({self.ip})"


class ConnectionManager:


    def __init__(self, agent_port=8765, app_port=8766, agent_ips=None):
        self.agent_port = agent_port
        self.app_port = app_port
        self.agent_ips = agent_ips if agent_ips else []
        self.agents: dict[str, Agent] = {}
        self.apps: dict[str, App] = {}
        self.logger = get_logger("ConnectionManager")
        self.setup_listener()

    def setup_listener(self):
        zeroconf = Zeroconf()
        self.listener = AppListener()
        ServiceBrowser(zeroconf, "_lazy._tcp.local.", self.listener)

    def start(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.loop_forever())

    async def loop_forever(self):
        tasks = [
            self.try_connect_agents(),
            self.try_connect_apps(),
        ]
        await asyncio.gather(*tasks)

    async def try_connect_apps(self):
        while True:
            for ip in self.listener.ips:
                if ip in self.apps and self.apps[ip].connection.state == websockets.protocol.State.OPEN:
                    continue  # Already connected
                self.logger.info(f"Discovered app: {ip}")
                await self._connect_to_app(ip)

            for app in self.apps.values():
                if app.connection.state > websockets.protocol.State.OPEN:
                    self.logger.info(f"Reconnecting to app {app.ip}")
                    async def reconnect():
                        try:
                            ws = await websockets.connect(f"ws://{app.ip}:{self.app_port}")
                            await self.on_app_connect(app)
                            app.connection = ws
                        except Exception as e:
                            pass
                    asyncio.create_task(reconnect())
            await asyncio.sleep(2)

    async def _connect_to_app(self, ip: str):
        try:
            ws = await websockets.connect(f"ws://{ip}:{self.app_port}")
            self.apps[ip] = App(ip, ws)
            await self.on_app_connect(self.apps[ip])
            self.loop.create_task(self.process_app_messages(self.apps[ip]))
        except Exception as e:
            self.logger.warning(f"Failed to connect to app at {ip}: {e}")

    async def try_connect_agents(self):
        while True:
            for ip in self.agent_ips:
                agent = self.agents.get(ip)
                if agent and agent.connection.state == websockets.protocol.State.OPEN:
                    continue  # Already connected
                asyncio.create_task(self._connect_to_agent(ip))
            await asyncio.sleep(5)

    async def _connect_to_agent(self, ip: str):
        try:
            ws = await websockets.connect(f"ws://{ip}:{self.agent_port}")
            self.agents[ip] = Agent(ip, ws)
            await self.on_agent_connect(self.agents[ip])
            self.loop.create_task(self.process_agent_messages(self.agents[ip]))
        except Exception as e:
            pass
            # self.logger.warning(f"Failed to connect to agent at {ip}: {e}")

    async def ping(self):
        for agent, ws in self.agents.items():
            try:
                await ws.ping()
                self.logger.info(f"Pinged {agent}")
            except Exception as e:
                self.logger.warning(f"Failed to ping {agent}: {e}")

    async def send_message(self, ip: str, message: str):
        if ip in self.agents:
            ws = self.agents[ip]
            await ws.send(message)
            self.logger.info(f"Sent to {ip}: {message}")
        else:
            self.logger.info(f"No connection to {ip}")

    async def process_agent_messages(self, agent: Agent):
        try:
            async for message in agent.connection:
                await self.handle_agent_message(message, agent)
        except websockets.ConnectionClosed:
            self.logger.info("Connection closed")

    async def process_app_messages(self, app: App):
        try:
            async for message in app.connection:
                await self.handle_app_message(message, app)
        except websockets.ConnectionClosed:
            self.logger.warning(f"{app} connection closed")

    async def close_connections(self):
        for agent, ws in self.agents.items():
            await ws.close()
            self.logger.info(f"Closed connection to {agent}")

    async def handle_agent_message(self, message: str, agent: Agent):
        pass

    async def handle_app_message(self, message: str, app: App):
        pass

    async def on_agent_connect(self, agent: Agent):
        pass

    async def on_app_connect(self, app: App):
        pass
