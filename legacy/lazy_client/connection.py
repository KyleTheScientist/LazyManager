import socket
import asyncio
import websockets
from websockets.exceptions import ConnectionClosed
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf


class LazyListener(ServiceListener):

    def __init__(self, client):
        self.client = client
        self.service = None
    
    def update_service(self, zc, type_, name):
        pass
    
    def remove_service(self, zc, type_, name):
        pass

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"\n[DISCOVERED] Service: {name}")
        if self.service:
            return  # Already found a service
        
        info = zc.get_service_info(type_, name)
        properties = {}
        address = None
        
        if info:
            address = socket.inet_ntoa(next(iter(info.addresses)))
            if info.properties:
                for key, value in info.properties.items():
                    decoded_key = key.decode('utf-8') if isinstance(key, bytes) else key
                    decoded_value = value.decode('utf-8') if isinstance(value, bytes) else value
                    properties[decoded_key] = decoded_value
        else:
            return
        
        print(f"  Found service at {address}:{info.port} with properties: {properties}")

        if address and 'data_port' in properties:
            self.service = {
                'name': name,
                'address': address,
                'port': info.port,
                'data_port': int(properties['data_port']),
                'properties': properties
            }

class WebSocketClient:
    
    def __init__(self, app):
        self.app = app
        self.zeroconf = None
        self.listener = None
        self.browser = None
        self.service = None
        self.ws = None

    async def find_service(self):
        self.zeroconf = Zeroconf()
        self.listener = LazyListener(self)
        self.browser = ServiceBrowser(self.zeroconf, "_lazy._tcp.local.", self.listener)
        for i in range(10):
            if self.listener.service:
                break
            await asyncio.sleep(1)
        if not self.listener.service:
            print("No service found.")
            return None
        self.service = self.listener.service

    async def connect(self, reconnect=True):
        if reconnect:
            self.app.message_queue.put("status:Reconnecting to server...")
        else:
            self.app.message_queue.put("status:Connecting to server...")

        if not self.service:
            print("No service to connect to.")
            return
        
        uri = f"ws://{self.service['address']}:{self.service['data_port']}"
        try:
            self.ws = await websockets.connect(uri)
            print(f"Connected to {uri}")
            self.app.message_queue.put("status:Connected")
            await self.send_message("list_devices:")
        except Exception as e:
            print(f"Failed to connect to {uri}: {e}")

    async def send_message(self, message):
        try:
            await self.ws.send(message)
        except Exception as e:
            self.app.message_queue.put(f"status:Error sending message: {e}")
            await self.connect()

    async def close(self):
        if self.ws:
            await self.ws.close()
            print("WebSocket connection closed.")
        if self.zeroconf:
            self.zeroconf.close()
            print("Zeroconf closed.")

    def start(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.run())

    async def run(self):
        await self.find_service()
        if self.service:
            await self.connect(reconnect=False)
        
        while True:
            try:
                response = await self.ws.recv()
                self.app.message_queue.put(response)
            except ConnectionClosed:
                print("Connection closed by server. Reconnecting...")
                await self.connect()
            except Exception as e:
                print(f"Error during receive: {e}")
                await asyncio.sleep(5)
            
    def send(self, message):
        asyncio.run_coroutine_threadsafe(
            self.send_message(message), 
            self.loop
        )
    
if __name__ == "__main__":
    client = WebSocketClient()
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("Shutting down client...")
    finally:
        asyncio.run(client.close())