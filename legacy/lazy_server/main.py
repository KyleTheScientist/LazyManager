import websockets
import threading
import asyncio
import psutil
from makro import MakroServer
from broadcast import ServiceBroadcaster

PORT = 5000


class WebSocketServer:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.server = None
        self.clients = set()
        self.makro_server = MakroServer()

    def is_network_adapter_active(self, adapter_name):
        net_if_stats = psutil.net_if_stats()
        if adapter_name in net_if_stats:
            return net_if_stats[adapter_name].isup
        return False

    async def handle_command(self, client, command):
        parts = command.split(":")
        
        
        if parts[0] == "list_devices":
            await self.makro_server.list_devices(client)
            return
        
        if not self.is_network_adapter_active("Ethernet 2"):
            return "status", "Not connected to VPN"

        if parts[0] == "get_log" and len(parts) == 3:
            log_type, ip = parts[1], parts[2]
            return parts[0], self.makro_server.get_log(ip, log_type)
        
        command = parts[0]
        ip = parts[1]

        if command == "start_automakro":
            await client.send(f"status:Starting automakro on {ip}")
            return await self.makro_server.start_automakro(ip)
        elif command == "stop_automakro":
            await client.send(f"status:Stopping automakro on {ip}")
            return await self.makro_server.stop_automakro(ip)
        elif command == "start_egm_controller":
            await client.send(f"status:Starting EGM Controller on {ip}")
            return await self.makro_server.start_egm_controller(ip) 
        elif command == "stop_egm_controller":
            await client.send(f"status:Stopping EGM Controller on {ip}")
            return await self.makro_server.stop_egm_controller(ip)
        elif command == "clear_ram":
            await client.send(f"status:Clearing RAM on {ip}")
            return await self.makro_server.clear_ram(ip)
        elif command == "ping":
            await client.send(f"status:Pinging {ip}")
            return await self.makro_server.ping(ip, client)
        elif command == "f1":
            await client.send(f"status:Deploying to {ip}")
            return await self.makro_server.deploy(ip, client)
        return "status", f"Unknown command: {command}"
    
    async def process_message(self, client, message):
        print(f"Processing message: {message}")
        response = await self.handle_command(client, message)
        if response:
            response_str = f"{response[0]}:{response[1]}"
            try:
                await client.send(response_str)
            except Exception as e:
                print(f"Error sending response: {e}")
            print(f"Sent response: {response_str}")

    async def handler(self, client):
        self.clients.add(client)
        try:
            async for message in client:
                print(f"Received message: {message}")
                asyncio.create_task(self.process_message(client, message))
        except websockets.ConnectionClosed:
            print("Client disconnected")
        except Exception as e:
            await client.close(1011, str(e))
        finally:
            self.clients.remove(client)
    
    async def start(self):
        self.server = await websockets.serve(self.handler, self.host, self.port)
        print(f"WebSocket server started on ws://{self.host}:{self.port}")
        await self.server.wait_closed()

if __name__ == "__main__":
    broadcaster = ServiceBroadcaster(PORT)
    broadcast_thread = threading.Thread(target=broadcaster.run, daemon=True)
    broadcast_thread.start()

    server = WebSocketServer(host='0.0.0.0', port=PORT)
    asyncio.run(server.start())
