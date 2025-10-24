import asyncio
import json
from asyncio.subprocess import PIPE
import paramiko

class Device:

    def __init__(self, ip, site, bv_type):
        self.ip = ip
        self.status = "Offline"
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            print(f"Connecting to {ip}...")
            self.client.connect(self.ip, username="Administrator", password="replay")
            self.status = "Online"
            print(f"Connected to {ip}.")
        except Exception as e:
            print(f"Failed to connect to {ip}: {e}")
        self.octet = ip.split(".")[-1]
        self.site = site
        self.bv_type = bv_type

    async def is_reachable(self):
        command = f"ping -n 1 {self.ip}"
        # print(command)
        proc = await asyncio.create_subprocess_shell(command, stdout=PIPE, stderr=PIPE)
        stdout, stderr = await proc.communicate()
        stdout = stdout.decode().lower()
        
        if proc.returncode != 0 or 'unreachable' in stdout or 'timed out' in stdout:
            self.status = "Offline"
            return False
        
        self.status = "Online"
        return True
    
    def serialize(self):
        return json.dumps({
            "ip": self.ip,
            "octet": self.octet,
            "site": self.site,
            "bv_type": self.bv_type,
            "status": self.status
        })

    def __str__(self):
        return f"EGM {self.octet}"


DEVICES = [
    Device(f"10.0.0.2", "Lab 1", "JcmUba"),
    Device(f"10.0.0.4", "Lab 1", "MeiCashflow"),
    Device(f"10.0.0.5", "Lab 1", "JcmUba"),
    Device(f"10.0.0.6", "Lab 1", "MeiCashflow"),
    Device(f"10.0.0.7", "Lab 1", "JcmUba"),
    Device(f"10.0.0.8", "Warehouse", "JcmUba"),
    Device(f"10.0.0.9", "Warehouse", "JcmUba"),
    Device(f"10.0.0.10", "Warehouse", "JcmUba"),
    Device(f"10.0.0.11", "Warehouse", "JcmUba"),
    Device(f"10.0.0.12", "Warehouse", "JcmUba"),
    Device(f"10.0.0.13", "Warehouse", "JcmUba"),
    Device(f"10.0.0.14", "Warehouse", "JcmUba"),
    Device(f"10.0.0.15", "Warehouse", "JcmUba"),
    Device(f"10.0.0.16", "Warehouse", "JcmUba"),
    # Device(f"10.0.0.17", "Warehouse", "JcmUba"),
    Device(f"10.0.0.18", "Warehouse", "MeiCashflow"),
    Device(f"10.0.0.19", "Warehouse", "MeiCashflow"),
    Device(f"10.0.0.20", "Warehouse", "MeiCashflow"),
    Device(f"10.0.0.21", "Warehouse", "MeiCashflow"),
    Device(f"10.0.0.22", "Warehouse", "MeiCashflow"),
    Device(f"10.0.0.23", "Warehouse", "MeiCashflow"),
    Device(f"10.0.0.24", "Warehouse", "MeiCashflow"),
    Device(f"10.0.0.25", "Warehouse", "MeiCashflow"),
    # Device(f"10.0.0.26", "Warehouse", "MeiCashflow"),
    Device(f"10.0.0.27", "Warehouse", "MeiCashflow"),
]

def get_device(ip):
    return next((d for d in DEVICES if d.ip == ip), None)