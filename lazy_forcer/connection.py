import socket
import json
from time import sleep
from enum import IntEnum
from lazy_socket.client import LazyClient


class Type(IntEnum):
    BINGO = 17777
    PULLTAB = 17778


class MachineType(IntEnum):
    UNKNOWN = -1
    NONE = 0
    EGM = 1
    POS = 2
    KIOSK = 3
    REPORTER = 4
    BIGSIGN = 5
    COMMUNITYSIGN = 6
    MANAGER = 7
    DBIN = 4848
    NEOSERVER = 8888


class Outcome:
    def __init__(self, pattern, match_in):
        self.pattern = pattern
        self.match_in = match_in


class Mailman:

    def __init__(self, address, port):
        self.host = address
        self.port = port
        self.ip = self.get_my_ip()

    def get_my_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            my_ip = s.getsockname()[0]
        except Exception as e:
            print(f"Error getting IP: {e}")
            my_ip = "0.0.0.0"
        finally:
            s.close()
        return my_ip

    def get_payload(self, outcome: Outcome, site_id: int, target_ip: str, type_: Type = Type.BINGO):
        payload = {
            "overwatchMT": type_,
            "identity": {
                "machine": {
                    "siteID": site_id,
                    "clientIP": self.ip,
                    "machineType": MachineType.NONE,
                },
                "sessionToken": "",
            },
            "pattern": {"pattern": outcome.pattern, "matchIn": outcome.match_in},
        }

        if target_ip:
            payload['machine'] = {
                "siteID": site_id,
                "clientIP": target_ip,
                "machineType": MachineType.EGM,
            }
        return json.dumps(payload).encode("utf-8")

    def force_outcomes(self, outcomes: list[Outcome], site_id: int, target_ip: str):
        if not outcomes:
            return
        
        client = LazyClient(self.host, self.port, reconnect=False)
        client.start()
        sleep(1)
        
        responses = 0
        while True:
            if client.queue.empty():
                sleep(0.1)
                continue

            message = client.queue.get()
            if "connected" in message:
                for outcome in outcomes:
                    payload = self.get_payload(outcome, site_id, target_ip)
                    client.send(payload)

            if "error" in message:
                print(f"Error: {message}")
                return False

            if "RNQueueForceBingoOutcome executed successfully" in message:
                responses += 1
            
            if responses >= len(outcomes):
                break
            
            sleep(0.1)
        client.stop()
        return True