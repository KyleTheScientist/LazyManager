import json
import asyncio
from asyncio.subprocess import PIPE
from connection_manager import Agent


class EGM:

    def __init__(self, agent: Agent, **properties):
        self.agent = agent
        self.ip = agent.ip
        self.id = agent.id
        self.site = properties.get("site")
        self.bv_type = properties.get("bv_type")
        self.type = properties.get("type")
        self.lazy_egm_version = properties.get("lazy_egm_version", "unknown")
        self.last_seen = 0
        self.status = "Offline"

    async def is_reachable(self):
        command = f"ping -n 1 {self.ip}"
        proc = await asyncio.create_subprocess_shell(command, stdout=PIPE, stderr=PIPE)
        stdout, stderr = await proc.communicate()
        stdout = stdout.decode().lower()
        
        if proc.returncode != 0 or 'unreachable' in stdout or 'timed out' in stdout:
            self.status = "Offline"
            return False
        
        self.status = "Online"
        return True
    
    def serialize(self):
        return {
            "ip": self.ip,
            "id": self.id,
            "site": self.site,
            "type": self.type,
            "bv_type": self.bv_type,
            "status": self.status,
            "lazy_egm_version": self.lazy_egm_version
        }

    def __str__(self):
        return f"EGM {self.id}"