import time
import socket
import json
import subprocess
import pyautogui
from lazy_socket.server import LazyServer
from pathlib import Path

CONFIG_PATH = Path("lazy_egm.cfg")
VERSION = "1.0.1"


class EGM(LazyServer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.properties = self.load_config()
        self.properties["lazy_egm_version"] = VERSION
        self.properties["ip"] = self.get_ip()

    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def load_config(self):
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text())
        else:
            content = {
                "site": "lab/warehouse",
                "bv_type": "JcmUba/MeiCashflow",
                "type": "vertical/1600"
            }
            CONFIG_PATH.touch()
            CONFIG_PATH.write_text(json.dumps(content, indent=4))
            return content

    def serialize(self):
        result = "&".join([f"{k}={v}" for k, v in self.properties.items()])
        return result

    async def process_message(self, client, message):
        if message.startswith("manager:"):
            split = message.split(":")
            try:
                await self.run_manager_command(client, split[1])
            except Exception as e:
                print(f"Error processing manager command {split[1]}: {e}")
                await client.send(f"egm:result:{split[1]}:{str(e)}")

        if message.startswith("app:"):
            split = message.split(":")
            try:
                await self.run_app_command(client, split[1])
            except Exception as e:
                print(f"Error processing app command {split[1]}: {e}")
                await client.send(f"egm:result:{split[1]}:{str(e)}")

    async def run_manager_command(self, client, command):
        if command == "connected":
            await client.send(f"egm:register:{self.serialize()}")

        if command == "ping":
            await client.send(f"egm:pong")

    async def run_app_command(self, client, command):
        if command == "ping":
            await client.send(f"egm:result:pong:Success")

        elif command == "start_explorer":
            result = "Success" if self._try_run("explorer.exe", 1) else "Failure"
            await client.send(f"egm:result:start_explorer:{result}")

        elif command == "stop_automakro":
            result = "Success" if self._try_kill("AutoMakro.exe") else "Failure"
            await client.send(f"egm:result:stop_automakro:{result}")

        elif command == "start_automakro":
            result = "Success" if self._try_start("AutoMakro.exe", cwd="D:/AutoMakro") else "Failure"
            await client.send(f"egm:result:start_automakro:{result}")

        elif command == "stop_egmc":
            result = "Success" if self._try_kill("EGMController.exe", force=False) else "Failure"
            await client.send(f"egm:result:stop_egmc:{result}")

        elif command == "start_egmc":
            result = "Success" if self._try_start("EGMController.exe", cwd="D:/EGMController") else "Failure"
            await client.send(f"egm:result:start_egmc:{result}")

        elif command == "clear_ram":
            try:
                Path("E:/Storage").unlink(missing_ok=True)
                await client.send(f"egm:result:clear_ram:Success")
            except Exception as e:
                await client.send(f"egm:result:clear_ram:Failure")

        elif command == "f1":
            pyautogui.press("f1")
            await client.send(f"egm:result:f1:Success")

        elif command == "f2":
            pyautogui.hotkey('alt', 'tab', interval=0.2)
            await client.send(f"egm:result:alt_tab:Success")

        else:
            await client.send(f"egm:result:{command}:Unknown command")

    def _try_kill(self, process_name, force=True):
        command = f"taskkill {'/F' if force else ''} /IM {process_name}"
        print(command)
        result = subprocess.run(command, capture_output=True, shell=True)
        return result.returncode == 0 or result.returncode == 128

    def _try_start(self, process_path, cwd=None):
        print(process_path)
        result = subprocess.Popen(process_path, cwd=cwd, shell=True)
        time.sleep(2)
        return result.poll() is None

    def _try_run(self, command, rc=0):
        print(command)
        result = subprocess.run(command, capture_output=True, shell=True)
        print(result.returncode)
        return result.returncode == rc


if __name__ == "__main__":
    egm = EGM(name="LazyEGM", host="0.0.0.0", port=8765, broadcast=False)
    egm.start()
