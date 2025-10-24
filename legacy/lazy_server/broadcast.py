from zeroconf import ServiceInfo, Zeroconf
import socket
import time

class ServiceBroadcaster:
    
    def __init__(self, port=5000):
        self.port = port

    def get_local_ip(self):
        """Get the local IP address of this machine"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Doesn't need to be reachable, just used to determine local IP
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def run(self):
        # Get local IP
        local_ip = self.get_local_ip()
        print(f"Local IP address: {local_ip}")
        
        # Service configuration
        service_type = "_lazy._tcp.local."
        service_name = "KylePC._lazy._tcp.local."
        port = self.port
        
        # Create zeroconf instance
        zeroconf = Zeroconf()
        
        # Create service info
        # The 'properties' dict can contain custom metadata about your service
        properties = {
            'version': '1.0',
            'description': 'Test server',
            'data_port': str(port)
        }
        
        info = ServiceInfo(
            service_type,
            service_name,
            addresses=[socket.inet_aton(local_ip)],
            port=port,
            properties=properties,
            server=f"{socket.gethostname()}.local."
        )
        
        print(f"\nAdvertising service:")
        print(f"  Service Type: {service_type}")
        print(f"  Service Name: {service_name}")
        print(f"  IP Address: {local_ip}")
        print(f"  Port: {port}")
        print(f"  Properties: {properties}")
        
        # Register the service
        print("\nRegistering service...")
        zeroconf.register_service(info)
        print("Service registered! Clients can now discover this server.")
        print("\nPress Ctrl+C to stop the server...\n")
        
        try:
            # Keep the service running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            print("Unregistering service...")
            zeroconf.unregister_service(info)
            zeroconf.close()
            print("Service stopped.")

if __name__ == "__main__":
    broadcaster = ServiceBroadcaster()
    broadcaster.run()